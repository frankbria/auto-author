# #307 — Require E2E_ALLOW_BYPASS for backend (FastAPI) BYPASS_AUTH in all environments

**Plan source**: self-authored (issue body has scope bullets, no step plan; no comments).
**Approval**: autonomous — no architectural fork.

## Design decisions (autonomous — safe defaults)

1. **Reuse `E2E_ALLOW_BYPASS=1`** (issue offered a backend-specific flag as an option) —
   one flag, same semantics as the frontend middleware (#272), already documented. Exact
   value `'1'` required, mirroring the frontend.
2. **Gate lives in the `Settings` field_validator (`backend/app/core/config.py`) as a
   coercion**: prod + `BYPASS_AUTH=true` + no flag → raise (FATAL, unchanged); non-prod +
   `BYPASS_AUTH=true` + no flag → **coerce to `False`** + warn ("ignored — set
   E2E_ALLOW_BYPASS=1"); flag `'1'` present → allowed. Chosen over a computed property or
   call-site helper because ~15 existing tests monkeypatch the `settings.BYPASS_AUTH`
   attribute at the object level — coercion at construction keeps every one of them green
   with zero call-site changes (`security.py`, `dependencies.py` untouched).
3. **`main.py validate_production_security()`** prod branch unchanged (validator raises at
   construction first; main.py stays defense-in-depth). Its non-prod warn remains accurate:
   after coercion it only fires when bypass is genuinely active (flag set).
4. **Backend pytest suite needs no new fixtures** — env-gate pins construct real `Settings`
   with monkeypatched env (existing `TestProductionSecurityValidation` pattern).
5. Demo = Showboat only (API-only backend; HTTP 401-vs-200 + startup log lines as evidence).

## Steps

- [x] 1. **TDD pins** — `backend/tests/test_core/test_security.py`
      (`TestProductionSecurityValidation`):
  - [x] invert the 5 "allowed without flag" pins (:432-478 dev/test/staging/unset,
        :529-538 ENVIRONMENT=staging) → without flag, `Settings().BYPASS_AUTH is False`
  - [x] new pins: same 5 env combos **with** `E2E_ALLOW_BYPASS=1` → `is True`
  - [x] loose flag value (`'true'`) → `is False`; prod + flag → still blocked
        (no exemption — backend has no production-marked E2E path)
  - [x] coercion emits a warning naming `E2E_ALLOW_BYPASS` (caplog)
  - [x] keep all prod-blocked pins (:414-430, :480-492, :494-508) unchanged
  - [x] `test_main.py`: update the 4 "allows bypass" docstrings to note the flag gate
        (mock-based function tests still valid)
- [x] 2. **Implement** — `backend/app/core/config.py`: extend the `BYPASS_AUTH` validator
      per decision 2 (add module logger for the coercion warning).
- [x] 3. **CI** — `.github/workflows/tests.yml`: add `E2E_ALLOW_BYPASS: '1'` to the
      Start-backend step env (:166-173) — without it the E2E job loses its backend bypass.
- [x] 4. **Docs** — `backend/.env.example` (:34-43, flag + rule),
      `frontend/tests/e2e/E2E_TEST_STATUS.md` (:167-169 backend uvicorn command),
      `README.md` backend env block (:162-165), `backend/ENV_VAR_CHANGELOG.md` (:48-54
      behavior table), `CLAUDE.md` (:969 — rule now covers backend too), check
      `docs/GITHUB_SECRETS_SETUP.md` for the backend-start env mention.
- [x] 5. **Verify** — `cd backend && uv run pytest tests/` full suite + coverage gate
      (`--cov-fail-under=85` as CI does), lint per repo hooks.

## Acceptance criteria (from issue scope bullets)

- [x] Backend `BYPASS_AUTH` gated on the purpose-built flag in every environment
      (mirroring the frontend middleware).
- [x] Test pins updated (the ~5 env-gate pins inverted + new flag pins; suite green).
- [x] Backend bypass docs/scripts (`BYPASS_AUTH=true uv run uvicorn …`) and the CI
      backend-start step updated.

## Known limitations / out of scope

- Frontend untouched (done in #272). `NEXT_PUBLIC_BYPASS_AUTH` remains frontend-only.
- Residual by design: leaked `BYPASS_AUTH=true` **plus** leaked `E2E_ALLOW_BYPASS=1` still
  bypasses — purpose-built flag, never set by real deploys; deploy-staging secret gate
  unchanged as backstop.
- Object-level `monkeypatch.setattr(settings, "BYPASS_AUTH", True)` in unit tests still
  forces bypass at call sites — that's the test seam for call-site behavior, not an
  env-gate hole.
