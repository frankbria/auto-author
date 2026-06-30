# Issue #50 — P2.10 Accessibility (WCAG 2.1 AA)

Branch: `feature/50-accessibility`. Frontend-only. Driven by the real axe audit + explorer evidence, not blind edits. Solid foundation already exists (Radix, jest-axe 0 violations on 6 components, correct form labels).

## Scope: concrete, automatable, testable deliverables (mapped to ACs)

### A. ARIA labels on icon-only buttons (AC: all interactive elements have ARIA labels)
- [ ] `components/chapters/EditorToolbar.tsx` — 13 buttons have `title=` but NO `aria-label` (titles aren't read by SRs). Add `aria-label` to each.
- [ ] `components/chapters/TabBar.tsx` — scroll up/down buttons: add `aria-label`.
- [ ] `components/chapters/TabOverflowMenu.tsx` — trigger: `aria-label="Show more tabs"`.
- [ ] `components/ui/user-button.tsx` — avatar trigger: `aria-label="Account menu"`.
- (Forms already labeled — sign-in/up, BookMetadataForm verified correct → no change.)

### B. Keyboard navigation (AC: full keyboard nav — tab/arrow/enter/escape)
- [x] ~~Arrow/Home/End roving tab navigation~~ — **DEFERRED (documented)**: `TabBar` renders tabs via react-beautiful-dnd `Draggable`s, which reserve Space/arrow keys for keyboard drag-reorder. Roving arrow nav would conflict and risk breaking accessible reordering. Tabs are already keyboard-operable (each `tabIndex=0`, Enter/Space activates → WCAG 2.1.1 met) + Ctrl+1-9 quick-switch. Arrow roving is an ARIA-APG recommendation, not an AA criterion.
- [ ] `components/books/DeleteBookModal.tsx` — wrap confirm input + actions in `<form onSubmit>` so Enter submits when confirmation matches.

### C. Landmarks + skip link (AC: skip links available)
- [ ] `app/layout.tsx` — add a `Skip to main content` link (`sr-only focus:not-sr-only`) at the top; change the wrapper `<main>` to a `<div>` (it's a layout wrapper, and nesting banner/contentinfo inside `main` is an axe violation).
- [ ] `app/dashboard/layout.tsx` — convert content `<div className="flex-1 bg-gray-950">` to `<main id="main-content">`; add `aria-label` to the `<nav>`s.
- [ ] `app/page.tsx` + auth `sign-in`/`sign-up` — ensure a single `<main id="main-content">` landmark wraps page content (skip-link target on public pages).

### D. Focus indicators (AC: focus indicators clearly visible)
- [ ] `app/globals.css` — add a global `*:focus-visible` outline fallback (complements component rings) for elements without their own ring.

### E. Color contrast (AC: contrast meets AA) — narrow; dark theme mostly passes
- [ ] `components/SummaryInput.tsx:104` `text-gray-500 dark:text-gray-600` help text → bump dark to `gray-400` (gray-600 on dark fails AA). Spot-fix only genuine failures; do NOT mass-swap (most `gray-400` on dark passes ~6:1).

### F. Automated a11y tests (AC: automated a11y tests pass)
- [ ] Extend `src/__tests__/accessibility/ComponentAccessibilityAudit.test.tsx` — unskip/ add Navigation (dashboard layout), EditorToolbar, and a SkipLink/landmark test (jest-axe → 0 violations).
- [ ] Unit tests: EditorToolbar aria-labels, ChapterTabs arrow/Home/End nav, DeleteBookModal Enter-submits, skip-link present + targets `#main-content`.

## ACs that are manual/deploy-time (documented, not auto-verifiable here)
- Lighthouse a11y >95 — deploy/manual (changes only improve it).
- Screen reader (NVDA/JAWS) announcements — manual; we wire the correct ARIA (role=alert/aria-live already documented + used).

## Gates
- [ ] lint + typecheck clean; full unit suite + coverage (≥85/85/75/85) green.
- [ ] jest-axe suite green (existing + new).
- [ ] codex cross-family review clean.
