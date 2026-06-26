# Issue #120 — Remove ~1,909 stmts of dead service code + omit seed script

## Verified findings (Phase 2)
All 9 service modules are genuinely dead in `app/` — no importers, no re-exports in
`services/__init__.py`, no dynamic/class-name references. Total **4,983 LOC**.

Non-`app/` references (only 2 of the 9 modules):
- `tests/test_chapter_tabs_api.py` — **collects 0 pytest tests** (manual harness), imports
  `ChapterMetadataCache` + `ChapterErrorHandler` alongside live modules.
- `validate_chapter_tabs.py`, `quick_validate.py`, `simple_validate.py` (backend root) —
  manual dev scripts, **not referenced by any CI/config**.

## Plan
1. Delete 9 dead service modules:
   content_analysis_service, historical_data_service, question_feedback_service,
   chapter_error_handler, chapter_cache_service, user_level_adaptation,
   question_quality_service, genre_question_templates, chapter_soft_delete_service.
2. Add `*/populate_db_test_data.py` to `.coveragerc` `omit`.
3. Handle the 4 manual scripts referencing chapter cache/error modules (decision pending user):
   delete as ghost code, OR surgically drop the dead imports.
4. Re-run backend suite — must stay green (no module-named test files exist).
5. Re-measure coverage; record before/after in PR + CLAUDE.md.

## Acceptance criteria
- [ ] Dead modules removed
- [ ] `populate_db_test_data.py` omitted from coverage
- [ ] Coverage re-measured and recorded (~70% expected)
- [ ] Test suite green
- [ ] Coordinates with #90 (dead-code/bloat cleanup)
