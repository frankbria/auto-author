# Deployment Configuration — GitHub Secrets

Secrets consumed by `.github/workflows/deploy-staging.yml` and
`.github/workflows/e2e-staging-tests.yml`. Every entry below was cross-checked
against those workflow files; nothing here is aspirational.

Configure at: `Settings` → `Secrets and variables` → `Actions`.

> **Scope matters.** The staging test credentials (`TEST_USER_EMAIL`,
> `TEST_USER_PASSWORD`) are **environment** secrets on the `staging`
> environment, not repository secrets — a workflow that reads them must declare
> `environment: staging` or it will silently receive empty strings.

---

## Required Secrets

### SSH & Server Access

| Secret | Description | Example |
|--------|-------------|---------|
| `SSH_KEY` | Private SSH key for server access | `-----BEGIN OPENSSH PRIVATE KEY-----…` |
| `HOST` | Server hostname or IP address | `195.35.14.177` |
| `USER` | SSH username | `root` |

### Application URLs

| Secret | Description | Example |
|--------|-------------|---------|
| `API_URL` | Backend API URL, including the version prefix | `https://api.dev.autoauthor.app/api/v1` |
| `FRONTEND_URL` | Frontend application URL | `https://dev.autoauthor.app` |

`FRONTEND_URL` is reused in five places by the deploy: the build-time
`NEXT_PUBLIC_BETTER_AUTH_URL`, the backend's `BETTER_AUTH_URL`, the backend's
`BACKEND_CORS_ORIGINS` (as its sole entry), the frontend's
`NEXT_PUBLIC_BETTER_AUTH_URL`, and the `__BETTER_AUTH_URL__` substitution in
`ecosystem.config.template.js`. Getting it wrong breaks auth and CORS together.

### Database (MongoDB)

| Secret | Description | Example |
|--------|-------------|---------|
| `MONGODB_URI` | MongoDB connection string — written to `.env` as `DATABASE_URL` | `mongodb+srv://user:pass@cluster.mongodb.net` |
| `DATABASE_NAME` | Database name | `auto_author_staging` |

Staging uses MongoDB Atlas. When the server's IP changes, add the new address to
the Atlas allowlist or every deploy health-check will fail.

### Authentication (better-auth)

| Secret | Description | Example |
|--------|-------------|---------|
| `BETTER_AUTH_SECRET` | Shared HS256 JWT secret, used by **both** backend and frontend | 64+ char random string |

Generate with:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(64))'
```

**This one is not optional.** The backend validates it at startup and refuses to
boot on a missing, default, or weak value — a deploy without it fails the
backend health check. The frontend must receive the identical value or every
issued token fails verification.

### OpenAI

| Secret | Description | Example |
|--------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key. Written to the backend `.env` twice, as `OPENAI_API_KEY` and `OPENAI_AUTOAUTHOR_API_KEY`. | `sk-proj-…` |

Get from: https://platform.openai.com/api-keys

---

## Recommended Secrets

Deploys succeed without these, but the corresponding feature is silently
degraded — which is worse than a loud failure. Set them.

### Transactional Email (password reset — #332)

| Secret | Description | Example |
|--------|-------------|---------|
| `EMAIL_SERVICE_PROVIDER` | `resend` (recommended) or `sendgrid` | `resend` |
| `EMAIL_SERVICE_API_KEY` | API key for that provider | `re_…` |
| `EMAIL_FROM_ADDRESS` | Verified sender address | `noreply@autoauthor.app` |

Unset, the reset flow still renders "Check your email" and sends nothing —
account recovery is dead with no error anywhere.

### Error Tracking (#334)

| Secret | Description | Notes |
|--------|-------------|-------|
| `SENTRY_DSN_BACKEND` | Backend Sentry DSN | Empty ⇒ Sentry off |
| `SENTRY_DSN_FRONTEND` | Frontend Sentry DSN | Inlined into the client bundle at build time; a DSN is designed to be public |

### Staging E2E Test Account

| Secret | Description | Notes |
|--------|-------------|-------|
| `TEST_USER_EMAIL` | Real staging account the E2E suite signs in as | Also written to the backend as `E2E_EXEMPT_EMAILS`, exempting it from rate limits / AI quota / entitlement checks. Fenced to non-production in code. |
| `TEST_USER_PASSWORD` | Password for that account | Used only by `e2e-staging-tests.yml` |

Both are **`staging` environment** secrets — see the note at the top.

---

## Optional Secrets

### AWS (S3 storage and transcription)

| Secret | Description | Example |
|--------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key ID | `AKIA…` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key | `wJalrXUtnFEMI/…` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `AWS_S3_BUCKET` | S3 bucket name | `auto-author-uploads` |

> ⚠️ These are written to the **backend** `.env` only. Never expose an AWS
> credential to the frontend under a `NEXT_PUBLIC_` name — Next.js inlines those
> into the client bundle at build time, publishing the secret to every visitor.

### Cloudinary (image storage)

| Secret | Description | Example |
|--------|-------------|---------|
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name | `your-cloud-name` |
| `CLOUDINARY_API_KEY` | Cloudinary API key | `123456789012345` |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret | `abcdefghijklmnopqrstuvwxyz` |

### Notifications (E2E failures)

| Secret | Description |
|--------|-------------|
| `SLACK_WEBHOOK_URL` | Slack incoming webhook for staging E2E failure alerts |
| `DISCORD_WEBHOOK_URL` | Discord webhook for the same |

### `BYPASS_AUTH`

Not a secret you should ever set. The deploy workflow reads it purely to **abort
the deploy** if it is `true`, and the backend hard-blocks it in production
regardless.

---

## Environment Files the Workflow Creates

### Backend: `/opt/auto-author/current/backend/.env`

```bash
# Database
DATABASE_URL=<MONGODB_URI>
DATABASE_NAME=<DATABASE_NAME>

# CORS — plain comma-separated origins, NOT a JSON array.
# A quoted JSON array gets its quotes mangled by the dotenv reader into invalid
# JSON, crashing Settings() at startup.
BACKEND_CORS_ORIGINS=<FRONTEND_URL>

# OpenAI
OPENAI_API_KEY=<OPENAI_API_KEY>
OPENAI_AUTOAUTHOR_API_KEY=<OPENAI_API_KEY>

# Error tracking — empty => Sentry off
SENTRY_DSN=<SENTRY_DSN_BACKEND>

# Better Auth
BETTER_AUTH_SECRET=<BETTER_AUTH_SECRET>
BETTER_AUTH_URL=<FRONTEND_URL>
BETTER_AUTH_ISSUER=better-auth

# API
API_V1_PREFIX=/api/v1

# E2E account exempt from rate limit / AI quota / entitlement
E2E_EXEMPT_EMAILS=<TEST_USER_EMAIL>

# AWS (optional)
AWS_ACCESS_KEY_ID=<AWS_ACCESS_KEY_ID>
AWS_SECRET_ACCESS_KEY=<AWS_SECRET_ACCESS_KEY>
AWS_REGION=<AWS_REGION>
AWS_S3_BUCKET=<AWS_S3_BUCKET>

# Cloudinary (optional)
CLOUDINARY_CLOUD_NAME=<CLOUDINARY_CLOUD_NAME>
CLOUDINARY_API_KEY=<CLOUDINARY_API_KEY>
CLOUDINARY_API_SECRET=<CLOUDINARY_API_SECRET>
```

### Frontend: `/opt/auto-author/current/frontend/.env.production`

```bash
NODE_ENV=production
NEXT_PUBLIC_API_URL=<API_URL>
NEXT_PUBLIC_BETTER_AUTH_URL=<FRONTEND_URL>
BETTER_AUTH_SECRET=<BETTER_AUTH_SECRET>
DATABASE_URL=<MONGODB_URI>
DATABASE_NAME=<DATABASE_NAME>
NEXT_PUBLIC_ENVIRONMENT=staging
PORT=3002
EMAIL_SERVICE_PROVIDER=<EMAIL_SERVICE_PROVIDER>
EMAIL_SERVICE_API_KEY=<EMAIL_SERVICE_API_KEY>
EMAIL_FROM_ADDRESS=<EMAIL_FROM_ADDRESS>
NEXT_PUBLIC_SENTRY_DSN=<SENTRY_DSN_FRONTEND>
```

Only `NEXT_PUBLIC_*` entries reach the browser. Everything else on this list is
read server-side by `next start`.

---

## Verification

1. Confirm the workflow file: `.github/workflows/deploy-staging.yml`
2. Trigger a deploy: merge to `main` (deploys after "Tests and Quality Checks" passes) or run `gh workflow run deploy-staging.yml`
3. Watch it: GitHub Actions → **Deploy to Staging**
4. The workflow health-checks the backend, the frontend, CORS headers, and `/docs` — a green run means all four passed

---

## Troubleshooting

### Deployment fails with "connection refused" or an SSH timeout

- Verify `SSH_KEY`, `HOST`, `USER`.
- The staging host runs fail2ban in aggressive mode and bans bursty CI connections. The upload step already retries 3× with a 60s cool-down; if it still fails, check whether the runner IP is banned on the server.

### Backend health check fails

- `BETTER_AUTH_SECRET` unset or weak — the app deliberately refuses to start.
- MongoDB unreachable — check `MONGODB_URI` and the Atlas IP allowlist.
- `pm2 logs auto-author-backend --lines 50`
- Inspect the generated file: `cat /opt/auto-author/current/backend/.env`

### Frontend health check fails

- `pm2 logs auto-author-frontend --lines 50`
- "Cannot find module 'typescript'" ⇒ devDependencies were skipped; the workflow uses `npm ci --include=dev` for this reason.
- `netstat -tulpn | grep 3002` — the VPS is shared, so the port may belong to another app.

### CORS errors

- `BACKEND_CORS_ORIGINS` must contain `FRONTEND_URL` and must not be a quoted JSON array (see above).
- `curl -I -X OPTIONS <API_URL>/books -H "Origin: <FRONTEND_URL>"`

### Password reset does nothing

`EMAIL_SERVICE_*` secrets are unset. The UI reports success either way.

---

## Security Practices

1. **Never prefix a secret with `NEXT_PUBLIC_`** — Next.js inlines those into the client bundle at build time. `scripts/check-secrets.sh` blocks commits that introduce one.
2. Rotate secrets periodically, and immediately after any suspected exposure.
3. Use different values per environment; never share staging and production secrets.
4. `BETTER_AUTH_SECRET` must be rotated on **both** frontend and backend simultaneously — a mismatch invalidates every session.
5. Never enable `BYPASS_AUTH` in a deployed environment. Production blocks it in code; the deploy workflow aborts on it.
