# Issue #185 — [P1.5] /profile route has no authentication guard

**Plan source**: self-authored (no plan comment on issue). No architectural fork — AC permits either guard; we apply both to mirror the dashboard exactly → approved autonomously.

## Findings
- `middleware.ts:37` protects only `/dashboard*`; `app/profile/page.tsx` uses `useSession` but never guards/redirects → profile page (edit name/bio, delete-account UI) renders for unauthenticated visitors.
- Dashboard fails closed via BOTH middleware (server redirect + `?redirect=` deep link) and `ProtectedRoute` in `dashboard/layout.tsx` (client guard); profile has neither.
- `?redirect=/profile` flows into #184's `sanitizeRedirectPath` — relative path, so deep-link back after sign-in works.
- `ProtectedRoute` pushes `/auth/sign-in` without the redirect param — same as dashboard, consistent, not in scope.

## Steps (TDD)
1. [x] Tests first:
   - `src/__tests__/middleware.test.ts` (node env): `/profile` without session cookie → redirect to `/auth/sign-in?redirect=/profile`; with cookie (both dev + `__Secure-` prod names) → pass; `/dashboard` regression; public `/` passes.
   - `ProfilePage.test.tsx`: unauthenticated (`data: null, isPending: false`) → `router.push('/auth/sign-in')`, profile form + delete-account UI NOT rendered; `isPending` → loading state; authenticated regression.
2. [x] `middleware.ts`: `isProtectedRoute = pathname.startsWith('/dashboard') || pathname.startsWith('/profile')`.
3. [x] `app/profile/page.tsx`: wrap page JSX in `<ProtectedRoute>` (same as `dashboard/layout.tsx`). Side effect: `jest.setup.ts` browser globals guarded for node-env suites.
4. [x] Full frontend suite (110 suites, 2035 passed / 8 skipped) + lint 0 errors + typecheck clean.
5. [x] PR #238. opencode (GLM) pre-PR ×2 rounds → "clean to merge" (M2 indent + N2 assertion fixed; M1/M3/M4/N1/N3 rebutted). Post-PR fresh session → "clean to merge" (M1 `__Secure-` cookie test added; N4 deep-link drop filed as #239).
6. [ ] Demo (hard gate), CI green, merge.
