# Staging Deployment Guide

**Last Updated**: 2026-08-13
**Deploy path**: containers, live since 2026-08-12 (#484)

Staging is https://dev.autoauthor.app (frontend) and https://api.dev.autoauthor.app
(backend). It runs as Docker containers on a **shared VPS** — other applications
live on the same box, so every step here is a check, not an assumption.

> The PM2/rsync deploy this replaced (build-on-the-VPS, `releases/<id>` symlinked
> to `current`) is retired. Its workflow is kept as `deploy-staging.yml.disabled`
> for rollback; see [Falling back to PM2](#falling-back-to-pm2).

---

## Architecture

```
Shared VPS
├── nginx (:80/:443, TLS termination + security headers; CORS itself comes
│         from the backend's CORSMiddleware / BACKEND_CORS_ORIGINS)
│   ├── dev.autoauthor.app      → 127.0.0.1:3002  (frontend container)
│   └── api.dev.autoauthor.app  → 127.0.0.1:8000  (backend container)
├── /opt/auto-author/
│   ├── docker-compose.yml            shipped by the deploy
│   ├── docker-compose.staging.yml    shipped by the deploy
│   └── .env                          NOT shipped — hand-maintained secrets
└── MongoDB: Atlas (external, IP-allowlisted)
```

Images are built in CI by `build-images.yml` and published to GHCR as
`sha-<short>` and `staging`. The **image tag is the release identifier** — there
is no release directory.

### Network exposure (#189)

The box is shared, so only nginx may face the internet:

- **Loopback binding (primary)** — both containers publish to loopback only:
  `127.0.0.1:8000:8000` and `127.0.0.1:3002:3002` in `docker-compose.yml`. A bare
  `8000:8000` would expose the app on the public interface past nginx's TLS and
  headers; don't.
- **Host firewall (defense in depth)** — ufw is active, default-deny inbound,
  only 22/80/443 allowed. Verified 2026-07-10: off-box `curl` to `:8000` and
  `:3002` times out while `https://dev.autoauthor.app` serves normally.
- **Verify after a deploy** — `ss -tlnp | grep -E ':8000|:3002'` must show only
  `127.0.0.1` binds.

---

## The box `.env` is the source of truth

`/opt/auto-author/.env` carries every application secret. **No workflow writes
it.** The deploy ships compose files and runs `docker compose up`; the values
come from that file.

Compose asserts the required ones with `${VAR:?...}`, so a missing key fails the
deploy with a named error instead of starting a container that dies at first
query:

```
MONGODB_URI, DATABASE_NAME, BETTER_AUTH_SECRET, OPENAI_API_KEY
```

Everything else in the file is passed through wholesale via `env_file:` — the app
also needs `AWS_*`, `CLOUDINARY_*`, `BETTER_AUTH_ISSUER` and
`BACKEND_CORS_ORIGINS`, which an explicit allowlist would have silently dropped.

Editing a value requires **recreating** the containers, not restarting them:

```bash
cd /opt/auto-author
# The staging overlay pins image: ...:${IMAGE_TAG:?}, so `up -d` needs IMAGE_TAG.
# It is a per-deploy release id the workflow exports inline (never written to
# .env), so it is absent in a manual shell — without it compose aborts during
# interpolation and nothing is recreated. Reuse the tag already running, so an
# env-only change does not also move the release:
export IMAGE_TAG="$(docker ps --format '{{.Image}}' | sed -n 's#.*auto-author-backend:##p' | head -1)"
echo "$IMAGE_TAG"   # expect sha-xxxxxxx; if empty, pass the tag explicitly
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d
```

Database values have their own rules (no db name in the URI, percent-encode the
password, rotation runbook): `docs/DATABASE_CONNECTION_STANDARD.md`.

---

## One-time setup on the box

1. **Ports.** Confirm 8000 and 3002 are free, or held only by this app:
   `sudo ss -ltnp | grep -E ':(8000|3002)'`
2. **Docker.** Daemon installed and running; note containers belonging to other
   applications: `docker ps -a`
3. **Directory.** `mkdir -p /opt/auto-author`, then place the two compose files
   and the `.env`. Secrets live only in that file — never baked into an image.
4. **Registry access.** If the GHCR packages are private, `docker login ghcr.io`
   with a token carrying `read:packages`.
5. **nginx.** Upstreams point at `127.0.0.1:8000` / `127.0.0.1:3002`. Unchanged
   from the PM2 setup — which is why those ports were kept.

---

## Deploying

> **Gate before the first deploy carrying better-auth 1.7 (#556).** 1.7 made
> `account.issuer` required and keys accounts on `(issuer, accountId)`. Every
> account row written by 1.6 lacks that field, so **sign-in returns 401 for the
> entire existing user base** the moment 1.7 goes out. CI cannot catch this — the
> E2E suite creates its users fresh, and accounts created *on* 1.7 work fine.
>
> Password *reset* is worse than a 401: it succeeds and creates a **second**
> credential account, so each rescued user leaves behind two rows that then
> collide on the new unique key and need reconciling by hand. That is the reason
> this runs before the deploy rather than as a repair after it.
>
> Run the backfill **before** deploying, in a window with authentication writes
> stopped and the `account` and `user` collections backed up. Both containers get
> the same database — compose feeds `MONGODB_URI` to the backend and the identical
> value to the frontend as `DATABASE_URL` — so the backend container's own env
> already points at the collections better-auth writes, and the command takes no
> arguments:
>
> ```bash
> # dry run first — it is the default and writes nothing
> docker compose exec backend python -m app.scripts.migration_account_issuer
> # then, once the counts read right:
> docker compose exec backend python -m app.scripts.migration_account_issuer --apply
> ```
>
> Two things that bite here. `python`, not `uv run`: the runtime image ships
> `/app/.venv` on `PATH` but neither `uv` nor `pyproject.toml`. And do **not**
> spell the connection out as `--mongodb-uri "$MONGODB_URI"` — under
> `docker compose exec` your *host* shell expands that, where the variable is
> unset, and the gate would run against an empty string. The script reads the
> container's own environment; `--mongodb-uri` / `--database` exist only for a
> database the backend's settings do not point at.
>
> Exit codes: `0` done, `1` refused (read the message — an identity collision
> needs manual reconciliation), `2` could not connect. It is idempotent, so
> re-running the dry run afterwards should report `issuer_backfilled: 0`. Full
> runbook in the script's docstring. Acceptance test: an account created under 1.6
> still signs in.

Trigger **Deploy Staging (Containers)** via workflow dispatch with an explicit
`image_tag` (e.g. `sha-3931169`) published by `build-images.yml`. The workflow:

1. connects over Tailscale (#485, #489) and ships the two compose files by `scp`,
   retrying with a cool-down — first SSH contact on this box intermittently gets
   dropped during host-key discovery (#162);
2. `docker compose … pull` then `up -d --remove-orphans` — `pull` always goes to
   the registry, so re-running the same tag still picks up a rebuilt image
   instead of reusing a stale local layer;
3. polls `/api/v1/health` and `/` for up to 150s, dumping the last 60 log lines
   and failing the job if either never returns 200;
4. prunes images older than 14 days — deliberately **after** the health check, so
   a rollback target is never deleted first.

`concurrency: deploy-staging` with `cancel-in-progress: false` means two deploys
can never race on the box.

### Verifying

```bash
curl -s 127.0.0.1:8000/api/v1/health          # real dependency checks since #333
curl -s -o /dev/null -w '%{http_code}\n' 127.0.0.1:3002/
curl -s -o /dev/null -w '%{http_code}\n' https://dev.autoauthor.app/
```

`/health` pings Mongo and asserts required secrets are present, so a
misconfigured release returns 503 naming the failing component rather than a
misleading 200. The staging E2E suite (`npm run test:e2e:staging`) uses real auth
and is the check that actually exercises the deployed stack.

### Rolling back

Re-run the deploy with an earlier tag. That is the whole procedure:

```bash
cd /opt/auto-author
IMAGE_TAG=sha-<previous> docker compose \
  -f docker-compose.yml -f docker-compose.staging.yml up -d
```

---

## Troubleshooting

**Compose exits with `MONGODB_URI is required`** — the box `.env` is missing that
key, or the deploy is running from a directory without it. This is the assertion
working; check `/opt/auto-author/.env`.

**Backend health 503** — read the `checks` object in the response body; it names
the failing component. Mongo failures are usually a rotated password not yet
written to the box `.env`, or a VPS IP that left the Atlas allowlist.

**Ports already in use** — `sudo ss -ltnp | grep -E ':(8000|3002)'`. Shared box:
confirm the holder is ours before killing anything.

**Container up but serving stale code** — the tag was reused. Deploy an explicit
`sha-` tag rather than `staging`.

**Logs**

```bash
cd /opt/auto-author
docker compose -f docker-compose.yml -f docker-compose.staging.yml logs --tail=100 backend
docker compose -f docker-compose.yml -f docker-compose.staging.yml ps
```

---

## Falling back to PM2

The retired path still exists: `deploy-staging.yml.disabled` regenerates
`/opt/auto-author/current/backend/.env` and `frontend/.env.production` **from
GitHub secrets** on every run, and manages processes with PM2. To use it, stop
the containers first (`docker compose … down`), then re-enable the workflow.

Two differences that bite:

- it writes the connection string under the key `DATABASE_URL`, not
  `MONGODB_URI` — the backend accepts both, preferring `MONGODB_URI`;
- its secret values are whatever is in GitHub, which may have drifted from the
  box `.env` that the containers have been using.

Remove this path (and the `MONGODB_URI` / `DATABASE_NAME` GitHub secrets, and the
PM2 ecosystem template) once containers have run without a rollback long enough
to trust — #427 AC 8.

---

## Maintenance

**Weekly** — review container logs for errors, check disk space (images
accumulate), confirm Atlas backups.
**Monthly** — `apt update && apt upgrade` on the box; review the image prune
window.
**As needed** — re-check the Atlas IP allowlist after any VPS network change.

---

**Related**: `.github/DEPLOYMENT.md` (which workflow reads which secret),
`docs/DATABASE_CONNECTION_STANDARD.md` (DB values and rotation).
