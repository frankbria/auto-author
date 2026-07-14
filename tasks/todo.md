# Issue #217 — 2FA lockout risk: backup codes shown once, no regenerate, no sign-in recovery path

**Plan source**: self-authored (no plan comment on the issue).
**Approval**: autonomous — no architectural fork. Minor decisions: recovery link = inline
instructions + existing support@autoauthor.com address; forced acknowledgment = checkbox
gating "Verify & Enable".
**Scope**: frontend-only. better-auth 1.4.9 client exposes
`authClient.twoFactor.generateBackupCodes({ password })` → `{ backupCodes }`
(POST /two-factor/generate-backup-codes, password-gated, verified in installed .d.mts).
Types are inferred via the twoFactorClient plugin — no cast changes needed in auth-client.ts.

## Steps (TDD: tests first)

1. **Tests (RED)** — extend `frontend/src/components/settings/__tests__/SecuritySettings.test.tsx`:
   - T1: enable flow — "Verify & Enable" stays disabled until the "I've saved my backup codes" acknowledgment is checked; warning text ("won't be shown again") rendered; verifyTotp not callable before ack.
   - T2: enabled state shows "Regenerate backup codes"; click → password step → submit calls the regenerate client method → new codes rendered with old-codes-invalidated warning + Copy; Done returns to idle.
   - T3: regenerate with wrong password → destructive toast, no codes shown.
   Extend `frontend/src/__tests__/VerifyTwoFactorPage.test.tsx`:
   - T4: "Lost access to your authenticator and backup codes?" disclosure present; expanding reveals recovery instructions with support email.
   Add `generateBackupCodes` mock to `frontend/src/__mocks__/better-auth-react.ts` twoFactor object.

2. **Implement** `frontend/src/components/settings/TwoFactorSetup.tsx`:
   - `mode: 'enable' | 'disable' | 'regenerate'`; new step `'codes'` for regenerated codes.
   - Idle+enabled: "Regenerate backup codes" button beside "Disable 2FA".
   - Password step regenerate branch → `generateBackupCodes` → step 'codes' (warning + codes grid + Copy + Done). Error → destructive toast (same idiom as enable).
   - Verify step: explicit warning "these codes won't be shown again — save them now" + acknowledgment Checkbox gating the "Verify & Enable" button (forced acknowledgment before enable). Reset ack state on entry.

3. **Implement** `frontend/src/app/auth/verify-2fa/page.tsx`:
   - Below the backup-code toggle: native `<details>` "Lost access to your authenticator and backup codes?" → instructions to contact support@autoauthor.com (address already published on /dashboard/help) from the account email to verify identity and reset 2FA.

4. **Gates**: jest (affected suites + coverage), lint, typecheck. Deslop scan. Cross-family review pre-PR. Mutation check (remove ack gating → T1 red; point regenerate at enable → T2 red).

## Acceptance criteria mapping
- AC1 "Regenerate backup codes action in enabled state" → Step 2, T2/T3.
- AC1 "one-time-only warning (forced acknowledgment) before enable" → Step 2 verify-step checkbox, T1.
- AC2 "Lost access link with support/recovery instructions on verify-2fa" → Step 3, T4.

## Assumptions / deviations
- No support/recovery page exists → inline `<details>` instructions + existing support email (a new /support route would be YAGNI).
- "View backup codes" not added: better-auth stores codes encrypted server-side; regenerate is the client-exposed, password-gated path and satisfies the AC as written.
- Backend untouched (better-auth handles the endpoint natively).
