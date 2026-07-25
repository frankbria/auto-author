# Plan — #336 [P1.4] Chapter-question `status` filter applied AFTER DB pagination

Self-authored (the issue carried acceptance criteria but no implementation-plan comment).

## Root cause

`get_questions_for_chapter` (`backend/app/db/questions.py:207-287`) resolves a question's
`response_status` from a **different collection** (`question_responses`), so `status` could not be
expressed in the initial `questions` query. The original code worked around that by filtering in
Python — but *after* `.sort().skip().limit()` had already selected the page. Consequences, all in
one function:

| Field | Computed as | Wrong because |
|-------|-------------|---------------|
| page contents | `find(query)` unfiltered → skip/limit → Python filter | paging skips **raw** docs, so status-matching questions past the first page are unreachable |
| `total` (response) | `len(processed_questions)` | post-filter length of **one page**, not a total |
| `total` (internal) | `count_documents(query)` | ignores `status` |
| `pages` / `has_more` | derived from the unfiltered count | disagrees with both totals above |

The existing endpoint test (`test_books_chapter_questions_coverage.py:267`) uses `limit=50` with 5
questions, so page length == collection count == filtered count — it cannot discriminate.

## Fix (AC branch 1: resolve the status-matching id set BEFORE skip/limit/count)

When `status` is one of the three known values, resolve the matching `_id` set first and fold it
into the Mongo query as `_id: {"$in": [...]}`. Then the **existing** sort/skip/limit/count runs
against a query that already encodes status, so page contents, `total`, `pages`, and `has_more` all
derive from the same filtered set. Delete the post-pagination Python filter; return the real
`count_documents(query)` as `total`.

## Steps

1. **RED** — `backend/tests/test_db/test_question_status_pagination.py` (real Mongo, mirrors the
   `test_n1_and_projection.py` fixtures): >1 page + `status` asserting complete, non-overlapping
   coverage across pages and an accurate `total`/`pages`; per-status cases; a `status=None`
   regression pin; a pin for the deliberately-unchanged unknown-status behavior.
2. **GREEN** — implement id-set resolution in `get_questions_for_chapter`, drop the post-pagination
   filter, return the true filtered total.
3. **Wire contract** — add a >1-page status-filter case to
   `tests/test_api/test_routes/test_books_chapter_questions_coverage.py`.
4. **Mutation-verify** — restore the old post-pagination filter → the new tests must go RED.

## Autonomous decisions (no architectural fork)

- **Id set over `$lookup`.** `question_responses.question_id` is a *string* of `questions._id`
  (ObjectId), so a `$lookup` needs `$toString` (Mongo 4.0+) plus `$facet` for count+page. The id-set
  form is smaller, version-agnostic, and is the AC's first-listed option. The two extra reads run
  **only** when `status` is passed, so the common path is unchanged.
- **`total` becomes the true filtered count.** The AC demands "an accurate total". Verified no
  production consumer reads `total` from this endpoint; `bookClient` line 2054 consumes `pages`
  (its pagination loop), which becomes correct rather than changing meaning. The service-layer
  persistence check (`question_generation_service.py:206`) compares `total >= expected` and only
  gets *more* lenient.
- **Unknown `status` values keep today's lenient behavior** (filter silently ignored). The endpoint
  does not validate `status`, and tightening it is a separate breaking change outside this issue.
- **Reuse the status map** already built for filtering to enrich the page, instead of re-querying.

## Acceptance criteria

- [ ] Resolve the status-matching id set (or `$lookup` aggregation) BEFORE skip/limit/count.
- [ ] Add a test with >1 page and a status filter asserting complete, non-overlapping results and an
      accurate total.

## Known limitations (for the PR)

- Production frontend never passes `status` today (`QuestionContainer.tsx:83` calls with no
  options, so `limit` defaults to 10). This is a real **public-API** correctness bug but currently
  latent — the demo must show it at the API/DB level, not through the UI.
- Unknown `status` values still silently return unfiltered results (pre-existing, out of scope).
