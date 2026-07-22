# Demo — #276: honest question-response completion status + dead toc-readiness composite

**Setup**: two real uvicorn servers on a local MongoDB — a **pristine `main` worktree** (:8001, `before`)
vs the **branch** (:8000, `after`) — each `BYPASS_AUTH=true E2E_ALLOW_BYPASS=1 ENVIRONMENT=test`
(the #272/#307 requirement), on separate DBs. Each run creates a book, seeds two clarifying questions
directly on the book document (no OpenAI needed — this demo is about the PUT/readiness behavior for a
book that *has* questions), then drives the endpoint with partial / complete / duplicate answer sets and
reads the stored status back through the real GET path.

## AC1 — the endpoint distinguishes partial from complete (derive server-side)

Same requests to both servers:

| Scenario | MAIN (before) | BRANCH (after) |
|---|---|---|
| **Partial set** — 1 of 2 answered (the #203 mid-typing auto-save shape) | `ready_for_toc_generation = True`, stored `status = 'completed'` — **the trap** | `ready_for_toc_generation = False`, stored `status = 'draft'` |
| **Complete set** — both answered | `completed` | `completed` (unchanged) |
| **Duplicate set** — Q1 answered twice, Q2 omitted (a count check says 2/2) | `completed` — count-foolable | `draft` — **coverage by question text** |

The branch stores `completed` **only** when every current clarifying question is covered by a response.
Duplicate/stale responses can't reach a headcount and fake completion — the sharpest evidence that
coverage-by-text (not a count) was the correct interpretation; a naive `len(responses) >= count` fix would
mis-store the duplicate case as `completed` exactly like `main`.

## AC2 — toc-readiness's dead composite is deleted

`GET /toc-readiness` returns the **identical** body on both servers:

```
keys           = ['analysis', 'character_count', 'confidence_score',
                  'is_ready_for_toc', 'meets_minimum_requirements', 'suggestions', 'word_count']
next_steps in body = False   # on BOTH main and branch
```

The composite `is_ready_for_toc` + `next_steps` were **computed then discarded** by both return branches on
`main`, so deleting them (−49 lines in the handler) is behavior-preserving cleanup — the API contract is
byte-identical, only the dead code is gone. Evidence is the unchanged output plus the removed code, not a
behavior flip.

## AC3 — tests pin the semantics

`test_books_pretoc_coverage.py::TestQuestionResponseCompletionStatus` — partial→`draft`/`False`,
complete→`completed`/`True`, **duplicate responses don't fake completion**→`draft`, no-questions→`draft`;
plus a toc-readiness pin (analysis-ready with zero questions/responses still reads ready; `next_steps`
absent). Two bug pins RED against the old hardcode; the duplicate pin RED against a count-based (`>=`) check
(mutation-verified). Full pretoc suite **45 passed**.
