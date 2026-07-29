# Deployment and Development Setup

**Stack**: Next.js (frontend) + FastAPI (backend) + MongoDB, authenticated with better-auth, deployed to a shared VPS under PM2 behind nginx.

> The authoritative description of a deploy is `.github/workflows/deploy-staging.yml`.
> If this document and that workflow ever disagree, the workflow is right — fix this file.
> GitHub Secrets required by the workflow are documented in [`.github/DEPLOYMENT.md`](.github/DEPLOYMENT.md).

---

## 🎯 Environments

| Stage | Where | How it is deployed |
|-------|-------|--------------------|
| **Local development** | Your machine | `npm run dev` + `uvicorn --reload` (below) |
| **Staging** | https://dev.autoauthor.app (API: https://api.dev.autoauthor.app) | `deploy-staging.yml`, automatically after "Tests and Quality Checks" passes on `main` |
| **Production** | Not yet provisioned | — |

Staging runs on a **shared VPS** — other applications live on the same box. The
backend listens on `8000` and the frontend on `3002`, but check nginx for the
current truth before assuming a port is free.

---

## 🚀 Prerequisites

- **Node.js**: 20.x (CI tests on 20; the deploy workflow currently builds on 18)
- **Python**: 3.13 or higher (`backend/pyproject.toml` sets `requires-python = ">=3.13"`)
- **uv**: Python package manager — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **MongoDB**: 7.x locally, or a MongoDB Atlas cluster for staging/production

There is no PostgreSQL, no Docker image, and no Alembic migration chain in this
project. MongoDB collections and indexes are created by the application at
startup.

---

## 📦 Installation

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local     # then fill in the values
```

### Backend

```bash
cd backend
uv sync --extra test           # `uv sync` alone omits the test tooling
cp .env.example .env           # then fill in the values
```

`uv sync` installs from `uv.lock`, which is generated from `pyproject.toml`.
`requirements.txt` is a generated export kept for tooling that cannot read a
lockfile — never hand-edit it, and never install from it in preference to
`uv sync` (see #383).

---

## 🏃 Development

Start MongoDB first — most backend tests and all real API calls need it.

Each server runs in the foreground, so give them **separate terminals**, both
starting from the repository root:

```bash
# Terminal 1 — frontend, http://localhost:3002
cd frontend && npm run dev

# Terminal 2 — backend, http://localhost:8000, docs at /docs
cd backend && uv run uvicorn app.main:app --reload --port 8000
```

---

## 🧪 Testing

```bash
# Frontend
cd frontend
npm test
npm run test:coverage

# Backend
cd backend
uv run pytest
uv run pytest --cov=app tests/ --cov-report=term-missing

# E2E (Playwright, against a local stack)
cd frontend && npx playwright test --ui
```

Coverage floor is 85%. CI is the real gate — see `docs/references/quality-standards.md`.

---

## 🔍 Code Quality

```bash
# Frontend
cd frontend
npm run typecheck
npm run lint          # `npm run lint -- --fix` to auto-fix

# Backend
cd backend
uv run ruff format .
uv run ruff check .
uv run mypy app/
```

---

## 🔐 Environment Variables

The complete, commented lists live in **`backend/.env.example`** and
**`frontend/.env.example`**. Those files are the source of truth; the tables
below are orientation only.

### Backend (`backend/.env`)

| Variable | Required | Notes |
|----------|----------|-------|
| `DATABASE_URL` | ✅ | MongoDB connection string (`mongodb://…` or `mongodb+srv://…`) |
| `DATABASE_NAME` | ✅ | e.g. `auto_author` |
| `BETTER_AUTH_SECRET` | ✅ | Shared HS256 JWT secret; must match the frontend value exactly. **Production refuses to start without it. Staging does not** — it falls back to the committed CI test secret, so an unconfigured staging boots happily on a publicly-known signing key. Always set it explicitly. Generate: `python -c 'import secrets; print(secrets.token_urlsafe(64))'` |
| `BETTER_AUTH_URL` | ✅ | Base URL of the frontend |
| `BETTER_AUTH_ISSUER` | ✅ | `better-auth` |
| `OPENAI_AUTOAUTHOR_API_KEY` | ✅ | OpenAI key |
| `BACKEND_CORS_ORIGINS` | ✅ | Comma-separated origins, or a JSON array. See the caveat under "CORS" below. |
| `API_V1_PREFIX` | | Defaults to `/api/v1` |
| `SENTRY_DSN` | | Empty ⇒ Sentry off |
| `AWS_*`, `CLOUDINARY_*` | | Optional storage/transcription backends |

### Frontend (`frontend/.env.local` / `.env.production`)

| Variable | Required | Notes |
|----------|----------|-------|
| `NEXT_PUBLIC_API_URL` | ✅ | Backend API base URL |
| `NEXT_PUBLIC_BETTER_AUTH_URL` | ✅ | Base URL for better-auth endpoints |
| `BETTER_AUTH_SECRET` | ✅ | Server-side only. Must equal the backend value. |
| `DATABASE_URL`, `DATABASE_NAME` | ✅ | better-auth writes its session/user collections directly |
| `EMAIL_SERVICE_PROVIDER`, `EMAIL_SERVICE_API_KEY`, `EMAIL_FROM_ADDRESS` | staging/prod | Without these, password reset **silently no-ops** — the UI reports success and no mail is sent (#332) |
| `NEXT_PUBLIC_SENTRY_DSN` | | Inlined at build time; empty ⇒ Sentry off |

### ⚠️ Never put a secret behind `NEXT_PUBLIC_`

Next.js **inlines every `NEXT_PUBLIC_*` variable into the client bundle at build
time**. Anything with that prefix is readable by every visitor via View Source —
it is public by definition, not merely "exposed to the browser at runtime".

Concretely: **AWS credentials belong in the backend `.env` only**
(`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`), which is where the deploy
workflow writes them. There is no supported configuration in which
`NEXT_PUBLIC_AWS_SECRET_ACCESS_KEY` (or any other `NEXT_PUBLIC_` secret) is
correct. `scripts/check-secrets.sh` rejects commits that introduce one.

The same rule covers `BETTER_AUTH_SECRET`, `OPENAI_AUTOAUTHOR_API_KEY`, and
`CLOUDINARY_API_SECRET` — all server-side only. Note that `BYPASS_AUTH` is
likewise deliberately *not* `NEXT_PUBLIC_`.

---

## 🚢 Deploying to Staging

Deploys are automated. `.github/workflows/deploy-staging.yml` runs when the
"Tests and Quality Checks" workflow succeeds on `main`, or on manual
`workflow_dispatch`. Deploys are serialized (`concurrency: deploy-staging`) so
two merges a minute apart cannot overlap SSH bursts on the shared box.

What the workflow does, in order:

1. Checks out **the exact commit that passed tests** (`workflow_run.head_sha`), not current `main`.
2. Builds the frontend on the runner to fail fast on build errors.
3. `rsync` + `tar` a deployment package and `scp` it to the server (retried 3× — the host's fail2ban is aggressive).
4. Refuses to continue if `BYPASS_AUTH` is set to `true` in the deployment environment.
5. Over SSH, on the server:
   - unpacks into `/opt/auto-author/releases/<timestamp>/`
   - `uv venv && uv sync` for the backend
   - writes `backend/.env` and `frontend/.env.production` from GitHub Secrets
   - `npm ci --include=dev && npm run build` (dev deps are needed — `next build` loads `next.config.ts` via typescript)
   - flips `/opt/auto-author/current` to the new release **atomically** (`ln -snf` + `mv -Tf`)
   - renders `ecosystem.config.template.js` → `ecosystem.config.js` and restarts both PM2 apps
   - health-checks `localhost:8000/api/v1/health` and `localhost:3002` with retries
   - prunes all but the 5 most recent releases
6. Re-checks health, CORS headers, and `/docs` from outside.

### Manual re-deploy

```bash
gh workflow run deploy-staging.yml
```

Prefer this over hand-running commands on the server. There is intentionally no
standalone deploy script in `scripts/` — the workflow is the single deploy path,
and a second one drifts (the previous `scripts/deploy.sh` and
`deploy-fixed.sh` were removed for exactly this reason: they still configured
Clerk, long after the migration to better-auth).

### On the server

```bash
pm2 list
pm2 logs auto-author-backend --lines 50
pm2 logs auto-author-frontend --lines 50

readlink -f /opt/auto-author/current    # which release is live
ls -t /opt/auto-author/releases          # available releases
```

To roll back, point the symlink at a previous release and restart PM2:

```bash
ln -snf /opt/auto-author/releases/<previous> /opt/auto-author/current.tmp
mv -Tf /opt/auto-author/current.tmp /opt/auto-author/current
cd /opt/auto-author/current && pm2 restart ecosystem.config.js
```

---

## 🔧 Troubleshooting

### Backend will not start

- **`BETTER_AUTH_SECRET` missing or weak** — production rejects default/short values at startup by design; check `pm2 logs auto-author-backend`. In staging the same condition does *not* raise, so a backend that starts fine may still be running on the repo's CI default — confirm the value was actually written (see `.github/DEPLOYMENT.md` for a check that does not print it).
- **MongoDB unreachable** — verify `DATABASE_URL`; for Atlas confirm the server's IP is on the cluster allowlist.
- **`ModuleNotFoundError`** — the venv is stale or was built from something other than the lockfile. Rebuild: `cd backend && uv sync`.

### CORS errors

`BACKEND_CORS_ORIGINS` accepts a plain comma-separated list or a JSON array. The
deploy workflow writes it **comma-separated on purpose**: a quoted JSON array
gets its quotes mangled by the dotenv reader into invalid JSON, which crashes
`Settings()` at startup. Verify with:

```bash
curl -s -D - -o /dev/null -X OPTIONS https://api.dev.autoauthor.app/api/v1/books \
  -H "Origin: https://dev.autoauthor.app" \
  -H "Access-Control-Request-Method: POST" | grep -i access-control-allow-origin
```

### Frontend build fails with "Cannot find module 'typescript'"

`NODE_ENV=production` makes `npm ci` skip devDependencies. Install with
`npm ci --include=dev`, as the workflow does.

### Port already in use

**Identify the owner before touching it.** The staging box is shared, so a
process on 3002 is not necessarily ours:

```bash
lsof -i:3002 -sTCP:LISTEN        # who holds it — command, PID, user
pm2 list                          # is it one of our PM2 apps?
```

If it is our app, restart it through PM2 rather than signalling the PID:

```bash
pm2 restart auto-author-frontend
```

If it belongs to something else, leave it alone and pick a different port —
never blanket-kill by port number on a shared host.

---

## 🔐 Security Audits

Supply-chain advisories are gated in CI against a baseline ledger, so only *new*
advisories fail the build:

Run from the repository root — the subshells keep each `cd` from leaking into
the next command:

```bash
(cd backend && uv export --no-dev --no-emit-project --format requirements-txt > /tmp/reqs.txt \
  && uvx pip-audit -r /tmp/reqs.txt --format=json > /tmp/pip-audit.json)

(cd frontend && npm audit --json > /tmp/npm-audit.json)

python scripts/audit_gate.py --pip-audit /tmp/pip-audit.json \
  --npm-audit /tmp/npm-audit.json --baseline security-baseline.json
```

Both audit tools exit non-zero when they find advisories, which is the normal
case here — `audit_gate.py` decides pass/fail against the baseline.

Adding a dependency that carries a new advisory means either fixing it or
adding it to `security-baseline.json` with a stated reason.

---

## 📚 Additional Resources

- **GitHub Secrets required for deploys**: [`.github/DEPLOYMENT.md`](.github/DEPLOYMENT.md)
- **API documentation**: `/docs` on the running backend
- **Development guidelines**: `CLAUDE.md`
- **Quality gates & PR checklist**: `docs/references/quality-standards.md`
- **Changelog**: `docs/CHANGELOG.md`
