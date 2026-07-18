# Issue #272: E2E_ALLOW_BYPASS required for auth bypass in all environments

*2026-07-18T01:46:44Z by Showboat 0.6.1*
<!-- showboat-id: 54340c32-978d-48a4-8849-31ca12de203e -->

Demo for PR #308. Proves the acceptance criteria of issue #272 with live server evidence: `BYPASS_AUTH=true` only bypasses auth when `E2E_ALLOW_BYPASS=1` is also set — in every environment. Four live scenarios map the full truth table: production FATAL (no flag), dev bypass-alone ignored, dev bypass with flag, and flag-alone.

**Scenario A — production build, `BYPASS_AUTH=true`, no flag.** The pre-existing FATAL guard must still fire: `next start` forces `NODE_ENV=production`, so a request to a protected route throws instead of bypassing.

```bash
cd /home/frankbria/projects/auto-author/frontend
LOG=/tmp/demo-272-prod.log
BYPASS_AUTH=true npm start -- -p 3100 >$LOG 2>&1 &
SRV=$!
for i in $(seq 1 30); do curl -s -o /dev/null http://localhost:3100/ && break; sleep 1; done
echo "== GET /dashboard (prod build, BYPASS_AUTH=true, no flag) =="
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:3100/dashboard
sleep 1
echo "== server log =="
grep -m1 "FATAL" $LOG
kill $SRV 2>/dev/null
wait $SRV 2>/dev/null
true
```

```output
== GET /dashboard (prod build, BYPASS_AUTH=true, no flag) ==
HTTP 500
== server log ==
FATAL: BYPASS_AUTH cannot be enabled in production environment
```

**Scenario B — dev server, `BYPASS_AUTH=true` alone (the #272 fix).** Before this change the request bypassed auth (200). Now the bypass must be ignored: 307 redirect to sign-in, plus a warning in the server log naming the missing flag.

```bash
cd /home/frankbria/projects/auto-author/frontend
LOG=/tmp/demo-272-dev-noflag.log
BYPASS_AUTH=true BETTER_AUTH_SECRET=test-secret-for-ci-minimum-32-characters-long-safe-for-testing BETTER_AUTH_URL=http://localhost:3101 npm run dev -- -p 3101 >$LOG 2>&1 &
SRV=$!
for i in $(seq 1 90); do curl -s -o /dev/null http://localhost:3101/ && break; sleep 1; done
echo "== GET /dashboard (dev, BYPASS_AUTH=true, no flag) =="
curl -s -o /dev/null -w "HTTP %{http_code} -> %{redirect_url}\n" http://localhost:3101/dashboard
sleep 1
echo "== server log =="
grep -m1 "BYPASS_AUTH ignored" $LOG
kill $SRV 2>/dev/null
wait $SRV 2>/dev/null
true
```

```output
== GET /dashboard (dev, BYPASS_AUTH=true, no flag) ==
HTTP 307 -> http://localhost:3101/auth/sign-in?redirect=%2Fdashboard
== server log ==
⚠️  BYPASS_AUTH ignored - set E2E_ALLOW_BYPASS=1 alongside it to bypass auth (#272)
```

**Scenario C — dev server, `BYPASS_AUTH=true` + `E2E_ALLOW_BYPASS=1`.** The intended E2E path must keep working: with both set, the bypass engages and the protected route serves 200.

```bash
cd /home/frankbria/projects/auto-author/frontend
LOG=/tmp/demo-272-dev-flag.log
BYPASS_AUTH=true E2E_ALLOW_BYPASS=1 BETTER_AUTH_SECRET=test-secret-for-ci-minimum-32-characters-long-safe-for-testing BETTER_AUTH_URL=http://localhost:3102 npm run dev -- -p 3102 >$LOG 2>&1 &
SRV=$!
for i in $(seq 1 90); do curl -s -o /dev/null http://localhost:3102/ && break; sleep 1; done
echo "== GET /dashboard (dev, BYPASS_AUTH=true + E2E_ALLOW_BYPASS=1) =="
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:3102/dashboard
sleep 1
echo "== server log =="
grep -m1 "BYPASS_AUTH enabled" $LOG
kill $SRV 2>/dev/null
wait $SRV 2>/dev/null
true
```

```output
== GET /dashboard (dev, BYPASS_AUTH=true + E2E_ALLOW_BYPASS=1) ==
HTTP 200
== server log ==
⚠️  BYPASS_AUTH enabled - authentication is disabled for testing
```

**Scenario D — dev server, `E2E_ALLOW_BYPASS=1` alone (no `BYPASS_AUTH`).** The flag by itself must never be a bypass: auth is still enforced (307).

```bash
cd /home/frankbria/projects/auto-author/frontend
LOG=/tmp/demo-272-flagonly.log
E2E_ALLOW_BYPASS=1 BETTER_AUTH_SECRET=test-secret-for-ci-minimum-32-characters-long-safe-for-testing BETTER_AUTH_URL=http://localhost:3103 npm run dev -- -p 3103 >$LOG 2>&1 &
SRV=$!
for i in $(seq 1 90); do curl -s -o /dev/null http://localhost:3103/ && break; sleep 1; done
echo "== GET /dashboard (dev, E2E_ALLOW_BYPASS=1 alone) =="
curl -s -o /dev/null -w "HTTP %{http_code} -> %{redirect_url}\n" http://localhost:3103/dashboard
kill $SRV 2>/dev/null
wait $SRV 2>/dev/null
true
```

```output
== GET /dashboard (dev, E2E_ALLOW_BYPASS=1 alone) ==
HTTP 307 -> http://localhost:3103/auth/sign-in?redirect=%2Fdashboard
```

**AC2 — local/E2E workflows updated.** Evidence: the CI E2E job env, the tracked `.env.example` template, the Playwright webServer hardcode (from #271), and the documented `npm run dev` instructions all carry the flag.

```bash
cd /home/frankbria/projects/auto-author
grep -n "E2E_ALLOW_BYPASS" .github/workflows/tests.yml frontend/playwright.config.ts frontend/.env.example frontend/tests/e2e/E2E_TEST_STATUS.md frontend/docs/E2E_TEST_STATUS.md | head -12
```

```output
.github/workflows/tests.yml:202:          E2E_ALLOW_BYPASS: '1'
frontend/playwright.config.ts:103:      E2E_ALLOW_BYPASS: '1'
frontend/.env.example:24:E2E_ALLOW_BYPASS=0
frontend/tests/e2e/E2E_TEST_STATUS.md:151:> **Note (#272):** the bypass now requires `E2E_ALLOW_BYPASS=1` alongside
frontend/tests/e2e/E2E_TEST_STATUS.md:164:E2E_ALLOW_BYPASS=1
frontend/tests/e2e/E2E_TEST_STATUS.md:173:BYPASS_AUTH=true E2E_ALLOW_BYPASS=1 NEXT_PUBLIC_BYPASS_AUTH=true npm run dev
frontend/docs/E2E_TEST_STATUS.md:200:E2E_ALLOW_BYPASS=1
```

**AC3 — tests pin that `BYPASS_AUTH=true` alone (any `NODE_ENV`) does not bypass.** The named pins in the middleware suite (22/22 passing):

```bash
cd /home/frankbria/projects/auto-author/frontend && npx jest src/__tests__/middleware.test.ts --verbose 2>&1 | grep -E "✓|Tests:"
```

```output
    ✓ redirects unauthenticated /profile to sign-in with redirect param (6 ms)
    ✓ allows /profile through with a session cookie (2 ms)
    ✓ allows /profile through with the production (HTTPS) session cookie (1 ms)
    ✓ still redirects unauthenticated /dashboard (regression) (1 ms)
    ✓ leaves public routes alone without a session (1 ms)
    ✓ throws in production even when CI=true (the #192 hole) (26 ms)
    ✓ throws in production with no exemption flag (3 ms)
    ✓ allows bypass in production only with E2E_ALLOW_BYPASS=1 (2 ms)
    ✓ E2E_ALLOW_BYPASS alone is not a bypass — auth still enforced (1 ms)
    ✓ only the exact value "1" exempts — loose values still throw (2 ms)
    ✓ does not bypass with BYPASS_AUTH=true alone and NODE_ENV=test (2 ms)
    ✓ does not bypass with BYPASS_AUTH=true alone and NODE_ENV=development (2 ms)
    ✓ does not bypass with BYPASS_AUTH=true alone and NODE_ENV=staging (1 ms)
    ✓ does not bypass with BYPASS_AUTH=true alone and NODE_ENV unset (5 ms)
    ✓ bypasses outside production when the flag is also set (2 ms)
    ✓ only the exact value "1" enables the non-production bypass (2 ms)
    ✓ only the exact value "true" arms BYPASS_AUTH — case variants do not bypass (1 ms)
    ✓ sets a nonce-based CSP with no unsafe-inline/unsafe-eval and no Clerk origins (1 ms)
    ✓ sets the CSP on authenticated protected routes (1 ms)
    ✓ sets the CSP on the BYPASS_AUTH early-return path (2 ms)
    ✓ forwards x-nonce to the app matching the CSP nonce, overwriting any client-sent value (1 ms)
    ✓ generates a fresh nonce per request (1 ms)
Tests:       22 passed, 22 total
```

## Verdict — all acceptance criteria VERIFIED

| Criterion | Action | Outcome evidence | Status |
|---|---|---|---|
| AC1: `BYPASS_AUTH=true` only takes effect with `E2E_ALLOW_BYPASS=1` in every environment | Four live server scenarios across prod build and dev server | prod+no flag → HTTP 500 + `FATAL` log; dev+no flag → HTTP 307 to `/auth/sign-in` + `BYPASS_AUTH ignored` warn; dev+both vars → HTTP 200 + bypass warn; flag alone → HTTP 307 | VERIFIED |
| AC2: workflows updated (`.env.test`, webServer env, `npm run dev` docs, CI E2E job) | `grep -n E2E_ALLOW_BYPASS` across the touched files | `tests.yml:202` (CI job), `playwright.config.ts:103` (webServer hardcode), `.env.example:24` (tracked template; `.env.test` itself is gitignored), `E2E_TEST_STATUS.md:164,173,200` (docs incl. reuseExistingServer note) | VERIFIED |
| AC3: tests pin `BYPASS_AUTH=true` alone (any `NODE_ENV`) does not bypass | `npx jest src/__tests__/middleware.test.ts --verbose` | Named pins passing: NODE_ENV=test/development/staging/unset → no bypass; exact-`1` and exact-`true` value pins; 22/22 green | VERIFIED |

Demo produced with showboat; server logs under /tmp/demo-272-*.log (ephemeral).
