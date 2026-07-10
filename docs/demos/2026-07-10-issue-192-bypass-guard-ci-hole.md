# Issue #192: production auth-bypass guard no longer exempted by the generic CI env var

*2026-07-10T23:01:47Z*

The Next.js middleware has a FATAL guard meant to prevent BYPASS_AUTH=true from ever disabling auth in a production build — but on main it is exempted whenever CI=true, an env var most CI/PaaS/container runtimes set automatically. This demo runs the SAME production artifact (built with no bypass vars, like a real deploy) under different runtime env combinations, against two servers: one from main (port 3020), one from the fix branch (port 3021). Neither server needs a backend — the middleware decision (bypass / FATAL / redirect) is fully observable in HTTP status codes and server logs.

First, the guard code on each side. On main the exemption is the generic CI var; on the branch it is the purpose-built E2E_ALLOW_BYPASS flag, and CI is not consulted at all.

```bash
sed -n "17,27p" /tmp/claude-1000/-home-frankbria-projects-auto-author/f36c3e66-fb03-483c-badb-7f269ac54f62/scratchpad/aa-main/frontend/src/middleware.ts
```

```output
  // Production safety check - prevent accidental bypass in production
  // Allow BYPASS_AUTH in CI/testing environments (GitHub Actions sets CI=true)
  const isCI = process.env.CI === 'true';
  if (bypassAuth && process.env.NODE_ENV === 'production' && !isCI) {
    console.error('FATAL: BYPASS_AUTH cannot be enabled in production environment');
    throw new Error(
      'FATAL SECURITY ERROR: BYPASS_AUTH is enabled in production. ' +
      'This completely disables authentication. Set BYPASS_AUTH=false immediately.'
    );
  }

```

```bash
sed -n "17,31p" /home/frankbria/projects/auto-author/frontend/src/middleware.ts
```

```output
  // Production safety check - prevent accidental bypass in production.
  // The ONLY exemption is the purpose-built E2E_ALLOW_BYPASS=1 flag, set
  // explicitly by the Playwright webServer config and never by real deploys.
  // Deliberately NOT keyed on the generic CI env var (#192): CI=true is set
  // by most CI/PaaS/container runtimes, so it would silently disable auth in
  // any production artifact that happens to run with it.
  const e2eAllowBypass = process.env.E2E_ALLOW_BYPASS === '1';
  if (bypassAuth && process.env.NODE_ENV === 'production' && !e2eAllowBypass) {
    console.error('FATAL: BYPASS_AUTH cannot be enabled in production environment');
    throw new Error(
      'FATAL SECURITY ERROR: BYPASS_AUTH is enabled in production. ' +
      'This completely disables authentication. Set BYPASS_AUTH=false immediately.'
    );
  }

```

Both artifacts are production builds made with NO bypass variables (BETTER_AUTH_SECRET only) — the scenario is a real deploy artifact whose runtime environment happens to carry stray vars. **Scenario 1 — the bug on main**: run the main artifact with BYPASS_AUTH=true and CI=true (the combination any containerized CI/PaaS runtime can produce). An unauthenticated request to /dashboard should have been blocked or fatal — instead it renders: auth is silently disabled.

```bash
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/f36c3e66-fb03-483c-badb-7f269ac54f62/scratchpad/aa-main/frontend && BETTER_AUTH_SECRET=test-secret-for-ci-minimum-32-characters-long-safe-for-testing BYPASS_AUTH=true CI=true npx next start -p 3020 > /tmp/claude-1000/-home-frankbria-projects-auto-author/f36c3e66-fb03-483c-badb-7f269ac54f62/scratchpad/main-ci.log 2>&1 & PID=$!; for i in $(seq 1 30); do curl -so /dev/null http://localhost:3020/ && break; sleep 1; done; echo "--- GET /dashboard (no session cookie) ---"; curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:3020/dashboard; curl -s http://localhost:3020/dashboard | grep -o "<title>[^<]*</title>" | head -1; kill $PID 2>/dev/null; echo "--- server log (middleware) ---"; grep -a -o "BYPASS_AUTH enabled.*" /tmp/claude-1000/-home-frankbria-projects-auto-author/f36c3e66-fb03-483c-badb-7f269ac54f62/scratchpad/main-ci.log | head -1
```

```output
--- GET /dashboard (no session cookie) ---
HTTP 200
<title>Auto Author</title>
--- server log (middleware) ---
BYPASS_AUTH enabled - authentication is disabled for testing
```

**Scenario 2 — the fix**: identical runtime environment (BYPASS_AUTH=true, CI=true) against the branch artifact. CI no longer exempts the guard: the request fails closed with HTTP 500 and the FATAL security error in the server log. Auth cannot be silently disabled in a production build by the generic CI var.

```bash
cd /home/frankbria/projects/auto-author/frontend && BETTER_AUTH_SECRET=test-secret-for-ci-minimum-32-characters-long-safe-for-testing BYPASS_AUTH=true CI=true npx next start -p 3021 > /tmp/claude-1000/-home-frankbria-projects-auto-author/f36c3e66-fb03-483c-badb-7f269ac54f62/scratchpad/branch-ci.log 2>&1 & PID=$!; for i in $(seq 1 30); do curl -so /dev/null http://localhost:3021/ && break; sleep 1; done; echo "--- GET /dashboard (no session cookie) ---"; curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:3021/dashboard; kill $PID 2>/dev/null; echo "--- server log (guard) ---"; grep -a -o "FATAL SECURITY ERROR.*" /tmp/claude-1000/-home-frankbria-projects-auto-author/f36c3e66-fb03-483c-badb-7f269ac54f62/scratchpad/branch-ci.log | head -1
```

```output
--- GET /dashboard (no session cookie) ---
HTTP 500
--- server log (guard) ---
FATAL SECURITY ERROR: BYPASS_AUTH is enabled in production. This completely disables authentication. Set BYPASS_AUTH=false immediately.
```

**Scenario 3 — the E2E path still works**: the branch artifact with BYPASS_AUTH=true plus the purpose-built E2E_ALLOW_BYPASS=1 flag — exactly what the Playwright webServer config now sets for the CI prod-build E2E job (and what no real deploy sets). Bypass is allowed, so the E2E suite keeps functioning.

```bash
cd /home/frankbria/projects/auto-author/frontend && BETTER_AUTH_SECRET=test-secret-for-ci-minimum-32-characters-long-safe-for-testing BYPASS_AUTH=true E2E_ALLOW_BYPASS=1 CI=true npx next start -p 3022 > /tmp/claude-1000/-home-frankbria-projects-auto-author/f36c3e66-fb03-483c-badb-7f269ac54f62/scratchpad/branch-e2e.log 2>&1 & PID=$!; for i in $(seq 1 30); do curl -so /dev/null http://localhost:3022/ && break; sleep 1; done; echo "--- GET /dashboard (no session cookie) ---"; curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:3022/dashboard; kill $PID 2>/dev/null; echo "--- server log ---"; grep -a -o "BYPASS_AUTH enabled.*" /tmp/claude-1000/-home-frankbria-projects-auto-author/f36c3e66-fb03-483c-badb-7f269ac54f62/scratchpad/branch-e2e.log | head -1
```

```output
--- GET /dashboard (no session cookie) ---
HTTP 200
--- server log ---
BYPASS_AUTH enabled - authentication is disabled for testing
```

**Scenario 4 — normal production**: the branch artifact with no bypass vars at all (CI=true still present, as on any CI/PaaS box). Unauthenticated /dashboard gets the ordinary 307 redirect to sign-in — regular auth flow untouched.

```bash
cd /home/frankbria/projects/auto-author/frontend && BETTER_AUTH_SECRET=test-secret-for-ci-minimum-32-characters-long-safe-for-testing CI=true npx next start -p 3023 > /dev/null 2>&1 & PID=$!; for i in $(seq 1 30); do curl -so /dev/null http://localhost:3023/ && break; sleep 1; done; echo "--- GET /dashboard (no session cookie) ---"; curl -s -o /dev/null -w "HTTP %{http_code} -> %{redirect_url}\n" http://localhost:3023/dashboard; kill $PID 2>/dev/null
```

```output
--- GET /dashboard (no session cookie) ---
HTTP 307 -> http://localhost:3023/auth/sign-in?redirect=%2Fdashboard
```

The unit suite pins all of the above plus the defense-in-depth properties: only the exact value E2E_ALLOW_BYPASS=1 exempts (loose values like "true" still throw), and the flag alone is NOT a bypass — BYPASS_AUTH is still required.

```bash
cd /home/frankbria/projects/auto-author/frontend && npx jest src/__tests__/middleware.test.ts 2>&1 | grep -E "✓|✕|Tests:" | sed "s/ ([0-9]* ms)//"
```

```output
    ✓ redirects unauthenticated /profile to sign-in with redirect param
    ✓ allows /profile through with a session cookie
    ✓ allows /profile through with the production (HTTPS) session cookie
    ✓ still redirects unauthenticated /dashboard (regression)
    ✓ leaves public routes alone without a session
    ✓ throws in production even when CI=true (the #192 hole)
    ✓ throws in production with no exemption flag
    ✓ allows bypass in production only with E2E_ALLOW_BYPASS=1
    ✓ still bypasses outside production without the flag
    ✓ E2E_ALLOW_BYPASS alone is not a bypass — auth still enforced
    ✓ only the exact value "1" exempts — loose values still throw
Tests:       11 passed, 11 total
```

Summary: the same production artifact that silently served /dashboard unauthenticated on main (HTTP 200 under BYPASS_AUTH=true + CI=true) now fails closed on the branch (HTTP 500 + FATAL), while the purpose-built E2E_ALLOW_BYPASS=1 flag keeps the CI E2E prod-build job working and normal production auth is unchanged (307 to sign-in). Both acceptance criteria of #192 are demonstrated with outcome evidence.
