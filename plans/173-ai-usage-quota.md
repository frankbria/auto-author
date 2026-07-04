# Issue #173 — Cap per-user AI usage / OpenAI spend

Per-user generation quota (daily + monthly) persisted in Mongo, incremented on every
AI endpoint, 429 at a configurable cap. Enforced at the dependency layer (reserve
budget *before* the OpenAI call).

## Plan
- [ ] `config.py`: `AI_QUOTA_ENABLED` (True), `AI_QUOTA_DAILY_LIMIT` (50), `AI_QUOTA_MONTHLY_LIMIT` (500). Limit ≤ 0 disables that window.
- [ ] `app/db/usage.py`: atomic `increment_usage(user_id, period_key, ttl_seconds)` on `usage_counters` (`$inc` upsert, ReturnDocument.AFTER, lazy TTL index). Re-export via `database.py`.
- [ ] `dependencies.py`: `get_ai_usage_quota()` factory → checker keyed on `auth_id`; bypass on `BYPASS_AUTH`/disabled; 429 with clear message + Retry-After at cap.
- [ ] `books.py`: add `dependencies=[Depends(get_ai_usage_quota())]` to the 10 AI decorators (analyze-summary, generate-questions, generate-toc, chapter generate-questions, regenerate single/all, generate-draft, transform-style, enhance-text, enhance-transcription).
- [ ] `conftest.py`: no-op quota swap + `real_ai_quota` fixture (mirror `real_rate_limiter`).
- [ ] Tests: DAO increments atomically & keys are independent; real checker rejects Nth+1 in a window (AC); config defaults.

## Notes
- Counter counts *attempts* (rejected calls still increment) — matches the existing in-memory limiter.
- Keys off `auth_id` today; swaps to plan/entitlement when P0.2 lands.
