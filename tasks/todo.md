# Issue #185 — [P1.5] /profile route has no authentication guard

**Plan source**: self-authored (no plan comment on issue). No architectural fork — AC permits either guard; we apply both to mirror the dashboard exactly → approved autonomously.

## Findings
- `middleware.ts:37` protects only `/dashboard*`; `app/profile/page.tsx` uses `useSession` but never guards/redirects → profile page (edit name/bio, delete-account UI) renders for unauthenticated visitors.
- Dashboard fails closed via BOTH middleware (server redirect + `?redirect=` deep link) and `ProtectedRoute` in `dashboard/layout.tsx` (client guard); profile has neither.
- `?redirect=/profile` flows into #184's `sanitizeRedirectPath` — relative path, so deep-link back after sign-in works.
- `ProtectedRoute` pushes `/auth/sign-in` without the redirect param — same as dashboard, consistent, not in scope.

## Steps (TDD)
1. [ ] Tests first:
   - `src/__tests__/middleware.test.ts` (node env): `/profile` without session cookie → redirect to `/auth/sign-in?redirect=/profile`; with cookie → pass; `/dashboard` regression; public `/` passes.
   - `ProfilePage.test.tsx`: unauthenticated (`data: null, isPending: false`) → `router.push('/auth/sign-in')`, profile form NOT rendered; `isPending` → loading state, form not rendered.
2. [ ] `middleware.ts`: `isProtectedRoute = pathname.startsWith('/dashboard') || pathname.startsWith('/profile')`.
3. [ ] `app/profile/page.tsx`: wrap page JSX in `<ProtectedRoute>` (same as `dashboard/layout.tsx`).
4. [ ] Full frontend suite + lint + typecheck.
5. [ ] Deslop scan, quality gate (opencode GLM pre-PR review), PR, post-PR review, demo (two real dev servers: main leaks profile page unauthenticated vs branch redirects), CI, merge.
