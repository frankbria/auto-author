# Issue #337 — [P1.5] TOC add/update/delete/reorder do an unguarded whole-TOC overwrite

_Self-authored plan (issue had acceptance criteria but no implementation plan comment)._

## Problem

`_add_chapter_internal`, `_update_chapter_internal`, `_delete_chapter_internal`, and
`_reorder_chapters_internal` in `backend/app/db/toc_transactions.py` all follow the same
read-modify-write shape:

```
find_one({_id, owner_id})  ->  mutate toc dict in memory  ->  update_one({_id}, {$set: {table_of_contents: toc}})
```

The write filter is `{_id}` only — no `owner_id`, no version guard, no `modified_count` check.
On standalone (non-replica-set) Mongo `session=None`, so this is plain last-write-wins: a
concurrent autosave (`apply_chapter_content_update`) and a chapter mutation silently clobber
each other.

`update_chapter_statuses_with_version_guard` (#159) already does this correctly:
filter on `{_id, owner_id, table_of_contents.version}` with an `$exists:false` fallback for
legacy version-less TOCs, then raise on `modified_count == 0`.

## Design decisions (made autonomously)

1. **Extract one shared CAS helper** rather than copy-pasting the guard into four places.
   Root-cause fix, one implementation, and it dedupes the existing #159 helper too.
2. **`modified_count` (not `matched_count`) is the correct conflict signal here** because every
   one of these writes increments `table_of_contents.version` — the document always differs, so
   `modified_count == 0` can only mean the filter didn't match. Noted in the helper docstring as
   an invariant future writes must preserve.
3. **Leave `_update_toc_internal` alone.** It already has the guard plus a bespoke
   conflict-vs-generic-write-failure distinction (`"Failed to update TOC"`) that tests depend on.
   Not in scope for this issue.
4. **Add `owner_id` to the write filter.** The read already verified ownership; matching the
   hardened helper closes the (theoretical) window where ownership changed mid-operation.
5. **Map the new `ValueError` to HTTP 409 at the API layer.** Without this, a concurrent edit
   would surface as a 400 with a raw internal message — a regression introduced by the fix.
   `reorder_chapters_with_transaction` is imported in `books.py` but has **no endpoint caller**,
   so it needs no mapping.

## Steps

1. **(test-first)** Add interleaved-writer tests to `backend/tests/test_db/test_toc_transactions.py`
   that fire a competing TOC write between the read and the write of each of the four
   operations, and assert (a) `ValueError("Version conflict...")` and (b) the competing writer's
   data survived intact. Parametrized across add / update / delete / reorder. These fail today.
2. **(test-first)** Add a legacy version-less TOC test for the new helper — an unversioned TOC
   must not produce a false conflict on first write.
3. Add `_set_toc_guarded(...)` to `backend/app/db/toc_transactions.py`: compare-and-swap
   `update_one` on `{_id, owner_id, table_of_contents.version}` (with `$exists:false` fallback)
   plus the `modified_count == 0` -> `ValueError` check.
4. Route the four internal functions through it.
5. Refactor `update_chapter_statuses_with_version_guard` to use the same helper (dedupe).
6. Add `version conflict` -> 409 branches to the add / update / delete chapter endpoints in
   `backend/app/api/endpoints/chapters.py`, matching the wording already used at
   `chapters.py:562` and `books.py:1392`.
7. **(test)** API-level tests asserting 409 (not 400) on a concurrent-edit conflict.

## Acceptance criteria (from issue)

- [x] Add the same optimistic-lock filter (`table_of_contents.version` with `$exists:false`
      legacy fallback) and `modified_count` check used by `update_chapter_statuses_with_version_guard`.
- [x] Add an interleaved-writer test proving no lost update on standalone.

## Cross-family review outcomes (opencode / GLM)

| Finding | Severity | Disposition |
|---|---|---|
| Replica-set transaction path surfaces conflict as 500, not 409 | Medium | **Documented, not fixed.** Pre-existing behavior the issue explicitly acknowledges; fixing it means dropping the transaction wrappers, unverifiable without a replica-set fixture. Recorded as a Known Limitation + follow-up. |
| `modified_count == 0` conflated version conflict with book deleted / ownership transferred | Low | **Fixed.** Helper re-reads on filter miss and raises `Book not found` / `Not authorized` / `Version conflict` distinctly; tests updated to assert the sharper contract. |
| `version: null` TOC raises `TypeError` | Low | **Not fixed (YAGNI).** Pre-existing and unreachable — nothing writes null; the `+ 1` increment fails before the guard is consulted. |
| `reorder_chapters_with_transaction` has no live endpoint | Info | Confirmed independently; no 409 mapping needed. Noted in PR. |

## Test strategy

| Criterion | Covered by |
|---|---|
| Optimistic-lock filter on all four ops | interleaved-writer parametrized test (step 1) |
| Legacy `$exists:false` fallback | version-less TOC test (step 2) |
| `modified_count` check | conflict raises `ValueError` (step 1) |
| No lost update on standalone | competing writer's data verified intact post-conflict (step 1) |
| No user-facing regression | endpoint 409 tests (step 7) |
