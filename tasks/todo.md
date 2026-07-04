# Issue #174 — [P0.2] Billing / entitlement gate for paid access (epic)

**Decision (from issue + CodeRabbit plan, matches roadmap):** free-invite beta, single
`free` plan now, Stripe deferred. Deliver the *entitlement hook* so P0.1 can key AI caps
off plan and paid launch isn't a rebuild. **No payment provider built now.**

Adapted from the CodeRabbit plan against the real codebase (verified #173 already ships the
per-user AI quota — the closest analog; entitlement gate mirrors it exactly).

## Ponytail notes (deliberate simplifications)
- Entitlement is a **hook**: today `free` allows every AI feature, so no real beta user is
  ever denied. A named `restricted` plan is the demonstrable deny path (invite revoked /
  trial expired). No paid tiers invented (YAGNI).
- Use the **factory-function** dependency form `get_entitlement_checker(feature)` in
  `dependencies.py` (next to its siblings `get_ai_usage_quota`/`get_rate_limiter`), not a
  class in `security.py`. Matches the two deps already on these exact endpoints and gets
  `Depends`-caching of the user for free. (Plan said class/security.py — deviation noted.)
- One feature string per endpoint (self-documenting, matches quota wiring); registry stays
  trivial (`free` → `{"*"}`). Per-feature paid granularity is future config, no code change.
- Only add `ENTITLEMENT_REQUIRED` (402). Skip `ENTITLEMENT_LIMIT_EXCEEDED` — the over-limit
  case already ships as a 429 in #173; an unused enum is dead code.

## Phase 1 — Decision record + epic decomposition
- [ ] ADR `docs/adr/2026-07-04-beta-entitlement-model.md` (committed): decision, alternatives,
      why paid deferred, entitlement contract (402 `ENTITLEMENT_REQUIRED`), how P0.1 keys caps.
- [ ] GitHub sub-issues (P0.2.x) for deferred Stripe work, referencing #174 + ADR:
      customer/subscription model + webhook (raw-body HMAC verify), checkout/upgrade flow,
      billing settings UI, (optional) invite-gating enforcement. Out of scope this PR.

## Phase 2 — Backend entitlement foundation
- [ ] `app/core/entitlements.py`: `AI_FEATURES`, `PLAN_ENTITLEMENTS` (`free`→`{"*"}`,
      `restricted`→`{}`), `DEFAULT_PLAN="free"`, `is_feature_allowed(plan, feature)`
      (None→free; unknown explicit plan → deny/fail-closed).
- [ ] `plan: str = "free"` on `UserBase` (models/user.py) + `UserResponse` (schemas/user.py);
      set in lazy create dict (`security.py`), legacy `POST /users/` dict (users.py), and
      `read_users_me` UserResponse. No migration (model default covers legacy docs).
- [ ] `config.py`: `PLAN_ENFORCEMENT_ENABLED: bool = True` (+ `.env.example`), bypassed with
      `BYPASS_AUTH`.
- [ ] `errors.py`: `ErrorCode.ENTITLEMENT_REQUIRED`.
- [ ] `error_handlers.py`: `handle_entitlement_denied(feature, plan, request_id)` → 402 via
      `create_error_response`, `X-Entitlement-Plan/-Feature` headers.
- [ ] `dependencies.py`: `get_entitlement_checker(feature)` — mirrors `get_ai_usage_quota`;
      short-circuits on BYPASS_AUTH / !PLAN_ENFORCEMENT_ENABLED; else denies via helper.
- [ ] Wire `Depends(get_entitlement_checker("<feature>"))` onto the 10 AI endpoints in
      `books.py` (alongside existing quota dep).
- [ ] Fixtures: add `plan` to conftest `test_user`/`fake_user` + both BYPASS_AUTH dicts.
- [ ] Tests: `test_entitlements.py` (registry), checker (allow/deny/bypass/disabled),
      route-level 402 `ENTITLEMENT_REQUIRED` on an AI endpoint w/ restricted user.

## Phase 3 — Frontend clear-path (upgrade) UX
- [ ] `useProfileApi.ts`: `plan?: string` on `UserProfile`.
- [ ] `errors/types.ts`: `ErrorType.ENTITLEMENT`; map `402`; severity HIGH.
- [ ] `aiErrorHandler.ts`: classify 402 as `entitlement` (not retryable), upgrade copy,
      carry plan/feature; upgrade branch in `handleAIServiceError`.
- [ ] `ErrorNotification.tsx`: entitlement branch → toast with upgrade CTA (link
      settings/contact), no RetryCountdown.
- [ ] Tests: aiErrorHandler 402 classification; ErrorNotification upgrade CTA.

## Gates
- Backend `uv run pytest --cov=app --cov-fail-under=85`; Frontend jest ≥85/85/75/85;
  lint+typecheck; demo 402→upgrade; CI green.
