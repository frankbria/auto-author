# Demo — #516 Verify mongodb 7.5.0 auth against staging Atlas

**Date:** 2026-08-26/27 · **Issue:** #516 · **Deployed tag:** `sha-bae440a`

`mongodb` was bumped **6.21.0 → 7.5.0** in `/frontend` via #507. CI's E2E runs against a
local/ephemeral Mongo, so the residual gap was **real Atlas connectivity from the staging
box** — TLS negotiation, connection-string parsing (`mongodb-connection-string-url` goes to a
new major; the deployed lockfile resolves **7.0.2**), and driver-side retry against a hosted
cluster.

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
| staging E2E | **green**, `1 flaky` ([33028231204](https://github.com/frankbria/auto-author/actions/runs/33028231204)) | **green**, `1 flaky` ([33028714230](https://github.com/frankbria/auto-author/actions/runs/33028714230)) |

Both runs report `1 flaky, 10 passed`, and it is the **same spec in both** — see AC3, where it is
disclosed rather than absorbed into the word "green".

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

## AC3 — `npm run test:e2e:staging` green, including `regressions.spec.ts` ✅ — with a disclosed flake

[Run 33028714230](https://github.com/frankbria/auto-author/actions/runs/33028714230) —
`E2E Staging (Playwright): success`, **`1 flaky, 10 passed`**. That suite includes
`regressions.spec.ts`, whose #83 session/401 and #54 answer-persistence specs both exercise session
handling, which is the part a driver regression would break.

**The flake is that #83 session/401 spec — the canary just named.** It failed its first attempt and
passed only on Playwright's retry, so reporting this AC as unqualified "green" would have been the
one misleading claim in the record:

| | first attempt | retry #1 |
|---|---|---|
| before — `sha-de87eea`, mongodb 6.21.0 | ✘ 32.7s | ✓ 3.9s |
| after — `sha-bae440a`, mongodb **7.5.0** | ✘ 32.4s | ✓ 3.7s |

```
TimeoutError: page.waitForURL: Timeout 30000ms exceeded.
  waiting for navigation until "load"
  at fixtures/auth.fixture.ts:52   // await page.waitForURL(/\/dashboard/, { timeout: 30000 })
```

**It reproduces identically on the pre-bump driver, which is precisely what the baseline was built to
settle.** Same spec, same fixture line, same ~32s first attempt and ~4s retry on 6.21.0 as on 7.5.0.
The flake is therefore driver-independent and does not impeach this verification — but it is a
first-attempt failure inside the sign-in path under test, and it is pre-existing rather than
introduced here. A third run ([33030415162](https://github.com/frankbria/auto-author/actions/runs/33030415162))
made it 3/3 with the first attempt clustering at 32.4–32.7s, which is too tight to be random.
Filed as **#551**; it is a staging-latency defect, not a finding of #516.

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
  attempts with backoff; none were needed. This is the direct evidence on two of the three
  residual risks: connection-string parsing under the new `mongodb-connection-string-url@7`
  major and TLS negotiation against a hosted cluster both worked first time.
- **The third residual risk — driver-side retry/reconnect against a hosted cluster — is
  *not* discharged, and connecting first-try is exactly why.** Nothing here exercised SDAM
  failover or retryable operations on a transient Atlas error. Establishing that needs
  induced failure, which this issue did not attempt.
- **`User not found`** is the bogus-email probe above, not a driver warning.
- Backend logs: no mongo/TLS warnings at all.
- **Window:** this snapshot was taken at ~01:00:32Z, before the E2E run began at 01:01:54Z.
  So it covers startup plus the bogus-credentials probe — not the frontend logs under the
  ~12 real sign-ins the E2E suite then performed. The AC asks about "startup or first auth",
  which is what is captured; sustained authenticated traffic was not re-inspected afterwards.

And the driver actually running, read from inside the container rather than inferred from
the image tag:

```console
$ docker exec auto-author-frontend-1 node -p "require('mongodb/package.json').version"
7.5.0
```

---

## Verdict

**mongodb 7.5.0 is verified against staging Atlas.** Every criterion holds, and the
pre-bump baseline makes the comparison controlled rather than merely reassuring — including
for the one blemish: the #83 canary's first-attempt timeout reproduces on 6.21.0, so the
baseline is what lets it be dismissed as pre-existing (#551) instead of leaving a doubt
hanging over the bump.

## Scope — what this does and does not cover

The deploy carried **14** commits (`de87eea..bae440a`), of which **8** are app-code rather than
CI/docs-only — not just the driver:
radix UI patches (#508, #511), `pydantic-settings` 2.10.1 → 2.14.2 (#502),
`pytest-asyncio` (#500, test-only), the #495 TOC validation fix, E2E spec fixes (#494),
and a dropped `pytest.ini` (#535). The other six touch no application code: four Actions tag
bumps (#498, #501, #506, #515), the container-deploy docs rewrite (#497), and hiding the generated
requirements export from Dependabot (#521).

Only `mongodb` touches the auth path, so a login/session failure would have implicated the
driver. A failure in TOC or book creation would more likely have been `pydantic-settings`
or #495. Everything passed, so the distinction did not have to be exercised — but the
green result validates the *bundle*, and it is the driver specifically that this issue set
out to clear.

**Not covered: better-auth 1.6 → 1.7** (#543), which merged during this work and is now on
`main` unverified against Atlas. Same class of risk as this issue — auth path, only
exercised against a local Mongo in CI. It needs its own pass, filed as **#550**.
