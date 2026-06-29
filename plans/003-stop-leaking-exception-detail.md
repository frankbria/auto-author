# Plan 003: API error responses no longer leak internal exception detail to clients

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on. If a
> STOP condition occurs, stop and report — do not improvise. Update
> `plans/README.md` when done unless a reviewer maintains the index.
>
> **Drift check (run first)**: `git diff --stat e6980f3..HEAD -- backend/app/main.py backend/app/api/endpoints/books.py`
> Compare the "Current state" excerpts to live code before proceeding; on
> mismatch, treat as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S–M
- **Risk**: LOW
- **Depends on**: none (do plan 001 first if you want a clean test gate)
- **Category**: security
- **Planned at**: commit `e6980f3`, 2026-06-21
- **Issue**: https://github.com/frankbria/auto-author/issues/87

## Why this matters

The global exception handler returns the raw exception string and class name to
the client, and ~25 endpoint handlers embed `{str(e)}` in their HTTP error
`detail`. That exposes internal implementation details — database errors,
stack-relevant messages, library internals — to anyone hitting the API, which
aids reconnaissance and can leak data embedded in exception messages. The fix:
return generic, stable client messages while logging the full detail
server-side (with `exc_info`). Behavior for callers stays the same (same status
codes); only the leaked text changes.

## Current state

**Global + validation handlers** — `backend/app/main.py`:
```python
141   @app.exception_handler(ValidationError)
142   async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
143       logger.error(f"Pydantic validation error: {exc}", exc_info=True)
144       return JSONResponse(
145           status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
146           content={"detail": f"Validation error: {str(exc.errors())}"},
147       )
...
151   @app.exception_handler(Exception)
152   async def global_exception_handler(request: Request, exc: Exception):
153       logger.error(f"Unhandled exception: {exc}", exc_info=True)
154       return JSONResponse(
155           status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
156           content={
157               "detail": f"An unexpected error occurred: {str(exc)}",
158               "type": str(type(exc).__name__),
159           },
160       )
```
Line 157 leaks `str(exc)`; line 158 leaks the exception class name; line 146
leaks `str(exc.errors())`. (The `RequestValidationError` handler at lines
119–137 returns field-level validation messages — that is standard FastAPI
behavior describing the client's own bad input, and is acceptable; do not
change it.)

**Endpoint handlers that embed `{str(e)}` / `{e}` in `detail`** (from grep):
- `backend/app/core/security.py:142` — `detail=f"Error fetching user: {e}"`
- `backend/app/api/endpoints/book_cover_upload.py:93` — `detail=f"Failed to upload cover image: {str(e)}"`
- `backend/app/api/endpoints/books.py:154,185,247,329,338,416,424,491,567,765,894,1225,2145,3051`
- `backend/app/services/file_upload_service.py:183` — `detail=f"Failed to process image: {str(e)}"`
- `backend/app/api/endpoints/users.py:89,135,226,256,289,329`
- `backend/app/api/endpoints/export.py:97,170`

**Convention**: each affected handler already wraps logic in `try/except` and
raises `HTTPException`. The fix keeps the `raise HTTPException(status_code=...)`
shape but (a) logs the exception server-side and (b) gives `detail` a generic
message.

## Commands you will need

| Purpose       | Command                                          | Expected        |
|---------------|--------------------------------------------------|-----------------|
| Backend deps  | `cd backend && uv sync`                          | exit 0          |
| Lint          | `cd backend && uv run ruff check app/`           | exit 0          |
| Tests         | `cd backend && uv run pytest tests/`             | no NEW failures |

## Scope

**In scope**:
- `backend/app/main.py` (handlers at lines 141–160 only)
- `backend/app/core/security.py` (line 142)
- `backend/app/api/endpoints/books.py` (the listed `detail=` lines)
- `backend/app/api/endpoints/book_cover_upload.py` (line 93)
- `backend/app/api/endpoints/users.py` (the listed lines)
- `backend/app/api/endpoints/export.py` (lines 97, 170)
- `backend/app/services/file_upload_service.py` (line 183)

**Out of scope**:
- The `RequestValidationError` handler (`main.py:119-137`) — standard FastAPI
  client-input feedback, keep as-is.
- Any change to status codes, control flow, or which exceptions are caught.
- `HTTPException(detail=...)` where the detail is a fixed, intentional message
  (e.g. `detail="Book not found"`) — those are fine; only fix ones that
  interpolate `e`/`str(e)`/`exc`.

## Git workflow

- Branch: `advisor/003-stop-leaking-exception-detail`
- Conventional commits, e.g. `fix(security): return generic API error messages, log detail server-side`.
- Do NOT push or open a PR unless instructed.

## Steps

### Step 1: Fix the global and pydantic handlers in main.py

Change `main.py:157-158` so the response no longer includes `str(exc)` or the
class name:
```python
        content={
            "detail": "An unexpected error occurred",
        },
```
(The `logger.error(..., exc_info=True)` on line 153 already records full
detail server-side — keep it.)

Change `main.py:146` to:
```python
        content={"detail": "Validation error"},
```
(Line 143 already logs the full pydantic error server-side — keep it.)

**Verify**: `grep -n "str(exc)\|type(exc).__name__\|str(exc.errors())" backend/app/main.py` → no matches.

### Step 2: Fix endpoint handlers to log + return generic detail

For each listed `detail=f"...{str(e)}"` / `{e}` location, apply this pattern.
Example (`books.py:154`):
```python
# before
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create book: {str(e)}",
        )
# after
    except Exception as e:
        logger.error("Failed to create book", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create book",
        )
```
Rules:
- Keep the existing status code exactly.
- The generic `detail` = the human part of the old message minus the
  `{str(e)}` (e.g. "Failed to update book", "Error retrieving user profile").
- If the module lacks a module logger, add `import logging` +
  `logger = logging.getLogger(__name__)` at the top (match
  `better_auth_session.py:22-26`).
- If a handler that interpolates `e` does NOT already log it, add the
  `logger.error(..., exc_info=True)` line as shown.
- For `file_upload_service.py:183` (a service, not an endpoint) — same
  treatment: log then `detail="Failed to process image"`.

Note: some of these `print(...)` of `e` may already be handled by plan 002 —
if a line already changed, leave plan 002's version and only adjust the
`detail=` string here. There is no conflict: plan 002 touches `print()`, this
plan touches `HTTPException(detail=...)`.

**Verify**: `grep -rn 'detail=f"[^"]*{str(e)}\|detail=f"[^"]*{e}"' backend/app` → no matches.

### Step 3: Lint and test

**Verify**:
- `cd backend && uv run ruff check app/` → exit 0
- `cd backend && uv run pytest tests/` → no NEW failures. If a test asserts a
  500 body contained `str(e)`, see STOP.

## Test plan

- Add a regression test `backend/tests/test_security/test_error_messages.py`
  (create dir if needed; model after an existing `backend/tests/test_api/`
  test for app/client setup). It triggers a handled 500 (e.g. by mocking a DB
  call to raise) on one book endpoint and asserts the JSON `detail` is the
  generic string and does NOT contain the raised exception's message text.
- **Verify**: `cd backend && uv run pytest tests/test_security/test_error_messages.py` → passes.

## Done criteria

ALL must hold:

- [ ] `grep -n "str(exc)\|type(exc).__name__\|str(exc.errors())" backend/app/main.py` → no matches
- [ ] `grep -rn 'detail=f"[^"]*{str(e)}\|detail=f"[^"]*{e}"' backend/app` → no matches
- [ ] `cd backend && uv run ruff check app/` exits 0
- [ ] `cd backend && uv run pytest tests/` → no NEW failures
- [ ] Regression test exists and passes
- [ ] No files outside scope modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report if:
- A test asserts that an error body contains the raw exception text.
- A `detail=` line's surrounding `except` block differs from the pattern (e.g.
  it re-raises a typed domain exception you don't recognize) — report it.
- The `main.py` handlers differ from the excerpts (drift).

## Maintenance notes

- Reviewer should confirm no endpoint relies on the leaked text for legitimate
  client behavior (search the frontend for parsing of `detail` substrings).
- Future pattern: client-facing `detail` is a stable message; full diagnostics
  go to `logger.error(..., exc_info=True)`. Consider adding a correlation/request
  ID to logs so support can map a generic client error to a server log line —
  deferred.
