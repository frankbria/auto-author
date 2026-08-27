# Demo — #556 better-auth 1.7 account-identity backfill

**Date:** 2026-08-27 · **Issue:** #556 · **Branch:** `fix/556-better-auth-account-issuer-backfill`
**Environment:** local MongoDB 127.0.0.1:27017, database `aa_issue556_demo`, real `better-auth@1.7.1`
from `frontend/node_modules` — no mocks, no stubs, no network.

## Result: the lockout is closed. Two defects fixed, one new failure mode found.

The acceptance test #556 asked for — *"an account created under 1.6 must still sign in after the
change"* — passes: **401 → run the backfill → 200**, same account, same account row, no re-signup.

Two things this demo established that the issue did not have:

1. **The mechanism**, read out of the shipped library rather than guessed (the issue's
   "Not yet established" section).
2. **A second, separate defect in the same upgrade**: the forgot-password page posts to a route
   1.7 deleted. The one page a locked-out user would reach for was itself broken.

And one new finding that changes the deploy order: **password reset does not fail on a pre-1.7
account — it silently duplicates it.**

---

## Mechanism

`@better-auth/core/dist/db/schema/account.mjs` makes `issuer` a required field, and
`get-tables.mjs:200` keys `account` on a unique `(issuer, accountId)`.
`createLocalAccountIssuer("credential")` returns `local:credential`. Sign-in then does:

```js
// better-auth/dist/api/routes/sign-in.mjs:320
const credentialAccount = userRecord?.accounts.find((account) =>
  account.providerId === "credential" &&
  account.issuer === credentialIssuer &&        // <- 1.7 only; 1.6 rows have no such field
  account.accountId === userRecord.user.id);
if (!userRecord || !credentialAccount) {
  ctx.context.logger.warn("User not found");    // <- logged about a user it already loaded
  throw APIError.from("UNAUTHORIZED", BASE_ERROR_CODES.INVALID_EMAIL_OR_PASSWORD);
}
```

That is the whole bug, and it explains the one-way asymmetry in the issue: 1.6 never reads
`issuer`, so it is perfectly happy with rows 1.7 wrote.

---

## Building a genuine 1.6-shaped account

Sign up on 1.7, then remove the `issuer` key — 1.6 simply did not have that field, so the
resulting document is byte-identical to what is in the staging database today.

```
account rows as 1.7 writes them:
  _id=6a90c3e3cd3056bfbbff3211  providerId=credential  issuer="local:credential"  accountId=6a90c3e3cd3056bfbbff3210

$unset issuer on 1 row(s) -> byte-identical to a 1.6-written account

account rows as 1.6 wrote them:
  _id=6a90c3e3cd3056bfbbff3211  providerId=credential  issuer=<<absent>>  accountId=6a90c3e3cd3056bfbbff3210
```

## The acceptance test, three points on one row

| # | stage | `signInEmail` |
|---|---|---|
| 1 | 1.6-shaped row on 1.7, before the backfill | **401** |
| 2 | after `--apply` | **200** |
| 3 | re-run the backfill (idempotence) | still **200**, nothing rewritten |

**Point 1 — reproduces the issue's symptom exactly, log line and all:**

```
WARN [Better Auth]: User not found
sign-in: UNAUTHORIZED  INVALID_EMAIL_OR_PASSWORD
```

**Dry run is the default and writes nothing** — it reports the size of the change first:

```
DRY RUN (nothing written): scanned=1 already_migrated=0 issuer_backfilled=1 account_id_repaired=0

account rows:
  _id=6a90c3e3cd3056bfbbff3211  providerId=credential  issuer=<<absent>>  accountId=6a90c3e3cd3056bfbbff3210
```

**Point 2 — `--apply`, then the same account signs in:**

```
APPLIED: scanned=1 already_migrated=0 issuer_backfilled=1 account_id_repaired=0

account rows:
  _id=6a90c3e3cd3056bfbbff3211  providerId=credential  issuer="local:credential"  accountId=6a90c3e3cd3056bfbbff3210

sign-in: 200  session token p4VpdeUZbpWE…
```

The `_id` is unchanged: this is the same account row, repaired, not a new one.

**Point 3 — idempotent, so a second pass is safe:**

```
APPLIED: scanned=1 already_migrated=1 issuer_backfilled=0 account_id_repaired=0
```

---

## New finding: password reset does not fail — it duplicates the account

Reading `password.mjs` closely after the sign-in path: `resetPassword` calls
`findCredentialAccount`, which uses the same issuer filter. Finding nothing, it does not error —
it **creates a second credential account** with the correct issuer. Measured on a fresh 1.6-shaped
row:

```
reset URL: http://localhost:3000/api/auth/reset-password/iPdz6bYcltYgU56fJHh58Nf4?callbackURL=%2F
reset-password: 200 (no error raised)

account rows after a password reset on 1.7:
  _id=6a90c6a04adfae3b3bcfc996  providerId=credential  issuer=<<absent>>       accountId=6a90c6a04adfae3b3bcfc995
  _id=6a90c6b2b1f95035caeb5f4e  providerId=credential  issuer="local:credential"  accountId=6a90c6a04adfae3b3bcfc995

sign-in: 200  session token kjnWTZImXN4y…
```

The user gets back in, so nothing looks wrong from the outside — but the collection now holds two
credential rows for one user, and both resolve to the same `(local:credential, <userId>)` key.
The backfill refuses rather than write into that, naming both rows:

```
ERROR - Refused: identity collision: 1 (issuer, accountId) key(s) map to more than one account
row, which 1.7's unique index rejects. Nothing was written. Reconcile these by hand and re-run:
local:credential/6a90c6a04adfae3b3bcfc995 -> 6a90c6a04adfae3b3bcfc996, 6a90c6b2b1f95035caeb5f4e
```

Exit code `1`, so a deploy script can gate on it.

**Consequence for the runbook:** every hour 1.7 serves pre-1.7 accounts produces more of these,
each needing manual reconciliation. That is why the backfill runs *before* the deploy, not as a
repair afterwards.

`/change-password` goes through the same `findCredentialAccount` and throws
`CREDENTIAL_ACCOUNT_NOT_FOUND` — read from `update-user.mjs:217`, **not demoed here**, because
reaching it needs a session cookie minted before the deploy and sign-in is already refusing.

---

## Second defect: forgot-password posts to a route 1.7 deleted

Found while wiring the reset step above: `auth.api.forgetPassword` is not a function on 1.7. The
method was renamed to `requestPasswordReset` and the route moved. Probed against the real 1.7
handler:

```
POST /api/auth/forget-password        -> 404
POST /api/auth/request-password-reset -> 200 {"status":true,"message":"If this email exists in our system, check your email for the reset link"}
```

`src/app/auth/forgot-password/page.tsx` called `(authClient as any).forgetPassword(...)`, and
`auth-client.ts` declared a hand-written `PasswordResetMethods` interface naming that method and
cast the client to it. Two blindfolds over the same surface, which is why `tsc` was silent.

Both are gone — 1.7 types these methods itself. With the cast removed, mutating the call back to
`forgetPassword` now fails the build:

```
src/app/auth/forgot-password/page.tsx(40,54): error TS2551: Property 'forgetPassword' does not
exist on type 'ReactAuthClient<...>'. Did you mean 'resetPassword'?
```

CI already runs `npm run typecheck`, so that is the standing guard.

---

## Test evidence

| gate | result |
|---|---|
| `pytest tests/test_db/test_migration_account_issuer.py` | **18 passed** (real MongoDB) |
| `pytest tests/` (backend, full) | **1254 passed, 9 skipped**, coverage 92.14% (gate 85%) |
| `pytest scripts/test_dependabot_config.py` | **7 passed, 1 skipped** |
| `npm test` (frontend) | **2288 passed, 5 skipped, 133 suites** |
| frontend coverage gate 85/85/75/85 | **pass** |
| `npm run typecheck` | **clean** |
| `npm run lint` | **0 errors** |

### Mutation checks

Every test was verified to bite by breaking the source and re-running.

| mutation | caught by |
|---|---|
| collision check removed | `test_aborts_on_an_identity_collision_before_writing` |
| orphan check removed | `test_reports_and_skips_an_account_with_no_user` |
| non-credential refusal removed | `test_aborts_on_an_unmigrated_non_credential_provider` |
| dry-run guard removed | `test_dry_run_writes_nothing` |
| accountId repair removed | `test_repairs_an_account_id_that_does_not_match_the_user` |
| `exclude-patterns` dropped from dependabot.yml | `test_better_auth_is_never_grouped` |
| call site back to `forgetPassword` | `npm run typecheck` (TS2551) |
| `str(account["userId"])` → raw value | `test_matches_a_user_whose_id_was_stored_as_a_string` |
| `LOCAL_CREDENTIAL_ISSUER` → `"credential"` | **survived the first pass** — see below |

The issuer mutation surviving is the one worth recording. Every test compared against the
constant rather than against the string better-auth actually looks for, so the single value the
whole fix turns on was untested and a wrong one would have produced a clean, green, useless
migration. Now pinned directly and cross-checked against `createLocalAccountIssuer` in the
installed library.

---

## Two defects found after the first green run

Recorded because both would have reached an operator mid-maintenance-window.

**`userId` was matched by BSON type, not by value** (self-review). `user_ids` held
`ObjectId`s and the membership test compared the raw stored value, so an account whose `userId`
is the hex *string* matched no user, was filed as an orphan and skipped — a real person left
locked out while the run reported success and exited 0. better-auth's adapter normally stores an
ObjectId there; a custom id generator, an import or a hand-repaired document does not, and that
is exactly the population a repair script meets. Both sides are compared as strings now.

**The runbook command expanded its variables on the wrong side** (third-party review, `codex`,
pre-PR). The first draft said `docker compose exec backend python -m ... --mongodb-uri
"$MONGODB_URI"`. That variable lives in the container, not the operator's shell, so the host
expands it to an empty string and the pre-deploy gate runs against nothing. Fixed at the design
rather than the quoting: the script defaults to `MONGODB_URI` (then `DATABASE_URL`, the name the
frontend container sees) and `DATABASE_NAME`, so the documented command takes no arguments:

```
$ docker compose exec backend python -m app.scripts.migration_account_issuer
```

Verified both ways — zero-arg against a container-shaped environment, and the empty-string case,
which now names the footgun and exits `2`:

```
ERROR - no MongoDB connection string: pass --mongodb-uri, or run where MONGODB_URI (or
DATABASE_URL) is set. If you are using `docker compose exec`, note that $MONGODB_URI in that
command line is expanded by your shell, not the container's.
```

opencode/GLM was the primary reviewer and produced no output in 15 minutes before being
terminated; `codex review` is the documented fallback and is what found the above.

---

## Not covered here

- **Staging and production are untouched.** The backfill needs Atlas credentials held by the
  operator. `main` stays undeployable until it is run — runbook in the script docstring and in
  `docs/STAGING-DEPLOYMENT.md`.
- The demo builds `betterAuth()` with the same adapter, plugins and `emailAndPassword` config as
  `frontend/src/lib/auth.ts` rather than importing that module, which is `server-only` and
  Next-aliased. The credential lookup under test is library code and is identical either way.
