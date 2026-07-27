# Issue #341 — [P1.9] Hollow/tautological tests + untested rich-text editing inflate green CI

Branch: `fix/341-hollow-tests-rich-text-e2e`
**Plan source:** self-authored (issue had no plan comment).
No architectural fork — proceeding without approval per Phase 4.

## Acceptance criteria
- [ ] Delete the tautological/zero-assert/harness tests (#200/#210 precedent).
- [ ] Add one real-browser E2E that applies Bold/Heading/List via the toolbar and asserts the resulting marks/HTML.
- [ ] Drop the brittle mock call-count assertion.

## Findings from exploration (verified, not assumed)
- `src/e2e/` is the root `playwright.config.ts` `testDir`, and `.github/workflows/tests.yml`
  runs `npx playwright test --project=chromium` as a **required** check — a new spec there genuinely gates.
  (`tests/e2e/staging/` is the separate scheduled staging suite.)
- `editing-autosave-flow.spec.ts` already drives the real TipTap editor against a real backend with
  deterministic seeded books (`helpers/testData.ts`, no AI) — the model to follow.
- The live toolbar is **inlined in `ChapterEditor.tsx`** and labels buttons with `title=` only (no `aria-label`).
  Playwright's accessible-name computation falls back to `title`, so `getByRole('button', {name:'Bold'})` matches.
- Deleting `test_debug_chapter_questions.py` loses no coverage: `test_services/test_question_generation_service.py`
  covers that service call (11 refs), and the near-identical sibling `tests/test_debug_questions.py` makes the
  same call **with 3 real asserts**.
- `grep` confirms **no importer** of `TestInfrastructureIntegration.test.tsx`'s exported `testUtils` /
  `renderWithSuspense` / `renderWithErrorBoundary`.

## Steps

### 1. Delete the hollow tests (AC 1)
| File | Why it validates nothing |
|---|---|
| `frontend/src/__tests__/MockSystemFlow.test.tsx` | Mocks `bookClient` wholesale, renders no component, asserts the mocks return their own configured values. Prints "All core workflows validated". Zero product coverage. |
| `frontend/src/__tests__/TestInfrastructureIntegration.test.tsx` | Tests the harness ("Jest is configured", "the router mock returns the mock"). Renders only inline throwaway components. |
| `frontend/src/__tests__/example.test.tsx` | Scaffold: renders a local `<Hello>`, asserts it says hello. |
| `backend/tests/test_debug_chapter_questions.py` | **Zero asserts**, only `print()` — collected, cannot fail. |

Root-cause sweep (per the #210 "sweep the class, not just the cited file" precedent): scanned all of
`backend/tests` for collected-but-assertless files. Three hits.
- `test_debug_chapter_questions.py` → delete.
- `test_e2e_no_mocks.py` → **keep**: no asserts of its own, but delegates to `SystemE2ETest.run()`, whose
  `raise_for_status()` calls give it teeth; skipped without `OPENAI_API_KEY`. Not tautological.
- `test_system_e2e_simplified.py` → **fix, don't delete** (step 4).

### 2. Drop the brittle mock call-count assertion (AC 3)
`RichTextEditor.test.tsx:154` — `expect(mockRunFn).toHaveBeenCalledTimes(7)` against a shared mock; it passes
whether Bold is wired to `toggleBold` or `toggleItalic`. Replace with **per-command wiring assertions**: each
`toggle*` becomes its own `jest.fn()`, and clicking Bold must call `toggleBold`, Italic `toggleItalic`, H1
`toggleHeading({level:1})`. Still a mock, but it pins the one thing this jsdom layer can honestly prove —
button → correct command. Real formatting output is proven by step 3.

### 3. Real-browser formatting E2E (AC 2)
New `frontend/src/e2e/editor-formatting.spec.ts`, modelled on `editing-autosave-flow.spec.ts`.
Per format (Bold, Heading 2, Bullet List): type into the real `.tiptap`, select, click the toolbar button by
accessible name, then assert **both** (a) the live DOM contains the mark (`strong`, `h2`, `ul > li`) wrapping
the text, and (b) the auto-saved backend content contains the tag — outcome evidence that formatting survives
the round trip, not merely that a command ran.

### 4. Give `test_system_e2e_simplified.py` its missing assert
On the zero-assert list, but `raise_for_status()` means HTTP failures fail it — deleting a working smoke test
would be the wrong call. Its one hollow line is `verify_system()` computing `has_toc` and **discarding it**:
a book that generated no TOC passes today. Assert the returned value. One line.

### 5. Verification
- `npm test` + coverage gate (85/85/75/85). Deleted files carry no product coverage → no regression expected.
- `uv run pytest` on the touched backend paths.
- `npx playwright test editor-formatting --project=chromium` against real backend + Mongo.
- **Mutation-check** the new E2E: break the Bold wiring in `ChapterEditor.tsx`, confirm the spec goes RED.
  (A formatting test that can't fail would recreate the exact problem this issue is about.)

## Autonomous decisions (no architectural fork)
- **Fix rather than delete** `test_system_e2e_simplified.py` — a one-line assert beats deleting a test that
  already catches HTTP failures.
- **Rewrite rather than delete** the `RichTextEditor` formatting test — the AC only says drop the count
  assertion; button→command wiring is still worth pinning.
- **Keep the global TipTap mock** in `jest.setup.ts`. TipTap can't run in jsdom; the issue's own remedy is a
  real-browser test, which step 3 adds. Removing the mock breaks many suites and proves nothing.

## Out of scope — follow-up to file
`frontend/src/components/chapters/EditorToolbar.tsx` has **zero production importers** — the shipping toolbar is
inlined in `ChapterEditor.tsx`. Its suite `__tests__/EditorToolbar.test.tsx` asserts `aria-label` on every
icon-only button (#50, WCAG 2.1 AA) against a component **no user ever sees**, while the live inline toolbar has
`title=` and **no `aria-label`**. Same hollow-test class as this issue, plus a real a11y gap — but it needs its
own change (dedupe, or delete-and-retarget) rather than doubling this PR.
