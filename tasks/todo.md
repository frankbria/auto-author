# Issue #183 — DB indexes never created at startup + unbounded chapter_access_logs (no TTL)

**Plan source**: self-authored from issue body (no plan comment). Issue evidence verified 2026-07-06 — all cited lines accurate: `main.py:69-72` only runs question+user indexes; `ChapterTabIndexManager` (`app/db/indexing_strategy.py`) holds the book `owner_id` indexes and the 90-day access-log TTL but has zero runtime callers (only an unmounted migration script + one integration test). No architectural fork → approved autonomously.

## Problem
- Dashboard `find({owner_id})` (`app/db/book.py:67`) full-scans books.
- `chapter_access_logs` written on ~every read/edit, never expires, analytics queries unindexed.

## Design
Wire `ChapterTabIndexManager(base._db).create_all_indexes()` into the existing lifespan startup block, right after `ensure_user_indexes()`. The manager is already idempotent and per-index try/except (a failed index logs, never bricks startup) — matches the `ensure_user_indexes` pattern.

**One justified deviation**: drop the `chapter_content_text_idx` spec from `create_book_toc_indexes`. No `$text` query exists anywhere in `app/`; a text index over every chapter's full content re-tokenizes on each 3s autosave — pure write amplification with zero readers. AC only requires the `owner_id` and TTL indexes ("or equivalent").

## Changes
- [ ] 1. RED: `backend/tests/test_startup_indexes.py`
  - `create_all_indexes()` → books has `owner_book_id_idx` + `owner_updated_idx`; `chapter_access_logs` has `access_logs_ttl_idx` with `expireAfterSeconds == 7776000` (90 days) + the 4 access-pattern indexes.
  - Idempotent: run twice, no error, indexes intact.
  - No text index on books (regression for the removal).
  - Lifespan wiring: patch `ChapterTabIndexManager.create_all_indexes`, run `app.router.lifespan_context(app)`, assert awaited.
  - NB memory `motor-reinit-drop-index-race`: warm both collections with a real insert before creating/asserting indexes.
- [ ] 2. GREEN: `backend/app/main.py` lifespan — instantiate `ChapterTabIndexManager` on `app.db.base._db` (module attribute at call time, so test rebinds are honored) and await `create_all_indexes()`.
- [ ] 3. GREEN: `backend/app/db/indexing_strategy.py` — remove the text-index spec.
- [ ] 4. Gates: full backend suite + coverage, ruff.
- [ ] 5. opencode (GLM) pre-PR review on branch diff.
- [ ] 6. PR → post-PR review comment → demo (real Mongo: startup creates indexes, TTL visible via `listIndexes`) → CI green → merge.

## Acceptance criteria mapping
1. `create_all_indexes()` runs at lifespan startup, idempotent → change 2 + lifespan-wiring test.
2. 90-day TTL index exists → TTL assertion test + demo `listIndexes` evidence.
3. Test asserts `owner_id` + TTL indexes exist after startup → `test_startup_indexes.py`.
