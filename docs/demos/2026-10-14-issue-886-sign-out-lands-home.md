# Issue #886: signing out, or deleting the account, lands on the home page

*2026-10-14T17:24:30Z by Showboat 0.6.1*
<!-- showboat-id: 5d45571c-d455-4b07-bdfe-7f4345cabf87 -->

The real-auth Playwright suite (#843): a real better-auth server and a real backend on their own ports, bypass off, in Chromium. src/e2e/real-auth/sign-out-lands-home.spec.ts signs up and verifies an account, then (1) signs out from the dashboard's account menu, or (2) deletes the account from the profile page, and expects to end on /. The run script puts main's versions of the five changed source files in place for the 'main' run and asserts the tree is restored after.

```bash
bash "$DEMO/run_spec.sh" main
```

```output
✘  1 [chromium] › src/e2e/real-auth/sign-out-lands-home.spec.ts:13:5 › signing out from the dashboard lands on the home page (1.3m)
✘  2 [chromium] › src/e2e/real-auth/sign-out-lands-home.spec.ts:22:5 › deleting the account from the profile page lands on the home page (1.2m)
Error: expect(page).toHaveURL(expected) failed
- unexpected value "http://localhost:3001/dashboard"
- unexpected value "http://localhost:3001/auth/sign-in?redirect=%2Fdashboard"
test-results/real-auth/sign-out-lands-home-signin-5c063-oard-lands-on-the-home-page-chromium/test-failed-1.png
Error: expect(page).toHaveURL(expected) failed
- unexpected value "http://localhost:3001/profile"
112 × unexpected value "http://localhost:3001/auth/sign-in?redirect=%2Fprofile"
- unexpected value "http://localhost:3001/auth/sign-in?redirect=%2Fprofile"
test-results/real-auth/sign-out-lands-home-deleti-2ff12-page-lands-on-the-home-page-chromium/test-failed-1.png
2 failed
```

On main, sign-out ends on sign-in with a way back to the dashboard, and deletion ends on sign-in with a way back to the profile (the page's refetch gets a 401 and the shared handler redirects). In an earlier run on main the deletion never left the profile page at all: the delete was refused with a 429, because GET, PATCH and DELETE /users/me shared one rate-limit bucket, and the buckets only coincide in some windows, so this run did not hit it. This branch:

```bash
bash "$DEMO/run_spec.sh" branch
```

```output
✓  1 [chromium] › src/e2e/real-auth/sign-out-lands-home.spec.ts:13:5 › signing out from the dashboard lands on the home page
✓  2 [chromium] › src/e2e/real-auth/sign-out-lands-home.spec.ts:22:5 › deleting the account from the profile page lands on the home page
2 passed
```

Mutation check (scratch script, each reverted and asserted clean): ProtectedRoute ignoring the flag, the 401 handler ignoring it, the flag never expiring, the flag kept after a failed sign-out, and the rate-limit bucket without the method were each caught by name.
