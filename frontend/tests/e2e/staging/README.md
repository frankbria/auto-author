# Staging E2E Tests

Comprehensive end-to-end tests that run against the staging environment (`https://dev.autoauthor.app`) with real Better-auth authentication.

## Purpose

These tests prevent regressions by validating the complete user journey:
- ✅ Authentication flow
- ✅ Book creation
- ✅ Summary management
- ✅ TOC generation
- ✅ Chapter Q&A workflow
- ✅ Draft generation

**Recent bugs these tests would have caught:**
- Session cookie signing issue (signed cookies not parsed correctly)
- ObjectId/string conversion bug (book creation validation error)
- User lookup regression (dashboard 401 after ObjectId fix)
- Question answer persistence (Issue #54)

## Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
npx playwright install chromium
```

### 2. Configure Test Credentials

Copy the environment template:

```bash
cp tests/e2e/staging/.env.test.example tests/e2e/staging/.env.test
```

Edit `.env.test` and add your test credentials:

```env
STAGING_TEST_EMAIL=your-test-email@example.com
STAGING_TEST_PASSWORD=your-test-password
```

**Important**: `.env.test` is gitignored to keep credentials safe.

### 3. Create Test User (if needed)

Visit https://dev.autoauthor.app and create a test user account, then use those credentials in `.env.test`.

## Running Tests

### Run all staging tests

```bash
npm run test:e2e:staging
```

### Run with UI mode (interactive)

```bash
npm run test:e2e:staging:ui
```

### Run in headed mode (see browser)

```bash
npm run test:e2e:staging:headed
```

### Debug mode (step through tests)

```bash
npm run test:e2e:staging:debug
```

## Test Structure

```
tests/e2e/staging/
├── playwright.config.ts          # Staging-specific Playwright config
├── .env.test.example              # Template for test credentials
├── .env.test                      # Your test credentials (gitignored)
├── README.md                      # This file
├── fixtures/
│   └── auth.fixture.ts            # Better-auth login fixtures
├── helpers/
│   └── (future helper functions)
├── page-objects/
│   └── (future page object models)
└── complete-user-journey.spec.ts  # Main E2E test covering full workflow
```

## Writing New Tests

### Use the auth fixture

```typescript
import { test, expect } from './fixtures/auth.fixture';

test('my test', async ({ authenticatedPage }) => {
  // authenticatedPage is already logged in
  await authenticatedPage.goto('/dashboard');
  // ... rest of test
});
```

The fixture signs in **once per worker** and shares the saved storage state with
every test in that worker — it does not sign in per test. That is deliberate
(#551): better-auth rate-limits any `/sign-in*` path at **3 requests per 10s per
IP**, and the window only resets after 10s of silence. One sign-in per test meant
11 sign-ins from a single CI IP at 2–6s spacing, which reliably tripped the limit
partway through the run. If you add a spec that needs a *fresh* sign-in, do it
inside the test rather than by widening the fixture, and keep the pacing in mind.

Two consequences worth knowing before you write a spec:

- **Never sign out.** The session is shared by every test in the worker, so a spec that
  signs out revokes it server-side and every later test in that worker 401s with no
  obvious cause. Clearing cookies is fine — that only touches the calling test's own
  context, which is why `edge-cases.spec.ts`'s session-expiration test still works.
- **Workers are clamped to 1–2.** Each worker signs in once at startup, so a 4th worker
  would 429 its own bootstrap. The ceiling is 2 rather than 3 to leave one slot spare:
  if Playwright replaces a crashed worker mid-run, that replacement's sign-in lands
  inside the same 10s window. `STAGING_E2E_WORKERS` is clamped in the config.

### Test organization

- `complete-user-journey.spec.ts` - Full workflow from start to finish
- `regressions.spec.ts` (future) - Tests for specific bugs
- `edge-cases.spec.ts` (future) - Boundary conditions and error cases

## CI/CD Integration

These tests run automatically on:
- Every push to `main`
- Every pull request
- Scheduled runs every 6 hours

See `.github/workflows/e2e-staging-tests.yml` for CI configuration.

### GitHub Secrets Required

Add these secrets to GitHub repository settings:
- `STAGING_TEST_EMAIL` - Test user email
- `STAGING_TEST_PASSWORD` - Test user password

## Debugging Failed Tests

### View test report

After tests run:

```bash
npx playwright show-report playwright-report-staging
```

### Screenshots and videos

Failed tests automatically capture:
- Screenshots (in `test-results/`)
- Videos (in `test-results/`)

**Traces are off, and the HTML report is not uploaded. Do not turn either back on
without reading this.** (#599)

This repository is **public**, and `e2e-staging-tests.yml` uploads `test-results/`
as a CI artifact that any GitHub user can download. Two Playwright features put
live credentials in there:

| what | why it leaks |
|---|---|
| `trace.zip` | records request **headers**, so every authenticated call carries `Cookie: __Secure-better-auth.session_token=...`; also records action arguments, so the password passed to `fill()` is stored verbatim |
| `error-context.md` | its page snapshot renders each input's **value**, so the password appears in plaintext |
| the HTML report | inlines every failure attachment, reproducing `error-context.md` |

So: `trace: 'off'` in the config, `error-context.md` and `trace.zip` excluded from
both upload steps, and the report step removed. The exclusions are deliberately
redundant with the config setting — flipping one back on must not be enough to
re-open the leak. A jest guard in `src/__tests__/StagingE2eFlakyGate.test.ts`
fails if `trace` stops being `'off'`.

Screenshots and video are kept: a `type="password"` input renders masked, so
neither carries the credential.

**To debug a staging failure**, re-run it with a manual `workflow_dispatch`, or
run the suite locally with `npm run test:e2e:staging` where traces stay available
and nothing is published. The thrown sign-in error also now carries the sign-in
page's own alert text, which covers the common cases without a trace.

### Common issues

**"Session cookie not found"**
- Verify credentials in `.env.test`
- Check that staging auth is working (try manual login)
- Ensure Better-auth cookies are being set

**"Test timeout"**
- Check staging server is running
- Verify network connectivity to https://dev.autoauthor.app
- Increase timeout in test if operation is legitimately slow

**"Element not found"**
- UI may have changed - update selectors in test
- Page may be loading slowly - add appropriate waits
- Check for console errors in browser DevTools

## Performance Budgets

Tests validate these performance requirements:
- TOC Generation: < 3000ms
- Question Generation: < 2000ms
- Draft Generation: < 5000ms
- Page Navigation: < 500ms
- Auto-save: < 1000ms

## Maintenance

### When UI changes

Update selectors in tests to match new UI structure. Use data-testid attributes when possible:

```tsx
// In component
<button data-testid="create-book">Create Book</button>

// In test
await page.click('[data-testid="create-book"]');
```

### Adding regression tests

When a bug is fixed:
1. Add a test case that reproduces the bug
2. Verify the test fails with the bug present
3. Verify the test passes with the fix
4. Document the issue number in the test

Example:

```typescript
test('Issue #54: Question answers persist after page refresh', async ({ authenticatedPage }) => {
  // Test that would have caught the bug
});
```

## Troubleshooting

### Local vs CI differences

- CI runs headless, local can run headed for debugging
- CI uses Ubuntu, local may be macOS/Windows
- CI has different network environment

### Flaky tests

**The job fails on flaky.** `failOnFlakyTests` is on under CI, so a test that
fails its first attempt and passes on retry turns the run red instead of
reporting `1 flaky` and exiting `success`. Retries (`retries: 2`) stay on so the
retry still produces a trace — they buy diagnostics, not a green tick.

This was decided in #551. The `regressions.spec.ts` #83 session canary is the
spec most likely to catch an auth-path break; while `flaky` counted as success, a
real regression that broke first-attempt sign-in looked exactly like the status
quo and still reported green.

If a test fails intermittently:
1. Add explicit waits for elements/conditions
2. Increase timeouts if operations are slow
3. Use `waitForCondition` instead of arbitrary timeouts
4. Check for race conditions in test
5. Check whether you are tripping the better-auth sign-in rate limit (3 per 10s
   per IP) — the symptom is a 30s navigation timeout with "Too many attempts.
   Please try again later" on the sign-in page

## Resources

- [Playwright Documentation](https://playwright.dev)
- [Better-auth Documentation](https://better-auth.com)
- [GitHub Issue #83](https://github.com/frankbria/auto-author/issues/83) - E2E Test Suite Implementation

## Support

Questions or issues? See:
- GitHub Issue #83 for implementation plan
- CLAUDE.md for project-specific guidance
- Playwright Discord for framework help
