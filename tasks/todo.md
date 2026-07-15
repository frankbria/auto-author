# [P2.18] #242 — Batch question-response save writes duplicate documents for a repeated question_id

**Plan source**: self-authored (CodeRabbit posted only its issue-planner stub, no plan).
**Approval**: autonomous — no architectural fork.

## Verified premise (before building) — issue is PARTIALLY STALE

Probed the real DAO against real Mongo with the same `question_id` twice in one batch,
no pre-existing response. Behavior depends on whether the `question_user_idx`
**unique** index on `(question_id, user_id)` (`questions.py:86-91`) is present:

| unique index | actual outcome |
|---|---|
| **absent** | 2 docs stored — exactly as the issue describes |
| **present** (production: `main.py:71` `ensure_question_indexes()` at startup) | 1 doc, but the **FIRST** answer persists and the user's newer **SECOND** answer is **lost**; item 1 returns `success: false` with a raw `E11000 duplicate key error ...` Mongo string leaked into the API response |

So in a correctly-started deployment the symptom is **not** duplicate documents — it is
**silent last-write-loss + a leaked internal DB error**. The issue's data-integrity
concern is real; the mechanism differs. The unique index is the reason, and it can
still be absent: `ensure_question_indexes` wraps every index in a single try/except, so
if `create_index(unique=True)` fails on a collection that *already* holds duplicates,
that index — and every index after it — is skipped and merely logged.

The dedup fix corrects **both** states, which is why it's the right branch.

## Design decisions (autonomous — no architectural fork)

1. **Dedup, not upsert** (the issue offered both). Dedup fixes the no-index state too;
   upsert alone cannot collapse two items inside one batch without relying on the
   unique index existing. Dedup is also the smaller diff.
2. **Dedup happens *after* per-item validation**, not before. Keeps each item's own
   honest validation error: `[{q1,"text"}, {q1,""}]` → item 1 fails "Missing
   response_text" and "text" still saves — exactly what two sequential saves do.
   Deduping the payload up front would mis-attribute the winner's error to item 0.
3. **Both collapsed items report the single write's outcome** (same `response_id`).
   A client that debounces a double-send must not get `success: false` for a benign
   payload. Preserves the existing `total == saved + failed` per-item invariant.
4. **Not chasing `edit_history` parity**: two sequential saves leave 1 history entry;
   one collapsed write leaves 0. The intermediate value was never a persisted state,
   so recording it as an "edit" would be fiction.
5. **Out of scope**: the generic `f"Database error: {str(e)}"` leak (pre-existing class,
   applies to any DB error) and the concurrent-request E11000 race. Dedup makes both
   unreachable *from a duplicate batch*; the residual race is a Known Limitation.

## Steps

- [ ] 1. `backend/app/db/questions.py::save_question_responses_batch` — collapse
      repeated `question_id`s to one write, last-write-wins: after validation, if an op
      already exists for that id, overwrite its payload fields (text/status/word_count/
      timestamps) in place, record the earlier index as an alias, skip the redundant
      `find_one`. At execute time, emit the write's result (success *or* error) for
      every collapsed index.
- [ ] 2. Tests in `backend/tests/test_batch_question_responses.py` (the fixture drops the
      DB and creates **no** indexes, so the suite today only ever sees the no-index path):
  - [ ] duplicate in batch → exactly **1** document stored (RED today: 2)
  - [ ] **production shape** — `ensure_question_indexes()` first → last answer wins,
        `success: true`, no `E11000` anywhere in the response (RED today: first answer
        persists, `success: false`, raw E11000 leaked)
  - [ ] per-item results: both indices report success with the **same** `response_id`;
        `total == saved + failed`
  - [ ] duplicate over an **existing** response → single update, last wins
  - [ ] validation independence: `[{q1,"text"}, {q1,""}]` → item 1 fails honestly,
        "text" saved
- [ ] 3. Mutation-verify each new test (strip the dedup → the intended test fails).
- [ ] 4. Full backend suite + coverage gate green; pre-commit clean (no `--no-verify`).

## Acceptance criteria (from issue)

- [ ] A batch containing the same `question_id` twice writes **one** response document,
      not two.
- [ ] Result is last-write-wins within the batch — matching what two sequential saves
      would produce.
- [ ] Subsequent reads/updates keyed on `(question_id, user_id)` are deterministic.
