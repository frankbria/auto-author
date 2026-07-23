# Issue #328 — frontend global functions coverage gate chronically red

## Root cause
Frontend `global.functions` coverage gate = 85%, but main sits at 84.64% (954/1127).
The gap is ~4 covered functions. Two files in the denominator are TEST INFRASTRUCTURE,
not shippable code, only counted because jest was never told to exclude them:
- src/__tests__/fixtures/chapterTabsFixtures.ts (9/14 fns)
- src/__tests__/mocks/speechRecognition.ts (7/10 fns)

## Plan (Option 1 — raise coverage honestly, keep the 85 bar)
1. jest.config.cjs: add `coveragePathIgnorePatterns` excluding test-infra dirs
   (src/__tests__/fixtures/, src/__tests__/mocks/, src/__mocks__/). Root-cause
   denominator fix. -> functions 84.64% -> 85.04%. Applies to both local & CI (both run jest).
2. Add genuine unit tests for currently-untested PURE functions (durable, not UI theater):
   - src/components/export/exportHelpers.ts: formatFileSize, estimateExportTime, downloadBlob
   - src/lib/api/bookClient.ts: 3 uncovered methods (if cheap) for extra buffer
3. Re-measure; target functions >= ~85.7% for jitter/erosion headroom.
4. Verify full suite still green.

## NOT chosen (documented for the PR)
- Lowering the threshold (weakens the gate) — unnecessary for a 4-function gap.
- Per-directory thresholds — more config to maintain for the same effect.
- Fallback if this recurs: pin an honest no-regression floor + ratchet.

## Acceptance criteria (from #328)
- [ ] Frontend PRs with all tests passing no longer require --admin to merge
      (i.e. main functions coverage >= 85%, gate green)
- [ ] Chosen approach documented in CLAUDE.md / CI config
