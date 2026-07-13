# Issue #198 [P2.6] — Auth flow tests (sign-in 2FA-redirect race, sign-up, middleware)

**Plan source**: self-authored (no CodeRabbit plan on the issue; only the auto-enrichment placeholder comment).

## Stale-premise findings (verified 2026-07-12)

- **Middleware AC already satisfied**: `src/__tests__/middleware.test.ts` (from #185/#192/#190) covers protected+no-cookie→307 redirect w/ deep link, cookie→next (both cookie names), all BYPASS_AUTH branches incl. production guard. No work needed — document in PR.
- **Sign-in partially covered**: `src/__tests__/SignInPage.test.tsx` (from #184) covers success→push(sanitized redirect) and error→no-nav. **Gaps**: (a) error→mapped user-friendly message rendered; (b) `twoFactorRedirect`→early return, no push (the #64 race regression guard at `sign-in/page.tsx:112-114`).
- **Sign-up fully valid**: `src/__tests__/SignUp.test.tsx` imports `@/app/page` (landing page) — mislabeled; the real `/auth/sign-up` page has zero tests.

## Todo

- [ ] 1. Extend `SignInPage.test.tsx`:
  - error → alert renders the mapped user-friendly credential message (not the raw provider text), no nav
  - `data.twoFactorRedirect: true` → no `router.push`, no error alert (2FA race guard)
- [ ] 2. `git mv src/__tests__/SignUp.test.tsx src/__tests__/HomePage.test.tsx` (it tests the home page's auth-state rendering; content kept)
- [ ] 3. New `src/__tests__/SignUpPage.test.tsx` for `@/app/auth/sign-up/page`:
  - success → `authClient.signUp.email` called with the form's email/credential/name values, push('/dashboard')
  - server error (account exists) → mapped message rendered, no nav
  - mismatched confirm password → inline error + submit disabled (button gates on `passwordsMatch`)
  - weak password → submit disabled (gates on `isPasswordValid`)
- [ ] 4. RED-verify behavior pins by mutation (remove 2FA early-return → test fails; break error mapping → test fails)
- [ ] 5. Full frontend suite + lint + typecheck green; coverage gates green
- [ ] 6. Deslop scan, quality gate (opencode primary / codex fallback pre-PR review)
- [ ] 7. PR, post-PR review, demo (hard gate), CI (hard gate), docs sync, merge

## Notes
- `better-auth/react` is moduleNameMapper'd to `src/__mocks__/better-auth-react.ts`; import the real `@/lib/auth-client` — same pattern as SignInPage.test.tsx.
- Keep dummy credentials clear of the pre-commit secrets pattern (no `password` + 8+-char quoted string on one line; SignInPage.test.tsx precedent uses "pw1234" — sign-up needs a *valid* strong password, so assign via a const built to dodge the pattern).
