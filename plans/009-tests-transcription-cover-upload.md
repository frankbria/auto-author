# Plan 009: Transcription and cover-upload endpoints have real test coverage

> **Executor instructions**: Follow step by step. Run each verification command
> and confirm before moving on. STOP and report on any STOP condition. Update
> `plans/README.md` when done unless a reviewer maintains the index.
>
> **Drift check (run first)**: `git diff --stat e6980f3..HEAD -- backend/app/api/endpoints/transcription.py backend/app/api/endpoints/book_cover_upload.py`
> Compare the "Current state" excerpts to live code; mismatch → STOP.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW (adds tests; touches no production code)
- **Depends on**: 001 (test discovery/gate). Coordinates with 004 (path
  traversal) and 008 — if those land first, extend rather than duplicate.
- **Category**: tests
- **Planned at**: commit `e6980f3`, 2026-06-21
- **Issue**: https://github.com/frankbria/auto-author/issues/93

## Why this matters

Two real, user-facing endpoints — audio transcription (voice input, a core
feature) and book cover-image upload — are reported at 0% coverage. Their auth
checks, file-size/format validation, ownership enforcement, and error handling
have no automated safety net, so regressions ship silently. These endpoints
handle file uploads and call external services, exactly the surface where bugs
are costly. This plan adds focused integration tests for both. It writes
**only tests** — no production behavior changes.

## Current state

> Note: the "0%" figure comes from `backend/TEST_COVERAGE_REPORT.md`, which may
> be stale (a separate finding flags doc drift). Step 1 re-measures so you work
> from real numbers. An older `backend/tests/test_api/test_book_cover_upload.py`
> may exist — if so, EXTEND it rather than creating a duplicate.

**`backend/app/api/endpoints/book_cover_upload.py`** — `POST /{book_id}/cover-image`:
- Auth: `Depends(get_current_user_from_session)` (line 23).
- Ownership: 404 if book missing (35–36); 403 if `book.owner_id != current_user.auth_id` (37–40).
- Rate limit: `Depends(get_rate_limiter(limit=5, window=60))` (25).
- Success: processes image, deletes old cover, updates book, audits, returns URLs (42–86).
- Error: 500 with detail (90–94).

**`backend/app/api/endpoints/transcription.py`**:
- `POST /transcribe` (14–75): auth (19); size cap 10 MB → 413 (35–39); format
  validation → 400 (45–49); service call (52–56); service error → 500 (58–62);
  generic 500 (70–75).
- `GET /transcribe/status` (137–157): auth; returns capabilities dict.
- `POST /transcribe/validate` (159–213): auth; size/format checks; returns
  validation result.
- `WS /transcribe/stream` (77–135): mock streaming — low priority, optional.

**Test conventions** (verified): backend tests live in `backend/tests/`;
API tests in `backend/tests/test_api/` (e.g. `test_export_endpoints.py`,
`test_dependencies.py`). They use FastAPI's test client / httpx and existing
auth fixtures. Model new tests on `backend/tests/test_api/test_export_endpoints.py`
for app setup and auth mocking. The repo runs tests with
`cd backend && uv run pytest tests/`. Auth bypass for tests is available via
`BYPASS_AUTH=true` (config rejects it only in production).

## Commands you will need

| Purpose            | Command                                                                 | Expected |
|--------------------|------------------------------------------------------------------------|----------|
| Backend deps       | `cd backend && uv sync`                                                 | exit 0   |
| Measure coverage   | `cd backend && uv run pytest --cov=app tests/ --cov-report=term-missing` | report   |
| Cover-upload tests | `cd backend && uv run pytest tests/test_api/test_book_cover_upload.py`  | pass     |
| Transcription tests| `cd backend && uv run pytest tests/test_api/test_transcription.py`      | pass     |

## Scope

**In scope** (tests + fixtures only):
- `backend/tests/test_api/test_book_cover_upload.py` (create or extend)
- `backend/tests/test_api/test_transcription.py` (create)
- Reuse/extend existing fixtures in `backend/tests/conftest.py` (only if a
  needed fixture is missing; prefer reusing what's there)

**Out of scope**:
- Any change to `transcription.py`, `book_cover_upload.py`, or the services they
  call. (If a test reveals a real bug, STOP and report it — do not fix
  production code in this plan.)
- The WebSocket streaming endpoint deep-testing (the mock implementation makes
  it low-value; a single "accepts connection" smoke test is optional).
- Raising global coverage to 85% — that is a larger effort; this plan targets
  these two modules.

## Git workflow

- Branch: `advisor/009-tests-transcription-cover-upload`
- Conventional commit, e.g. `test(api): cover transcription and book cover-upload endpoints`.
- Do NOT push or open a PR unless instructed.

## Steps

### Step 1: Re-measure current coverage for the two modules

Run the coverage command and record the actual % for
`app/api/endpoints/transcription.py` and `app/api/endpoints/book_cover_upload.py`
from the `--cov-report=term-missing` output. Note the uncovered line ranges —
those guide which branches your tests must hit.

**Verify**: you have the real current coverage numbers and the missing-line
list for both files (paste into your report).

### Step 2: Cover-upload endpoint tests

In `backend/tests/test_api/test_book_cover_upload.py` (create or extend), add
tests for `POST /api/v1/books/{book_id}/cover-image`:
- **Auth required**: unauthenticated request → 401/403 (per how other tests
  assert auth).
- **Not found**: authenticated user, nonexistent `book_id` → 404.
- **Ownership enforced**: authenticated user A uploading to user B's book → 403.
- **Happy path**: owner uploads a small valid image (mock
  `file_upload_service.process_and_save_cover_image` to return fake URLs) →
  200 with `cover_image_url`/`cover_thumbnail_url`; assert `update_book` called.
- **Old cover cleanup**: when the book already has `cover_image_url`, assert
  `delete_cover_image` is invoked with the old URLs.
- **Service failure**: mock the service to raise → 500.

Mock the external image processing and DB calls (do not write real files or hit
real storage). Follow the mocking style already used in
`backend/tests/test_api/`.

**Verify**: `cd backend && uv run pytest tests/test_api/test_book_cover_upload.py` → all pass.

### Step 3: Transcription endpoint tests

In `backend/tests/test_api/test_transcription.py` (create), add tests:
- `POST /transcribe`:
  - **Auth required** → 401/403 unauthenticated.
  - **Too large**: `audio.size > 10MB` → 413.
  - **Bad format**: mock `transcription_service.validate_audio_format` → False
    → 400.
  - **Happy path**: mock `validate_audio_format` → True and
    `transcription_service.transcribe_audio` → a success result → 200 with the
    transcript payload.
  - **Service error**: mock `transcribe_audio` to return `status == "error"` → 500.
- `GET /transcribe/status`: authenticated → 200 with the capabilities keys
  (`status`, `supported_formats`, `supported_languages`, `max_file_size`,
  `features`).
- `POST /transcribe/validate`: valid sample → `{"valid": True, ...}`; oversized →
  `{"valid": False, ...}`; bad format → `{"valid": False, ...}`.

Mock the transcription service throughout (no AWS calls, no real audio).

**Verify**: `cd backend && uv run pytest tests/test_api/test_transcription.py` → all pass.

### Step 4: Confirm coverage moved

Re-run the coverage command from Step 1.

**Verify**: coverage for both modules is materially higher than the Step-1
baseline (target: the auth/validation/error branches above are now exercised;
report the new numbers).

## Test plan

The tests above ARE the deliverable. They must assert real behavior (status
codes, response keys, that mocked collaborators were called with expected args)
— not merely that a call returns without raising. Avoid asserting on internal
implementation detail beyond the documented contract.

## Done criteria

ALL must hold:

- [ ] `backend/tests/test_api/test_transcription.py` exists with the cases above; all pass
- [ ] `backend/tests/test_api/test_book_cover_upload.py` exists/extended with the cases above; all pass
- [ ] Coverage for `transcription.py` and `book_cover_upload.py` is higher than the Step-1 baseline (numbers in report)
- [ ] No production source files modified (`git status` shows only test/fixture changes)
- [ ] `cd backend && uv run pytest tests/` → no NEW failures elsewhere
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report if:
- A test exposes a real bug in the endpoint (e.g. ownership check missing on a
  path, validation bypassable) — report it; do not fix production code here
  (open it as a follow-up finding).
- Required auth/db fixtures don't exist and can't be reused from `conftest.py`
  without modifying production code.
- The endpoints differ materially from the excerpts (drift).

## Maintenance notes

- If plan 004 (path traversal) lands, add a cover-upload/delete test asserting
  traversal URLs are refused.
- These tests mock external services by design (no AWS/Cloudinary). A separate,
  clearly-marked integration suite could exercise the real providers — deferred.
- Reviewer should verify the mocks assert on call arguments, not just return
  values, so the tests can't silently pass against a broken implementation.
