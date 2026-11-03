# Staging Deployment Guide

**Last Updated**: 2026-10-14
**Deploy path**: containers, live since 2026-08-12 (#484)

Staging is https://dev.autoauthor.app (frontend) and https://api.dev.autoauthor.app
(backend). It runs as Docker containers on a **shared VPS** — other applications
live on the same box, so every step here is a check, not an assumption.

> The PM2/rsync deploy this replaced (build-on-the-VPS, `releases/<id>` symlinked
> to `current`) is gone: its workflow and the PM2 template were deleted (#656,
> #846). Roll back by deploying an older image tag; see [Rolling back](#rolling-back).

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

Images are built in CI by `build-images.yml` and published to GHCR. The **image
tag is the release identifier** — there is no release directory.

- **Backend**: `sha-<short>` and `staging`. Configured at run time, so one image
  serves every environment.
- **Frontend**: one image per environment (#779), because Next inlines
  `NEXT_PUBLIC_*` into the bundle at build time — `sha-<short>-staging` (also
  floated as `staging`). Staging is the only environment built today; production
  becomes a second matrix entry with its deploy (#782). The values come from the
  GitHub environment's **variables** (`NEXT_PUBLIC_API_URL`,
  `NEXT_PUBLIC_BETTER_AUTH_URL`, optional `NEXT_PUBLIC_SENTRY_DSN`); a main build
  fails if a required one is unset rather than baking in another environment's
  hosts. `NEXT_PUBLIC_ENVIRONMENT` is the environment's name.

The deploy's `image_tag` input is the backend's `sha-<short>`; the staging
overlay pulls `<image_tag>-staging` for the frontend.

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

`/opt/auto-author/.env` carries every application secret. The deploy ships
compose files and runs `docker compose up`; the values come from that file.

**One workflow writes one key of it:** `sync-staging-env.yml` (manual dispatch,
#537) copies the `staging` environment secret `MONGODB_URI` into the file in
place, keeps a timestamped `.env.bak.*` (the five newest), leaves every other
key alone, and (unless dispatched with `recreate=false`) recreates the
containers on the running tag. Dispatching it with a stale secret
puts the stale credential on the box. Every other key is edited by hand.

Compose asserts the required ones with `${VAR:?...}`, so a missing key fails the
deploy with a named error instead of starting a container that dies at first
query:

```
MONGODB_URI, DATABASE_NAME, BETTER_AUTH_SECRET, OPENAI_API_KEY
```

**`BETTER_AUTH_SECRET` must be the same value for both containers** (#795). The
frontend signs the session cookie with it and the backend verifies that
signature on every request. Both read it from this one file, so they agree. If
they ever differ, sign-in still works and every backend call answers 401; the
backend log says `Rejected ... cookie: signature does not verify`. The backend
knows one secret only: better-auth's rotation list (`BETTER_AUTH_SECRETS`) is
not supported until the backend check is taught it.

The **backend** gets everything else in the file wholesale via `env_file:` — it
also needs `AWS_*`, `CLOUDINARY_*` and `BACKEND_CORS_ORIGINS`, which an explicit
allowlist would have silently dropped.

**Upload storage must be configured on a deployed backend** (#806). The backend
uses Cloudinary when `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY` and
`CLOUDINARY_API_SECRET` are all set, else S3 when `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY` and `AWS_S3_BUCKET` are all set. With neither complete it
falls back to a local `uploads/` directory, which the image cannot create (`/app`
belongs to root). The container still starts; the first cover or avatar upload
fails, and the log says `Uploads are not available: no cloud storage is configured
and the local directory /app/uploads cannot be created`, followed by the settings
to set and any that are half set. With `ENVIRONMENT=production` the backend
refuses to start instead: `Application startup blocked: no upload storage is
configured`.

**What `/api/v1/health` reports** (#807). Besides `mongodb` and `config` it has
`storage`, `billing` and `error_reporting`, each `ok`, `disabled` or `missing:`
followed by the names of the settings that are not set (never their values).
Outside production these three are information: staging answers 200 with them
listed. With `ENVIRONMENT=production` any `missing:` makes the answer a 503, so
the deploy gate stops a box that cannot store uploads, bill or report errors.
`BILLING_ENABLED=false` reports billing as `disabled` for a deployment that
sells nothing. `/api/v1/health/live` answers 200 whenever the process is
serving; the container's own health check uses it, so a database outage does
not mark a live container unhealthy.

The **frontend does not** (#781). It takes an explicit `environment:` list in
`docker-compose.yml` — the Mongo connection, `BETTER_AUTH_*`, the `EMAIL_*`
settings (password reset, and since #792 the sign-up verification email, without
which no new account can sign in; `GET /api/health` on the frontend reports
whether a provider is configured, #968), `NEXT_PUBLIC_SENTRY_DSN`/`NEXT_PUBLIC_ENVIRONMENT` —
with values still read from this same `.env` by compose interpolation, so there
is one file on the box and no second one to keep in step. OpenAI, Stripe, AWS
and Cloudinary keys never enter the Next.js process. Consequences:

- **A new server-side variable the frontend reads must be added to that list**,
  or it is silently absent in the container. `scripts/test_frontend_env_allowlist.py`
  fails CI if the list names anything `frontend/src` does not read, or anything
  backend-only.
- The deploy checks the running container: **Frontend carries no backend secret**
  runs `env` inside `auto-author-frontend-1` and fails on any `OPENAI*`, `AI_API_KEY`,
  `STRIPE*`, `AWS*`, `CLOUDINARY*` or `SENTRY_DSN` name (names only are logged).
  By hand: `docker exec auto-author-frontend-1 env | cut -d= -f1 | sort`.

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
# docker-compose.yml also requires ENVIRONMENT with no default (#777); the
# workflows export it the same way, so a manual shell must too.
export ENVIRONMENT=staging
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d
```

Database values have their own rules (no db name in the URI, percent-encode the
password, rotation runbook): `docs/DATABASE_CONNECTION_STANDARD.md`.

---

### AI provider settings (#917)

All optional. With none set, the backend calls api.openai.com with `gpt-4o`
for both model classes (the default class used `gpt-4` until OpenAI retired it, #1205). They reach the backend through `env_file:`,
so adding a line to the box `.env` and recreating the containers is the whole
change.

| Variable | Default | Meaning |
|---|---|---|
| `AI_BASE_URL` | empty (api.openai.com) | Any OpenAI-compatible endpoint, such as z.ai, OpenRouter, vLLM or Ollama (`…/v1`). This is the only routing switch: the SDK's own `OPENAI_BASE_URL` is ignored |
| `AI_API_KEY` | empty | That provider's key, which takes precedence over `OPENAI_API_KEY`. **Required whenever `AI_BASE_URL` is set**, because the OpenAI key is never sent to another endpoint and `/health` reports `AI_API_KEY` as missing. A keyless local server (Ollama) still needs a non-empty value, any string will do. Compose still requires `OPENAI_API_KEY`, so leave the existing value |
| `AI_MODEL_DEFAULT` | `gpt-4o` | Summary analysis, clarifying and chapter questions, enhance, transform, transcription cleanup |
| `AI_MODEL_LONG_OUTPUT` | `gpt-4o` | Chapter drafts and TOC generation (needs ≥ 6000 output tokens for TOC) |
| `AI_MAX_OUTPUT_TOKENS_DEFAULT` | `4000` | Cap on every default-class request's `max_tokens` |
| `AI_MAX_OUTPUT_TOKENS_LONG` | `8000` | Cap on drafts and TOC. Lowering it below 6000 truncates large TOCs, which then fail cleanly as `AI_RESPONSE_TRUNCATED` |
| `AI_REASONING_HEADROOM_TOKENS` | `0` | Added to every flow's `max_tokens` before the caps clamp it, for reasoning models (below). Must be ≥ 0 |

Things that differ by provider:

- **Out of credit.** OpenAI's 429 `insufficient_quota` and the HTTP 402 that
  OpenAI-compatible providers send (Ollama cloud, OpenRouter) both map to
  `AI_PROVIDER_QUOTA_EXHAUSTED` (503, not retried). A provider that signals
  billing some other way surfaces as `AI_UNEXPECTED_ERROR`; check the backend
  log for its message. A retired or unknown model name is the same.
- **Reasoning models** (Nemotron, Qwen3, GLM thinking modes) spend part of
  `max_tokens` on hidden reasoning. Each flow's own budget is fixed in code
  (analysis 1000, clarifying questions 800, chapter questions 2000, rewrites
  4000 or more, TOC 6000, a draft 1.6 tokens a word). Measured live,
  `nemotron-3-nano:30b` spent all 1000 analysis tokens thinking and returned
  empty content, which every flow reports as `AI_RESPONSE_TRUNCATED` rather
  than parsing the empty answer. To run one, set `AI_REASONING_HEADROOM_TOKENS`
  (3000 made Nemotron's analysis return a verdict in 3 of 3 runs, #925) and
  raise `AI_MAX_OUTPUT_TOKENS_DEFAULT` / `_LONG` to at least the largest
  budget plus the headroom (5000 and 9000 for 3000), within the model's
  output limit: the caps still clamp the sum. A truncated transform, enhance
  or transcription cleanup answers 413 "too long", which on a reasoning model
  usually means the headroom is too small, not that the chapter is.
- **Output format.** The parsers are pinned against real `nemotron-3-nano:30b`
  output (`backend/tests/fixtures/ai_provider_outputs/`). Capture another
  model's fixtures the same way before relying on it in production.
- **Nothing is OpenAI-only.** Voice input uses the browser's speech
  recognition. Its server-side cleanup is an ordinary chat call on
  `AI_MODEL_DEFAULT`. There is no Whisper, embeddings or image call.

### Stripe Managed Payments (#1234)

Auto Author sells under Stripe Managed Payments: Stripe, as Link, is merchant of
record and handles sales tax, fraud and disputes, for a fee on top of processing.
Checkout sends `managed_payments.enabled` from `STRIPE_MANAGED_PAYMENTS` on every
session, so the Dashboard default never decides it. Turn it on in this order:

1. In the Stripe Dashboard (in the same mode, test or live, as `STRIPE_SECRET_KEY`):
   Settings → Managed Payments → activate it.
2. Product catalog → Auto Author Pro → Edit product → set a **Product tax code**
   labelled "Eligible for Managed Payments".
3. Settings → Business details → support email `support@autoauthor.app`. Link
   escalates customer issues there and may refund if nobody answers in 48 hours.
4. Add `STRIPE_MANAGED_PAYMENTS=true` to `/opt/auto-author/.env` and **recreate**
   the containers (see above).
5. Start a checkout and confirm Stripe's page says it is sold through Link and
   shows a tax line for a taxable address.

Doing step 4 before steps 1 and 2 makes Stripe reject every checkout (the API
returns 502 "Payment provider error"). To undo, set it back to `false` and
recreate. With it on, `STRIPE_AUTOMATIC_TAX` is ignored and the Stripe Tax steps
below don't apply.

### Stripe Tax (#783, not used under Managed Payments)

Checkout always collects a billing address and tax IDs. Tax **calculation** stays
off until `STRIPE_AUTOMATIC_TAX=true` is in the box `.env`. Turn it on in this order:

1. In the Stripe Dashboard (in the same mode, test or live, as `STRIPE_SECRET_KEY`):
   Tax → set the origin address and add a registration for each place you must
   collect in.
2. Add `STRIPE_AUTOMATIC_TAX=true` to `/opt/auto-author/.env` and **recreate** the
   containers (see above).
3. Start a checkout and confirm Stripe's page shows a tax line.

Doing step 2 before step 1 makes Stripe reject every checkout (the API returns 502
"Payment provider error"). To undo, set it back to `false` and recreate.

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

   The frontend `location /` **must** carry
   `proxy_set_header X-Real-IP $remote_addr;`. better-auth buckets its sign-in
   rate limit (3 per 10s) by client IP and reads `x-real-ip` first (#602); with
   the header missing it falls back to `x-forwarded-for`, which nginx builds
   with `$proxy_add_x_forwarded_for` — that *appends* to whatever the client
   sent, so any request arriving with its own `X-Forwarded-For` becomes a
   multi-hop chain better-auth cannot resolve and drops into a single bucket
   shared by every such request. `X-Real-IP` is immune because `proxy_set_header`
   overwrites a client-supplied value.

   **If a second proxy is ever put in front of nginx** (CDN, load balancer),
   `X-Real-IP` becomes *that* proxy's address. Either have the outermost proxy
   set `X-Real-IP`, or switch `frontend/src/lib/auth-ip.ts` to
   `advanced.ipAddress.trustedProxies` listing the whole chain.

   The API `location /` **must** carry
   `proxy_set_header X-Forwarded-Proto $scheme;` and
   `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;` (#814). The
   backend builds its own redirects (`/api/v1/books` to `/api/v1/books/`) from
   the scheme it believes it was reached on, and logs the client it believes
   called. uvicorn believes those two headers only from the peers in
   `FORWARDED_ALLOW_IPS`, which `docker-compose.yml` sets to the ranges Docker
   gives its networks, because nginx reaches the container as the network's
   gateway. If Docker on the box was given its own address pools, that list has
   to name them. To check: `curl -sI https://<api host>/api/v1/books` must show
   a `location:` that starts with `https://`.

---

## Deploying

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
gh workflow run deploy-staging-containers.yml -f image_tag=sha-<previous>
```

The workflow's only input is `image_tag`. To do the same by hand on the box:

```bash
cd /opt/auto-author
IMAGE_TAG=sha-<previous> ENVIRONMENT=staging docker compose \
  -f docker-compose.yml -f docker-compose.staging.yml up -d
```

Builds from before #779 have no `-staging` frontend tag, so the current overlay
cannot roll back past that change; pin the frontend image by hand
(`auto-author-frontend:sha-<previous>`) for such a rollback.

better-auth 1.7.0 through 1.7.2 find a credential account only when it carries
`account.issuer`; 1.7.7 (#919) neither writes nor reads that field (#950), so
accounts created since then have none. Before rolling back to an image on
1.7.0-1.7.2, back up the `account` and `user` collections and run the issuer
backfill from that image, which still ships it, or those accounts get a 401 on
sign-in:

```bash
docker run --rm --env-file .env ghcr.io/frankbria/auto-author-backend:sha-<previous> \
    python -m app.scripts.migration_account_issuer          # dry run; add --apply
```

Its docstring in that image is the full runbook. 1.6 and 1.7.7 need nothing:
both ignore the field.

---

## Troubleshooting

**Compose exits with `MONGODB_URI is required`** — the box `.env` is missing that
key, or the deploy is running from a directory without it. This is the assertion
working; check `/opt/auto-author/.env`.

**Compose exits with `ENVIRONMENT is required`** — the shell running compose
did not export `ENVIRONMENT`. There is deliberately no default (#777): the
backend's production guards key off it. The workflows export `staging`; a manual
shell must do the same.

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
# Every compose command interpolates the files: export IMAGE_TAG and
# ENVIRONMENT=staging first, as in the recreate snippet above.
docker compose -f docker-compose.yml -f docker-compose.staging.yml logs --tail=100 backend
docker compose -f docker-compose.yml -f docker-compose.staging.yml ps
```

---

## Maintenance

**Weekly** — review container logs for errors, check disk space (images
accumulate), confirm Atlas backups.
**Monthly** — `apt update && apt upgrade` on the box; review the image prune
window.
**As needed** — re-check the Atlas IP allowlist after any VPS network change.

### Orphaned upload sweep (#938)

Cover and avatar files are deleted best-effort after the database write, so a
failed storage call, a crash in between, or a raced upload can leave a file no
record names. `app.scripts.sweep_orphaned_uploads` lists every object under
`cover_images/` and `profile_pictures/` in the configured storage (S3,
Cloudinary or local `uploads/`) that no `books.cover_image_url` /
`cover_thumbnail_url` or `users.avatar_url` points at. Nothing outside those two
prefixes is listed or deleted.

```bash
cd /opt/auto-author   # IMAGE_TAG and ENVIRONMENT exported as in the recreate snippet above
docker compose exec backend python -m app.scripts.sweep_orphaned_uploads           # dry run
docker compose exec backend python -m app.scripts.sweep_orphaned_uploads --apply   # delete
```

- **Dry run is the default**: it logs each candidate (`Orphan: <key>`) and a
  count line, and deletes nothing. `--apply` deletes them and logs each one
  (`Deleted: <key>`, or `Storage did not delete <key>`).
- **Grace window**: objects written in the last 60 minutes are skipped
  (`--grace-minutes N` changes it), because an upload is stored before the record
  naming it is saved.
- **Empty-database guard**: `--apply` refuses (exit `2`) when no book or user
  references any upload while storage holds some, since a wrong `--database` makes
  every file look orphaned. Pass `--allow-no-references` only if that is really so.
- `exec` into the running backend, not a throwaway container: it needs the same
  storage settings, and with local storage the same files.
- Exit codes: `0` done, `1` at least one delete failed (logged), `2` connection
  or configuration error, or the empty-database guard.

---

**Related**: `.github/DEPLOYMENT.md` (which workflow reads which secret),
`docs/DATABASE_CONNECTION_STANDARD.md` (DB values and rotation).
