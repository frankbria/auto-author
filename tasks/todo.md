# Issue #52 [P2.8] — Comprehensive loading indicators & progress tracking

**Source**: CodeRabbit plan in issue comments, adapted to current codebase.
**Branch**: `feature/52-loading-indicators`
**Scope**: frontend-only. Reuses existing `Skeleton`, `LoadingStateManager`, `Loading03Icon`.

## Adapted steps

### Already done (verified in code — skipped)
- ~~DraftGenerator dead `LoadingStateManager`~~ — fixed in #55 (`isGenerating` checked first).
- ~~DraftGenerationButton fetch-gap loading~~ — `handleGenerateDraft` sets `step='generating'` *before* the fetch; `LoadingStateManager` already shows during it. No gap.

### Step 1 — Page-level skeleton loaders (replace centered spinners)
1a. `app/dashboard/page.tsx` (l.93-102) → skeleton: header + 3-col BookCard-shaped grid + button placeholder. `role="status"` `aria-live="polite"`.
1b. `app/dashboard/loading.tsx` → matching dashboard skeleton (lightweight).
1c. `app/dashboard/books/[bookId]/page.tsx` (l.322-331) → skeleton: breadcrumb, title, stepper, two-column form/sidebar, tabs.
1d. `components/chapters/ChapterTabs.tsx` (l.150-159) → skeleton: vertical tab list + content area.

### Step 2 — Component loading-state gaps
2a. `components/toc/TocReview.tsx` — "Accept & Continue" button: spinner + "Saving..." when `isLoading` (mirror Regenerate button).
2b. `components/toc/ClarifyingQuestions.tsx` — add `isLoadingResponses`; skeleton/disabled question+textarea area during initial `loadExistingResponses`.
2c. `components/BookMetadataForm.tsx` — `isSaving` indicator gets a spinner; `disabled={isSaving}` on inputs.
2d. `components/chapters/questions/ChapterQuestions.tsx` — small spinner in progress-summary area while `loading` (instead of hiding it).

### Step 3 — DraftGenerator cleanup (trivial)
3a. Remove the now-dead inline `isGenerating` spinner branch in the Generate button (unreachable since the form only renders when `!isGenerating`).

## Tests (TDD)
- Skeleton renders (role=status, no spinner text) for 1a/1c/1d; loading.tsx render (1b).
- TocReview: Accept button shows "Saving..."/disabled when isLoading (2a).
- ClarifyingQuestions: loading skeleton + disabled inputs during load (2b).
- BookMetadataForm: spinner + inputs disabled when isSaving (2c).
- ChapterQuestions: progress spinner while loading (2d).

## Acceptance criteria (issue #52)
- [ ] All async operations show loading state
- [ ] Operations >2s show progress percentage — (LoadingStateManager, pre-existing for AI ops)
- [ ] Operations >5s show estimated time — (LoadingStateManager, pre-existing)
- [ ] Skeleton screens for page loads — Step 1
- [ ] Consistent loading UI pattern throughout
- [ ] Loading states accessible (ARIA live regions)
- [ ] No operation leaves user without feedback

## Deviations
- Two plan tasks dropped as already-satisfied (see above) — no value in re-doing.
- `LoadingSpinner` (named in plan) does not exist; use inline spinner / `Loading03Icon`.
- Skeletons inline per-page (plan Design Choice 2, option 2) — no new abstraction.
