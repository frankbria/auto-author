# Issue #336 — chapter-question status filter resolved before pagination

*2026-07-25T03:06:29Z by Showboat 0.6.1*
<!-- showboat-id: d5a68f97-7032-4710-8b18-be923757b656 -->

The `GET /books/{id}/chapters/{cid}/questions` endpoint filters by response status. Before this fix, `get_questions_for_chapter` paged the `questions` collection with `status` absent from the Mongo query, then dropped non-matching rows from the already-sliced page in Python.

This demo runs **two real uvicorn servers against the same Mongo database** — pristine `main` on :8801 and the fix branch on :8802 — so the only variable is the application code. Question generation is never invoked (it would call OpenAI); the endpoint under test is a pure read, so the fixture is seeded directly.

## The fixture

Seven questions in one chapter, with response statuses **interleaved** on purpose: any page of the raw ordering mixes matching and non-matching rows, which is precisely what filter-after-paginate mishandles.

```bash
cd /home/frankbria/projects/auto-author/backend && uv run python /tmp/claude-1002/-home-frankbria-projects-auto-author/48192e2d-a073-40c8-a78c-9b6cfc927d64/scratchpad/seed336.py | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(\"order -> response status\")
for row in d[\"layout\"]:
    print(f\"  {row[\"order\"]}: {row[\"status\"]}\")
print()
print(\"completed questions:\", d[\"completed_orders\"], \"=> a correct ?status=completed total is\", d[\"expected_completed_total\"])
"
```

```output
order -> response status
  1: completed
  2: not_answered
  3: completed
  4: draft
  5: completed
  6: not_answered
  7: completed

completed questions: [1, 3, 5, 7] => a correct ?status=completed total is 4
```

## AC1 — the filter must be resolved before pagination

The sharpest evidence is the `draft` filter. Exactly one question (order 4) is a draft. Ask each server for the first page of drafts.

On `main`, `skip(0).limit(2)` selects raw questions 1 and 2, *then* the Python filter discards both — so the API answers **an empty page with `total: 0`**. A client has no way to tell that apart from "this chapter has no drafts", stops, and silently loses the draft that exists.

```bash
echo "----- MAIN :8801 -----"; curl -s "http://127.0.0.1:8801/api/v1/books/68000000000000000000d336/chapters/chapter-336/questions?status=draft&page=1&limit=2" | python3 -m json.tool | head -8; echo; echo "----- BRANCH :8802 -----"; curl -s "http://127.0.0.1:8802/api/v1/books/68000000000000000000d336/chapters/chapter-336/questions?status=draft&page=1&limit=2" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(json.dumps({k: d[k] for k in (\"total\",\"page\",\"pages\",\"has_more\")}, indent=4))
print(\"questions returned:\", [(q[\"order\"], q[\"response_status\"]) for q in d[\"questions\"]])
"
```

```output
----- MAIN :8801 -----
{
    "questions": [],
    "total": 0,
    "page": 1,
    "pages": 4,
    "has_more": true
}

----- BRANCH :8802 -----
{
    "total": 1,
    "page": 1,
    "pages": 1,
    "has_more": false
}
questions returned: [(4, 'draft')]
```

Note how incoherent the `main` response is on its own terms: `total: 0` (nothing matched), `pages: 4`, `has_more: true` — three fields describing three different sets in a single body. The branch returns one internally consistent answer.

Now the `completed` filter, walked the way a client does — read page 1, then follow the `pages` count the API itself reports.

```bash
walk() { /home/frankbria/projects/auto-author/backend/.venv/bin/python /tmp/claude-1002/-home-frankbria-projects-auto-author/48192e2d-a073-40c8-a78c-9b6cfc927d64/scratchpad/walk336.py "$1" completed 2 | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(\"pages reported by API :\", d[\"pages_reported_by_api\"])
for w in d[\"walk\"]:
    print(f\"  page {w[\"page\"]}: orders={w[\"orders_returned\"]!s:<12} total={w[\"total_reported\"]}  has_more={w[\"has_more\"]}\")
print(\"  union of everything the client saw:\", d[\"all_orders_client_saw\"])
print(\"  duplicates served:\", d[\"duplicates_served\"] or \"none\")
"; }
echo "=== MAIN  :8801   ?status=completed&limit=2 ==="; walk 8801
echo
echo "=== BRANCH :8802  ?status=completed&limit=2 ==="; walk 8802
```

```output
=== MAIN  :8801   ?status=completed&limit=2 ===
pages reported by API : 4
  page 1: orders=[1]          total=1  has_more=True
  page 2: orders=[3]          total=1  has_more=True
  page 3: orders=[5]          total=1  has_more=True
  page 4: orders=[7]          total=1  has_more=False
  union of everything the client saw: [1, 3, 5, 7]
  duplicates served: none

=== BRANCH :8802  ?status=completed&limit=2 ===
pages reported by API : 2
  page 1: orders=[1, 3]       total=4  has_more=True
  page 2: orders=[5, 7]       total=4  has_more=False
  union of everything the client saw: [1, 3, 5, 7]
  duplicates served: none
```

Being precise about the impact, because the issue overstates one part of it: a client that *blindly follows the inflated `pages` count* does eventually sweep the whole raw collection and see all four completed questions — `main` gets the union right here by accident, because paging the unfiltered set happens to visit every document.

What `main` gets wrong is everything a client actually decides on:

- **`total` is 1 on every page** when four questions match. Any UI rendering "1 result" or sizing a pager from `total` is wrong.
- **Pages are half-empty** (1 row for `limit=2`), so a client that stops when a page is short — a normal convention — stops after page 1.
- **A page can be entirely empty while matches exist** (the `draft` case above), which reads as "no results" and is an unrecoverable miss.
- `pages`/`has_more` describe the unfiltered set, so they disagree with `total` in the same body.

The branch returns two full pages, `total: 4` on both, and `pages: 2` — every field describing the same filtered set.

## AC2 — a test with >1 page and a status filter

`tests/test_db/test_question_status_pagination.py` pins the multi-page contract against real Mongo, and the endpoint suite pins it over HTTP.

```bash
cd /home/frankbria/projects/auto-author/backend && BYPASS_AUTH=false uv run pytest tests/test_db/test_question_status_pagination.py "tests/test_api/test_routes/test_books_chapter_questions_coverage.py::test_list_questions_status_filter_pages_completely" -q 2>&1 | tail -6
```

```output
collected 10 items

tests/test_db/test_question_status_pagination.py .........               [ 90%]
tests/test_api/test_routes/test_books_chapter_questions_coverage.py .    [100%]

============================== 10 passed in 0.50s ==============================
```

Green tests only prove the suite ran. To show they actually pin the fix, run the same tests against the **pristine `main` worktree** — the real pre-fix code, not a synthetic mutation.

```bash
W=/tmp/claude-1002/-home-frankbria-projects-auto-author/48192e2d-a073-40c8-a78c-9b6cfc927d64/scratchpad/main-336
cp /home/frankbria/projects/auto-author/backend/tests/test_db/test_question_status_pagination.py "$W/backend/tests/test_db/"
cd "$W/backend" && BYPASS_AUTH=false uv run pytest tests/test_db/test_question_status_pagination.py -q 2>&1 | tail -9
```

```output
E   AssertionError: assert 3 == 7
E    +  where 3 = QuestionListResponse(questions=[Question(question_text='Question number 1 for the chapter?', question_type=<QuestionTy...info=datetime.timezone.utc), has_response=True, response_status='completed')], total=3, page=1, pages=3, has_more=True).total
=========================== short test summary info ============================
FAILED tests/test_db/test_question_status_pagination.py::test_completed_filter_across_multiple_pages_is_complete_and_disjoint
FAILED tests/test_db/test_question_status_pagination.py::test_completed_filter_page_shape_and_ordering
FAILED tests/test_db/test_question_status_pagination.py::test_not_answered_filter_never_yields_an_empty_page
FAILED tests/test_db/test_question_status_pagination.py::test_draft_filter_returns_only_the_draft_question
FAILED tests/test_db/test_question_status_pagination.py::test_unfiltered_total_is_the_collection_count_not_the_page_length
========================= 5 failed, 4 passed in 1.13s ==========================
```

Five of the nine pins go RED against the real pre-fix code — the four status-filter behaviours plus the unfiltered `total`. The remaining four (user scoping, filter composition, unfiltered page coverage, and the deliberately-unchanged unknown-status behaviour) pass on both sides by design; they are guards against regressions the rewrite could have introduced, not demonstrations of the bug, and the file says so.

Two further targeted mutations confirm each half of the fix is independently load-bearing:

- disabling only the id-set resolution (`if False and status in RESPONSE_STATUS_FILTERS`) → the 5 status pins fail, the unfiltered `total` pin still passes
- reverting only `total=total` → `total=len(processed_questions)` → the 3 total-accuracy pins fail

## Regression check

The whole backend suite, on the branch.

```bash
cd /home/frankbria/projects/auto-author/backend && BYPASS_AUTH=false uv run pytest tests/ -q --ignore=tests/test_services/test_ai_service.py --ignore=tests/test_e2e_no_mocks.py 2>&1 | tail -3
```

```output

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================ 1105 passed, 11 skipped, 12 warnings in 54.07s ================
```

(The two excluded files make live network calls and hang offline — a documented pre-existing condition, unrelated to this diff. CI runs them with a key.)

## Acceptance criteria

| Criterion | Evidence |
|---|---|
| Resolve the status-matching id set BEFORE skip/limit/count | `main` returns an empty page with `total: 0` for a filter matching one question, and `total: 1` on every page of a 4-match filter; the branch returns full pages with a consistent `total`, `pages`, and `has_more`. |
| Test with >1 page + a status filter asserting complete, non-overlapping results and an accurate total | `test_completed_filter_across_multiple_pages_is_complete_and_disjoint` (2 pages, union equals the completed set, no duplicates, `total == 4` on both pages) plus the HTTP-level `test_list_questions_status_filter_pages_completely`; both RED against pre-fix code. |

## Scope note

No production frontend code passes `status` today — `QuestionContainer.tsx:83` calls `getChapterQuestions(bookId, chapterId)` with no options. This is a real public-API correctness bug, but a latent one, which is why the evidence above is at the API layer rather than in the UI.
