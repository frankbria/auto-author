# Issue #492 — a 200 that destroyed the author's table of contents

*2026-08-13T15:01:54Z*

**Claim under test:** `PUT /api/v1/books/{id}/toc` accepted a body without the `toc` wrapper, wiped the book's saved chapters, and answered `200 success: true`.

Every step below runs against **real MongoDB** through the real FastAPI app — no mocks, no stubs. Step [3] and [5] are `GET` read-backs, so the evidence is *what is in the database*, not what the handler claimed.

The harness (`backend/tests/test_492_demo.py`, removed after this run) does five things: save a real 3-chapter TOC, PUT the malformed flat payload from the issue, read the TOC back, clear it deliberately, read back again.

## Before the fix — the data loss, reproduced

```bash
cd /home/frankbria/projects/auto-author/backend && uv run pytest tests/test_492_demo.py -q -s -p no:logging 2>&1 | grep -E "^\[|^    version"
```

```output
[1] Author saves a real TOC     -> 200  chapters_count=3  version=2
[2] Client PUTs 50 chapters flat -> 200  body={"book_id":"6a7ddc637d155b87ac1afbe9","toc":{},"updated_at":"2026-08-13T15:01:55.328044+00:00","version":3,"chapters_cou
[3] Read back from MongoDB       -> 0 chapters: []
    version now                  -> 3
[4] Deliberate clear             -> 200  chapters_count=0
[5] Read back after clear        -> 0 chapters
```

Read that in order. The author had **3 chapters** saved at version 2. A client sent 50 chapters in the wrong shape. The API answered **200** with `"toc":{}` — and the read-back at [3] shows **0 chapters**. Their work is gone, the version was bumped to 3 so the optimistic lock records it as a legitimate edit, and nothing anywhere reported a failure.

This also answers the question the issue left open: the malformed request does **not** merely no-op. It overwrites real work.

## After the fix

```bash
cd /home/frankbria/projects/auto-author/backend && uv run pytest tests/test_492_demo.py -q -s -p no:logging 2>&1 | grep -E "^\[|^    version"
```

```output
[1] Author saves a real TOC     -> 200  chapters_count=3  version=2
[2] Client PUTs 50 chapters flat -> 400  body={"detail":"Request body must contain a 'toc' object"}
[3] Read back from MongoDB       -> 3 chapters: ['Why Systems Fail', 'The Silent 200', 'Designing for Loud Failure']
    version now                  -> 2
[4] Deliberate clear             -> 200  chapters_count=0
[5] Read back after clear        -> 0 chapters
```

Same client, same malformed payload — now **400** with a message naming the missing key, and step [3] shows the three real chapters **still in the database**, still at version 2. The bad request changed nothing.

Step [4] is the guard against over-correcting: clearing a TOC on purpose, `{"toc": {"chapters": []}}`, is still a `200`, and [5] confirms it persisted. The endpoint can now tell a mistake from an intent — which is exactly what the issue said it could not do.

## Acceptance criteria

| From the issue | Evidence |
|---|---|
| Reject when `toc` is absent — 400, not a defaulted `{}` | Step [2] after the fix: `400 {"detail":"Request body must contain a 'toc' object"}` |
| An explicit empty TOC can still be sent as `{"toc": {"chapters": []}}` | Steps [4]/[5]: `200`, `chapters_count=0`, reads back as 0 chapters |
| A flat (unwrapped) payload must not return 2xx — add a regression test | `test_unwrapped_payload_is_rejected_and_preserves_toc`, which asserts the status **and** the read-back; verified failing on the pre-fix code |
| *(open question)* Does it overwrite an existing TOC? | Answered yes, before the fix: step [3] returned 0 chapters where 3 were saved. Now preserved. |

## Nothing else broke

```bash
uv run pytest --cov=app tests/ -q 2>&1 | tail -2
```

```output
TOTAL                                          5233    394    92%
=========== 1237 passed, 9 skipped, 15 warnings in 103.69s (0:01:43) ===========
```
