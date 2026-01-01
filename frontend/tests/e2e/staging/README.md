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
- Traces (in `test-results/`)

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

If a test fails intermittently:
1. Add explicit waits for elements/conditions
2. Increase timeouts if operations are slow
3. Use `waitForCondition` instead of arbitrary timeouts
4. Check for race conditions in test

## Resources

- [Playwright Documentation](https://playwright.dev)
- [Better-auth Documentation](https://better-auth.com)
- [GitHub Issue #83](https://github.com/frankbria/auto-author/issues/83) - E2E Test Suite Implementation

## Support

Questions or issues? See:
- GitHub Issue #83 for implementation plan
- CLAUDE.md for project-specific guidance
- Playwright Discord for framework help
