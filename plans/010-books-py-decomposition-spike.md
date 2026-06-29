# Plan 010: A safe decomposition plan for the 3,184-line books.py (design + first extraction)

> **Executor instructions**: This is a **design + characterization-test +
> single-extraction** plan, NOT a big-bang refactor. Do the characterization
> tests and the FIRST extraction only; produce the decomposition map as a
> deliverable. Follow steps in order, run every verification command, and STOP
> on any STOP condition rather than improvising a larger refactor. Update
> `plans/README.md` when done unless a reviewer maintains the index.
>
> **Drift check (run first)**: `git diff --stat e6980f3..HEAD -- backend/app/api/endpoints/books.py backend/app/api/endpoints/router.py`
> If `books.py` changed, re-derive line ranges before proceeding.

## Status

- **Priority**: P3
- **Effort**: L (scoped down to: map + characterization tests + one extraction)
- **Risk**: MED (refactor risk is why this is staged and test-gated)
- **Depends on**: 001 (test gate). Strongly benefits from 009-style coverage first.
- **Category**: tech-debt / architecture
- **Planned at**: commit `e6980f3`, 2026-06-21
- **Issue**: https://github.com/frankbria/auto-author/issues/94

## Why this matters

`backend/app/api/endpoints/books.py` is **3,184 lines** with ~50 route handlers
spanning unrelated concerns: book CRUD, chapters, TOC, questions, draft
generation, summaries, exports, analytics, and chapter content. It is ~45× the
backend's median module size and only ~46% covered. Every book-area feature
edits this one file, maximizing merge conflicts, review fatigue, and accidental
coupling. A full split is high-risk for a single pass, so this plan does it
**safely and incrementally**: (1) produce a decomposition map, (2) add
characterization tests that pin current behavior of the first slice to extract,
(3) extract exactly ONE cohesive router (chapters) into its own module behind
the same URL paths, proving the pattern. Subsequent slices become their own
follow-up plans using the map.

## Current state

- `backend/app/api/endpoints/books.py` — 3,184 lines, single `router = APIRouter()`,
  mounted in `backend/app/api/endpoints/router.py:10`:
  ```python
  router.include_router(books.router, prefix="/books", tags=["books"])
  ```
- Other endpoint modules already follow the one-domain-per-file pattern
  (`users.py`, `export.py`, `sessions.py`, `transcription.py`,
  `book_cover_upload.py`) and are wired in `router.py:8-12`. `book_cover_upload.py`
  even carries a header comment "content will be integrated into books.py" —
  i.e. the team already splits routers into files and includes them; this plan
  follows that established structure rather than inventing one.
- Approximate concern clusters inside books.py (from grep of handler decorators
  during audit — **re-derive exact ranges in Step 1**, do not trust these):
  book CRUD; chapters (create/update/delete/list); TOC; questions; drafts;
  summaries; chapter content/analytics. Several `print()`/`str(e)` issues here
  are addressed by plans 002/003 — let those land first to reduce churn.

## Commands you will need

| Purpose       | Command                                                       | Expected |
|---------------|--------------------------------------------------------------|----------|
| Backend deps  | `cd backend && uv sync`                                       | exit 0   |
| List routes   | `cd backend && uv run python -c "from app.main import app; [print(r.methods, r.path) for r in app.routes]"` | route list |
| Lint          | `cd backend && uv run ruff check app/`                        | exit 0   |
| Tests         | `cd backend && uv run pytest tests/`                          | no NEW failures |

## Scope

**In scope**:
- `plans/010-books-decomposition-map.md` (create — the deliverable map)
- `backend/tests/test_api/test_chapters_characterization.py` (create —
  characterization tests for the chapters slice)
- `backend/app/api/endpoints/chapters.py` (create — the ONE extracted router)
- `backend/app/api/endpoints/books.py` (remove only the chapter handlers that
  moved)
- `backend/app/api/endpoints/router.py` (include the new chapters router so URL
  paths are unchanged)

**Out of scope**:
- Extracting more than the chapters slice. TOC, questions, drafts, summaries,
  analytics each get their OWN follow-up plan using the map. Do NOT extract them
  here.
- Changing any URL path, request/response schema, status code, or auth
  dependency. This is a move, not a redesign — clients must see identical behavior.
- Renaming functions or altering business logic.

## Git workflow

- Branch: `advisor/010-books-decomposition-spike`
- Commit per logical step (map; characterization tests; extraction). Conventional
  commits, e.g. `refactor(api): extract chapter endpoints from books.py into chapters.py`.
- Do NOT push or open a PR unless instructed.

## Steps

### Step 1: Produce the decomposition map (deliverable)

Read `books.py` and catalog every route handler: its decorator (method + path),
function name, line range, and which concern cluster it belongs to (book-crud /
chapters / toc / questions / drafts / summaries / content-analytics). Write this
into `plans/010-books-decomposition-map.md` as a table. Identify shared helpers
(module-level functions, imports) each cluster depends on — these determine
extraction order (extract clusters with the fewest shared deps first).

**Verify**: `plans/010-books-decomposition-map.md` exists and lists every
`@router.<method>` handler in books.py with its line range and cluster. Confirm
the handler count matches `grep -c "@router\." backend/app/api/endpoints/books.py`.

### Step 2: Snapshot the current route table

Capture the full route list (paths + methods) before any change, so you can
prove it's identical after extraction.

**Verify**: save the output of the "List routes" command. The `/books/...`
chapter paths you intend to move are present.

### Step 3: Characterization tests for the chapters slice

Before moving code, pin its behavior. In
`backend/tests/test_api/test_chapters_characterization.py`, add tests that
exercise each chapter endpoint you will extract (create/list/update/delete
chapter), asserting current status codes and response shapes for: happy path,
auth-required, and not-owned. Model on `backend/tests/test_api/test_export_endpoints.py`.
Mock DB/services as those tests do. These tests must pass against the CURRENT
(pre-extraction) code.

**Verify**: `cd backend && uv run pytest tests/test_api/test_chapters_characterization.py` → all pass (against unextracted books.py).

### Step 4: Extract the chapters router

Create `backend/app/api/endpoints/chapters.py` with its own
`router = APIRouter()`. Move ONLY the chapter handlers (and any helper used
solely by them) from books.py into it, keeping function bodies byte-for-byte
where possible and preserving the exact path strings. In `router.py`, include
the new router so the final URLs are unchanged — e.g. if chapter paths were
`/books/{book_id}/chapters/...` under the books prefix, mount chapters with the
same effective prefix (`router.include_router(chapters.router, prefix="/books", tags=["chapters"])`)
so no path changes. Remove the moved handlers from books.py.

If a helper is shared between chapters and another cluster still in books.py,
do NOT duplicate it — leave it in books.py (or a shared module) and import it.
If that gets tangled, STOP and report (it means the slice boundary needs the map
revisited).

**Verify**:
- Route table identical: re-run the "List routes" command; diff against Step 2's
  snapshot → the set of (method, path) pairs is unchanged.
- `cd backend && uv run ruff check app/` → exit 0.

### Step 5: Re-run characterization + full suite

**Verify**:
- `cd backend && uv run pytest tests/test_api/test_chapters_characterization.py` → still all pass (behavior preserved through the move).
- `cd backend && uv run pytest tests/` → no NEW failures.

## Test plan

- Characterization tests (Step 3) are the safety net: they pass before AND after
  extraction, proving behavior is preserved.
- No new behavior is introduced, so no new behavioral tests beyond
  characterization.

## Done criteria

ALL must hold:

- [ ] `plans/010-books-decomposition-map.md` exists and catalogs all books.py handlers by cluster + line range
- [ ] `backend/app/api/endpoints/chapters.py` exists with the chapter handlers; books.py no longer contains them
- [ ] The (method, path) route set is byte-identical before and after (Step 2 vs Step 4 snapshots)
- [ ] Characterization tests exist and pass both before and after extraction
- [ ] `books.py` line count is meaningfully reduced (`wc -l backend/app/api/endpoints/books.py`) — report before/after
- [ ] `cd backend && uv run ruff check app/` exits 0; `uv run pytest tests/` → no NEW failures
- [ ] No URL/schema/status-code changes; no files outside scope modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report (do NOT improvise a bigger refactor) if:
- A chapter handler shares a helper with another cluster in a way that can't be
  cleanly imported without moving unrelated code.
- The route table differs after extraction (a path changed — clients would break).
- Characterization tests can't be made to pass against the current code (means
  current behavior is unclear — surface it; don't refactor on an unstable base).
- You find yourself wanting to extract a second cluster — that's a separate plan.

## Maintenance notes

- The remaining clusters (toc, questions, drafts, summaries, analytics) each get
  a follow-up plan modeled exactly on this one, using the Step-1 map and the same
  characterization-then-extract discipline. Do them one at a time.
- Reviewer should scrutinize that no path/schema changed (the whole point is a
  behavior-preserving move) and that shared helpers weren't duplicated.
- Once books.py is decomposed, fold `book_cover_upload.py` in alongside the
  cover/book CRUD slice if it makes sense (its header comment anticipated this).
