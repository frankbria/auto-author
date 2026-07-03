# Code Review: Account Settings (#64)

**Date**: 2026-07-02 · **Scope**: working-tree diff vs `main` (20 files, +709/−299)
**Review plan**: A07 Authentication (HIGH — 2FA/password/sessions), A01 Access Control,
Data Integrity (preferences replace semantics), hook-cache correctness.
Skipped: LLM/ML checks (no AI-code change), performance (no hot paths).

## Findings & Resolutions

### Fixed during review (pre-commit)

1. **[HIGH] Sign-in raced the 2FA redirect** — `sign-in/page.tsx` unconditionally
   `router.push(redirect)` after a non-error `signIn.email`. A 2FA account returns
   `twoFactorRedirect` with **no session**, so the push to `/dashboard` raced the
   plugin redirect and bounced through middleware. Fixed: early-return on
   `twoFactorRedirect`.
2. **[MEDIUM] verify-2fa swallowed transport failures** (CodeRabbit) — `verifyTotp`/
   `verifyBackupCode` rejections (network) left the page stuck. Fixed: catch →
   destructive toast → reset/refocus.
3. **[MEDIUM] Preference-cache clobber race** (CodeRabbit) — an in-flight GET could
   overwrite a fresher value stored by `invalidateUserPreferencesCache`. Fixed:
   generation counter; only same-generation fetches fill the cache.
4. **[MEDIUM] 2FA status didn't flip after disable** — session's `twoFactorEnabled`
   is stale until refetch; the old flicker-guard only covered enable. Fixed:
   `localEnabledOverride: boolean | null` covers both directions (+ regression test).
5. **[LOW] QR-only enrollment** (CodeRabbit) — added a selectable manual-entry
   secret (parsed from the `totpURI`) for apps that can't scan.

### Verified safe (no change needed)

- **Access control**: preferences ride `PATCH /users/me` behind
  `get_current_user_from_session` + rate limit; no new endpoints.
- **Input validation**: all new preference fields are `Literal`/bounded ints —
  nested strings can't carry payloads even though `sanitize_input` only walks
  top-level strings.
- **Replace-not-merge semantics**: `UserUpdate.preferences` replaces the whole
  object (Pydantic default-fills omissions). Every writer (settings page, profile
  page) merges loaded prefs before saving; tested with an unknown
  `future_flag` survival test.
- **Credential handling**: passwords only pass through better-auth client calls;
  no logging; `revokeOtherSessions: true` on password change; backup codes exist
  only in component state.
- **Active sessions**: uses better-auth native `listSessions`/`revokeSession`
  (scoped server-side to the requesting user). The legacy backend `/sessions/*`
  store is never populated post-better-auth (`request.state.user` is never set) —
  deliberately not used.

### Rebutted (with reasons)

- **Native `<select>` → shadcn Select** (CodeRabbit): native selects are the
  established profile-page pattern (#63), fully labeled (max a11y), and testable
  in jsdom without the portal mock; declined for consistency.
- **Cache should store null results** (CodeRabbit): intentional — a failed fetch
  must retry on a later mount rather than pinning "no preferences" for the session.

## Verdict

✅ Approved. Frontend 2003 passed/8 skipped (108/108 suites, coverage
89.96/81.04/86.51/91.2); backend preferences tests 15/15 + full suite green with
`BYPASS_AUTH=false` (a leftover `backend/.env` `BYPASS_AUTH=true` explains local
failures in auth-assertion tests — environmental, not code); E2E settings spec
5/5 (chromium).
