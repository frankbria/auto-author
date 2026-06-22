# Issue #45 — Complete API endpoints (remove mock data, harden error handling, fix integration tests)

Plan source: CodeRabbit comment, adapted to verified codebase state.

## Phase 1 — Remove mock/hardcoded responses
- [ ] **1.1** `transcription.py` WebSocket `stream_transcription` (lines ~94-129): replace mock partial/final transcript messages with a single JSON `{type:"error", code:"NOT_IMPLEMENTED", message:...}` then close. Add comment (needs AWS Transcribe Streaming for production). Leave POST `/transcribe` untouched. Update `/transcribe/status` `features.streaming` → `false`.
- [ ] **1.2** `books.py` `get_question_responses` (line ~926): the `{"responses": [], "status": "not_provided"}` is a legitimate empty-data case. Add a clarifying comment; confirm shape. (No behavior change.)

## Phase 2 — Error handling robustness
- [ ] **2.1** `export_service.py`: wrap `reportlab` / `python-docx` / `html2text` imports in try/except → `PDF_AVAILABLE`/`DOCX_AVAILABLE`/`HTML2TEXT_AVAILABLE` flags; `generate_pdf`/`generate_docx` (and the markdown path) raise descriptive `RuntimeError` if missing. `export.py` pdf/docx routes catch → HTTP 503. `/formats` reports `available` per format.
- [ ] **2.2** Verify `books.py` AI endpoints catch full hierarchy (already do). Replace genuinely-silent `except: pass`/`except: ...` handlers in `session_service.py`, `ai_service.py`, `chapter_error_handler.py` with `logger.*`. Minimal — only where currently silent.

## Phase 3 — Integration test infrastructure
- [ ] **3.1** Rewrite `test_chapter_questions_integration.py.disabled` → `.py`. Drop non-existent services (`DraftGenerationService`, `AnalyticsService`, `QuestionProgressService`, `QuestionResponseService`). Use real `QuestionGenerationService` + `motor_reinit_db` fixture (NOT `app.database.get_database`). Cover: generate → save response → retrieve response → progress.
- [ ] **3.2** Fix `run_test_chapter_tabs_integration.py` → rename to `test_chapter_tabs_integration.py`; fix DB access to `app.db.base`/`motor_reinit_db` (commented `get_database` doesn't exist). Keep `ChapterAccessService`/`ChapterStatusService`/`ChapterMetadataCache`/`ChapterTabIndexManager` (all exist). Align fixtures with `chapter_tabs_fixtures.py`.
- [ ] **3.3** `tests/factories/models.py`: `QuestionFactory.text`→`question_text` (also update `generate_interview_questions` `text=q`), `ResponseFactory.content`→`response_text` (also its metadata `self.content`). Matches `app/models/book.py` + `app/schemas/book.py`.

## Acceptance criteria (issue #45)
- [ ] No hardcoded/mock responses in any endpoint (transcription streaming = explicit NOT_IMPLEMENTED, not fake data)
- [ ] Endpoints query DB properly (verified: already do)
- [ ] Inputs validated / errors handled gracefully (export 503, AI hierarchy)
- [ ] Integration tests verify real data flow (Phase 3)
- [ ] Tests pass; lint clean

## Notes / deviations
- Webhook placeholder left as-is (intentional, per design choice 2).
- Scope confirmed narrow by audit: most endpoints already use real DB/AI.
- Baseline main CI is red (per project memory); merge uses `--admin`/`--no-verify`.
