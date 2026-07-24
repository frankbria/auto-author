# Demo — #332 Password reset fails loudly when the email provider is unconfigured

**Issue:** Password reset advertised "Check your email" but sent nothing in
production — a silent fake-success dead-end. Root cause: `sendPasswordResetEmail`
`console.warn`'d and returned silently when `EMAIL_SERVICE_PROVIDER` was unset in
every non-production environment, and `auth.ts`'s deliberate anti-enumeration
`void (async…)()` swallowed the production throw.

The forgot-password UI still shows generic success (email-enumeration protection
is intentional and unchanged). The failure must be observable in **server logs**,
not the HTTP response — that is what this fix delivers.

## AC3 — unconfigured provider is now observable (main-vs-branch differential)

Same scenario (`EMAIL_SERVICE_PROVIDER` unset), run against the branch fix and
against the old silent behavior (restored via mutation):

### Branch (fixed) — 7/7 green
```
✓ throws and logs a loud [email] error when no provider is configured (not a fake success)
✓ is observable in non-production environments too (no silent warn-and-return)
✓ throws naming an unknown provider
✓ sends via Resend when configured
✓ throws when Resend is selected without an API key
✓ sends via SendGrid when configured
✓ dumps to console in development with no provider (dev convenience, no send, no throw)
```

### Old behavior (silent warn-and-return, = the bug) — observability pins RED
```
✕ throws and logs a loud [email] error when no provider is configured (not a fake success)
✕ is observable in non-production environments too (no silent warn-and-return)
✓ throws naming an unknown provider
✓ sends via Resend when configured
✓ throws when Resend is selected without an API key
✓ sends via SendGrid when configured
✓ dumps to console in development with no provider (dev convenience, no send, no throw)
Tests: 2 failed, 5 passed, 7 total
```

The two RED pins are the exact fake-success dead-end the issue reports: an unset
provider that produced no email and no observable error. On the branch the same
call emits a greppable `[email] Password reset email NOT sent — EMAIL_SERVICE_PROVIDER
is not configured. Set EMAIL_SERVICE_PROVIDER, EMAIL_SERVICE_API_KEY, and
EMAIL_FROM_ADDRESS to enable delivery.` and throws. The dev-console convenience
path is unchanged on both (last pin green in both columns).

## AC1 — vars documented + wired to deploy

- `frontend/.env.example` now documents `EMAIL_SERVICE_PROVIDER`,
  `EMAIL_SERVICE_API_KEY`, `EMAIL_FROM_ADDRESS` (+ optional `EMAIL_FROM_NAME`)
  with the "REQUIRED in staging/production or account recovery silently fails"
  warning.
- `.github/workflows/deploy-staging.yml` writes the three `EMAIL_*` secrets into
  the frontend `.env.production` block; `next start` loads `.env.production` at
  runtime, so a configured provider reaches the server-side sender.

## AC2 — real staging delivery (MANUAL, ops step)

Cannot be executed from here — it requires a live provider (Resend/SendGrid) API
key set as the `EMAIL_SERVICE_PROVIDER` / `EMAIL_SERVICE_API_KEY` /
`EMAIL_FROM_ADDRESS` GitHub secrets and a staging deploy. After those secrets are
set and staging redeploys:
1. Trigger a password reset for a real staging account.
2. Confirm the email arrives (check the provider dashboard for the send event).
3. If misconfigured, the new `[email] … NOT sent` error appears in the frontend
   PM2 logs (`~/.pm2/logs/auto-author-frontend-error.log`) instead of a silent
   no-op.
