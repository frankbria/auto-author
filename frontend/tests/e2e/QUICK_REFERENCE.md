# E2E Testing Quick Reference

## Cleanup Pattern

```typescript
import { registerTestBook, registerTestChapter } from './fixtures/test-data.fixture';

// Track at module level
let createdBookId: string | null = null;
let createdChapterIds: string[] = [];

test.afterAll(async () => {
  if (createdBookId) registerTestBook(createdBookId);
  createdChapterIds.forEach(id => registerTestChapter(id));
});

test('create data', async ({ page }) => {
  // When you create a book:
  createdBookId = bookId;

  // When you create a chapter:
  createdChapterIds.push(chapterId);
});
```

## Condition-Based Waiting

```typescript
import {
  waitForAutoSave,
  waitForSaveComplete,
  waitForCSPValidation,
  waitForCondition
} from '../helpers/condition-waiter';

// Auto-save (replaces 3s timeout)
await waitForAutoSave(page);

// Manual save (replaces 1s timeout)
await waitForSaveComplete(page);

// CSP validation (replaces 1s timeout)
const errors = await waitForCSPValidation(page);

// Custom condition
await waitForCondition(
  async () => await element.isVisible(),
  { timeout: 5000, interval: 100 }
);
```

## Common Patterns

### Wait for Element Text

```typescript
import { waitForTextContent } from '../helpers/condition-waiter';

await waitForTextContent(
  page.locator('.status'),
  'Saved',
  { timeout: 5000 }
);
```

### Wait for API Response

```typescript
import { waitForAPIResponse } from '../helpers/condition-waiter';

await waitForAPIResponse(
  page,
  '/api/v1/books',
  200,
  { timeout: 10000 }
);
```

### Wait for Element Stability

```typescript
import { waitForElementStable } from '../helpers/condition-waiter';

await waitForElementStable(
  page.locator('.modal'),
  { timeout: 5000 }
);
```

## Anti-Patterns (Avoid)

```typescript
// ❌ DON'T use arbitrary timeouts
await page.waitForTimeout(3000);

// ✅ DO use condition-based waiting
await waitForAutoSave(page);

// ❌ DON'T create data without tracking
const bookId = await createBook();
// (not tracked for cleanup)

// ✅ DO track all created data
const bookId = await createBook();
createdBookId = bookId; // Track it!

// ❌ DON'T share state between files
export let globalBookId; // Bad!

// ✅ DO use module-level variables within a file
let createdBookId: string | null = null; // Good!
```

## File Structure

```
tests/e2e/
├── fixtures/
│   ├── auth.fixture.ts           # Auth helpers
│   ├── test-data.fixture.ts      # Test data + cleanup
│   ├── performance.fixture.ts    # Performance budgets
│   ├── cleanup-template.ts       # Example patterns
│   └── README.md                 # Full documentation
├── helpers/
│   ├── condition-waiter.ts       # Condition-based waiting
│   ├── console-monitor.ts        # Console monitoring
│   ├── csp-validator.ts          # CSP validation
│   └── network-monitor.ts        # Network monitoring
├── page-objects/
│   ├── auth.page.ts              # Auth page object
│   ├── dashboard.page.ts         # Dashboard page object
│   ├── book-form.page.ts         # Book form page object
│   ├── chapter-editor.page.ts    # Chapter editor page object
│   └── ...
└── global-teardown.ts            # Global cleanup
```

## Environment Variables

```bash
# API base URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# Auth bypass for testing
NEXT_PUBLIC_BYPASS_AUTH=true

# Test credentials (if not using bypass)
TEST_USER_EMAIL=test@example.com
TEST_USER_PASSWORD=password123

# Auth token for cleanup (optional)
TEST_AUTH_TOKEN=your-token-here
```

## Running Tests

```bash
# All tests
npx playwright test

# Specific test file
npx playwright test tests/e2e/book-creation.spec.ts

# With UI mode (recommended)
npx playwright test --ui

# With auth bypass
NEXT_PUBLIC_BYPASS_AUTH=true npx playwright test

# Watch mode
npx playwright test --watch
```

## Debugging

```bash
# Debug mode (step through tests)
npx playwright test --debug

# Show browser (headed mode)
npx playwright test --headed

# Verbose output
npx playwright test --reporter=line

# Generate HTML report
npx playwright test --reporter=html
```

## Need More Info?

- **Full documentation**: `tests/e2e/fixtures/README.md`
- **Examples**: `tests/e2e/fixtures/cleanup-template.ts`
- **Summary**: `tests/e2e/CLEANUP_IMPLEMENTATION_SUMMARY.md`
