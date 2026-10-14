# Deployment and Development Setup

**Stack**: Next.js (frontend) + FastAPI (backend) + MongoDB, authenticated with better-auth, deployed to a shared VPS as Docker containers behind nginx.

> The authoritative description of a deploy is `.github/workflows/deploy-staging-containers.yml`.
> If this document and that workflow ever disagree, the workflow is right — fix this file.
> Secrets, variables and the box `.env` keys are documented in [`.github/DEPLOYMENT.md`](.github/DEPLOYMENT.md).

---

## 🎯 Environments

| Stage | Where | How it is deployed |
|-------|-------|--------------------|
| **Local development** | Your machine | `npm run dev` + `uvicorn --reload` (below) |
| **Staging** | https://dev.autoauthor.app (API: https://api.dev.autoauthor.app) | `deploy-staging-containers.yml`, dispatched with an image tag (below) |
| **Production** | Not yet provisioned | — |

Staging runs on a **shared VPS** — other applications live on the same box. The
backend listens on `8000` and the frontend on `3002`, but check nginx for the
current truth before assuming a port is free.

---

## 🚀 Prerequisites

- **Node.js**: 24.x (`frontend/package.json` `engines`, CI and the image all use 24)
- **Python**: 3.13 or higher (`backend/pyproject.toml` sets `requires-python = ">=3.13"`)
- **uv**: Python package manager — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **MongoDB**: 7.x locally, or a MongoDB Atlas cluster for staging/production

There is no PostgreSQL and no Alembic migration chain in this project. MongoDB collections and indexes are created by the application at
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

`uv sync` installs from `uv.lock`, which is generated from `pyproject.toml`. That is
the only supported install path. The generated `requirements.txt` export was removed in
#534 — nothing installed from it, and keeping it in sync cost a manual regen on every
backend dependency PR.

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

Staging runs two containers (backend on `127.0.0.1:8000`, frontend on
`127.0.0.1:3002`) from images built in CI; nothing is built on the box.

1. A merge to `main` that touches `backend/`, `frontend/` or a compose file runs
   `build-images.yml`, which smoke-tests, scans and publishes
   `ghcr.io/frankbria/auto-author-backend:sha-<short>` and the frontend's
   `sha-<short>-staging`. The tag **is** the release id.
2. Deploy that tag:

   ```bash
   gh workflow run deploy-staging-containers.yml -f image_tag=sha-<short>
   ```

   The workflow joins Tailscale, copies the compose files to `/opt/auto-author`,
   pulls the images, runs `docker compose up -d` with `IMAGE_TAG` and
   `ENVIRONMENT=staging`, and waits for both containers to answer. Deploys are
   serialized (`concurrency: deploy-staging`).
3. A successful deploy triggers `e2e-staging-tests.yml`, with the specs from the
   commit the deploy was dispatched from (after a rollback to an older tag, those
   are newer than the build).

Application secrets come from `/opt/auto-author/.env` on the box. Only
`sync-staging-env.yml` writes to it, and only the `MONGODB_URI` key; see
[`.github/DEPLOYMENT.md`](.github/DEPLOYMENT.md).

### Rolling back

Dispatch the deploy with the previous tag:

```bash
gh workflow run deploy-staging-containers.yml -f image_tag=sha-<previous>
```

The workflow pulls the tag from GHCR, and its prune (after a healthy deploy)
removes only untagged images older than 14 days. Running compose by hand on the box, and its caveats, are in
`docs/STAGING-DEPLOYMENT.md` → Rolling back.

---

## 🔧 Troubleshooting

### Backend will not start

- **`BETTER_AUTH_SECRET` missing or weak** — deployed environments reject the repo's default and short values at startup by design; check the backend container's logs (`docker compose … logs backend`, see `docs/STAGING-DEPLOYMENT.md`). To confirm the box has the key without printing it, see `.github/DEPLOYMENT.md`.
- **MongoDB unreachable** — verify `MONGODB_URI`; for Atlas confirm the server's IP is on the cluster allowlist.
- **`ModuleNotFoundError`** — the venv is stale or was built from something other than the lockfile. Rebuild: `cd backend && uv sync`.

### CORS errors

`BACKEND_CORS_ORIGINS` accepts a plain comma-separated list or a JSON array.
Write it **comma-separated** in the box `.env`: a quoted JSON array
gets its quotes mangled by the dotenv reader into invalid JSON, which crashes
`Settings()` at startup. Verify with:

```bash
curl -s -D - -o /dev/null -X OPTIONS https://api.dev.autoauthor.app/api/v1/books \
  -H "Origin: https://dev.autoauthor.app" \
  -H "Access-Control-Request-Method: POST" | grep -i access-control-allow-origin
```

### Frontend build fails with "Cannot find module 'typescript'"

`NODE_ENV=production` makes `npm ci` skip devDependencies. Install with
`npm ci --include=dev`, as the image build does.

### Port already in use

**Identify the owner before touching it.** The staging box is shared, so a
process on 3002 is not necessarily ours:

```bash
lsof -i:3002 -sTCP:LISTEN        # who holds it — command, PID, user
docker ps --format '{{.Names}} {{.Ports}}'   # is it one of our containers?
```

If it is our container, restart it through compose (in `/opt/auto-author`, with
`IMAGE_TAG` and `ENVIRONMENT` exported) rather than signalling the PID.

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

- **Secrets, variables and box `.env` keys**: [`.github/DEPLOYMENT.md`](.github/DEPLOYMENT.md)
- **API documentation**: `/docs` on the running backend
- **Development guidelines**: `CLAUDE.md`
- **Quality gates & PR checklist**: `docs/references/quality-standards.md`
- **Changelog**: `docs/CHANGELOG.md`
