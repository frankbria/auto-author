# Issue #887: a deleted account is locked out, in a real browser

*2026-10-14T18:06:57Z by Showboat 0.6.1*
<!-- showboat-id: 2dfdb4ff-25e6-4659-91ff-6c3030a3e5c0 -->

The real-auth Playwright suite: a real better-auth server and a real backend on their own ports, bypass off, Chromium. The spec signs up and verifies, signs in from a second device, deletes the account from the profile page, then checks the second device and the old password.

```bash
cd frontend && npx playwright test --config=playwright.real-auth.config.ts src/e2e/real-auth/deleted-account-locked-out.spec.ts 2>&1 | grep -E "✓|✘|passed|failed" | sed -E "s/ \([0-9.]+m?s\)$//; s/^ +//"; rm -rf test-results
```

```output
✓  1 [chromium] › src/e2e/real-auth/deleted-account-locked-out.spec.ts:14:5 › a deleted account cannot sign back in, and its old session cookie is refused
1 passed
```

Mutation check (scratch script, each reverted and asserted clean). Removing the better-auth purge from account deletion: this spec fails (the second device still has a better-auth session). Keeping the session and account rows but deleting the better-auth user: this spec passes, because better-auth refuses a session and a password whose user is gone, so the lock-out holds; the backend's real-Mongo test test_deleted_account_is_locked_out_and_its_better_auth_docs_are_gone fails on it, which is where row-level purging is checked.
