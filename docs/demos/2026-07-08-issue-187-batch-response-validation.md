# Issue #187 — batch question-response save now validates question ownership/existence

*2026-07-09T03:18:44Z*

Setup: two real `uvicorn app.main:app` servers against a local mongod — **main** (vulnerable, worktree, :8801, DB `demo187_main`) and the **fix branch** (:8802, DB `demo187_branch`). Each is seeded identically via the real API + mongosh: a book owned by the session user with a valid question in `ch1`, plus a **foreign** question (different book/chapter, same owner) and a **stale** ObjectId that never existed.

Acceptance criteria: (1) batch-fetch referenced question_ids scoped to user+book+chapter and reject/flag any not found; (2) a foreign question_id is rejected, not saved as a silent orphan.

## main — the bug: foreign and stale ids saved as `success: true` orphans

Seed the vulnerable server, then POST a 3-item batch to `POST /books/{book}/chapters/ch1/questions/responses/batch`: one valid answer, one aimed at a question in a *different book/chapter*, one aimed at a question id that never existed.

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/56f09185-e4c9-4d73-ba66-0a213c0277c6/scratchpad/seed187.sh 8801 demo187_main /tmp/claude-1000/-home-frankbria-projects-auto-author/56f09185-e4c9-4d73-ba66-0a213c0277c6/scratchpad/vars-main.env
```

```output
book=6a4f13266c8cc6030e8777b9  valid_q=6a4f1326c7ab4193374c5e19  foreign_q=6a4f13267a825861647523c4(book 6a4f13266c8cc6030e8777bc/ch9)  stale_q=6a4f1327a7282c10f3a200ec(never existed)
```

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/56f09185-e4c9-4d73-ba66-0a213c0277c6/scratchpad/attack187.sh 8801 /tmp/claude-1000/-home-frankbria-projects-auto-author/56f09185-e4c9-4d73-ba66-0a213c0277c6/scratchpad/vars-main.env
```

```output
{
    "success": true,
    "total": 3,
    "saved": 3,
    "failed": 0,
    "results": [
        {
            "index": 0,
            "question_id": "6a4f1326c7ab4193374c5e19",
            "response_id": "6a4f13276c8cc6030e8777bf",
            "success": true,
            "is_update": false
        },
        {
            "index": 1,
            "question_id": "6a4f13267a825861647523c4",
            "response_id": "6a4f13276c8cc6030e8777c0",
            "success": true,
            "is_update": false
        },
        {
            "index": 2,
            "question_id": "6a4f1327a7282c10f3a200ec",
            "response_id": "6a4f13276c8cc6030e8777c1",
            "success": true,
            "is_update": false
        }
    ],
    "errors": null,
    "message": "Batch save completed: 3/3 responses saved successfully",
    "request_id": "req_ef756317bbe8"
}
```

All three report `success: true` — `saved: 3` with no errors. Counting response documents in `demo187_main.question_responses`:

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/56f09185-e4c9-4d73-ba66-0a213c0277c6/scratchpad/orphans187.sh demo187_main /tmp/claude-1000/-home-frankbria-projects-auto-author/56f09185-e4c9-4d73-ba66-0a213c0277c6/scratchpad/vars-main.env
```

```output
responses for VALID question   : 1
responses for FOREIGN question : 1  <- orphan if 1
responses for STALE question   : 1  <- orphan if 1
```

The foreign and stale answers were **persisted as orphans** — the chapter read path resolves responses via its own questions, so these documents are invisible to the user yet permanently misattributed to real question ids in other books (or to nothing at all).

## fix branch — same attack: foreign/stale flagged per-item, nothing written

Identical seed + identical 3-item batch against the branch server. The batch now pre-fetches every referenced question id in one `$in` query scoped to `user_id + book_id + chapter_id`.

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/56f09185-e4c9-4d73-ba66-0a213c0277c6/scratchpad/seed187.sh 8802 demo187_branch /tmp/claude-1000/-home-frankbria-projects-auto-author/56f09185-e4c9-4d73-ba66-0a213c0277c6/scratchpad/vars-branch.env
```

```output
book=6a4f1335b398532e27f80769  valid_q=6a4f1336118d802a8914953b  foreign_q=6a4f1336d2c268b3e8cb26bb(book 6a4f1336b398532e27f8076c/ch9)  stale_q=6a4f1336cb7aea3974fa9f76(never existed)
```

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/56f09185-e4c9-4d73-ba66-0a213c0277c6/scratchpad/attack187.sh 8802 /tmp/claude-1000/-home-frankbria-projects-auto-author/56f09185-e4c9-4d73-ba66-0a213c0277c6/scratchpad/vars-branch.env
```

```output
{
    "success": false,
    "total": 3,
    "saved": 1,
    "failed": 2,
    "results": [
        {
            "index": 1,
            "question_id": "6a4f1336d2c268b3e8cb26bb",
            "success": false,
            "error": "Question not found in this book/chapter"
        },
        {
            "index": 2,
            "question_id": "6a4f1336cb7aea3974fa9f76",
            "success": false,
            "error": "Question not found in this book/chapter"
        },
        {
            "index": 0,
            "question_id": "6a4f1336118d802a8914953b",
            "response_id": "6a4f1336b398532e27f8076f",
            "success": true,
            "is_update": false
        }
    ],
    "errors": [
        {
            "index": 1,
            "question_id": "6a4f1336d2c268b3e8cb26bb",
            "error": "Question not found in this book/chapter"
        },
        {
            "index": 2,
            "question_id": "6a4f1336cb7aea3974fa9f76",
            "error": "Question not found in this book/chapter"
        }
    ],
    "message": "Batch save completed: 1/3 responses saved successfully",
    "request_id": "req_d5cdf222e641"
}
```

The valid answer still saves (partial-failure contract unchanged, HTTP 200), while the foreign and stale ids are flagged `"Question not found in this book/chapter"`. Counting documents in `demo187_branch.question_responses`:

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/56f09185-e4c9-4d73-ba66-0a213c0277c6/scratchpad/orphans187.sh demo187_branch /tmp/claude-1000/-home-frankbria-projects-auto-author/56f09185-e4c9-4d73-ba66-0a213c0277c6/scratchpad/vars-branch.env
```

```output
responses for VALID question   : 1
responses for FOREIGN question : 0  <- orphan if 1
responses for STALE question   : 0  <- orphan if 1
```

**Zero orphans** — rejected items write nothing. Both acceptance criteria hold: the batch is validated with a single scoped `$in` pre-fetch, and a foreign `question_id` is rejected instead of silently misattributed. Backend suite: 1106 passed / 13 skipped, 92.06% coverage.
