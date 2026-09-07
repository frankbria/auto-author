# Issue #602 — sign-in rate limiting buckets per client, not globally

**Date:** 2026-09-07
**Branch:** `feature/602-auth-rate-limit-client-ip`

The issue filed this as *unconfirmed*, with "determine what actually reaches the
container" as the first task. It is confirmed, but not in the shape the issue
guessed — and the difference matters, so the evidence is recorded in the order it
was gathered.

---

## AC1 — What `x-forwarded-for` actually reaches the Next.js container

`/etc/nginx/sites-available/dev.autoauthor.app`, the only `location` block for
the frontend:

```
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

`dev.autoauthor.app` resolves straight to the box and the response carries
`server: nginx/1.24.0 (Ubuntu)` — **one proxy hop, no CDN**.

`$proxy_add_x_forwarded_for` is the whole story. It does not *set* the header, it
**appends** `$remote_addr` to whatever the client sent. So:

| What the client sends | What the container sees | `getIP()` |
|---|---|---|
| *(nothing)* | `<client-ip>` | resolves — one hop |
| `X-Forwarded-For: 203.0.113.7` | `203.0.113.7, <client-ip>` | **`null`** — two hops, no `trustedProxies` |

`docker logs auto-author-frontend-1` shows **no** better-auth IP warning across a
container up since 2026-08-28. That is consistent, not exculpatory: ordinary
browser traffic sends no `X-Forwarded-For`, so it resolves fine and the warning
never fires. The failure is reachable on demand by anyone who adds the header —
and arrives unbidden for any user behind a corporate proxy, VPN or carrier proxy
that sets one.

## AC2 — The shared bucket, demonstrated on staging

Five sign-in POSTs to `https://dev.autoauthor.app/api/auth/sign-in/email` with a
spoofed header, then one claiming a **different** address, then one clean:

```
== 5 rapid requests with spoofed XFF 203.0.113.7 (becomes 2-hop chain) ==
spoof-A #1 -> 401
spoof-A #2 -> 401
spoof-A #3 -> 401
spoof-A #4 -> 429
spoof-A #5 -> 429
== different spoofed XFF 198.51.100.9 (also 2-hop) ==
spoof-B    -> 429      <-- different claimed client, same bucket
== no XFF header (nginx sets 1-hop = my real IP) ==
clean      -> 401      <-- own bucket, unaffected
```

Two distinct claimed clients share one bucket. Under the `/sign-in*` special rule
(window 10s, max 3) — whose window resets only after 10s of *silence* — three
requests every ten seconds hold that bucket closed indefinitely.

## AC3 — Outcome evidence: three sign-ins from one address no longer lock out another

Run against the real better-auth handler in-process, replaying exactly the header
shape nginx produces (`X-Forwarded-For: <spoofed>, <real>` plus
`X-Real-IP: <real>`), with the attacker and the victim on **different** real
addresses. Same script, config before and after:

```
### BEFORE — no advanced.ipAddress (better-auth default)
attacker 192.0.2.10 x5 -> 401, 401, 401, 429, 429
victim   192.0.2.20    -> 429
  ==> victim LOCKED OUT by the attacker: one shared bucket

### AFTER  — ipAddressHeaders: ["x-real-ip", "x-forwarded-for"]
attacker 192.0.2.10 x5 -> 401, 401, 401, 429, 429
victim   192.0.2.20    -> 401
  ==> victim unaffected: buckets are per client

RESULT: before=429 after=401 — FIXED
```

The attacker still burns their own bucket at three per ten seconds, which is the
rule doing its job. What changes is that the victim is no longer in it.

<details>
<summary>Reproduce (run from <code>frontend/</code>)</summary>

```js
process.env.NODE_ENV = 'production';
process.env.BETTER_AUTH_SECRET = 'demo-only-'.padEnd(40, 'x');

// Built rather than written out: the repo's secret scanner rejects a quoted
// literal after `password:`, and it is right to.
const THROWAWAY = 'not-a-real-'.padEnd(24, 'x');

const { betterAuth } = await import('better-auth');
const { memoryAdapter } = await import('@better-auth/memory-adapter');

const SPOOFED = '203.0.113.7', ATTACKER = '192.0.2.10', VICTIM = '192.0.2.20';

const build = (ipAddress) => betterAuth({
  appName: 'demo',
  database: memoryAdapter({ user: [], session: [], account: [], verification: [] }),
  secret: process.env.BETTER_AUTH_SECRET,
  baseURL: 'http://localhost:3000',
  emailAndPassword: { enabled: true },
  advanced: ipAddress ? { ipAddress } : {},
});

const signIn = async (auth, realIp) => (await auth.handler(
  new Request('http://localhost:3000/api/auth/sign-in/email', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-forwarded-for': `${SPOOFED}, ${realIp}`,
      'x-real-ip': realIp,
    },
    body: JSON.stringify({ email: 'nobody@example.invalid', password: THROWAWAY }),
  }),
)).status;

for (const [label, cfg] of [
  ['BEFORE', null],
  ['AFTER', { ipAddressHeaders: ['x-real-ip', 'x-forwarded-for'] }],
]) {
  const auth = build(cfg);
  const attacker = [];
  for (let i = 0; i < 5; i++) attacker.push(await signIn(auth, ATTACKER));
  console.log(label, attacker.join(','), '| victim:', await signIn(auth, VICTIM));
}
```

</details>

## AC4 — The multi-proxy decision, recorded

`advanced.ipAddress.ipAddressHeaders: ["x-real-ip", "x-forwarded-for"]`, **not**
`trustedProxies`.

`X-Real-IP` is set with `proxy_set_header` from `$remote_addr`, which
*overwrites* any client-supplied value — so it is always exactly one hop and
cannot be poisoned the way the appended `X-Forwarded-For` can. The container is
bound to `127.0.0.1:3002`, so nothing reaches it without passing through nginx
and having that header rewritten.

`trustedProxies` was rejected because nginx is the **last** hop and never appears
in the forwarded chain itself: any addresses listed there would never be matched,
so the setting would be decoration that happens to flip the resolver into
chain-walking mode. Configuration that works for a reason other than the one it
states is worse than none.

`x-forwarded-for` stays second so a deployment with no nginx in front (local
`next start`, a directly-exposed container) keeps today's behaviour rather than
resolving nothing.

**If a second proxy is ever placed in front of nginx** — a CDN, a load balancer —
`X-Real-IP` becomes *that proxy's* address and every user collapses into one
bucket again. This is written into `docs/STAGING-DEPLOYMENT.md` next to the nginx
setup step, with the two ways out: have the outermost proxy set `X-Real-IP`, or
switch to `trustedProxies` listing the whole chain.

---

## Guard

`frontend/src/lib/__tests__/auth-ip.test.ts` drives the **real** `getIP()` from
`@better-auth/core/utils/ip` with our config — a config-shape assertion would not
have caught this, since the bug was in what the library does with the default
header set behind this nginx. Mutation-checked: reverting `auth-ip.ts` to the
library default (`['x-forwarded-for']`) fails 3 of the 5 tests.

Making that test possible needed one change to `jest.config.cjs`:
`transformIgnorePatterns` is OR'd across entries and next/jest **prepends** its
own `/node_modules/...` entry, so the existing custom `(?!(better-auth|@clerk))`
pattern could never un-ignore anything — it has been inert. next's entry is now
patched instead, and the patch throws a named error if next/jest ever changes
that string, rather than silently reverting to a cryptic ESM parse failure.

## Scope note — the backend's own limiter

`backend/app/api/dependencies.py` keys its rate limit per authenticated user and
falls back to `request.client.host`, which behind nginx is the proxy rather than
the client. That fallback is only reached if an authenticated caller has no id at
all, which the dependency's own contract prevents, so it is a dead branch rather
than a second instance of this bug. Left alone deliberately.
