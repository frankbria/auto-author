# Plan 002: Auth tokens and PII no longer leak into logs or stdout

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on. If
> anything in "STOP conditions" occurs, stop and report — do not improvise.
> When done, update the status row in `plans/README.md` unless a reviewer told
> you they maintain the index.
>
> **Drift check (run first)**: `git diff --stat e6980f3..HEAD -- backend/app/core/better_auth_session.py backend/app/api/endpoints/books.py backend/app/db/book.py`
> If any in-scope file changed, compare the "Current state" excerpts against
> the live code before proceeding; on mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: security
- **Planned at**: commit `e6980f3`, 2026-06-21
- **Issue**: https://github.com/frankbria/auto-author/issues/86

## Why this matters

The session-validation path logs **full session tokens** and **entire session
documents** at `INFO` level, and ~39 `print()` calls across the backend dump
user IDs, database names, and request payloads to stdout. Session tokens are
bearer credentials: anyone who can read application logs (an aggregator, a
shared stdout stream, a misconfigured log sink) can replay them to impersonate
a user. The `print()` calls also leak operational/PII data and bypass the
configured logging system entirely. This is a cheap, high-leverage hardening:
remove the token/PII logging and route the few legitimately useful messages
through the logger at an appropriate level.

## Current state

**Token & full-session logging** — `backend/app/core/better_auth_session.py`:
```python
93        # Debug logging to track down the issue
94        logger.info(f"🔍 DEBUG: Database name: {session_collection.database.name}")
95        logger.info(f"🔍 DEBUG: Collection name: {session_collection.name}")
96        logger.info(f"🔍 DEBUG: Searching for session token: {session_token}")
...
99        total_sessions = await session_collection.count_documents({})
100       logger.info(f"🔍 DEBUG: Total sessions in collection: {total_sessions}")
...
106           logger.warning(f"Session not found for token: {session_token[:10]}...")
107           # Log a sample session to see what's in the database
108           sample_session = await session_collection.find_one({})
109           if sample_session:
110               logger.info(f"🔍 DEBUG: Sample session from DB: {sample_session}")
```
Line 96 logs the full token; line 110 logs an entire session document (which
contains a `token` field). Line 106 logs a 10-char token prefix. Lines 94–95,
99–100 are debug noise that should not run at INFO in production.

**`print()` calls that leak data** (from `grep -rn "print(" backend/app`):
- `backend/app/db/book.py:27` — `print(f"database of the books_collection: {books_collection.database.name}")`
- `backend/app/db/book.py:39` — `print(f"Audit log: {user_auth_id}")`
- `backend/app/db/book.py:52` — `print(f"create_book_error {e}")`
- `backend/app/db/user.py:131` — `print(f"Error deleting user books: {e}")`
- `backend/app/db/book_cascade_delete.py:39` — `print(f"Error deleting cover images for book {book_id}: {e}")`
- `backend/app/api/endpoints/books.py:139` — `print("->new_book", new_book)`
- `backend/app/api/endpoints/books.py:151` — `print("->create_book_error", e)`
- `backend/app/api/endpoints/books.py:206` — `print("->get_book", book_id)`
- `backend/app/api/endpoints/books.py:579,581,604,606` — `print(">>> DEBUG summary: current_user", current_user, ...)` and `print(">>> DEBUG found book:", book)`
- `backend/app/api/endpoints/books.py:1352,1421,1546,1595` — `print(f"Error ...: {str(e)}")`
- `backend/app/api/endpoints/books.py:1851,1885` — multi-line debug prints
- `backend/app/api/endpoints/books.py:1973,2078,2234` — `print(f"Failed to log ...: {e}")`
- `backend/app/api/endpoints/users.py:121` — `print(f"Error updating user: {msg}")`
- `backend/app/api/endpoints/export.py:66,140` — `print(f"Failed to log export access: {e}")`

**Leave alone** (not data leaks — they are CLI/help text, not runtime logging):
- `backend/app/core/config.py:21,79,89,106` — these are `print(...)` *inside
  string literals* ("Generate with: python -c '...print...'") — they are help
  messages, NOT executed prints. Do not touch.
- `backend/app/scripts/migration_chapter_tabs.py:320,321,324` — interactive
  CLI script prompts; acceptable in a script.
- `backend/app/populate_db_test_data.py:81,87` — standalone seeding script.
- `backend/app/services/session_service.py:83,87,182` — these are
  `generate_fingerprint(...)` calls/defs, NOT prints (grep false positives).

**Convention to follow**: modules already create a module logger, e.g.
`better_auth_session.py:26` → `logger = logging.getLogger(__name__)`. Use the
same pattern. Use `logger.debug(...)` for diagnostics, `logger.error(...)` for
errors, and never log token/credential values.

## Commands you will need

| Purpose       | Command                                          | Expected            |
|---------------|--------------------------------------------------|---------------------|
| Backend deps  | `cd backend && uv sync`                          | exit 0              |
| Lint          | `cd backend && uv run ruff check app/`           | exit 0              |
| Tests         | `cd backend && uv run pytest tests/`             | no NEW failures     |
| Grep guard    | see Done criteria                                | as specified        |

## Scope

**In scope**:
- `backend/app/core/better_auth_session.py`
- `backend/app/db/book.py`
- `backend/app/db/user.py`
- `backend/app/db/book_cascade_delete.py`
- `backend/app/api/endpoints/books.py`
- `backend/app/api/endpoints/users.py`
- `backend/app/api/endpoints/export.py`

**Out of scope** (do NOT touch):
- `backend/app/core/config.py` (help-text strings, not prints)
- `backend/app/scripts/*`, `backend/app/populate_db_test_data.py` (CLI scripts)
- `backend/app/services/session_service.py` (no real prints there)
- Any change to logging *configuration* (handlers/levels in `main.py`) — that's
  a separate concern; this plan only fixes call sites.
- The control flow of any function — only the logging/print lines change.

## Git workflow

- Branch: `advisor/002-scrub-secrets-and-debug-logging`
- Conventional commits, e.g. `fix(security): stop logging session tokens and PII`.
- Do NOT push or open a PR unless instructed.

## Steps

### Step 1: Remove token/full-session logging in better_auth_session.py

In `backend/app/core/better_auth_session.py`:
- Delete lines 93–100 (the `# Debug logging...` comment and the four
  `logger.info("🔍 DEBUG: ...")` lines including database name, collection name,
  full token, and total count).
- Delete lines 107–110 (the "Log a sample session" comment, the
  `sample_session = await session_collection.find_one({})` lookup, and the
  `logger.info(f"... Sample session from DB: {sample_session}")`). Keep the
  `return None` that follows.
- Change line 106 from
  `logger.warning(f"Session not found for token: {session_token[:10]}...")`
  to `logger.warning("Session not found for provided token")` (no token
  material at all).

Result: no token value, token prefix, or session document is ever logged.

**Verify**: `grep -n "session_token\|sample_session\|DEBUG" backend/app/core/better_auth_session.py`
→ no line logs a token value or a session document (the remaining
`session_token` references are the variable's legitimate use in lookup, not in
a log call).

### Step 2: Convert leaking `print()` calls to logger (or delete pure debug)

For each `print()` location listed in Current state (in the in-scope files):
- If the module has no module logger yet, add at the top:
  `import logging` and `logger = logging.getLogger(__name__)` (match the
  pattern in `better_auth_session.py:22-26`).
- Pure debug breadcrumbs that dump objects — delete them entirely:
  `books.py:139,151,206,579,581,604,606,1851,1885` and `book.py:27,39`.
- Error reporters — convert to `logger.error(...)` WITHOUT interpolating raw
  exception objects that may carry sensitive data; log a static message plus
  `exc_info=True`. Example transform for `book.py:52`:
  ```python
  # before
  print(f"create_book_error {e}")
  # after
  logger.error("Failed to create book", exc_info=True)
  ```
  Apply the same shape to: `book.py:52`, `user.py:131`,
  `book_cascade_delete.py:39`, `books.py:1352,1421,1546,1595,1973,2078,2234`,
  `users.py:121`, `export.py:66,140`.

Do not change any surrounding control flow, return values, or exception
handling — only replace the print line.

**Verify**: `grep -rn "print(" backend/app/db/book.py backend/app/db/user.py backend/app/db/book_cascade_delete.py backend/app/api/endpoints/books.py backend/app/api/endpoints/users.py backend/app/api/endpoints/export.py`
→ returns no matches (excluding any inside-string occurrences, of which these
files have none).

### Step 3: Lint and run tests

**Verify**:
- `cd backend && uv run ruff check app/` → exit 0
- `cd backend && uv run pytest tests/` → no test that passed before now fails
  because of these edits. (If a test asserted on a print/log, see STOP.)

## Test plan

- No new feature tests required; this is removal/redirection of logging.
- Add ONE guard test to prevent regression. Create
  `backend/tests/test_security/test_no_token_logging.py` (create the
  `test_security` dir if absent), modeled structurally after an existing test
  in `backend/tests/test_api/` (imports, async style). The test asserts that
  calling `validate_better_auth_session` with a crafted request whose cookie
  carries a known token does NOT emit that token into captured logs. Use
  pytest's `caplog` fixture: invoke the function (the session lookup will fail
  → returns None, which is fine) and assert the token string does not appear in
  `caplog.text`.
- **Verify**: `cd backend && uv run pytest tests/test_security/test_no_token_logging.py` → passes.

## Done criteria

ALL must hold:

- [ ] `grep -n "Sample session from DB\|Searching for session token" backend/app/core/better_auth_session.py` → no matches
- [ ] `grep -rn "print(" backend/app/api/endpoints/books.py backend/app/api/endpoints/users.py backend/app/api/endpoints/export.py backend/app/db/book.py backend/app/db/user.py backend/app/db/book_cascade_delete.py` → no matches
- [ ] `cd backend && uv run ruff check app/` exits 0
- [ ] `cd backend && uv run pytest tests/` shows no NEW failures vs. before
- [ ] New test `tests/test_security/test_no_token_logging.py` exists and passes
- [ ] No files outside the in-scope list modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report if:
- An existing test asserts on a `print()` output or the removed log lines
  (changing the test is a judgment call for the reviewer).
- A `print()` location's surrounding code differs from the excerpts (drift).
- Removing a debug line would leave an empty block that breaks Python syntax
  (report it; the reviewer will decide whether a `pass` or refactor is right).

## Maintenance notes

- Future code review should reject any `logger.*` or `print` that interpolates
  a token, cookie, password, or full session/user document.
- Consider (deferred) a logging filter that redacts known sensitive keys
  centrally in `main.py` logging config — out of scope here.
- The `session_token[:10]` prefix was also removed: even truncated tokens are
  risky if the token space is small; full removal is the safe default.
