# Demo — #550 Verify better-auth 1.7 against staging Atlas

**Date:** 2026-08-27 · **Issue:** #550 · **Tag under test:** `sha-8c796a9` · **Staging now:** `sha-bae440a` (rolled back)

## Result: better-auth 1.7.1 **fails** staging verification. Staging is rolled back.

**Every account created on better-auth ≤1.6 is locked out on 1.7.1.** The user row is still
there — sign-up rejects the address as a duplicate — but sign-in returns `401
INVALID_EMAIL_OR_PASSWORD` and the server logs `WARN [Better Auth]: User not found`. Accounts
created *on* 1.7 sign in normally, so the break is specific to pre-existing credential records.

This is exactly the risk #550 was opened to find, and exactly the part typecheck could not see:
#543 arrived as a **minor** bump, its one visible breaking change (`twoFactor.enable()` becoming
a discriminated union) was caught by the compiler and fixed in `TwoFactorSetup.tsx`, and the
invisible one — a total auth outage for the entire existing user base — was still sitting there.

`sha-8c796a9` is on `main`. Any staging or production deploy from `main` today reproduces this.
Filed as **#556**.

---

## The three-point reproduction

One account, `frank.bria+aa550-before2@pm.me`, created on staging at 15:48 while better-auth
1.6.26 was serving, then signed in at each stage:

| stage | tag | better-auth | `POST /api/auth/sign-in/email` |
|---|---|---|---|
| before the deploy | `sha-bae440a` | 1.6.26 | **200** — signed in, session cookie issued |
| after the deploy | `sha-8c796a9` | **1.7.1** | **401** `INVALID_EMAIL_OR_PASSWORD` |
| after rollback | `sha-bae440a` | 1.6.26 | **200** — signed in again |

The account was never damaged and never touched between those calls. 1.7 simply could not find
its credentials; 1.6 could, before and after. That third row is what rules out "the account got
corrupted" and leaves only "1.7 cannot read records 1.6 wrote".

And the converse, on the same DB:

| account | created on | signs in on 1.7? | signs in on 1.6? |
|---|---|---|---|
| `aa550-before2` | 1.6.26 | ✘ 401 | ✓ 200 |
| `aa550-books2` | 1.7.1 | ✓ 200 | ✓ 200 |

**The incompatibility is one-way.** Records written by 1.7 are readable by 1.6, so this is not a
schema migration in the ordinary sense — it is 1.7's lookup failing to match what 1.6 stored.

The mechanism inside the MongoDB adapter was not confirmed: reading the `account` collection
directly requires the live Atlas credentials from inside the container, which this environment
blocks. The behavioural evidence is conclusive on its own, and the mechanism is #556's job.

### The log line is misleading, which is worth knowing before someone debugs this at speed

```console
2026-08-27T15:53:13.419Z WARN [Better Auth]: User not found
```

The user is emphatically *found* — the same address returns
`422 USER_ALREADY_EXISTS_USE_ANOTHER_EMAIL` from sign-up at the same moment. Anyone chasing this
from the log alone will go looking for a missing or wiped user and find a perfectly intact one.

---

## AC-by-AC

### AC1 — Baseline recorded on `sha-bae440a` (better-auth 1.6.26) ✅

```console
$ docker inspect … --format '{{.Name}} image={{.Config.Image}}'
/auto-author-backend-1  image=…auto-author-backend:sha-bae440a
/auto-author-frontend-1 image=…auto-author-frontend:sha-bae440a

$ curl https://api.dev.autoauthor.app/api/v1/health
{"status":"healthy","checks":{"mongodb":"ok","config":"ok"}}   HTTP 200

$ curl https://dev.autoauthor.app/api/auth/ok      → {"ok":true}  HTTP 200
$ curl -X POST …/api/auth/sign-in/email  (bogus)   → HTTP 401
```

Staging E2E on this tag: **green**, [run 33089344716](https://github.com/frankbria/auto-author/actions/runs/33089344716)
(15:43:05 → 15:48:17Z, scheduled) — six minutes before the deploy. That run is what makes the
post-deploy failure attributable rather than arguable.

The other half of the baseline was the raw `two-factor/enable` shape, captured while 1.6.26 was
still serving:

```console
top-level keys: ['backupCodes', 'totpURI']
method: None            ← no `method` key at all on 1.6.26
```

### AC2 — Redeployed from a `main` image containing #543 ✅

[Deploy run 33089856995](https://github.com/frankbria/auto-author/actions/runs/33089856995), nine
steps green, 45s, containers up on `sha-8c796a9` at 15:49:05Z.

`sha-8c796a9` was chosen over the newer `sha-8b85d0f` deliberately. The AC allows "or later", but
later tags add openai 3.0.0 and a ten-package backend group. `8c796a9` keeps #543 as the **only**
app-code change in `bae440a..8c796a9` — the other four commits there (#546 docs, #540 Actions
tags, #545 CI secret sync, #538 Dependabot grouping) ship no application code. That is what lets
this report name better-auth rather than "something in the bundle", and it is #516's own
reasoning pointed the other way.

### AC3 — Real login succeeds; `/api/v1/books` returns ❌

**Failed for pre-existing users, which is every real user.** The staging E2E account could not
sign in at all: 11 of 11 specs failed at `auth.fixture.ts:52`, `waitForURL(/\/dashboard/)`
timing out after 30s on the first attempt **and both retries** — not the #551 flake, which passes
on retry.

The container log shows why, at a steady ~33s cadence across the whole run (15:53:13 → 16:09:21Z),
one line per login attempt:

```
WARN [Better Auth]: User not found
```

The session *mechanism* itself is intact on 1.7 — it was only ever the credential lookup that
broke. With an account created on 1.7, the full path works end to end:

```console
set-cookie: __Secure-better-auth.session_token=…; Max-Age=604800;
            Domain=.dev.autoauthor.app; Path=/; HttpOnly; Secure; SameSite=Lax

$ POST https://api.dev.autoauthor.app/api/v1/books/  -H "Cookie: …"   → HTTP 201
$ GET  https://api.dev.autoauthor.app/api/v1/books/  -H "Cookie: …"   → HTTP 200, 1 book
$ GET  https://api.dev.autoauthor.app/api/v1/books/  (no cookie)      → HTTP 401
```

`SameSite=Lax` (#341) survives 1.7, and `Domain=.dev.autoauthor.app` still lets the cookie reach
the backend, which validates it against Atlas directly
(`backend/app/core/better_auth_session.py`). A full browser sign-in on 1.7 with a 1.7-created
account also passed locally in 8.3s, cookie set, dashboard reached. So "1.7 is broken" is
precise, not blanket: **new accounts work, old accounts cannot log in.**

That distinction is the whole finding. A smoke test that signs up a fresh user and drives it
through the app would have passed on 1.7 and shipped this to production.

### AC4 — `npm run test:e2e:staging` green ❌

[Run 33090040109](https://github.com/frankbria/auto-author/actions/runs/33090040109) — **11 failed**,
0 passed. Every spec, including all three of `regressions.spec.ts` (#83 session/401, ObjectId,
#54 answer persistence), plus `complete-user-journey`, all six `edge-cases`, and `visual-smoke`.
All failed identically in the shared login fixture, so this is one defect reported eleven times,
not eleven defects.

Post-rollback re-run: [33092235853](https://github.com/frankbria/auto-author/actions/runs/33092235853)
— **`1 flaky, 10 passed`**, back to the exact pre-existing pattern (the flake is the #83 canary,
**#551**, which fails its first attempt and passes on retry). Same suite, same environment, same
credentials, 26 minutes apart: 0/11 on 1.7, 10/11-plus-a-known-flake on 1.6. That symmetry is the
cleanest single piece of evidence here.

### AC5 — 2FA enable flow exercised against staging ✅

The discriminated union is live and `TwoFactorSetup.tsx`'s narrowing takes the right branch:

| | `sha-bae440a` — 1.6.26 | `sha-8c796a9` — **1.7.1** |
|---|---|---|
| top-level keys | `['backupCodes', 'totpURI']` | `['backupCodes', 'method', 'totpURI']` |
| `method` | *absent* | `"totp"` |
| backup codes | 10 | 10 |

Both measured against the live deployment, not read off a changelog. Note what this implies for
the reverse direction: against a 1.6 server, the current `main` client would take the
`data.method !== 'totp'` error branch on **every** enable attempt. #543's client fix and its
server are a matched pair — which matters now that the server is rolled back to 1.6 while the
client code on `main` is the 1.7-shaped one. See #556.

The whole flow, run on a **throwaway** account so the shared E2E user is never left with 2FA
switched on:

```console
$ POST /api/auth/two-factor/enable      → 200  {"method":"totp","totpURI":"otpauth://totp/…"}
$ POST /api/auth/two-factor/verify-totp → 200   (code derived from the returned secret)
$ GET  /api/auth/get-session            → twoFactorEnabled: True
$ POST /api/auth/sign-in/email          → 200  {"twoFactorRedirect":true,"twoFactorMethods":["totp"]}
```

Enrolment, TOTP verification and the challenged re-login all work on 1.7. Two smaller
observations, recorded because they are the kind of thing a minor bump hides:

- `verify-totp`'s **response body** still reports `twoFactorEnabled: false` while `get-session`
  immediately after reports `true`. That is the staleness `TwoFactorSetup.tsx` already works
  around with `localEnabledOverride`, and the workaround is still required on 1.7.
- `session` and `user` come back with **keys in a different order** on 1.7 (`id` first, where
  1.6 put it last). Cosmetic for a JSON consumer, but it confirms the serialisation path changed
   — a fair reason not to have trusted the minor version number.
- `twoFactorMethods: ["totp"]` is **not** baselined; staging was already on 1.7 when that call
  was made. Reported as observed, not as a delta.

### AC6 — No new auth warnings on startup or first auth ❌

Startup itself was clean — the frontend container's whole log was 11 lines, and:

```console
MongoDB client connected for better-auth (attempt 1/3)
```

connected first try, no retries, so `auth.ts`'s three-attempt backoff was never needed. But the
log then filled with **35** `WARN [Better Auth]: User not found` lines, one per login attempt.
That line is not new in form — it appears once in the #516 baseline log on `sha-bae440a`, where
it was a deliberate bogus-email probe — but here it is the failure itself, at a rate of one every
33 seconds for seventeen minutes. Scoring this AC "no *new* warnings" on a string match would
have been the one badly misleading claim available in this whole exercise.

---

## What this cost, and what it bought

Staging ran better-auth 1.7 for roughly 26 minutes (15:49 → 16:15Z) and existing users could not
sign in during that window. No data was lost — the rollback restored logins immediately, and the
one-way nature of the incompatibility means nothing written on 1.7 became unreadable on 1.6.

In exchange, a change that would have locked every user out of production was caught on staging,
by a verification whose entire purpose was to catch it. #516 declined to bundle better-auth into
its own run and filed this issue instead; that decision is what made the result attributable to
one package within six minutes.

## Rollback

Done, as the issue specified. [Run 33092140241](https://github.com/frankbria/auto-author/actions/runs/33092140241),
green; both containers on `sha-bae440a`; `/health` 200; pre-1.7 logins working again.

## Scope — what this does and does not cover

The deploy carried 5 commits (`bae440a..8c796a9`), of which **exactly one** touches application
code: #543. Within it the frontend-prod group carries 26 package updates — Radix, TipTap, Sentry,
`@hookform/resolvers`, `dompurify` and others — but only better-auth is on the auth path, and the
before/after/rollback sequence pins the failure to credential lookup specifically.

**Not covered:**

- **The mechanism inside `@better-auth/mongodb-adapter`.** Direct inspection of the `account`
  collection was unavailable here. #556 owns it.
- **Whether 1.7 ships a migration** for pre-1.7 credential records, or whether the upstream
  changelog documents this. Not researched; the first job was getting staging back.
- **Session expiry and refresh on 1.7** — sessions here were minutes old, against a 7-day
  `expiresIn`, 24h `updateAge` and a 5-minute `cookieCache`.
- **2FA disable and backup-code regeneration**, and **password reset**, which also route through
  better-auth.
- **The stale local `frontend/tests/e2e/staging/.env.test` credentials**, which 401 against
  staging and are a pre-existing rough edge this work tripped over rather than caused.
- **Throwaway accounts left behind.** Five `frank.bria+aa550-*@pm.me` accounts remain in the
  staging database, one with 2FA enrolled. Harmless on staging, and left in place rather than
  deleted by hand against a live Atlas cluster.
