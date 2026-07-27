# Demo — #341: Hollow/tautological tests + untested rich-text editing

**Date:** 2026-07-27 · **PR:** #374 · **Branch:** `fix/341-hollow-tests-rich-text-e2e`

Every acceptance criterion below is demonstrated with **outcome evidence** — what the
suite reports on `main` versus on the branch, and what happens when the product is
deliberately broken. "The test passed" is not evidence here; the whole issue is that
passing tests were proving nothing.

Environment: real backend (`uvicorn` on :8000) against a real mongod (tmpfs, :27017),
real chromium via Playwright, `BYPASS_AUTH=true` + `E2E_ALLOW_BYPASS=1`. Pristine `main`
compared via a separate `git worktree`.

---

## AC 1 — Delete the tautological/zero-assert/harness tests

### Evidence: a backend test with zero asserts that pytest collects and reports green

On `main`:

```
$ grep -cE "^\s*assert " backend/tests/test_debug_chapter_questions.py
0

$ uv run pytest backend/tests/test_debug_chapter_questions.py -q
.                                                                        [100%]
1 passed in 0.06s
```

A collected test, counted in the green total, containing **no assertion of any kind** —
it cannot fail. It is deleted on the branch.

Nothing real was lost: the same service call is covered with real assertions by
`test_services/test_question_generation_service.py`, and the near-identical sibling
`tests/test_debug_questions.py` makes the same `generate_questions_for_chapter` call
with 3 asserts.

### Evidence: the frontend deletions carried no product coverage

Coverage before and after the deletions, same command as CI:

| Metric | `main` | branch | Δ |
|---|---|---|---|
| Statements | 88.93 | **89.00** | +0.07 |
| Branches | 79.06 | 79.06 | — |
| Functions | 85.20 | **85.56** | +0.36 |
| Lines | 90.16 | **90.24** | +0.08 |

Coverage **rose**. Deleting `MockSystemFlow.test.tsx`, `TestInfrastructureIntegration.test.tsx`
and `example.test.tsx` removed 15 tests and zero product coverage, because each one
exercised either a `jest.mock` or an inline throwaway component. The gain comes from the
6 new per-command assertions replacing the count.

Suite totals: `main` 131 suites / 2249 passed → branch 128 suites / 2240 passed.
The −9 reconciles exactly: −15 deleted, +6 added.

### Root-cause sweep, not just the cited files

Scanned every file in `backend/tests` for "collected but assertless". Three hits, each
triaged on its own merits rather than deleted by pattern:

| File | Call |
|---|---|
| `test_debug_chapter_questions.py` | **Deleted** — zero asserts, print-only. |
| `test_e2e_no_mocks.py` | **Kept** — no asserts of its own, but delegates to `SystemE2ETest.run()`, whose `raise_for_status()` calls genuinely fail it. Not tautological. |
| `test_system_e2e_simplified.py` | **Fixed**, not deleted — see the bonus finding below. |

---

## AC 3 — Drop the brittle mock call-count assertion

### Evidence: the old assertion passes with the Bold button wired to italic

The old test asserted `expect(mockRunFn).toHaveBeenCalledTimes(7)` against a shared mock.
Restoring that test and miswiring the live Bold button to `toggleItalic`:

```
$ sed -i "s|toggleBold().run()|toggleItalic().run()|" src/components/chapters/ChapterEditor.tsx
$ npx jest src/__tests__/RichTextEditor.test.tsx

  ✓ renders the rich text editor with toolbar (129 ms)
  ✓ shows character count in the footer (52 ms)
  ✓ handles save button click (152 ms)
  ✓ toggles formatting when toolbar buttons are clicked (126 ms)

Tests:       4 passed, 4 total
```

**Green, with Bold broken.** The Bold button no longer bolds anything, and the test named
"toggles formatting when toolbar buttons are clicked" does not notice — because `run()`
is still called 7 times either way.

The same mutation against the branch's replacement:

```
  ✕ the Bold button runs the toggleBold command (64 ms)
  ✓ the Italic button runs the toggleItalic command (63 ms)
  ✓ the Underline button runs the toggleUnderline command (59 ms)
  ✓ the Heading 1 button runs the toggleHeading command (59 ms)
  ✓ the Heading 2 button runs the toggleHeading command (58 ms)
  ✓ the Bullet List button runs the toggleBulletList command (58 ms)
  ✓ the Blockquote button runs the toggleBlockquote command (59 ms)

Tests:       1 failed, 9 passed, 10 total
```

Exactly the affected button fails, and it names itself. Unmutated: 10/10 green.

---

## AC 2 — Real-browser E2E asserting the resulting marks/HTML

### Evidence: on `main`, nothing asserts formatting output at all

```
$ grep -rlE "toggleBold|\.tiptap strong|<strong>" frontend/src/e2e/
NONE — no spec asserts formatting marks
```

TipTap is globally mocked in jsdom (`src/jest.setup.ts:267`) because it cannot run there,
so the unit layer can only ever observe that *a command was invoked*. The existing E2E
only inserted plain draft text. Between the two, **no test anywhere confirmed that
clicking Bold produces bold text.**

### Evidence: the branch spec runs in a real browser and passes

```
$ npx playwright test editor-formatting --project=chromium

  ✓  1 … Bold produces a <strong> mark that persists (17.6s)
  ✓  2 … Heading 2 converts the paragraph to an <h2> (18.0s)
  ✓  3 … Bullet List wraps the line in <ul><li> (9.0s)
  ✓  4 … formatting is reversible — toggling Bold off removes the mark (8.8s)

  4 passed (3.0m)
```

Each test asserts **twice**: the mark in the live editor DOM, and the corresponding tag in
the HTML the backend actually stored. Formatting that renders but never persists is still
a broken feature, so rendering alone is not accepted as evidence.

### Evidence: the spec fails when formatting breaks

Same Bold → italic mutation, against the real browser:

```
  ✓  2 … Heading 2 converts the paragraph to an <h2> (20.8s)
  ✓  3 … Bullet List wraps the line in <ul><li> (6.0s)
  ✘  1 … Bold produces a <strong> mark that persists (31.1s)
  ✘  4 … formatting is reversible — toggling Bold off removes the mark (12.9s)

    Expected: "Habits are the invisible architecture of daily life."
    Error: element(s) not found

  2 failed, 2 passed
```

Both Bold tests red, heading and list unaffected — the failure is scoped to the thing that
broke. Mutation reverted; 4/4 green again.

---

## Bonus finding — a test that printed "Has TOC: False" and reported PASSED

Not named in the issue; surfaced by the zero-assert sweep. `test_system_e2e_simplified.py`
on `main`:

```
🔸 Generating Table of Contents...
✅ Generated TOC with 2 chapters
🔸 Verifying system state...
✅ Has TOC: False
✅ SIMPLIFIED SYSTEM TEST PASSED in 0.14 seconds!

1 passed
```

It generates a TOC, verifies the book has none, and declares success.

**Two defects cancelling out.** `verify_system()` read `book["table_of_contents"]` — the
*Mongo document's* field name. `BookResponse` (`app/schemas/book.py:234`) does not declare
that field, so `.get("table_of_contents", {})` returned `{}` unconditionally and `has_toc`
could never be `True` **in any state**. And `run()` called `verify_system()` without
looking at the result, so the permanently-false check never mattered.

Fixed by reading the TOC from the endpoint that serves it and asserting the result:

```
🔸 Generating Table of Contents...
✅ Generated TOC with 2 chapters
🔸 Verifying system state...
✅ Has TOC: True (2 chapters)

1 passed
```

Mutation — skip TOC generation:

```
E   AssertionError: Workflow completed but the book has no persisted table of contents
1 failed
```

### A wrong assumption, caught by the mutation check

The first attempt added a 17-line `accept_toc()` step on the assumption that
`POST /generate-toc` only returns a candidate and `PUT /toc` persists it — with a
confident docstring saying so. The mutation check disproved it: removing the step still
passed, because `generate-toc` persists on its own. The step and its false docstring were
deleted, leaving a 2-line fix. Worth recording, since shipping a plausible-sounding but
false comment is the same failure mode this issue is about.

---

## Full-suite results

| Suite | Result |
|---|---|
| Frontend jest | 128 suites, **2240 passed** / 5 skipped |
| Frontend coverage gate (85/85/75/85) | **pass**, with headroom |
| Backend pytest | **1198 passed** / 11 skipped |
| New formatting E2E (chromium) | **4/4 passed** |
| `tsc --noEmit` | clean |
| `eslint` | 0 errors (403 pre-existing warnings untouched; none in changed files) |

One transient `VoiceTextInput.test.tsx` failure appeared in a single `--coverage` run while
the backend and dev server were running concurrently, and did not reproduce across three
subsequent full runs (two plain, one with coverage) or in isolation. It is a pre-existing
`waitFor` timing sensitivity on accumulated speech results, in a file this PR does not
touch — recorded here rather than dismissed.

---

## Cross-family review

**opencode (GLM-5.2)** — no Critical, no Major. It independently re-verified the four
load-bearing assumptions (toolbar `title=` attributes, AI mock method-name match, `/toc`
response shape, `BookResponse` lacking `table_of_contents`) against the live codebase, and
specifically checked the save-race question: the typing-triggered save produces
`<p>text</p>`, which is not a substring of any polled fragment, so an intermediate
un-formatted save cannot satisfy the poll.

1 of 5 Minor findings adopted: the standalone `'<ul>'` poll was weak (any list anywhere
would satisfy it), folded into the text-specific `<ul><li><p>text</p></li></ul>` and
re-run green rather than assumed. The rest were acknowledged as loud-failure maintenance
costs, or already empirically settled by the mutation runs.

## Follow-up filed

**#375** — `EditorToolbar.tsx` has zero production importers; its `aria-label` a11y suite
(#50, WCAG 2.1 AA) passes against a component no user renders, while the live inline
toolbar in `ChapterEditor.tsx` has `title=` and no `aria-label`. Same hollow-test class as
this issue plus a real accessibility gap, scoped out rather than doubling this PR.
