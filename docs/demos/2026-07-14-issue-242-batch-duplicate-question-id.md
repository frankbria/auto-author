# Issue #242 — a repeated question_id in one batch save no longer costs the user their newest answer

*2026-07-15T06:18:36Z*

Setup: two real `uvicorn app.main:app` servers on a local mongod — **main** (pristine worktree, :8801, DB `demo242_main`) and the **fix branch** (:8802, DB `demo242_branch`). Each is seeded identically with a genuine better-auth session row, a book created through the real API, and one chapter question. `BYPASS_AUTH=false` — every request below carries a real session cookie.

Both servers ran `ensure_question_indexes()` at startup, so both hold the **unique** index `question_user_idx` on `(question_id, user_id)` — the production shape.

**The issue's premise turned out to be only half the story.** It reports that a repeated `question_id` writes two documents. That happens only when the unique index is *absent*. With the index present — i.e. on any correctly-started deployment — the second insert trips `E11000` instead, and the failure mode is worse than a duplicate: the user's **newer answer is silently discarded** and a raw Mongo error is handed back to the client. Both states are demonstrated below; the fix corrects both.

**Acceptance criteria**: (1) one response document, not two; (2) last-write-wins within the batch, matching two sequential saves; (3) reads keyed on `(question_id, user_id)` stay deterministic.

## main — production shape: the newer answer is lost, and Mongo's error leaks

The user answers the question, refines it, and the client sends both revisions in one batch (`POST /books/{book}/chapters/ch1/questions/responses/batch`). Index present, no response saved yet.

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/654e6e2d-0446-4636-98dd-babcd882cfcd/scratchpad/batch242.sh /tmp/claude-1000/-home-frankbria-projects-auto-author/654e6e2d-0446-4636-98dd-babcd882cfcd/scratchpad/vars-main.env
```

```output
{
  "success": false,
  "total": 2,
  "saved": 1,
  "failed": 1,
  "results": [
    {
      "index": 0,
      "question_id": "<oid>",
      "response_id": "<oid>",
      "success": true,
      "is_update": false
    },
    {
      "index": 1,
      "question_id": "<oid>",
      "success": false,
      "error": "Database error: E11000 duplicate key error ... <raw Mongo error text leaked to the client>"
    }
  ],
  "errors": [
    {
      "index": 1,
      "question_id": "<oid>",
      "error": "Database error: E11000 duplicate key error ... <raw Mongo error text leaked to the client>"
    }
  ],
  "message": "Batch save completed: 1/2 responses saved successfully",
  "request_id": "req_<id>"
}
```

`success: false`, `saved: 1` of 2 — and index 1 comes back carrying a raw `E11000 duplicate key error` straight from the driver. That string is the *symptom*: both items were prepared before either was written, so the second item never saw the first's pending insert and tried to create a second document for the same question.

The batch reported partial failure. So what does the user actually have now? This is the real read path the editor calls on reload:

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/654e6e2d-0446-4636-98dd-babcd882cfcd/scratchpad/readback242.sh /tmp/claude-1000/-home-frankbria-projects-auto-author/654e6e2d-0446-4636-98dd-babcd882cfcd/scratchpad/vars-main.env
```

```output
response documents stored for this question: 1

--- what the user sees on reload: GET .../questions/{id}/response ---
  answer : 'She wants to leave town.'
  status : draft
```

There it is. The user's refined, **completed** answer is gone — the reload serves the earlier throwaway `draft`. The write that won was the *first* one, and the newer one was thrown away by the index. One document, but the wrong one.

## fix branch — same batch, same session shape: the newer answer wins cleanly

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/654e6e2d-0446-4636-98dd-babcd882cfcd/scratchpad/batch242.sh /tmp/claude-1000/-home-frankbria-projects-auto-author/654e6e2d-0446-4636-98dd-babcd882cfcd/scratchpad/vars-branch.env
```

```output
{
  "success": true,
  "total": 2,
  "saved": 2,
  "failed": 0,
  "results": [
    {
      "index": 0,
      "question_id": "<oid>",
      "response_id": "<oid>",
      "success": true,
      "is_update": false
    },
    {
      "index": 1,
      "question_id": "<oid>",
      "response_id": "<oid>",
      "success": true,
      "is_update": false
    }
  ],
  "errors": null,
  "message": "Batch save completed: 2/2 responses saved successfully",
  "request_id": "req_<id>"
}
```

`success: true`, `saved: 2` of 2, no errors, no `E11000`. Both items report the same `response_id` because they collapsed into the one write they always should have been. Reading it back:

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/654e6e2d-0446-4636-98dd-babcd882cfcd/scratchpad/readback242.sh /tmp/claude-1000/-home-frankbria-projects-auto-author/654e6e2d-0446-4636-98dd-babcd882cfcd/scratchpad/vars-branch.env
```

```output
response documents stored for this question: 1

--- what the user sees on reload: GET .../questions/{id}/response ---
  answer : 'She wants to leave town and never look back, because her mother stayed.'
  status : completed
```

The user's newest answer, with the status they set, exactly as two sequential saves would have left it (AC 2), in exactly one document (AC 1).

## The issue's literal claim: two documents, when the unique index is absent

`ensure_question_indexes()` wraps every index in one `try/except` and only logs on failure — so a collection that *already* holds duplicates fails to build `question_user_idx`, and that index (plus every one after it) is skipped. In that state nothing stops the second insert. Dropping the index reproduces it against **main**:

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/654e6e2d-0446-4636-98dd-babcd882cfcd/scratchpad/noindex242.sh /tmp/claude-1000/-home-frankbria-projects-auto-author/654e6e2d-0446-4636-98dd-babcd882cfcd/scratchpad/vars-main.env
```

```output
unique index present: false
response documents stored: 2
   - "She wants to leave town."  [draft]
   - "She wants to leave town and never look back, because her mother stayed."  [completed]
```

**Two response documents for one question** — the issue's report, reproduced verbatim. Now `(question_id, user_id)` no longer identifies a single row, so which one `find_one` returns is up to Mongo. The same drop against the **fix branch**:

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/654e6e2d-0446-4636-98dd-babcd882cfcd/scratchpad/noindex242.sh /tmp/claude-1000/-home-frankbria-projects-auto-author/654e6e2d-0446-4636-98dd-babcd882cfcd/scratchpad/vars-branch.env
```

```output
unique index present: false
response documents stored: 1
   - "She wants to leave town and never look back, because her mother stayed."  [completed]
```

One document, holding the newer answer. The fix collapses the repeat in the DAO itself, so it doesn't depend on the index being there to save it — it's correct in both states (AC 1, AC 3: `(question_id, user_id)` identifies exactly one row again, so reads are deterministic).

## The pins behind it

Five of the seventeen tests in this suite are new-behavior pins for #242; each was RED before the fix. Running the suite against the branch:

```bash
cd /home/frankbria/projects/auto-author/backend && BYPASS_AUTH=false uv run pytest tests/test_batch_question_responses.py -p no:cacheprovider --no-cov -q 2>&1 | tail -3 | sed -E "s/ in [0-9.]+s//"
```

```output
tests/test_batch_question_responses.py .................                 [100%]

============================== 17 passed ==============================
```

The five: one document per repeat, last-write-wins under the production index, both collapsed items reporting one shared `response_id`, a triple repeat, and the accounting invariant `total == saved + failed`. Each was mutation-verified — stripping the dedup fails exactly four of them; keeping the collapse but letting the *first* write win fails three, which is what pins the *winner* rather than just the document count.

## Known limitations

- **The audit trail deliberately diverges.** Two sequential saves leave one `edit_history` entry; a collapsed pair leaves none. The intermediate answer was never a persisted state, so recording it as an edit would be fiction. Documented on the function.
- **The residual `E11000` leak is untouched.** Two *concurrent* requests (not one batch) can still race the unique index and surface the same raw driver text — the generic `f"Database error: {e}"` path is a pre-existing class, out of scope here. This fix makes it unreachable from a duplicate batch, which is the only path #242 covers.

## Verdict

| Acceptance criterion | Evidence |
|---|---|
| One document, not two | `response documents stored: 1` on the branch in both index states; main stores 2 with the index absent |
| Last-write-wins, matching two sequential saves | The reload serves the newer completed answer on the branch; main serves the stale draft |
| `(question_id, user_id)` reads stay deterministic | Exactly one row per pair on the branch, so `find_one` has nothing to choose between |

The bug the issue described is real; the bug production actually had was worse than the report — the user's newest writing was being thrown away with a database error where a success belonged.
