# Issue #307: E2E_ALLOW_BYPASS required for backend BYPASS_AUTH in all environments

*2026-07-18T06:02:08Z by Showboat 0.6.1*
<!-- showboat-id: bf6dc03a-c346-4808-a983-0943ffe42830 -->

Demo for PR #310. Proves the acceptance criteria of issue #307 with live uvicorn evidence: the backend `BYPASS_AUTH` only bypasses auth when `E2E_ALLOW_BYPASS=1` is also set — in every non-production environment; production stays hard-blocked with no flag exemption. Four live scenarios map the truth table via HTTP behavior (401 vs 200 on a protected endpoint) and startup log lines.

**Scenario A — dev environment, `BYPASS_AUTH=true` alone (the #307 fix).** Before this change the bypass engaged silently. Now it must be coerced off: a startup warning names the missing flag, and an unauthenticated call to a protected endpoint gets 401 instead of the test user.

```bash
cd /home/frankbria/projects/auto-author/backend
LOG=/tmp/demo-307-a.log
BYPASS_AUTH=true MONGODB_URI=mongodb://localhost:27017 DATABASE_NAME=auto_author_test timeout 60 uv run uvicorn app.main:app --host 127.0.0.1 --port 8100 >$LOG 2>&1 &
for i in $(seq 1 30); do curl -s -o /dev/null http://127.0.0.1:8100/ && break; sleep 1; done
echo "== startup log (coercion warning) =="
grep -m1 "BYPASS_AUTH ignored" $LOG
echo "== GET /api/v1/users/me (no session) =="
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8100/api/v1/users/me
true
```

```output
== startup log (coercion warning) ==
BYPASS_AUTH ignored - set E2E_ALLOW_BYPASS=1 alongside it to bypass auth outside production (#307)
== GET /api/v1/users/me (no session) ==
HTTP 401
```

**Scenario B — dev environment, `BYPASS_AUTH=true` + `E2E_ALLOW_BYPASS=1`.** The intended E2E path must keep working: the bypass engages (startup warning confirms it is active) and the protected endpoint returns the mock test user with HTTP 200.

```bash
cd /home/frankbria/projects/auto-author/backend
LOG=/tmp/demo-307-b.log
BYPASS_AUTH=true E2E_ALLOW_BYPASS=1 MONGODB_URI=mongodb://localhost:27017 DATABASE_NAME=auto_author_test timeout 60 uv run uvicorn app.main:app --host 127.0.0.1 --port 8101 >$LOG 2>&1 &
for i in $(seq 1 30); do curl -s -o /dev/null http://127.0.0.1:8101/ && break; sleep 1; done
echo "== startup log (bypass active) =="
grep -m1 "will be bypassed" $LOG
echo "== GET /api/v1/users/me (no session) =="
curl -s -w "\nHTTP %{http_code}\n" http://127.0.0.1:8101/api/v1/users/me
true
```

```output
== startup log (bypass active) ==
2026-07-17 23:03:04,759 - app.main - WARNING - BYPASS_AUTH is enabled in unset environment. Authentication will be bypassed - DO NOT use in production.
== GET /api/v1/users/me (no session) ==
{"email":"test@example.com","first_name":"Test","last_name":"User","display_name":null,"avatar_url":null,"bio":null,"preferences":{"theme":"dark","email_notifications":true,"marketing_emails":false,"default_writing_style":"conversational","auto_save_interval":3,"default_export_format":"pdf","default_page_size":"letter","include_empty_chapters":false,"writing_reminders":false,"progress_updates":true,"backup_notifications":true},"id":"test-user-id","auth_id":"test-auth-id","created_at":null,"updated_at":null,"role":"user","plan":"free","stripe_customer_id":null,"stripe_subscription_id":null,"book_ids":[]}
HTTP 200
```

**Scenario C — production marker (`ENVIRONMENT=production`, the PM2 path), `BYPASS_AUTH=true` **with** `E2E_ALLOW_BYPASS=1`.** Deliberately stricter than the frontend: no backend E2E path runs production-marked, so the flag grants no exemption here — startup must be blocked with the FATAL error.

```bash
cd /home/frankbria/projects/auto-author/backend
LOG=/tmp/demo-307-c.log
ENVIRONMENT=production BYPASS_AUTH=true E2E_ALLOW_BYPASS=1 BETTER_AUTH_SECRET=production-secret-that-is-at-least-32-characters-long MONGODB_URI=mongodb://localhost:27017 DATABASE_NAME=auto_author_test timeout 30 uv run uvicorn app.main:app --host 127.0.0.1 --port 8102 >$LOG 2>&1
echo "uvicorn exit code: $?"
grep -m1 "FATAL SECURITY ERROR" $LOG
```

```output
uvicorn exit code: 1
  Value error, FATAL SECURITY ERROR: BYPASS_AUTH cannot be enabled in production environment. This would allow unauthorized access to all user data and features. Remove BYPASS_AUTH=true from your production configuration. [type=value_error, input_value='true', input_type=str]
```

**Scenario D — `E2E_ALLOW_BYPASS=1` alone (no `BYPASS_AUTH`).** The flag by itself must never bypass: the protected endpoint still requires a session (401).

```bash
cd /home/frankbria/projects/auto-author/backend
LOG=/tmp/demo-307-d.log
BYPASS_AUTH=false E2E_ALLOW_BYPASS=1 MONGODB_URI=mongodb://localhost:27017 DATABASE_NAME=auto_author_test timeout 60 uv run uvicorn app.main:app --host 127.0.0.1 --port 8103 >$LOG 2>&1 &
for i in $(seq 1 30); do curl -s -o /dev/null http://127.0.0.1:8103/ && break; sleep 1; done
echo "== GET /api/v1/users/me (no session) =="
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8103/api/v1/users/me
true
```

```output
== GET /api/v1/users/me (no session) ==
HTTP 401
```

**AC2 — workflows updated.** Evidence: the CI backend-start step, the backend `.env.example`, and the documented manual bypass commands all carry the flag.

```bash
cd /home/frankbria/projects/auto-author
grep -n "E2E_ALLOW_BYPASS" .github/workflows/tests.yml backend/.env.example frontend/tests/e2e/E2E_TEST_STATUS.md README.md backend/ENV_VAR_CHANGELOG.md | head -10
```

```output
.github/workflows/tests.yml:174:          E2E_ALLOW_BYPASS: '1'
.github/workflows/tests.yml:205:          E2E_ALLOW_BYPASS: '1'
backend/.env.example:43:E2E_ALLOW_BYPASS=0
frontend/tests/e2e/E2E_TEST_STATUS.md:151:> **Note (#272):** the bypass now requires `E2E_ALLOW_BYPASS=1` alongside
frontend/tests/e2e/E2E_TEST_STATUS.md:164:E2E_ALLOW_BYPASS=1
frontend/tests/e2e/E2E_TEST_STATUS.md:169:BYPASS_AUTH=true E2E_ALLOW_BYPASS=1 uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
frontend/tests/e2e/E2E_TEST_STATUS.md:173:BYPASS_AUTH=true E2E_ALLOW_BYPASS=1 NEXT_PUBLIC_BYPASS_AUTH=true npm run dev
README.md:71:- `BYPASS_AUTH=true` enables auth bypass for local development and E2E tests only — and only when `E2E_ALLOW_BYPASS=1` is also set (required in every environment since #272; Playwright's webServer config sets it automatically). In production the middleware rejects it at request time unless the flag is set.
README.md:147:# Requires E2E_ALLOW_BYPASS=1 alongside it in every environment (#272)
README.md:149:# E2E_ALLOW_BYPASS=1
```

**AC3 — tests pin that a bare `BYPASS_AUTH=true` (any environment) does not bypass.** The named pins in the validation class (19/19 passing):

```bash
cd /home/frankbria/projects/auto-author/backend && uv run pytest tests/test_core/test_security.py::TestProductionSecurityValidation -v 2>&1 | grep -E "PASSED|FAILED" | sed "s|tests/test_core/test_security.py::TestProductionSecurityValidation::||"
```

```output
test_bypass_auth_blocked_in_production PASSED [  5%]
test_bypass_auth_ignored_in_development_without_flag PASSED [ 10%]
test_bypass_auth_ignored_in_test_without_flag PASSED [ 15%]
test_bypass_auth_ignored_in_staging_without_flag PASSED [ 21%]
test_bypass_auth_ignored_when_env_not_set_without_flag PASSED [ 26%]
test_bypass_auth_ignored_warns_about_missing_flag PASSED [ 31%]
test_bypass_auth_allowed_with_e2e_flag[NODE_ENV-development] PASSED [ 36%]
test_bypass_auth_allowed_with_e2e_flag[NODE_ENV-test] PASSED [ 42%]
test_bypass_auth_allowed_with_e2e_flag[NODE_ENV-staging] PASSED [ 47%]
test_bypass_auth_allowed_with_e2e_flag[ENVIRONMENT-staging] PASSED [ 52%]
test_bypass_auth_allowed_with_e2e_flag_when_env_not_set PASSED [ 57%]
test_bypass_auth_loose_flag_value_does_not_allow PASSED [ 63%]
test_bypass_auth_blocked_in_production_even_with_flag PASSED [ 68%]
test_bypass_auth_false_allowed_in_production PASSED [ 73%]
test_bypass_auth_blocked_when_environment_is_production PASSED [ 78%]
test_ci_test_secret_rejected_when_environment_is_production PASSED [ 84%]
test_bypass_auth_ignored_when_environment_is_staging_without_flag PASSED [ 89%]
test_bypass_auth_blocked_when_environment_is_production_even_with_flag PASSED [ 94%]
test_e2e_allow_bypass_alone_is_not_a_bypass PASSED [100%]
```

## Verdict — all acceptance criteria VERIFIED

| Criterion | Action | Outcome evidence | Status |
|---|---|---|---|
| AC1: backend `BYPASS_AUTH` gated on the flag in every environment | Four live uvicorn scenarios | bypass alone → startup `BYPASS_AUTH ignored` warning + **401**; both vars → bypass-active warning + **200 with mock test-user JSON**; `ENVIRONMENT=production` **with** flag → **FATAL, exit 1** (no exemption); flag alone → **401** | VERIFIED |
| AC2: docs/scripts + CI backend-start step updated | `grep -n E2E_ALLOW_BYPASS` across the touched files | `tests.yml:174` (backend-start) and `:205` (E2E run), `backend/.env.example:43`, `E2E_TEST_STATUS.md:169` (uvicorn command), README/`ENV_VAR_CHANGELOG` updated | VERIFIED |
| AC3: test pins updated | `pytest TestProductionSecurityValidation -v` | 19/19 pins passing by name: 5 env-gate pins inverted, with-flag pins, loose-value, prod-blocked on both markers even with flag, flag-alone, warning pin | VERIFIED |

Demo produced with showboat; server logs under /tmp/demo-307-*.log (ephemeral). The full backend regression suite is running separately on the branch (environmentally slow locally; CI is the authoritative gate).
