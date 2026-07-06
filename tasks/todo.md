# Issue #180 — [P0.8] Rate limiting is tenant-wide and bypassable behind nginx

**Plan source**: self-authored (no plan comment on issue). **Approved autonomously** — no architectural fork: the shared store is Mongo via the existing `increment_usage` DAO (#173 pattern; Redis isn't in this stack), and per-user keying follows directly from the verified fact that every rate-limited endpoint already requires session auth.

## Findings (Phase 2)

- `get_rate_limiter` (`app/api/dependencies.py:66`) keys `{client_ip}:{endpoint}` in a plain in-process dict → per-worker (PM2 runs `--workers 2` since #175), resets on restart, never evicted.
- **Issue premise partially stale**: uvicorn 0.35 defaults `proxy_headers=True` with `forwarded_allow_ips=127.0.0.1`; staging nginx sets `X-Forwarded-For` and proxies via localhost. Staging backend logs already show real client IPs (`174.138.89.152:0` — the `:0` port is the ProxyHeadersMiddleware rewrite signature). AC1 still wants it explicit — cheap one-line pin.
- **Every** `get_rate_limiter` call site (books.py, chapters via books, export.py, users.py — verified by scanning all route signatures) also depends on `get_current_user_from_session` → the limiter can depend on it too; FastAPI's per-request dependency cache means zero extra DB hits.
- `increment_usage` (`app/db/usage.py`) is a generic atomic `$inc`+TTL counter keyed `_id = f"{user_id}:{period_key}"` — reusable as-is for rate buckets. TTL index already ensured.
- Only `tests/test_api/test_dependencies.py` exercises the real limiter (via `real_rate_limiter` fixture); all route tests get the conftest no-op fake. Blast radius contained.
- Deprecated `rate_limit()` + `rate_limit_cache` dict: zero production callers (books.py imports `rate_limit` but never uses it). This IS the "never evicted" dict from the issue → delete it.

## Design

- `get_rate_limiter(limit, window)` keeps its signature and 429/`X-RateLimit-*`/`Retry-After` contract. Internals change:
  - New dep param `current_user: Dict = Depends(get_current_user_from_session)`; subject = `auth_id` (fallback `id`/`clerk_id`).
  - Fixed epoch-aligned window: `bucket = int(now // window) * window`; count via `increment_usage(subject, f"rl:{path}:{bucket}", ttl=window*2)` → shared across workers, survives restarts, self-evicting (Mongo TTL).
  - `BYPASS_AUTH` short-circuit unchanged.
  - Unauthenticated callers now 401 before counting (previously counted then 401 in the endpoint) — strictly better.
- `ecosystem.config.template.js`: backend args += ` --proxy-headers --forwarded-allow-ips=127.0.0.1` (pins the uvicorn default per AC1; nginx proxies via localhost).
- Delete deprecated `rate_limit()`, `rate_limit_cache`, and their tests; drop the dead `rate_limit` import in books.py.

## Steps (TDD)

- [x] 1. **RED**: rewrote `TestRateLimiting` (7 tests, real Mongo via `motor_reinit_db`) — all would TypeError against the old signature (no `current_user` param), so failing-first is by construction.
- [x] 2. **GREEN**: Mongo-backed per-user limiter in `dependencies.py`; deleted deprecated `rate_limit`/`rate_limit_cache` + their 3 tests + dead books.py import.
- [x] 3. Ecosystem template: `--proxy-headers --forwarded-allow-ips=127.0.0.1` added.
- [x] 4. Full backend suite: **1084 passed / 13 skipped, 91.87% cov**. Ruff: my files clean; 9 pre-existing books.py dead imports left alone (out of scope, #94 precedent).
- [ ] 5. Deslop scan (clean — small diff, −112 net lines); pre-PR third-party review (opencode/GLM primary); PR; demo; CI gate; docs sync; merge.

## Acceptance criteria

- [ ] Uvicorn runs with `--proxy-headers --forwarded-allow-ips=<nginx>` (ecosystem template; verified staging nginx sends XFF from localhost).
- [ ] Limiter uses a shared store consistent across workers/restarts and keys per authenticated user.
- [ ] Test asserts two different users don't share a bucket.

## Out of scope

- Redis (new infra for what Mongo already does here).
- The per-IP fallback becoming primary for any future unauthenticated endpoints (none exist among rate-limited routes today).
- nginx config changes (already correct on staging).
