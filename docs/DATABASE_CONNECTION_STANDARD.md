# Database Connection Standard

**Last Updated**: 2026-08-13
**Status**: ✅ Current — enforced by code; the plumbing below matches the container deploy

## 🎯 The Standard (Non-Negotiable)

### Connection URI: NO Database Name
```
✅ CORRECT:   mongodb+srv://user:pass@cluster.mongodb.net/
❌ INCORRECT: mongodb+srv://user:pass@cluster.mongodb.net/mydb
```

### Database Name: Separate Variable
```
DATABASE_NAME=auto_author_staging
```

### Why this is not merely style

A database name in the path becomes the driver's `defaultauthdb`, and
`authSource` **defaults to that** when it isn't given explicitly. Atlas users
live in `admin`, so `…mongodb.net/auto_author_staging` without an explicit
`?authSource=admin` authenticates against the wrong database and fails — which
looks exactly like a bad password, and is especially confusing during a
credential rotation.

The name in the path is also *ignored* by both services regardless, because each
selects its database explicitly (see "How it works"). So it can only do harm.

## 📋 Variable Naming Convention

| Context | Variable | Contains |
|---|---|---|
| `/opt/auto-author/.env` on the box | `MONGODB_URI` | Connection URI, **no** DB name |
| `/opt/auto-author/.env` on the box | `DATABASE_NAME` | Database name only |
| Backend container env | `MONGODB_URI`, `DATABASE_NAME` | Passed through by compose |
| Frontend container env | `DATABASE_URL`, `DATABASE_NAME` | `DATABASE_URL` is `MONGODB_URI` remapped |
| Python | `settings.MONGODB_URI` / `settings.DATABASE_NAME` | Read from env |

`DATABASE_URL` is the backend's **legacy fallback**, used only when `MONGODB_URI`
is empty (`backend/app/core/config.py:53`). New configuration should set
`MONGODB_URI`.

## 🔄 How it works

### 1. The box `.env` is the source of truth

Staging runs the container deploy (`.github/workflows/deploy-staging-containers.yml`),
which ships the compose files and runs `docker compose up`. **It writes no env
file.** The values come from `/opt/auto-author/.env`, maintained by hand on the
server.

There is a `MONGODB_URI` GitHub secret, but it is referenced only by
`deploy-staging.yml.disabled` — the retired PM2 deploy. Changing it does not
affect what staging connects with.

### 2. Compose passes it to both services

```yaml
# docker-compose.yml
backend:
  environment:
    MONGODB_URI: ${MONGODB_URI:?MONGODB_URI is required}
    DATABASE_NAME: ${DATABASE_NAME:?DATABASE_NAME is required}
frontend:
  environment:
    DATABASE_URL: ${MONGODB_URI:?MONGODB_URI is required}   # better-auth's name for it
    DATABASE_NAME: ${DATABASE_NAME:?DATABASE_NAME is required}
```

The `:?` form makes compose fail fast with a named error rather than starting a
container that dies at first query.

### 3. Each service selects the database explicitly

```python
# backend/app/db/base.py:33
_db = _client[settings.DATABASE_NAME]
```

```typescript
// frontend/src/lib/auth.ts:156 — better-auth's MongoDB adapter
db = client.db(dbName);   // dbName = process.env.DATABASE_NAME
```

Neither reads the database from the URI path. That is what makes the standard
enforceable rather than aspirational.

## ⚠️ Escaping the password

The URI goes into a dotenv file that compose reads **twice** — once literally for
`env_file:`, once with `${...}` interpolation for the `environment:` block, and
the interpolated value wins. Characters that break one path or the other:

| Character | Breaks |
|---|---|
| `$` | compose interpolation (would need `$$`) |
| `#` | dotenv — starts a comment, truncating the URI |
| space | dotenv parsing |
| `| & \` | the `sed` substitution in the legacy PM2 path |

**Percent-encode the password** and all of this goes away — `%XX` contains none
of these. `@` → `%40`, `/` → `%2F`, `%` → `%25`, `:` → `%3A`.

## 🔁 Rotating the password

1. Rotate the user in Atlas. **The old password dies immediately** — the running
   containers start failing on their next reconnect, not at the next deploy.
2. Percent-encode the new password into the URI.
3. Edit `MONGODB_URI` in `/opt/auto-author/.env` on the box.
4. Recreate the containers. Set `IMAGE_TAG` first — the staging overlay pins
   `image: ...:${IMAGE_TAG:?}`, and the tag is a per-deploy release id the
   workflow exports inline rather than writing to `.env`, so without it compose
   aborts during interpolation and the new password is never loaded. Reusing the
   running tag keeps this an env-only change:
   ```bash
   cd /opt/auto-author
   export IMAGE_TAG="$(docker ps --format '{{.Image}}' | sed -n 's#.*auto-author-backend:##p' | head -1)"
   echo "$IMAGE_TAG"   # expect sha-xxxxxxx; if empty, pass the tag explicitly
   docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d
   ```
   — **recreate, not restart**; a restarted container keeps its old environment.
5. Verify: `curl -s 127.0.0.1:8000/api/v1/health`. Since #333 this does a real
   Mongo ping, so bad credentials surface here as a 503 naming the component.

Optionally update the `MONGODB_URI` GitHub secret to keep the disabled PM2
workflow from holding a dead credential — but note that leaves a second copy of a
live credential with no consumer.

## 🚫 Common mistakes

### ❌ DON'T: put the database name in the URI
```python
# WRONG — becomes defaultauthdb, breaks Atlas auth, and is ignored anyway
MONGODB_URI = "mongodb+srv://user:pass@cluster.mongodb.net/mydb"
```

### ❌ DON'T: hardcode the database name
```python
_db = _client["auto_author_staging"]   # WRONG
_db = _client[settings.DATABASE_NAME]  # correct
```

### ❌ DON'T: assume the GitHub secret is what's running
The live deploy reads the box's `.env`. Confirm there before debugging further.

## 🔍 Verifying compliance

```bash
# On the box — key names and shape, password masked
sed -E 's|(//[^:]+:)[^@]+@|\1****@|' /opt/auto-author/.env | grep -E 'MONGODB_URI|DATABASE_NAME'

# Code still selects the DB explicitly
grep -n "DATABASE_NAME" backend/app/db/base.py frontend/src/lib/auth.ts
```

`MONGODB_URI` should end at the host (a trailing `/` is fine); anything after it
is a bug per this document.

## 📝 Examples

```bash
# Local development
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=auto_author_dev

# Staging (in /opt/auto-author/.env on the box)
MONGODB_URI=mongodb+srv://staging_user:pa%24%24word@cluster.mongodb.net/
DATABASE_NAME=auto_author_staging

# Tests — note TEST_MONGO_URI is the exception: it DOES carry the db name in
# the path, and backend/tests/conftest.py parses it from there.
TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test
```

## 🔒 Security notes

1. **Never commit** connection URIs to git; they live only in the box `.env`.
2. Use different credentials per environment.
3. Limit the database user's permissions — the app needs no admin rights.
4. Rotate periodically, following the runbook above.

---

**Related**: `.github/DEPLOYMENT.md` (which secrets each workflow uses),
`docs/STAGING-DEPLOYMENT.md` (box setup for the container deploy).
