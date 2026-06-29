# Plan 008: Cascade book-delete is atomic (or safely ordered with compensation)

> **Executor instructions**: Follow step by step. Run each verification command
> and confirm before moving on. STOP and report on any STOP condition. Update
> `plans/README.md` when done unless a reviewer maintains the index.
>
> **Drift check (run first)**: `git diff --stat e6980f3..HEAD -- backend/app/db/book_cascade_delete.py backend/app/db/toc_transactions.py`
> Compare the "Current state" excerpt to live code; mismatch → STOP.

## Status

- **Priority**: P2
- **Effort**: M–L
- **Risk**: MED
- **Depends on**: 001 (need a trustworthy test gate before a data-integrity refactor)
- **Category**: bug / data-integrity
- **Planned at**: commit `e6980f3`, 2026-06-21
- **Issue**: https://github.com/frankbria/auto-author/issues/92

## Why this matters

`delete_book_with_cascade` deletes data across six collections in sequence with
**no transaction and no error handling** around the deletes. If any step fails
midway — a transient Mongo error after questions/responses/ratings are already
deleted but before the book document is removed — the database is left
inconsistent: orphaned book with its children gone, or children gone with the
book still listed in the user's `book_ids`. Deletion is destructive and
irreversible, so partial failure is the worst kind. This plan makes the cascade
atomic when MongoDB supports transactions (replica set), and applies a safe,
documented ordering with compensation/logging when it doesn't — mirroring the
pattern the repo already uses for TOC updates.

## Current state

`backend/app/db/book_cascade_delete.py:12-101` — `delete_book_with_cascade`:
- Ownership check (lines 21–26): `books_collection.find_one({"_id": ObjectId(book_id), "owner_id": user_auth_id})`; returns `False` if not owned.
- Best-effort cover-image cleanup wrapped in try/except (lines 31–39) — fine to keep (external storage; failure shouldn't block deletion). Note line 39 is a `print()` (handled by plan 002 if run first; otherwise convert here too).
- **Unprotected sequential deletes (lines 41–79)**, in order:
  1. `chapter_access_logs.delete_many({"book_id": book_id})` (43)
  2. gather `question_ids` from `questions` (50–54)
  3. `question_responses.delete_many({"question_id": {"$in": question_ids}})` (60–62)
  4. `question_ratings.delete_many({"question_id": {"$in": question_ids}})` (65–67)
  5. `questions.delete_many({"book_id": book_id})` (70)
  6. `books_collection.delete_one({"_id": ObjectId(book_id)})` (73)
  7. on success, `users_collection.update_one({"auth_id": user_auth_id}, {"$pull": {"book_ids": book_id}})` (77–79)
  8. audit log (82–97)

None of steps 1–7 is wrapped in a transaction or a try/except; an exception in
the middle propagates and leaves partial state.

**Existing pattern to mirror** — `backend/app/db/toc_transactions.py:16-41`:
```python
    use_transaction = True
    try:
        async with await _client.start_session() as session:
            info = await _client.admin.command('isMaster')
            use_transaction = info.get('setName') is not None  # Has replica set
    except Exception:
        use_transaction = False

    if use_transaction:
        async with await _client.start_session() as session:
            async with session.start_transaction():
                return await _update_toc_internal(book_id, toc_data, user_auth_id, session)
    else:
        return await _update_toc_internal(book_id, toc_data, user_auth_id, None)
```
`_client` is importable from `app.db.base` (see `toc_transactions.py:12`). The
collection objects used in `book_cascade_delete.py` come from
`from .base import books_collection, users_collection, get_collection`.

**Important Mongo constraint**: multi-document transactions require a replica
set. In single-node/test Mongo, transactions aren't available — hence the
conditional pattern above. Motor collection ops accept a `session=` kwarg.

## Commands you will need

| Purpose       | Command                                                      | Expected            |
|---------------|-------------------------------------------------------------|---------------------|
| Backend deps  | `cd backend && uv sync`                                      | exit 0              |
| Lint          | `cd backend && uv run ruff check app/`                       | exit 0              |
| Tests         | `cd backend && uv run pytest tests/`                         | no NEW failures     |
| Targeted test | `cd backend && uv run pytest tests/test_db/test_cascade_delete_atomic.py` | passes |

## Scope

**In scope**:
- `backend/app/db/book_cascade_delete.py` (refactor `delete_book_with_cascade`;
  you may extract an internal `_delete_book_internal(..., session)` helper, like
  `toc_transactions._update_toc_internal`)
- `backend/tests/test_db/test_cascade_delete_atomic.py` (create; create
  `test_db` dir if absent)

**Out of scope**:
- `soft_delete_book` / `restore_soft_deleted_book` (lines 104–188) — single-doc
  updates, already atomic; do not touch.
- The cover-image cleanup behavior (keep it best-effort, outside any transaction
  — image deletion is not transactional with Mongo).
- The audit-log call's content/shape (keep it; just ensure it runs after a
  successful delete).
- Changing the function signature or its `True/False` return contract.

## Git workflow

- Branch: `advisor/008-atomic-cascade-delete`
- Conventional commit, e.g. `fix(db): make cascade book delete atomic with transaction + fallback`.
- Do NOT push or open a PR unless instructed.

## Steps

### Step 1: Extract the delete body into an internal helper that accepts a session

Create `_delete_book_internal(book, book_id, user_auth_id, session)` containing
the current steps 1–7 (the `delete_many`/`delete_one`/`update_one` calls), with
every Mongo operation passed `session=session`. Motor accepts `session=None`
(non-transactional) transparently, so the same helper works both ways — mirror
`toc_transactions._update_toc_internal`. Return the per-collection counts (or a
small dict) so the audit log can be built by the caller.

Keep the ownership check and the best-effort cover-image cleanup in the public
function, BEFORE invoking the helper (image cleanup must not be inside the
transaction).

### Step 2: Wrap the helper in the conditional-transaction pattern

In `delete_book_with_cascade`, after ownership check + image cleanup, detect
replica-set support and run the helper accordingly — copy the structure from
`toc_transactions.py:25-41`:
```python
    use_transaction = True
    try:
        async with await _client.start_session():
            info = await _client.admin.command('isMaster')
            use_transaction = info.get('setName') is not None
    except Exception:
        use_transaction = False

    if use_transaction:
        async with await _client.start_session() as session:
            async with session.start_transaction():
                counts = await _delete_book_internal(book, book_id, user_auth_id, session)
    else:
        counts = await _delete_book_internal(book, book_id, user_auth_id, None)
```
Import `_client` from `.base` (add to the existing import line).

### Step 3: Preserve return contract and audit log

After the deletes succeed, write the audit log (as today, lines 82–97) using
`counts`, and return `True`. If the book document wasn't deleted (book vanished
between the ownership check and the delete), return `False` as before. In the
transactional path, a raised exception will roll the transaction back — let it
propagate to the caller (the endpoint already maps exceptions to a 500).

### Step 4: Fallback-path safety note

In the non-transactional fallback, you cannot get atomicity. Order the deletes
so the **book document and the user `book_ids` pull happen LAST** (children
first, parent last) so a failure leaves the book still discoverable rather than
an orphaned parent with missing children — and log a clear `logger.error(...,
exc_info=True)` if any step raises. (Do not add a print.) This is the same
order the current code already uses; just make it explicit and logged.

**Verify**: `cd backend && uv run ruff check app/` → exit 0.

## Test plan

Create `backend/tests/test_db/test_cascade_delete_atomic.py` (model fixture/db
setup after an existing `backend/tests/` test that hits Mongo). Cover:
- **Happy path**: a book with questions/responses/ratings/access-logs is fully
  removed; user `book_ids` no longer contains the id; function returns `True`.
- **Not owned**: deleting another user's book returns `False` and removes nothing.
- **Failure rollback/containment**: simulate a failure mid-cascade (e.g.
  monkeypatch one collection's `delete_many` to raise). On the transactional
  path assert nothing was deleted (rollback); on the non-transactional path
  assert the book document still exists (parent-last ordering) and the error was
  logged. Use whichever path the test Mongo supports; if single-node, assert the
  containment behavior and document that transaction rollback needs a replica set.

**Verify**: `cd backend && uv run pytest tests/test_db/test_cascade_delete_atomic.py` → passes.

## Done criteria

ALL must hold:

- [ ] `delete_book_with_cascade` runs its deletes via a session-aware internal helper
- [ ] Replica-set detection + `start_transaction()` wraps the deletes when supported (pattern mirrors `toc_transactions.py`)
- [ ] No `print()` remains in `book_cascade_delete.py` (`grep -n "print(" backend/app/db/book_cascade_delete.py` → none)
- [ ] Function still returns `True`/`False` per the original contract; audit log still written on success
- [ ] New test file exists and passes (happy path, not-owned, failure-containment)
- [ ] `cd backend && uv run ruff check app/` exits 0
- [ ] `cd backend && uv run pytest tests/` → no NEW failures
- [ ] No files outside scope modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report if:
- `_client` is not importable from `app.db.base` (find the real client handle
  and report).
- The collections used (`chapter_access_logs`, `questions`,
  `question_responses`, `question_ratings`) are accessed via a different handle
  than `get_collection(...)` such that passing `session=` is non-trivial.
- The excerpt at lines 41–79 differs materially (drift).
- The test Mongo cannot run the suite at all (environment problem — that's
  plan 001's domain; report it).

## Maintenance notes

- True rollback requires a replica set; single-node deployments get
  ordering+logging only. If production is single-node, consider a follow-up to
  run Mongo as a single-node replica set so transactions are available.
- Reviewer should confirm no other code path deletes book children outside this
  function (which would re-introduce orphaning).
- If a new child collection is added later, it must be added to this cascade.
