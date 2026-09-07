/**
 * Client-IP resolution for better-auth's rate limiter (issue #602).
 *
 * Kept separate from `auth.ts` (which pulls in `server-only` and the MongoDB
 * driver) so the resolution can be unit-tested against the real library.
 */

/**
 * Headers better-auth reads to identify the client, most trustworthy first.
 *
 * better-auth buckets rate limits by client IP, and its `/sign-in*` rule is
 * 3 requests per 10s. When it cannot resolve an IP it falls back to a single
 * `no-trusted-ip|<path>` bucket **shared by every such request**, so three
 * attempts from anywhere close sign-in for everyone who lands in that bucket —
 * and the window only reopens after 10s of silence.
 *
 * Its default is `x-forwarded-for` alone, which resolves only when the header
 * has exactly one hop (without `trustedProxies`, a longer chain is
 * unresolvable — the leftmost entry is attacker-controlled). Our nginx uses
 * `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for`, which
 * *appends* `$remote_addr` to whatever the client sent. So any request
 * arriving with an `X-Forwarded-For` — a spoofed one, or a real one from a
 * corporate proxy or VPN — became a two-hop chain and dropped into the shared
 * bucket. Verified on staging: five sign-ins with `X-Forwarded-For:
 * 203.0.113.7` returned 401,401,401,429,429, after which a request claiming
 * `198.51.100.9` was also 429.
 *
 * `X-Real-IP` fixes it: nginx sets it with `proxy_set_header` from
 * `$remote_addr`, which *overwrites* any client-supplied value, so it is always
 * exactly one hop and cannot be poisoned. `x-forwarded-for` stays as a fallback
 * for deployments with no nginx in front (local `next start`, direct container).
 *
 * This is preferred over `advanced.ipAddress.trustedProxies` because nginx is
 * the last hop and never appears in the forwarded chain itself — configuring
 * `trustedProxies` here would mean listing addresses that are never matched.
 *
 * **If a second proxy is ever placed in front of nginx** (a CDN, a load
 * balancer), `X-Real-IP` becomes that proxy's address rather than the client's,
 * and this config must change: either have the outermost proxy set `X-Real-IP`,
 * or switch to `trustedProxies` listing every proxy in the chain.
 */
export function getIpAddressConfig() {
  return {
    ipAddressHeaders: ['x-real-ip', 'x-forwarded-for'],
  };
}
