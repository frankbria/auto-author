# Deployment Configuration — Secrets, Variables and the Box `.env`

What each live workflow in `.github/workflows/` reads from GitHub, and which
application values live on the staging box instead. Every entry below was
cross-checked against those files and `docker-compose.yml`; nothing here is
aspirational.

Configure GitHub values at: `Settings` → `Secrets and variables` → `Actions`, or
under `Settings` → `Environments` → `staging` for environment-scoped ones.

> ### ⚠️ Application secrets live on the box, and one workflow writes one of them
>
> Staging is the container deploy (#484). `deploy-staging-containers.yml` ships
> the compose files and runs `docker compose up` — **it writes no env file**.
> Every application secret (`MONGODB_URI`, `DATABASE_NAME`, `BETTER_AUTH_SECRET`,
> `OPENAI_API_KEY`, Stripe, AWS, Cloudinary, …) is read from
> `/opt/auto-author/.env` **on the server**, which is maintained by hand.
>
> **The one exception is `MONGODB_URI`.** `sync-staging-env.yml` (manual
> dispatch, #537) writes the `staging` environment secret `MONGODB_URI` into
> that file in place, leaving a timestamped `.env.bak.*` beside it and every
> other key untouched, then (unless dispatched with `recreate=false`) recreates
> the containers on the running tag. Dispatching it with a
> stale secret puts the stale credential on the box.
>
> No other GitHub secret named after an application value is read by anything.
> **Changing one does not change what staging is running.** See
> `docs/STAGING-DEPLOYMENT.md` for the box setup and
> `docs/DATABASE_CONNECTION_STANDARD.md` for the database values.

> **Scope matters.** The staging test credentials (`TEST_USER_EMAIL`,
> `TEST_USER_PASSWORD`) and `MONGODB_URI` are **environment** secrets on the
> `staging` environment, not repository secrets — a workflow that reads them
> must declare `environment: staging` or it will silently receive empty strings.

---

## Which workflow uses what

| Workflow | Reads |
|---|---|
| `deploy-staging-containers.yml` | `TS_CLIENT_ID`, `TS_AUTH_SECRET`, `SSH_KEY`, `USER`, `STAGING_TS_HOST` (falls back to `HOST`) |
| `sync-staging-env.yml` | the same server-access secrets, plus `MONGODB_URI` (staging environment) |
| `build-images.yml` | `GITHUB_TOKEN` (automatic); staging environment **variables** `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_BETTER_AUTH_URL`, `NEXT_PUBLIC_SENTRY_DSN` |
| `e2e-staging-tests.yml` | `TEST_USER_EMAIL`, `TEST_USER_PASSWORD` (staging environment) |
| `staging-health.yml` | nothing — public URLs only |
| `glm-review.yml` | `ZHIPU_API_KEY` |

---

## Server access (GitHub secrets)

| Secret | Description | Example |
|--------|-------------|---------|
| `SSH_KEY` | Private SSH key for server access | `-----BEGIN OPENSSH PRIVATE KEY-----…` |
| `USER` | SSH username | — |
| `STAGING_TS_HOST` | Tailscale hostname for the box; preferred over `HOST` | `staging-vps` |
| `HOST` | Fallback when `STAGING_TS_HOST` is unset | `<staging-host>` |
| `TS_CLIENT_ID` | Tailscale OAuth client id — the deploy runs over Tailscale (#485, #489) | — |
| `TS_AUTH_SECRET` | Tailscale OAuth client secret; needs the client's full tag set (#490) | — |

## Frontend build values (GitHub environment variables)

`NEXT_PUBLIC_*` values are inlined into the browser bundle at **build** time, so
the image build reads them from the `staging` environment's variables, not from
the box. Setting one only in the box `.env` changes nothing the browser sees.

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL, including the version prefix | `https://api.dev.autoauthor.app/api/v1` |
| `NEXT_PUBLIC_BETTER_AUTH_URL` | Frontend application URL | `https://dev.autoauthor.app` |
| `NEXT_PUBLIC_SENTRY_DSN` | Frontend Sentry DSN; empty ⇒ Sentry off. A DSN is designed to be public | — |

The session cookie's domain is derived from the frontend URL's host:
`dev.autoauthor.app` yields `.dev.autoauthor.app`, which the API at
`api.dev.autoauthor.app` also receives. **Production must not put the frontend
on the apex with the API at `api.<apex>`** (#778). `.autoauthor.app` would also
match the shared staging box, so an apex gets a host-only cookie that
`api.autoauthor.app` never receives. Use a subdomain for production
(`app.autoauthor.app` + `api.app.autoauthor.app`), or serve the API from the
frontend's own host.

---

## Application values (keys in `/opt/auto-author/.env`)

`docker-compose.yml` passes the whole file to the backend and a fixed list of
names to the frontend. It asserts the required ones with `${VAR:?...}`, so a
missing key fails the deploy with a named error.

### Required

| Key | Description |
|-----|-------------|
| `MONGODB_URI` | Connection string, **no database name in the path**. Compose also hands it to the frontend as `DATABASE_URL` |
| `DATABASE_NAME` | Database name, e.g. `auto_author_staging` |
| `BETTER_AUTH_SECRET` | better-auth's session-cookie signing secret, used by **both** backend and frontend. 64+ random chars |
| `OPENAI_API_KEY` | AI provider key (see `docs/STAGING-DEPLOYMENT.md` → AI provider settings) |
| `ENVIRONMENT` | Exported by the workflows as `staging`; there is no default (#777) |

A database name in the URI path breaks Atlas auth (it becomes `defaultauthdb`,
which `authSource` then defaults to) and is ignored by the app regardless.
Percent-encode the password. Full rules and the rotation runbook:
`docs/DATABASE_CONNECTION_STANDARD.md`. Staging uses MongoDB Atlas: when the
server's IP changes, add the new address to the Atlas allowlist or every deploy
health check fails.

Generate `BETTER_AUTH_SECRET` with:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(64))'
```

Both containers read the same key from the same file, so they cannot disagree.
Rotating it signs every user out.

### Recommended

Deploys succeed without these, but the corresponding feature is silently
degraded — which is worse than a loud failure. Set them.

| Key | Description |
|-----|-------------|
| `EMAIL_SERVICE_PROVIDER`, `EMAIL_SERVICE_API_KEY`, `EMAIL_FROM_ADDRESS`, `EMAIL_FROM_NAME` | Verification and password-reset mail (#332). The frontend's `/api/health` reports which provider is configured |
| `SENTRY_DSN` | Backend Sentry DSN; empty ⇒ Sentry off |
| `BACKEND_CORS_ORIGINS` | Plain comma-separated origins, **not** a quoted JSON array — the dotenv reader mangles the quotes into invalid JSON and `Settings()` fails at start-up |
| `E2E_EXEMPT_EMAILS` | The staging E2E account's address, exempting it from rate limits, AI quota and entitlement checks. Fenced to non-production in code |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_PRO` | Billing; webhooks answer 503 without the webhook secret |

### Optional

| Key | Description |
|-----|-------------|
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_S3_BUCKET` | S3 storage and transcription |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | Image storage |

> ⚠️ These reach the **backend** only; the frontend container is given a fixed
> list of names (#781). Never expose a credential under a `NEXT_PUBLIC_` name —
> Next.js inlines those into the client bundle at build time, publishing the
> secret to every visitor.

`BYPASS_AUTH` is not something to set on the box: the backend ignores it unless
`E2E_ALLOW_BYPASS=1` is also set, and refuses to start with it in production.

---

## Verification

1. Merge to `main`: a change under `backend/`, `frontend/` or a compose file runs
   `build-images.yml`, which publishes `sha-<short>` images. A docs-only merge
   publishes nothing.
2. Dispatch the deploy with that tag:
   `gh workflow run deploy-staging-containers.yml -f image_tag=sha-<short>`.
3. The workflow waits for both containers to answer locally; then check
   `https://api.dev.autoauthor.app/api/v1/health` and
   `https://dev.autoauthor.app/api/health` from outside.
4. `e2e-staging-tests.yml` runs after a successful deploy, with the specs from
   the commit the deploy was dispatched from (normally the deployed build; not
   after a rollback to an older tag). Wait for it before calling the deploy done.

---

## Troubleshooting

### Deployment fails with "connection refused" or an SSH timeout

- Verify `SSH_KEY`, `USER`, `STAGING_TS_HOST`, and the Tailscale OAuth client.
- The staging host runs fail2ban in aggressive mode and bans bursty connections.

### Backend health check fails

- `BETTER_AUTH_SECRET` unset or weak — the app deliberately refuses to start.
- MongoDB unreachable — `/api/v1/health` reports `mongodb: error: OperationFailure`
  for bad credentials and `error: TimeoutError` when the IP allowlist or the
  cluster blocks it (the ping is cut off after 5 seconds).
- `docker compose -f docker-compose.yml -f docker-compose.staging.yml logs --tail=100 backend`
  in `/opt/auto-author` (export `IMAGE_TAG` and `ENVIRONMENT` first; see
  `docs/STAGING-DEPLOYMENT.md`).
- Check which keys the box has, **without printing their values**:
  ```bash
  cut -d= -f1 /opt/auto-author/.env    # names only
  grep -c '^BETTER_AUTH_SECRET=.\+' /opt/auto-author/.env   # 1 = set and non-empty
  ```
  Never `cat` that file — it holds the database URI, the auth secret, the
  OpenAI key, and any AWS credentials, and it tends to get pasted into tickets
  and screen shares.

### CORS errors

- `BACKEND_CORS_ORIGINS` must contain the frontend URL and must not be a quoted
  JSON array (see above).
- A real preflight needs the request-method header, not just `Origin`:
  ```bash
  curl -s -D - -o /dev/null -X OPTIONS <API_URL>/books \
    -H "Origin: <FRONTEND_URL>" \
    -H "Access-Control-Request-Method: POST" | grep -i access-control-allow-origin
  ```

### Password reset does nothing

`EMAIL_SERVICE_*` keys are unset. The UI reports success either way; the
frontend's `/api/health` names the configured provider.

---

## Security Practices

1. **Never prefix a secret with `NEXT_PUBLIC_`** — Next.js inlines those into the client bundle at build time. `scripts/check-secrets.sh` blocks commits that introduce one.
2. Rotate secrets periodically, and immediately after any suspected exposure.
3. Use different values per environment; never share staging and production secrets.
4. Never enable `BYPASS_AUTH` in a deployed environment. Production blocks it in code.
