# Demo — #291: Dashboard BookCard "undefined chapters" / bare "%"

**PR #312** · frontend-only · bug/ux

## What the bug was

`BookCard` reads computed `book.chapters` / `book.progress`, but `GET /api/v1/books/`
(`BookResponse`) returns neither field, and the dashboard passed
`bookClient.getUserBooks()` straight through. Result on the primary dashboard:
`undefined chapters`, a bare `%`, a fabricated progress bar, and the `chapters === 0`
"New" callout unreachable.

## The fix

`getUserBooks()` maps each `BookResponse` through the existing `toBookProject()`
helper (`chapters = toc_items.length`, `progress` from chapter statuses, `word_count`
sum). `toc_items ?? []` guards a legacy/partial payload from throwing.

## Outcome evidence

Drives the **real** `bookClient.getUserBooks()` against a stubbed `fetch` returning the
exact `BookResponse` payload the API sends, then renders the **real** `BookCard`. The
BEFORE block feeds a raw API object straight to `BookCard` — exactly what `main` did.

```
================ AFTER FIX (branch) ================
getUserBooks() mapped output:
  Half-written Book: chapters=4 progress=50% word_count=2000
  Brand New Book: chapters=0 progress=0% word_count=0

BookCard render — half-written book (AC1: real count + progress):
  [half] text: "Half-written Book...•4 chaptersProgress50%Open Project"
  [half] progress-bar width: 50%

BookCard render — fresh TOC-less book (AC2: "New", no bar):
  [fresh] text: "Brand New Book...•NewReady to start writing! Click below to begin creating your book content.Open Project"
  [fresh] progress-bar width: (no bar)

================ BEFORE FIX (raw passthrough, = main) ================
BookCard render — raw payload (AC3: the "undefined" bug):
  [raw-half] text: "Half-written Book...•undefined chaptersProgress%Open Project"
  [raw-half] progress-bar width: (no bar)
```

## AC mapping

| Acceptance criterion | Evidence |
|---|---|
| Real chapter count + progress value | `4 chapters` / `50%` with a 50%-width bar (half-written book, 2 of 4 completed) |
| Fresh (no TOC) book shows "New", not a fabricated bar | `•New` + "Ready to start writing!" callout, no progress bar |
| No "undefined" ever rendered | AFTER shows real numbers; BEFORE (main) shows the literal `undefined chapters` / bare `%` |

The demo is a runnable assertion gate (`4 chapters`, `progress === 50`, `New`, no `%`
in the fresh card) — reverting the mapping restores the `undefined chapters` string.
