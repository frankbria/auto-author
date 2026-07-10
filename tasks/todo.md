# Issue #188 — [P1.8] Nested retry wrappers can multiply OpenAI calls to max_retries²

Backend-only. No plan comment on the issue — plan authored from the codebase. **No architectural fork** → approved autonomously.

## Premise verification (drift check)
- Confirmed nesting: `_make_openai_request` (ai_service.py:216) already wraps itself in `_retry_with_backoff`; `generate_clarifying_questions` (:314) and `generate_table_of_contents` (:555) wrap it in a second `_retry_with_backoff`.
- **Premise partially stale**: no actual `AI_MAX_RETRIES²` call multiplication occurs today. The inner layer converts every OpenAI error into an `AIServiceError` subclass (ai_errors.py), and the outer wrapper's `except AIServiceError: raise` re-raises without retrying. A persistent failure makes exactly `AI_MAX_RETRIES` real calls on main.
- Real defects the nesting causes today:
  1. Outer logs a spurious extra "Attempting API call (attempt 1/N)" per request — 4 log records for 3 real calls.
  2. The caller's `correlation_id` is consumed by the outer wrapper; the inner retry loop (where the real attempts/backoff happen) generates its OWN uuid — retry/backoff logs are uncorrelated with the request.
  3. The non-squaring is accidental: it depends on the inner layer never leaking a raw `openai.*` exception. Any future edit to the inner error conversion silently re-introduces squaring.
- AC unchanged and valid: retry at exactly one layer; test pins ≤ AI_MAX_RETRIES requests on persistent failure.

## Plan (TDD)
1. **RED** — new `TestSingleRetryLayer` class in `backend/tests/test_services/test_ai_service_errors.py`:
   - Persistent `openai.RateLimitError`: `generate_clarifying_questions` makes exactly `settings.AI_MAX_RETRIES` calls to `client.chat.completions.create` (AC pin — passes on main too; regression guard against squaring).
   - Same assertion for `generate_table_of_contents` (AC pin).
   - Log-based red test: exactly `AI_MAX_RETRIES` "Attempting API call" log records (caplog) — FAILS on main (outer layer adds one more), proving single-layer.
   - Correlation red test: every "Attempting API call" record carries the same correlation_id (main has two distinct ids: outer's vs inner's uuid).
   - Patch `asyncio.sleep` in ai_service to keep tests fast.
2. **GREEN** — `backend/app/services/ai_service.py`:
   - `_make_openai_request` gains optional `correlation_id: Optional[str] = None`, forwarded to its internal `_retry_with_backoff` (preserves request-scoped correlation in retry logs; the other 5 direct call sites are unaffected).
   - Sites ~314 and ~555: replace `await self._retry_with_backoff(self._make_openai_request, ...)` with direct `await self._make_openai_request(messages=..., temperature=..., max_tokens=..., correlation_id=correlation_id)`.
3. Targeted tests → full backend suite + ruff (ping mongod first — pre-commit hang gotcha).
4. Deslop scan → pre-PR opencode (GLM) review → PR → post-PR review → demo (wire-boundary stub per stale-local-key memory; show attempt-count + single-layer log evidence main vs branch) → CI gate → docs sync → merge.

## Decisions (no fork)
- Keep the retry inside `_make_openai_request`, strip the outer wrappers (AC's first branch) — 5 other call sites already rely on the internal retry; stripping the internal one would touch 7 sites.
- Thread `correlation_id` through rather than dropping it — preserves the only useful thing the outer layer provided.
