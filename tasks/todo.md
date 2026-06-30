# Issue #51 — P2.9 Optimize mobile responsiveness

Branch: `feature/51-mobile-responsiveness`

## Adapted plan (verified against codebase + the real E2E spec)

The orphaned `frontend/e2e/responsive.spec.ts` is the acceptance spec. Key divergence from the
CodeRabbit plan: it proposed **opt-in** `mobile`/`icon-mobile` button variants. The test
`responsive.spec.ts:99` asserts *every visible button* is ≥44×44px — an opt-in variant nobody
wires up passes nothing. So instead: **auto-apply 44px sizing at mobile widths in the primitive
base classes** (one edit each, desktop unchanged). Less churn, actually passes.

### Phase 1 — Touch targets (44px) on mobile via responsive base classes
- [ ] `ui/button.tsx` — add `max-md:min-h-11 max-md:min-w-11` to the CVA base → all buttons ≥44px on mobile, desktop keeps h-9. (No new variants; drop plan's `mobile`/`icon-mobile`.)
- [ ] `ui/input.tsx` — add `max-md:min-h-11` (36→44 on mobile).
- [ ] `ui/select.tsx` — SelectTrigger `max-md:min-h-11`.
- [ ] `ui/textarea.tsx` — already `min-h-16` (64px) → **no change**.
- [ ] `ui/radio-group.tsx` — wrap 16px indicator in a 44px tappable area on mobile (`max-md:` padding) without shifting desktop.
- [ ] `ui/switch.tsx` — increase mobile tappable height to 44px (`max-md:min-h-11`, keep visual track).
- [ ] auth `sign-in`/`sign-up` password toggles (raw `<button>`) — add `flex items-center justify-center min-h-11 min-w-11` (mobile-safe; they're absolutely positioned).
- [ ] `QuestionNavigation.tsx` — already 44px → **no change**.

### Phase 2 — Swipe gesture hook + chapter navigation
- [ ] New `hooks/useSwipeGesture.ts` — native touch events, configurable threshold (~50px), horizontal-vs-vertical discrimination, returns a ref. Matches `use-media-query.ts` SSR-safe pattern. **+ unit test.**
- [ ] `ChapterTabs.tsx` — on mobile, attach swipe ref to the content container; swipe left→next chapter, right→prev (compute from `state.tab_order` + `active_chapter_id`, reuse `handleTabSelect`). No interference with vertical scroll/text selection.
- [ ] Skip decorative swipe-direction indicators / bottom prev-next buttons (plan's soft "consider" items — YAGNI; AC only requires swipe works).

### Phase 3 — Viewport, layout, E2E activation
- [ ] `app/layout.tsx` — add Next.js `export const viewport` (`width=device-width`, `initial-scale=1`, `viewport-fit=cover`). **No `maximum-scale=1`** (blocks zoom — a11y anti-pattern; plan hedged on it).
- [ ] Horizontal scroll: verify `/dashboard` at 320px via E2E; add `overflow-x-hidden` only where a real overflow is found. Don't pre-emptively rewrite `BookCard`/header unless the test fails.
- [ ] Move `frontend/e2e/responsive.spec.ts` → `frontend/src/e2e/responsive.spec.ts` (into the configured `testDir`). Make the viewport/touch-target/horizontal-scroll tests pass against the served app (mirror sibling specs' auth/route handling if redirect blocks them). Leave the 6 chapter-page-fixture-dependent skips documented if they can't be made deterministic.

## Acceptance criteria (issue #51)
- [ ] All touch targets ≥44×44px (mobile)
- [ ] No horizontal scroll at any mobile width (320px+)
- [ ] Content readable without zooming
- [ ] Forms work with mobile keyboards
- [ ] Swipe gestures navigate chapters
- [ ] Mobile Lighthouse perf >85 (manual/verify)
- [ ] E2E tests pass on mobile viewports

## Quality gates
- [ ] `npm run lint` + `npm run typecheck` clean
- [ ] Unit tests pass, coverage ≥85/85/75/85
- [ ] New: useSwipeGesture test, button/input/etc. variant tests as needed
- [ ] Frontend-only — backend untouched
