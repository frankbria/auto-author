# Demo — #516 Verify mongodb 7.5.0 auth against staging Atlas

**Date:** 2026-08-26/27 · **Issue:** #516 · **Deployed tag:** `sha-bae440a`

`mongodb` was bumped **6.21.0 → 7.5.0** in `/frontend` via #507. CI's E2E runs against a
local/ephemeral Mongo, so the residual gap was **real Atlas connectivity from the staging
box** — TLS negotiation, connection-string parsing (`mongodb-connection-string-url@7.0.0`
is itself a new major), and driver-side retry against a hosted cluster.

This is a genuine before/after, not a post-hoc check: staging was first restored on the
**pre-bump** build and proven green, then the bumped build was deployed and the same
checks re-run.

---

## The controlled comparison

| | before | after |
|---|---|---|
| image | `sha-de87eea` | `sha-bae440a` |
| `mongodb` driver | 6.21.0 | **7.5.0** |
| `GET /api/v1/health` | `200 {"mongodb":"ok"}` | `200 {"mongodb":"ok"}` |
| `POST /api/auth/sign-in/email` (bad creds) | `401` | `401` |
| staging E2E | **green** ([33028231204](https://github.com/frankbria/auto-author/actions/runs/33028231204)) | **green** ([33028714230](https://github.com/frankbria/auto-author/actions/runs/33028714230)) |

The pre-bump E2E pass matters more than it looks. Staging had been down six days (#537),
so without establishing that the environment was sound on the *old* driver first, a
post-deploy failure could not have been separated from residual outage damage. That
baseline cost one extra deploy and ten minutes, and it is what makes the result below
mean anything.

---

## AC1 — Redeployed from a `main` image at or after `8b2a447c` ✅

[Deploy run 33028619534](https://github.com/frankbria/auto-author/actions/runs/33028619534),
all nine steps green.

```console
$ docker inspect auto-author-backend-1 auto-author-frontend-1 \
    --format "{{.Name}} image={{.Config.Image}} created={{.Created}} health=..."
/auto-author-backend-1  image=...auto-author-backend:sha-bae440a   created=2026-08-27T00:59:25Z  health=healthy
/auto-author-frontend-1 image=...auto-author-frontend:sha-bae440a  created=2026-08-27T00:59:28Z  health=none
```

**`sha-bae440a` was chosen deliberately over the newer `sha-8c796a9`.** That newer image
carries #543, which bumps **better-auth 1.6 → 1.7** — a second change in the auth path.
Deploying it would have put two auth-path variables into this verification and destroyed
the attribution. `bae440a` still satisfies the AC ("at or after `8b2a447c`") while leaving
`mongodb` 6.21.0 → 7.5.0 as the only auth-path change in the span.

---

## AC2 — Real login succeeds, `/api/v1/books` returns ✅

```console
$ curl -X POST https://dev.autoauthor.app/api/auth/sign-in/email -d '{bogus creds}'
HTTP 401   (during the outage this was HTTP 500)
```

The 401 proves the auth path *reaches* Atlas and rejects correctly — but on its own it
does **not** prove a real user gets a session and can read their books. That is discharged
by AC3: `complete-user-journey.spec.ts` signs in as a real staging user, lands on
`/dashboard`, and creates and reads a book through `/api/v1/books`. AC2 rests on that run,
not on this curl.

---

## AC3 — `npm run test:e2e:staging` green, including `regressions.spec.ts` ✅

[Run 33028714230](https://github.com/frankbria/auto-author/actions/runs/33028714230) —
`E2E Staging (Playwright): success`. That suite includes `regressions.spec.ts`, whose
#83 session/401 and #54 answer-persistence specs both exercise session handling, which is
the part a driver regression would break.

---

## AC4 — Backend `/health` dependency checks green against Atlas ✅

```console
$ curl https://api.dev.autoauthor.app/api/v1/health
{"status":"healthy","checks":{"mongodb":"ok","config":"ok"}}   HTTP 200
```

---

## AC5 — No new driver warnings/errors on startup or first auth ✅

The frontend container's **entire** log since startup is 7 lines. Filtering for anything
resembling a driver complaint:

```console
$ docker logs auto-author-frontend-1 2>&1 | grep -iE "warn|error|deprecat|mongo|topology|tls|ssl"
MongoDB client connected for better-auth (attempt 1/3)
2026-08-27T01:00:32.844Z WARN [Better Auth]: User not found
```

- **`attempt 1/3`** — connected on the *first* try, no retries. `auth.ts` allows three
  attempts with backoff; none were needed. This is the direct evidence on the residual
  risk: connection-string parsing under the new `mongodb-connection-string-url@7` major
  and TLS negotiation against a hosted cluster both worked first time.
- **`User not found`** is the bogus-email probe above, not a driver warning.
- Backend logs: no mongo/TLS warnings at all.

And the driver actually running, read from inside the container rather than inferred from
the image tag:

```console
$ docker exec auto-author-frontend-1 node -p "require('mongodb/package.json').version"
7.5.0
```

---

## Verdict

**mongodb 7.5.0 is verified against staging Atlas.** Every criterion holds, and the
pre-bump baseline makes the comparison controlled rather than merely reassuring.

## Scope — what this does and does not cover

The deploy carried **8** app-code commits (`de87eea..bae440a`), not just the driver:
radix UI patches (#508, #511), `pydantic-settings` 2.10.1 → 2.14.2 (#502),
`pytest-asyncio` (#500, test-only), the #495 TOC validation fix, E2E spec fixes (#494),
and a dropped `pytest.ini` (#535).

Only `mongodb` touches the auth path, so a login/session failure would have implicated the
driver. A failure in TOC or book creation would more likely have been `pydantic-settings`
or #495. Everything passed, so the distinction did not have to be exercised — but the
green result validates the *bundle*, and it is the driver specifically that this issue set
out to clear.

**Not covered: better-auth 1.6 → 1.7** (#543), which merged during this work and is now on
`main` unverified against Atlas. Same class of risk as this issue — auth path, only
exercised against a local Mongo in CI. It needs its own pass.
