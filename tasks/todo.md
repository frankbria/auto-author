# Issue #214 — [P3.8] Remove dead code: transcription stack + AI cache; fold in N+1 perf cleanups

**Plan source:** self-authored (CodeRabbit only offered to generate a plan; none existed).
**Decision (autonomous, AC-endorsed):** REMOVE both dead subsystems, not wire.

## Why remove (not wire)
- **Transcription `/transcribe` stack**: router never mounted (`router.py` has no transcription include), service falls back to hardcoded mock transcripts, zero production importers. Standalone dead code (#93 only ever tested it on a bare app).
- **`ai_cache_service`**: `redis` is absent from `pyproject.toml`/`uv.lock`, so the import guard is permanently False and every cache op is a no-op. Wiring means provisioning redis on the shared VPS for a cache with zero real dependents — contradicts the project's YAGNI/dead-code ethos. Removal is **behavior-preserving**: cache always misses → always generates fresh; the error-fallback lookup always returns None today. Git preserves history if redis is ever provisioned.

## Verified scope (file:line evidence)
- Transcribe stack (DELETE): `app/api/endpoints/transcription.py`, `app/services/transcription_service.py`, `app/services/transcription_service_aws.py`, `app/schemas/transcription.py`. NOT the live `transcription_enhancement.py` / `enhance-transcription` (books.py) feature.
- Cache: `app/services/ai_cache_service.py` (DELETE) + strip 6 call sites in `ai_service.py` (314/350/367 in `generate_clarifying_questions`, 561/598/614 in `generate_toc_from_summary_and_responses`) + import (33-36). `AICacheError` in `ai_errors.py` (only-defined, unused → remove). Dead config: `REDIS_URL`, `AI_CACHE_TTL`, `AI_CACHE_ENABLED` (keep `AI_MAX_RETRIES` — used by retry logic).
- N+1 (real, fix): `questions.py` `get_questions` (243), `get_ratings_for_chapter` (427), `get_chapter_question_progress` (464). Lines 551/664 already batched (`$in`/`distinct`) — NOT touched.
- Projection: `book.py::get_books_by_user` (63-69) — sole caller is `GET /books/` returning `BookResponse` (uses `toc_items`, never `table_of_contents`). Exclude the heavy `table_of_contents.chapters.content` + `.subchapters.content` HTML blobs.

## Steps
1. Delete dead transcribe files + their tests; clean `__init__`/exports. Tests to delete: `test_api/test_transcription.py`, `test_api/test_transcription_endpoint.py`, `test_services/test_transcription_service.py`, `test_services/test_transcription_service_aws.py`, `test_services_isolated.py` (transcription-only scratch script). KEEP `test_services/test_transcription_enhancement.py`.
2. Delete `ai_cache_service.py`; strip the 2 cached AI methods to generate-only (preserve `cached_content_available = False` + re-raise on error). Remove `AICacheError` + dead cache config. Update `test_services/test_ai_service_errors.py` (drop mock-cache fixture + cache-fallback test; keep error-raising tests on `AIService()`). Delete `test_services/test_ai_cache_service.py`.
3. N+1: replace per-question `find_one` loops with one `$in` lookup + dict map in the 3 functions. TDD: pin correctness (+ query behavior).
4. Projection: add exclusion projection to `get_books_by_user`. TDD: pin content excluded, titles/toc_items/structure intact.
5. Full backend suite + coverage ≥85%; deslop; review; demo (outcome evidence per criterion); PR.

## Acceptance criteria
- [ ] Remove the dead transcription + cache modules (chosen over wiring)
- [ ] Mock-transcript fallback gone (router removed entirely — no mock text served)
- [ ] Replace per-question loops with `$in`/bulk queries
- [ ] Project out `chapters.content` on the list endpoint
