# Demo — Issue #339: session cookie `sameSite:"none"` removed CSRF protection

**Date:** 2026-07-27
**Branch:** `feature/339-samesite-lax-csrf` vs pristine `origin/main` (f4c19cf)

Both sides ran against the **same** MongoDB and the **same** environment, on two Next
dev servers (branch :3010, main :3011), so the code is the only variable.

---

## AC1 — `sameSite` is `"lax"`

Real `Set-Cookie` off the wire, from an actual sign-up against each server:

```
$ curl -si -X POST http://localhost:<port>/api/auth/sign-up/email \
    -H 'Content-Type: application/json' \
    -d '{"email":"...","password":"...","name":"Demo 339"}'
```

| | `Set-Cookie: better-auth.session_token` |
|---|---|
| **main** | `... Max-Age=604800; Path=/; HttpOnly; Secure; SameSite=None` |
| **branch** | `... Max-Age=604800; Path=/; HttpOnly; Secure; SameSite=Lax` |

---

## Impact — the CSRF attack actually stops working

Not just "the attribute changed": the attack from the issue was reproduced in a real
Chromium via Playwright, on both sides.

Topology models the production one:
- **victim API** `http://localhost:9098` — same site as the app (host `localhost`)
- **attacker page** `http://127.0.0.1:9099` — different host ⇒ **cross-site**

The attacker page auto-submits a **multipart form POST** at the victim API — the exact
"simple request, no preflight" upload shape called out in the issue
(`POST /users/me/avatar`, book cover).

| step | main | branch |
|---|---|---|
| sign-in | HTTP 200, cookie stored (`sameSite=None`) | HTTP 200, cookie stored (`sameSite=Lax`) |
| **legitimate** same-site app→API credentialed `fetch` | `http 200`, **cookie sent — app works** | `http 200`, **cookie sent — app works** |
| **cross-site** attacker multipart POST | request arrives, **session cookie rode along — CSRF WORKS** | request arrives, **no session cookie — CSRF BLOCKED** |

The cross-site request still *reaches* the server on the branch — the browser simply
withholds the cookie, so it lands unauthenticated. That is the fix working: CORS never
blocked the write, and it still doesn't; the cookie policy is what stops it.

The legitimate row is the control: it proves `lax` did **not** break the real
frontend→backend call. (While building this, an early version of the harness reported
"APP BROKEN" on *both* sides — a stub that didn't answer the CORS preflight, and then
one that answered it with `*` alongside `Allow-Credentials: true`, which is invalid.
The `main` column reading NO is what exposed the harness bug, since `None` always sends.)

### Reproduction

`node csrf-demo-339.js <app-port> <label>` from `frontend/`, with the app running and
mongod up. The script (kept here rather than in the tree, it is throwaway):

```js
const http = require('http');
const { chromium } = require('playwright');
const APP_PORT = process.argv[2], LABEL = process.argv[3];
let received = null;

const victim = http.createServer((req, res) => {
  const origin = req.headers.origin;
  if (origin) {
    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Access-Control-Allow-Credentials', 'true');
  }
  if (req.method === 'OPTIONS') {           // explicit, not "*" — a wildcard is
    res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    res.writeHead(204); res.end(); return;  // invalid with Allow-Credentials: true
  }
  if (req.method === 'POST') {
    received = req.headers.cookie || '';
    req.on('data', () => {});
    req.on('end', () => { res.writeHead(200); res.end('ok'); });
    return;
  }
  res.writeHead(200); res.end('ok');
});

const attacker = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/html' });
  res.end(`<!doctype html><body><form id="f"
    action="http://localhost:9098/users/me/avatar" method="POST"
    enctype="multipart/form-data"><input type="hidden" name="file" value="pwned">
    </form><script>document.getElementById('f').submit();<\/script></body>`);
});

(async () => {
  await new Promise(r => victim.listen(9098, '0.0.0.0', r));
  await new Promise(r => attacker.listen(9099, '0.0.0.0', r));
  const browser = await chromium.launch();
  const ctx = await browser.newContext();
  const page = await ctx.newPage();

  await page.goto(`http://localhost:${APP_PORT}/api/auth/ok`,
    { waitUntil: 'domcontentloaded', timeout: 120000 });
  const status = await page.evaluate(async (port) => (await fetch(
    `http://localhost:${port}/api/auth/sign-in/email`,
    { method: 'POST', headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email: `demo339-${port}@example.com`,
                             password: 'DemoPassword123!' }) })).status, APP_PORT);
  const session = (await ctx.cookies()).find(c => c.name === 'better-auth.session_token');
  console.log(`[${LABEL}] sign-in HTTP ${status}`);
  console.log(`[${LABEL}] cookie stored: ${session ? 'YES' : 'NO'} (sameSite=${session?.sameSite})`);

  received = null;                                  // legitimate same-site leg
  const legit = await page.evaluate(async () => {
    try {
      const r = await fetch('http://localhost:9098/api/v1/books', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' }, body: '{}' });
      return `http ${r.status}`;
    } catch (e) { return `FETCH FAILED: ${e.message}`; }
  });
  console.log(`[${LABEL}] same-site app->API: ${legit}; carried cookie: ` +
    `${received?.includes('better-auth.session_token') ? 'YES — app works' : 'NO — APP BROKEN'}`);

  received = null;                                  // cross-site attack leg
  await page.goto('http://127.0.0.1:9099/');
  await page.waitForTimeout(2500);
  console.log(`[${LABEL}] cross-site POST arrived: ${received !== null ? 'YES' : 'NO'}`);
  console.log(`[${LABEL}] >>> COOKIE RODE ALONG: ` +
    `${received?.includes('better-auth.session_token') ? 'YES — CSRF WORKS' : 'NO — CSRF BLOCKED'}`);

  await browser.close(); victim.close(); attacker.close(); process.exit(0);
})();
```

Observed output:

```
[MAIN]   sign-in HTTP 200
[MAIN]   cookie stored: YES (sameSite=None)
[MAIN]   same-site app->API: http 200; carried cookie: YES — app works
[MAIN]   cross-site POST arrived: YES
[MAIN]   >>> COOKIE RODE ALONG: YES — CSRF WORKS

[BRANCH] sign-in HTTP 200
[BRANCH] cookie stored: YES (sameSite=Lax)
[BRANCH] same-site app->API: http 200; carried cookie: YES — app works
[BRANCH] cross-site POST arrived: YES
[BRANCH] >>> COOKIE RODE ALONG: NO — CSRF BLOCKED
```

---

## AC2 — no genuinely cross-site case exists

Verified rather than assumed, so `"none"` is not needed anywhere:

- `frontend/src/lib/auth.ts` configures **email+password and `twoFactor()` only** — no
  social/OAuth provider, no magic link, so there is no cross-site POST-back.
- Stripe **is** present (`backend/app/api/endpoints/billing.py`, `webhooks.py`), but
  neither flow needs a cross-site cookie:
  - `success_url` / `cancel_url` / `return_url` all point at
    `{frontend_base}/dashboard/settings…` and are reached by a **top-level GET
    navigation** from Stripe — which `lax` *does* send.
  - `POST /webhooks/stripe` is deliberately unauthenticated and verified by the **HMAC
    signature over the raw body**, not by a cookie.
- Every frontend→backend hop is same-site (same-site is the registrable domain and
  ignores port/subdomain): `localhost:3000 → localhost:8000`, and
  `dev.autoauthor.app → api.dev.autoauthor.app` (both `autoauthor.app`).

---

## AC3 — CORS does not reflect arbitrary origins

`main` boots happily with a wildcard, and Starlette then mirrors the attacker's origin:

```
$ BACKEND_CORS_ORIGINS='*' ENVIRONMENT=production ... python -c "import app.main; ..."
MAIN: APP IMPORTED with wildcard CORS -> startup proceeds
MAIN: response headers for attacker origin ->
      {'access-control-allow-origin': 'https://evil.example', 'vary': 'Origin'}
```

The branch refuses to start:

```
$ BACKEND_CORS_ORIGINS='*' ENVIRONMENT=production ... python -c "import app.main"
RuntimeError: Application startup blocked: BACKEND_CORS_ORIGINS contains a wildcard
('*'). Combined with cookie authentication this reflects arbitrary origins back on
credentialed requests. List explicit origins instead.

$ BACKEND_CORS_ORIGINS='https://dev.autoauthor.app' ENVIRONMENT=production ...
APP IMPORTED — startup proceeds normally
```

No committed config sets a wildcard (`deploy-staging.yml`, `scripts/deploy*.sh`,
`backend/.env.example` all list explicit origins), so this blocks a misconfiguration,
not a working setup.
