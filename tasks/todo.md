# Issue #200 [P2.8] Remove/repair orphaned 'gold standard' tests

**Plan source**: self-authored (no plan comment on issue). Verified current state 2026-07-13 — all four files still exist and the issue premise holds, with one aggravation: the backend file is *collected and runs green* (asyncio_mode=auto), not merely orphaned.

## Verified evidence per file

1. `frontend/src/__tests__/SystemIntegration.test.tsx` — imports nonexistent `@/lib/api/aiClient` (no such file in `src/lib/api/`), calls nonexistent bookClient methods, Clerk-era, requires live OpenAI. Jest-excluded by name (`jest.config.cjs:27`). Real journey coverage: `src/e2e/complete-authoring-journey.spec.ts` (rewritten #193) + staging `complete-user-journey.spec.ts`.
2. `frontend/src/__tests__/e2e/SystemE2E.test.tsx` — Playwright `testDir` is `./src/e2e`; file is in `src/__tests__/e2e/` → collected by nothing (also triple-excluded in jest config lines 25/26/37). Clerk-era selectors. Same real coverage as above.
3. `frontend/src/__tests__/TocGenerationWizard.test.tsx` — RUNS in jest. Test 1 is vacuous (`expect(true).toBe(true)`, wizard import commented out). Tests 2–7 are real but test *child components*, not the wizard. The wizard itself now has 12 real state-machine tests in `src/components/toc/__tests__/TocGenerationWizardEntitlement.test.tsx` (#247).
4. `backend/tests/test_draft_generation_api.py` — collected (1 item), zero asserts, prints "READY!", passes unconditionally. Endpoint has 9 real route tests in `tests/test_api/test_routes/test_books_draft_style_coverage.py` (happy/404/403/400/503/500) plus `test_draft_generation_simple.py`.

## Steps

- [ ] 1. Delete `SystemIntegration.test.tsx`; remove its `testPathIgnorePatterns` entry (jest.config.cjs:27).
- [ ] 2. Delete `SystemE2E.test.tsx` + now-empty `src/__tests__/e2e/` dir; remove ignore entries (jest.config.cjs:25–26).
- [ ] 3. Dissolve `TocGenerationWizard.test.tsx` (file name promises wizard coverage it doesn't deliver):
  - vacuous wizard test → delete (real wizard tests exist, #247)
  - ClarifyingQuestions test → delete (redundant with 33-test dedicated suite incl. submit flow)
  - TocGenerating loading test → **move** to new `src/components/toc/__tests__/TocGenerating.test.tsx` (only coverage of this component anywhere)
  - TocReview "displays TOC structure" + "deeply nested and empty chapters" → **move** into existing `src/components/toc/__tests__/TocReview.test.tsx` (dedicated file only covers Accept-button loading state)
  - genre-interpolation test + "mobile responsive" test → delete as slop (former re-renders same component with different strings, zero branch coverage; latter asserts a padding class in jsdom — resize does nothing)
  - delete the old file
- [ ] 4. Delete `backend/tests/test_draft_generation_api.py`. Also delete `tests/test_api/test_draft_generation.py.disabled` (same trust class — a test that executes nowhere, superseded by the route tests; disclosed in PR).
- [ ] 5. Verify: frontend full jest suite green (moved tests collected + passing in new homes); backend suite green; grep shows zero remaining refs; mutation check — moved tests RED when their assertions are violated.
- [ ] 6. Deslop scan, quality gate, PR, reviews, demo (Showboat, tests-only — main-vs-branch differential showing the vacuous backend test passing green with 0 asserts on main), CI, merge.

## Out of scope (verified, left alone)
- `backend/tests/test_system_e2e.py` / `test_e2e_no_mocks.py` — real, skipif-gated on OPENAI_API_KEY; not vacuous.
- `frontend/src/lib/api/chapter-tabs-old.ts` — unrelated.
