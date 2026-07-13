# Issue #199 — [P2.7] Restore real rate-limit test coverage (limiter is neutered suite-wide)

**Plan source**: self-authored (no plan comment on issue; CodeRabbit comment is only the planner stub).

## Premise verification (done)

- Premise **holds**: `backend/tests/conftest.py:37-55` swaps `deps.get_rate_limiter` for a no-op factory *before* `app.main.app` is imported, so all 26 wired routes captured a never-counting closure at import time. #180's `TestRateLimiting` (test_dependencies.py:123-304) covers the dependency directly + one **synthetic** throwaway-app route — zero tests drive a real 429 through a production route. The one endpoint-level test (`test_export_endpoints.py:463`) is `@pytest.mark.skip`.
- 26 wired call sites (issue says ~27; the extra grep hits are the definition site / import lines). Classes: AI generate ×4 (books.py:1775, 2541, 2679, 2743), TOC ×3 (books.py:713, 835, 1169), export ×4 (export.py:91, 194, 289, 379), avatar ×1 (users.py:229), other ×14 (users/billing/books CRUD/regenerate/transcription).

## Design (autonomous decisions)

**Mechanism**: make the conftest fake factory return ONE shared module-level no-op function (today it returns a fresh closure per call — un-overridable). Every route then captures the *same* callable, so a test can re-arm the real limiter on any production route with a single `app.dependency_overrides[<noop>] = real_get_rate_limiter(limit=N, window=3600)` entry. Idiomatic FastAPI lever; no router rebuild, no import-order surgery.

- Test-trust property: if someone deletes `Depends(get_rate_limiter(...))` from an endpoint, the override never fires → no 429 → test goes RED. Exactly the regression the issue wants pinned.
- The override cap is the test's small cap (per AC: "real limiter with a small cap"), not the route's declared numbers. Buckets are per-path (`rl:{path}:{bucket}`), so setup requests on other paths don't consume the tested bucket.
- `BYPASS_AUTH` patched False for these tests (real limiter short-circuits on it); auth resolves through the client factory's `get_current_user_from_session` override (FastAPI resolves sub-deps through overrides).
- Mongo: `motor_reinit_db` drops the test DB per test → clean `usage_counters`; window=3600 in overrides so no epoch-boundary crossing mid-test.

## Steps

1. **conftest.py**: replace the per-call no-op closure with a shared module-level `noop_rate_limiter`; `fake_get_rate_limiter(limit, window)` returns it. Add fixture `arm_real_rate_limiter` → callable `(limit, window=3600)` that installs `app.dependency_overrides[noop_rate_limiter] = real_get_rate_limiter(...)` + patches `deps.settings.BYPASS_AUTH` False, with teardown restoring both. (AI-quota fake untouched — out of scope.)
2. **New `backend/tests/test_api/test_rate_limit_routes.py`** — one integration test per AC endpoint class, real Mongo, authenticated client, small cap (e.g. limit=2), asserting requests 1..N are not 429 and request N+1 → **429** with `X-RateLimit-Remaining: 0` + `Retry-After` headers:
   - (a) AI generate: `POST /books/{id}/chapters/{cid}/generate-questions` (AI boundary patched per the #182 fixture pattern so first N succeed)
   - (b) TOC: `POST /books/{id}/analyze-summary` (ai_service patched)
   - (c) export: `GET /books/{id}/export/pdf`
   - (d) avatar upload: `POST /users/me/avatar` (small real image, per existing avatar tests)
3. **Wiring completeness pin** (same file): introspection test walking `app.routes` dependant trees asserting every one of the 26 known rate-limited (method, path) pairs still carries the limiter dependency (the shared noop in test env). Protects the other 22 sites the behavioral tests don't hit.
4. **Delete** the superseded skipped `test_export_rate_limiting` block at `test_export_endpoints.py:463-478` (replaced by 2c).
5. Mutation check (quality gate): remove `Depends(get_rate_limiter(...))` from one endpoint → class test + completeness test fail; restore.

## Acceptance criteria

- [x] ≥1 un-skipped integration test per protected endpoint class (AI generate, TOC, export, avatar upload) using the real limiter with a small cap, asserting the Nth+1 request → 429
- [x] No remaining skipped rate-limit endpoint test
- [x] Full backend suite green, coverage ≥85%
