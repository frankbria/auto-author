# Issue #46 — Comprehensive error feedback to UI

## Ground truth (verified in codebase, not the stale issue body)
- Error infra exists & is solid: `@/lib/errors` (`classifyError`, `handleApiCall`, `ClassifiedError`), `@/components/errors` (`ErrorNotification`, `showErrorNotification`), `@/components/loading/LoadingStateManager`.
- `@/lib/toast` wrapper exists but is imported **nowhere**. Code uses `sonner` direct + `useToast()` hook. **All three render through the same sonner `<Toaster>`** → notifications already look identical to users.
- Issue body paths are stale (`src/utils/...`, `new-book/page.tsx`). Real paths verified below.

## Real user-facing gaps (CORE — recommended)
1. **Duplicate Toaster** — `src/app/layout.tsx` mounts both `<Toaster/>` (ui/toaster) and `<SonnerToaster/>` (ui/sonner). Two sonner Toasters = duplicate toasts. → remove one (keep `SonnerToaster`, theme-aware).
2. **new-book silent failure** — `src/app/dashboard/new-book/page.tsx` catch only `console.error`s. Loading state already exists. → add error feedback (`showErrorNotification` + `classifyError`) and success toast.
3. **ChapterTabs heavy retry** — `src/components/chapters/ChapterTabs.tsx` error state uses `window.location.reload()`. `refreshChapters()` already destructured. → swap reload→refreshChapters; reuse `ErrorNotification` for the error block.

## Optional (STANDARDIZATION — churn, low user value)
- Migrate `sonner`/`useToast` imports → `@/lib/toast` across dashboard/page, book-detail, export, settings, Draft*/Question* components. Pure import churn, no visual change, breaks ~10 test files that mock `sonner`/`useToast`. Acceptance "consistent UI" already met visually.

## Tests
- new-book: add test asserting error feedback on createBook rejection + success path.
- ChapterTabs: retry calls refreshChapters (not reload).
- layout: single Toaster mounted.
