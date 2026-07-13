# Issue #198: auth-flow tests — sign-in 2FA-redirect race, error mapping, real sign-up coverage

*2026-07-13T04:18:59Z*

Issue #198 says a regression in the primary login/registration paths ships green: the 2FA-redirect early return in sign-in was uncovered, error-message mapping was unpinned, and SignUp.test.tsx actually rendered the landing page instead of the sign-up form. This demo proves each gap with a main-vs-branch mutation differential: the same hand-applied regression sails through the test suite on main and is caught RED on the branch. Setup: a pristine main worktree at /tmp/.../scratchpad/main-198 (node_modules symlinked from the branch checkout — the diff is tests-only, dependencies identical); mutations are applied by scratchpad/mutate-and-test.sh, which mutates the page source, runs the sign-in/sign-up jest files, restores the source, and reports the verdict.

First, the stale-premise check. The issue also demanded middleware tests (protected+no-cookie→redirect, cookie→next, bypass branches) — those already exist from #185/#192/#190. Running the existing middleware suite as evidence that AC needs no new work:

```bash
cd /home/frankbria/projects/auto-author/frontend && npx jest src/__tests__/middleware.test.ts --silent 2>&1 | grep -E "^(PASS|FAIL)|Tests:"
```

```output
PASS src/__tests__/middleware.test.ts
Tests:       16 passed, 16 total
```

Next, the mislabeled sign-up test. On main, SignUp.test.tsx imports the home page component — and no test anywhere imports the real /auth/sign-up page:

```bash
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/a93f871d-0c6d-4fe0-ae41-b9d3958aad0b/scratchpad/main-198/frontend && grep -n "^import.*@/app" src/__tests__/SignUp.test.tsx && echo "-- tests importing the real sign-up page on main:" && (grep -rln "auth/sign-up/page" src --include="*.test.tsx" || echo NONE)
```

```output
3:import HomePage from '@/app/page';
-- tests importing the real sign-up page on main:
NONE
```

On the branch that file is renamed to HomePage.test.tsx (content unchanged — it genuinely tests the home page auth states) and a real SignUpPage.test.tsx exercises the actual registration form:

```bash
cd /home/frankbria/projects/auto-author/frontend && ls src/__tests__/ | grep -E "HomePage|SignUp" && grep -n "^import.*@/app" src/__tests__/SignUpPage.test.tsx
```

```output
HomePage.test.tsx
SignUpPage.test.tsx
6:import SignUpPage from "@/app/auth/sign-up/page";
```

Differential 1 — the 2FA-redirect race guard (the issue's headline AC). sign-in/page.tsx returns early when better-auth answers with twoFactorRedirect, so the page never races the 2FA client's /auth/verify-2fa navigation with router.push(/dashboard). Hand-remove that early return on MAIN and the auth suite stays green — exactly the "a regression here ships green" failure mode the issue describes:

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/a93f871d-0c6d-4fe0-ae41-b9d3958aad0b/scratchpad/mutate-and-test.sh /tmp/claude-1000/-home-frankbria-projects-auto-author/a93f871d-0c6d-4fe0-ae41-b9d3958aad0b/scratchpad/main-198 2fa
```

```output
== MUTATION: removed the twoFactorRedirect early return (sign-in now races router.push after a 2FA challenge)
 frontend/src/app/auth/sign-in/page.tsx | 4 +---
 1 file changed, 1 insertion(+), 3 deletions(-)
== running: npx jest src/__tests__/SignInPage.test.tsx 
PASS src/__tests__/SignInPage.test.tsx
Tests:       6 passed, 6 total
== RESULT: suite GREEN — this regression would ship
```

The identical mutation on the BRANCH is caught by the new pin:

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/a93f871d-0c6d-4fe0-ae41-b9d3958aad0b/scratchpad/mutate-and-test.sh /home/frankbria/projects/auto-author 2fa
```

```output
== MUTATION: removed the twoFactorRedirect early return (sign-in now races router.push after a 2FA challenge)
 frontend/src/app/auth/sign-in/page.tsx | 4 +---
 1 file changed, 1 insertion(+), 3 deletions(-)
== running: npx jest src/__tests__/SignInPage.test.tsx src/__tests__/SignUpPage.test.tsx 
FAIL src/__tests__/SignInPage.test.tsx
  ● SignInPage error and 2FA handling (#198) › returns early on twoFactorRedirect: no navigation, no error (2FA race guard, #64)
PASS src/__tests__/SignUpPage.test.tsx
Tests:       1 failed, 11 passed, 12 total
== RESULT: suite RED — regression caught (jest exit 1)
```

Differential 2 — error-message mapping. Main already pins "error → no navigation" but nothing pins the user-facing text, so leaking the raw provider error instead of the mapped "Email or password is incorrect" ships green on main:

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/a93f871d-0c6d-4fe0-ae41-b9d3958aad0b/scratchpad/mutate-and-test.sh /tmp/claude-1000/-home-frankbria-projects-auto-author/a93f871d-0c6d-4fe0-ae41-b9d3958aad0b/scratchpad/main-198 signin-mapping
```

```output
== MUTATION: credential errors now leak the raw provider message instead of the mapped text
 frontend/src/app/auth/sign-in/page.tsx | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
== running: npx jest src/__tests__/SignInPage.test.tsx 
PASS src/__tests__/SignInPage.test.tsx
Tests:       6 passed, 6 total
== RESULT: suite GREEN — this regression would ship
```

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/a93f871d-0c6d-4fe0-ae41-b9d3958aad0b/scratchpad/mutate-and-test.sh /home/frankbria/projects/auto-author signin-mapping
```

```output
== MUTATION: credential errors now leak the raw provider message instead of the mapped text
 frontend/src/app/auth/sign-in/page.tsx | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
== running: npx jest src/__tests__/SignInPage.test.tsx src/__tests__/SignUpPage.test.tsx 
PASS src/__tests__/SignUpPage.test.tsx
FAIL src/__tests__/SignInPage.test.tsx
  ● SignInPage error and 2FA handling (#198) › renders the mapped user-friendly message when credentials are rejected
Tests:       1 failed, 11 passed, 12 total
== RESULT: suite RED — regression caught (jest exit 1)
```

Differential 3 — sign-up success redirect. Main has no sign-up-page test at all (shown above), so ANY sign-up regression ships green there; on the branch, breaking the post-signup redirect target is caught:

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/a93f871d-0c6d-4fe0-ae41-b9d3958aad0b/scratchpad/mutate-and-test.sh /home/frankbria/projects/auto-author signup-redirect
```

```output
== MUTATION: successful sign-up now redirects to / instead of /dashboard
 frontend/src/app/auth/sign-up/page.tsx | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
== running: npx jest src/__tests__/SignInPage.test.tsx src/__tests__/SignUpPage.test.tsx 
PASS src/__tests__/SignInPage.test.tsx
FAIL src/__tests__/SignUpPage.test.tsx
  ● SignUpPage (#198) › signs up with name/email/password and redirects to /dashboard
Tests:       1 failed, 11 passed, 12 total
== RESULT: suite RED — regression caught (jest exit 1)
```

Finally, the unmutated branch: all auth-flow suites green (sign-in incl. the two new pins, the new sign-up suite, the renamed home-page suite, and the pre-existing middleware suite), and sources are pristine after the mutation rounds:

```bash
cd /home/frankbria/projects/auto-author/frontend && git status --porcelain src/app/auth/ && npx jest src/__tests__/SignInPage.test.tsx src/__tests__/SignUpPage.test.tsx src/__tests__/HomePage.test.tsx src/__tests__/middleware.test.ts --silent 2>&1 | grep -E "^(PASS|FAIL)|Tests:"
```

```output
PASS src/__tests__/middleware.test.ts
PASS src/__tests__/HomePage.test.tsx
PASS src/__tests__/SignInPage.test.tsx
PASS src/__tests__/SignUpPage.test.tsx
Tests:       32 passed, 32 total
```

AC map: (1) sign-in success→push(redirect) — pre-existing #184 pins, unchanged; (2) sign-in error→mapped message + no nav — Differential 2; (3) twoFactorRedirect→early return, no push — Differential 1; (4) real sign-up test + rename of the mislabeled file — the grep/ls blocks and Differential 3; (5) middleware protected/cookie/bypass branches — already satisfied by the pre-existing 16-test middleware suite (first exec block), no new work needed. Every mutation block restores the source before exiting, so re-running blocks is idempotent.
