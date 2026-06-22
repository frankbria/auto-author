# Issue #44 — Wire up broken/stubbed UI elements

Adapted from Traycer + CodeRabbit plans to the **actual** current code state
(tabs/tooltip/radio-group/progress UI primitives already exist from PRs #78/#79).

## Scope (4 genuinely-broken items)

### 1. Settings page save (`frontend/src/app/dashboard/settings/page.tsx`)
- `handleSaveSettings` is a TODO that only toasts. Wire to `PATCH /api/v1/users/me`.
- Use `useAuthFetch` hook (cookie auth, `credentials: 'include'`).
- Map: `darkMode` → `preferences.theme` ('dark'|'light'), `emailNotifications` → `preferences.email_notifications`.
- Loading state + error toast. autoSave/font-size/interval stay client-only (no backend fields).

### 2. QuestionGenerator (`.../questions/QuestionGenerator.tsx`)
- Delete inline stubs (lines 11-52).
- Import real `RadioGroup`/`RadioGroupItem` + `Tooltip*` (exist).
- Create `ui/checkbox.tsx` + `ui/slider.tsx` (shadcn pattern, lucide-react icon like radio-group); add deps `@radix-ui/react-checkbox`, `@radix-ui/react-slider`.

### 3. QuestionProgress (`.../questions/QuestionProgress.tsx`)
- Delete stub `Progress` → import `@/components/ui/progress`.
- Delete `StubTooltip` → use real `Tooltip` (already imported).

### 4. Chapter tab Edit action
- `TabContextMenu.tsx`: add `onEdit?`, Edit button calls `onEdit(chapterId)` (not console.log), gate on prop.
- `ChapterTabs.tsx` (line 225): pass `chapterId={state.active_chapter_id}` + `onEdit={setActiveChapter}`.

## Process
- TDD where it adds value (settings save, context menu edit, checkbox/slider).
- Branch: `fix/issue-44-broken-ui-elements`.
- Gates: lint, typecheck, unit tests, lockfile sync, cross-family review, demo, CI.

## Out of scope
- Backend (PATCH /users/me already works).
- autoSave/font-size persistence (no backend support — kept client-side).
