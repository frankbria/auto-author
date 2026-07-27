# Issue #340 — AI quota + entitlement route-wiring guard

Branch: `feature/issue-340-ai-gate-route-guard`
**Plan source:** self-authored (issue had no plan comment).

## Acceptance criteria
- [ ] Extend the `_walk_effective_routes` completeness pin to assert every AI endpoint declares BOTH deps.
- [ ] Add restricted-user→402 and real-quota→429 route-level tests parameterized across all 10 AI endpoints.

## Findings from exploration (verified, not assumed)
- 10 AI endpoints in `app/api/endpoints/books.py` declare
  `dependencies=[Depends(get_ai_usage_quota()), Depends(get_entitlement_checker(<feature>))]`.
- `tests/conftest.py::fake_get_ai_usage_quota` returns a **fresh** `_always_allow`
  closure per call → no single override key, which is why there is no HTTP-level
  quota test. The rate limiter uses ONE shared `noop_rate_limiter`, which is what
  makes `arm_real_rate_limiter` work.
- Entitlement is not faked; it short-circuits on `BYPASS_AUTH` /
  `PLAN_ENFORCEMENT_ENABLED`, so route tests just monkeypatch settings.
- Route-level `dependencies=[...]` are solved before body validation, so a dummy
  book id + `json={}` reaches the gate (proven by the existing #174 route test at
  `tests/test_api/test_entitlement_gate.py:63`).

## Steps
1. `tests/conftest.py`: make the quota fake return a shared module-level
   `noop_ai_quota` (mirrors `noop_rate_limiter`); add an `arm_real_ai_quota`
   fixture mirroring `arm_real_rate_limiter`.
2. `tests/route_introspection.py` (new): move `_walk_effective_routes` /
   `_route_dependency_calls` out of `test_api/test_rate_limit_routes.py` so two
   test modules can share them. Precedent: `tests/db_guard.py` is already
   imported as `tests.db_guard` from conftest.
3. `tests/test_api/test_rate_limit_routes.py`: import the helpers, drop the
   local copies (behavior unchanged).
4. `tests/test_api/test_ai_gate_routes.py` (new):
   - `EXPECTED_AI_GATED_ROUTES` — the 10 (method, path) pairs, with a length pin.
   - Completeness pin: every one declares BOTH a quota dep and an entitlement dep,
     naming exactly which route lost which.
   - Parameterized restricted-plan → 402 across all 10.
   - Parameterized real-quota-at-cap → 429 across all 10.

## Autonomous decisions (no architectural fork)
- Derive the shared callable by name from the live routes (the #199 approach)
  rather than importing conftest — that import double-executes conftest, a
  documented landmine.
- New test module rather than growing `test_rate_limit_routes.py`: different
  subject, and that file is already long.
- Do NOT assert the entitlement *feature string* per route — out of scope for the
  stated AC.

## Red proof (Phase 11 demo)
Temporarily delete each dep from one route; the pin + the 402/429 tests must fail
and name the route.
