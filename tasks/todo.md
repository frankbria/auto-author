# Issue #94 (P3.1) — Decompose books.py: map + extract chapters slice

**Branch**: `feature/issue-94-decompose-books-chapters`
**Type**: tech-debt / behavior-preserving move. NOT a redesign.

## Context (drift re-derived)
- `books.py` is now **3,496 lines** (plan was written at 3,184; drift confirmed, ranges re-derived).
- 43 route handlers, no module-level helper functions (every `async def` is a route handler).
- The chapter-management cluster is a **contiguous block, lines 1440–1994**
  (`# Individual Chapter CRUD Operations` → end of `save_tab_state`), fully self-contained
  (uses only module imports; no shared local helpers).

## Chapters slice = 9 handlers moving to `chapters.py`
create_chapter, get_chapters_metadata, get_tab_state, get_chapter, update_chapter,
delete_chapter, list_chapters, update_chapter_status_bulk, save_tab_state.
(Content/analytics/batch-content, questions, drafts stay — each a future slice.)

## Steps
- [x] Step 1 — Decomposition map -> `plans/010-books-decomposition-map.md` (deliverable)
- [x] Step 2 — Route-table snapshot before change (`/tmp/routes_before.txt`, 69 routes)
- [x] Step 3 — Characterization safety net (`test_chapters_characterization.py` route-table identity + existing CRUD/content suites)
- [x] Step 4 — Extracted `chapters.py`; removed moved handlers from `books.py` (3496→2938); trimmed 10 orphaned imports; wired `router.py`
- [x] Step 5 — Routes byte-identical (69, diff clean); full suite **961 passed / 15 skipped, 92.38% cov**; net-new ruff issues cleared

## Result
- `books.py`: 3,496 → 2,938 lines (−558); 43 → 34 handlers
- `chapters.py`: new, 9 handlers, 87% covered
- Route table (method, path) **byte-identical** before/after

## Acceptance criteria (from issue)
- [ ] `plans/010-books-decomposition-map.md` catalogs all handlers by cluster + line range
- [ ] `chapters.py` holds the chapter handlers; `books.py` no longer contains them
- [ ] (method, path) route set byte-identical before/after
- [ ] Characterization tests pass before AND after extraction
- [ ] `books.py` line count meaningfully reduced (report before/after)
- [ ] `ruff check app/` exit 0; `pytest tests/` no NEW failures
- [ ] No URL/schema/status-code changes; no out-of-scope files touched

## Autonomous decisions (no architectural fork)
1. **Characterization tests**: an equivalent behavioral suite already exists
   (`test_books_chapters_crud_coverage.py` + `test_books_chapter_content_coverage.py`
   cover CRUD/metadata/bulk-status/tab-state, happy/auth/not-owned/404). Rather than
   duplicate ~740 lines, add a lean `test_chapters_characterization.py` whose unique
   value is the **route-table identity** assertion (every chapter path still served
   after the move — the one invariant specific to this refactor) plus tab-state smoke
   coverage. Existing suites remain the behavioral net (pass before + after).
2. **Test file location**: `tests/test_api/test_routes/` (where all chapter tests live),
   not the plan's literal `tests/test_api/` — sibling convention wins.
3. **Mount**: `router.include_router(chapters.router, prefix="/books", tags=["chapters"])`
   after the books include; ordering within `chapters.py` preserves metadata/tab-state
   before `{chapter_id}` so no route shadowing.
