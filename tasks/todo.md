# Issue #187 — Batch question-response save skips ownership/existence check (P1.7, high/data-integrity)

**Plan source**: self-authored (no plan comment on issue — only a CodeRabbit
enrichment stub). No architectural fork — the AC dictates the design
("Batch-fetch referenced question_ids scoped to user_id+book_id+chapter_id;
reject/flag any not found") → approved autonomously.

## Problem
`save_question_responses_batch` (backend/app/db/questions.py:664) only checks
`question_id`/`response_text` are non-empty, then upserts by
`(question_id, user_id)`. It never verifies the question exists or belongs to
the URL's book/chapter — unlike the single-response path
(`question_generation_service.save_question_response`, which 404s via
`get_question_by_id` + book/chapter membership check). A stale, foreign, or
mistyped `question_id` returns `success: true` and writes an orphaned response
the normal read path never surfaces.

## Design
- `save_question_responses_batch(responses, user_id, book_id, chapter_id)` —
  two new required params.
- Up front, parse each item's `question_id` to `ObjectId` (unparseable → not
  valid) and run ONE query:
  `questions.find({"_id": {"$in": ids}, "user_id": user_id, "book_id": book_id,
  "chapter_id": chapter_id}, {"_id": 1})` → `valid_ids` set (string form).
- Per item: after the existing non-empty checks, `question_id not in valid_ids`
  → per-item failure ("Question not found in this chapter") — covers
  nonexistent, foreign-book/chapter, other-user, and malformed IDs. No response
  doc is written for rejected items.
- Per-item flag (not whole-request 4xx) preserves the endpoint's documented
  partial-failure contract; valid items still save.
- Endpoint (`books.py` batch handler) passes its `book_id`/`chapter_id` through.
- Validation lives in the DB function (no service wrapper exists for the batch
  path; adding one is indirection for nothing — YAGNI).

## Steps (TDD)
1. [ ] RED: new DB-layer tests in `test_batch_question_responses.py`:
   foreign-chapter question rejected + no orphan doc in `question_responses`;
   other-user's question rejected; nonexistent/malformed id rejected; mixed
   batch saves only the valid item. New endpoint test in
   `test_books_draft_style_coverage.py`: POST with a foreign question_id →
   per-item rejection, no orphan.
2. [ ] GREEN: implement the `$in` pre-fetch + per-item rejection; thread
   `book_id`/`chapter_id` from the endpoint.
3. [ ] Fix bug-characterizing tests: existing endpoint tests post fabricated
   ids ("q1", "qX") and assert success — rewrite them to create real questions
   first (via `create_question`, like the DB-layer tests). Update the 7
   positional DB-test call sites for the new signature.
4. [ ] Full backend suite + coverage gate; ruff.
5. [ ] Reviews (opencode GLM pre-PR + post-PR), PR, demo (hard gate), CI, merge.
