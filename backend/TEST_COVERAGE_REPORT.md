# Backend Test Coverage Report

**Report Date:** 2026-06-25
**Measured by:** `cd backend && uv run pytest tests/ --cov=app --cov-report=term-missing`
**Tracking issue:** #117 (P1.14)

---

## Summary

| Metric | Value |
|--------|-------|
| **Overall coverage** | **50%** |
| Total statements | 6,718 |
| Covered | 3,347 |
| Missing | 3,371 |
| Tests | 435 passed, 17 skipped |
| Runtime | ~56s |
| Gate target | 85% (`--cov-fail-under=85`) |

The previously-recorded 41% (2025-10-29) was stale. Real coverage is **50%**, and the
composition of the gap is very different from the old report.

---

## Key finding: most of the gap is dead code, not missing tests

**~1,909 statements (~28% of the backend) are service modules that are not referenced
anywhere in `app/`.** They sit at 0% coverage and drag the whole percentage down. Writing
tests for code nothing calls would be waste — the correct action is deletion (see #90) plus
a coverage omit for the test-data seeder.

| Dead module | Stmts | Referenced in `app/`? |
|-------------|------:|-----------------------|
| `services/content_analysis_service.py` | 329 | no |
| `services/historical_data_service.py` | 313 | no |
| `services/question_feedback_service.py` | 266 | no |
| `services/chapter_error_handler.py` | 265 | only by `chapter_cache_service` |
| `services/chapter_cache_service.py` | 198 | only by `chapter_error_handler` (mutual) |
| `services/user_level_adaptation.py` | 178 | no |
| `services/question_quality_service.py` | 170 | no |
| `services/genre_question_templates.py` | 122 | no |
| `services/chapter_soft_delete_service.py` | 68 | no |
| **Total** | **1,909** | |

Plus `app/populate_db_test_data.py` (34 stmts) is a seed script — it should be added to
`.coveragerc` `omit`, not tested.

**Effect of removal/omit:** denominator drops to ~4,775; coverage rises **50% → ~70%** with
zero new tests. This is the single highest-leverage step toward the 85% gate.
Tracked by child issue (see below).

---

## Real coverage gaps (used modules below 85%)

Ranked by uncovered lines. Excludes dead code (above), test utilities, modules already at
≥85%, and gaps already owned by another open issue.

| Module | Cover | Missing | Criticality | Owner |
|--------|------:|--------:|-------------|-------|
| `api/endpoints/books.py` | 40% | 584 | High (core CRUD) | child + coordinates with #94 |
| `db/toc_transactions.py` | 8% | 197 | High (data integrity) | child |
| `services/question_generation_service.py` | 73% | 71 | Medium | child |
| `api/endpoints/users.py` | 49% | 59 | Medium | child |
| `db/questions.py` | 78% | 52 | Medium | child |
| `core/better_auth_session.py` | 36% | 49 | High (auth) | child (auth cluster) |
| `api/endpoints/sessions.py` | 32% | 40 | Medium | child (session cluster) |
| `api/endpoints/transcription.py` | 40% | 32 | Medium | **#93** |
| `api/endpoints/book_cover_upload.py` | 0% | 33 | Medium | **#93** |
| `api/dependencies.py` | 64% | 29 | High (auth) | child (auth cluster) |
| `api/middleware/session_middleware.py` | 53% | 23 | Medium | child (auth cluster) |
| `db/indexing_strategy.py` | 66% | 23 | Low | — (minor) |
| `db/user.py` | 53% | 22 | Medium | child (session cluster) |
| `services/session_service.py` | 83% | 18 | Low | child (session cluster) |

Modules already ≥85% with small residual gaps (`ai_service.py` 86%, `export_service.py` 94%,
`ai_cache_service.py` 88%, `config.py` 88%, `db/book.py` 90%, etc.) are not worth dedicated
issues — they get incidental coverage as the modules above are tested.

---

## Path to 85%

1. **Remove dead code + omit seed script** → 50% → ~70% (no tests).
2. **Cover `books.py` and `toc_transactions.py`** (the two large used modules) → the bulk of
   the remaining lift.
3. **Cover the auth/session clusters + `users.py`/`questions.py` + `question_generation_service`**
   → clears 85% on the cleaned denominator (need ~+712 covered lines; these modules supply
   far more than that).

### Child issues filed from this triage
- #120 (P1.14.1) — Remove ~1,909 stmts dead service code + omit seed script (50% → ~70%)
- #121 (P1.14.2) — books.py endpoints (40% → 85%); coordinates with #94
- #122 (P1.14.3) — db/toc_transactions.py (8% → 85%)
- #123 (P1.14.4) — auth/session validation cluster (better_auth_session, dependencies, session_middleware)
- #124 (P1.14.5) — session API + db/user cluster
- #125 (P1.14.6) — users.py endpoints + db/questions.py
- #126 (P1.14.7) — question_generation_service.py (73% → 85%)

---

## Notes

- `security.py` is now **100%** (#116/#119) — no longer a gap.
- 17 skipped tests (rate-limiting, some account-deletion and race-condition cases) are
  pre-existing skips, not failures.
- Coverage config: `.coveragerc` (`source = app`, omits tests/migrations/venv).
