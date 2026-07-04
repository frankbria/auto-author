# Issue #177 — Lost update: chapter-content auto-save overwrites entire TOC (P0.5, critical/data-integrity)

## Problem
`update_chapter_content` (3s autosave), `update_book_summary`, and `generate_table_of_contents`
all persist via `update_book`'s version-less `$set` of the WHOLE `table_of_contents` (or history array).
Concurrent writers silently clobber each other → real data loss. `generate_toc` also hardcodes `version:1`.

## Approach (precedent: `update_chapter_statuses_with_version_guard` from #159)
- **`update_chapter_content`** → targeted **arrayFilters `$set`** of the ONE chapter's fields + atomic
  `$inc table_of_contents.version`. Touches only the target chapter, so concurrent saves to *different*
  chapters no longer collide. No version guard / no 409 / no frontend change needed. (AC1: "targeted
  positional/arrayFilters `$set`" branch — better than CAS for the high-frequency autosave path since it
  produces zero false conflicts.)
- **`update_book_summary`** → atomic **`$push` with `$slice:-20`** for `summary_history` (was read-modify-write
  of the whole array → lost revisions). (AC2)
- **`generate_table_of_contents`** → increment version from current, don't hardcode 1. (AC2)

## Tasks
- [ ] `db/book.py`: add `apply_chapter_content_update()` (targeted arrayFilters set + $inc version)
- [ ] `db/book.py`: add `update_book_summary_atomic()` ($push/$slice history)
- [ ] `db/database.py`: re-export both
- [ ] `endpoints/books.py`: rewire `update_chapter_content` to compute changed fields + parent id, call helper
- [ ] `endpoints/books.py`: rewire `update_book_summary` to call helper
- [ ] `endpoints/books.py`: `generate_table_of_contents` version = current+1 (0 default → 1 on first gen)
- [ ] Tests (real Mongo): interleaved chapter-content writers → no lost update; interleaved summary
      writers → both revisions kept; generate_toc increments from current version; subchapter targeted update
- [ ] Full backend suite green, coverage ≥85%

## Ceiling / notes (ponytail)
- arrayFilters path supports top-level + 1 level of subchapter = the data model's max depth
  (matches `add_chapter_with_transaction`). Deeper nesting would need another `$[...]` level.
- `generate_toc` stays a full-TOC replace (intended semantics for an explicit regenerate); only the
  hardcoded version is fixed. Interleaving test focuses on the real bug (content autosave + summary history).
