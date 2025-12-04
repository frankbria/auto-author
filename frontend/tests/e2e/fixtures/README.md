# E2E Test Fixtures and Cleanup System

## Overview

This directory contains test fixtures and utilities for E2E testing with comprehensive cleanup support.

## Files

### Core Fixtures

- **auth.fixture.ts** - Authentication helpers with Clerk bypass support
- **test-data.fixture.ts** - Static test data and cleanup utilities
- **performance.fixture.ts** - Performance budgets and measurement utilities

### Utilities

- **cleanup-template.ts** - Template showing how to implement cleanup in test files
- **README.md** - This file

## Cleanup System

### Architecture

The cleanup system uses a three-tier approach:

1. **Module-level tracking** - Tests track created data in module-level variables
2. **afterAll hooks** - Test suites register data for cleanup after all tests complete
3. **Global teardown** - Global teardown function cleans up all registered data

### Usage

#### 1. Track Created Data

```typescript
// At the top of your test file
let createdBookId: string | null = null;
let createdChapterIds: string[] = [];

test('create book', async ({ page }) => {
  // Create book...
  createdBookId = extractedBookId;

  // Create chapter...
  createdChapterIds.push(extractedChapterId);
});
```

#### 2. Register for Cleanup

```typescript
import { registerTestBook, registerTestChapter } from './fixtures/test-data.fixture';

test.afterAll(async () => {
  if (createdBookId) {
    registerTestBook(createdBookId);
  }

  createdChapterIds.forEach(id => registerTestChapter(id));
});
```

#### 3. Global Teardown (Already Configured)

The global teardown in `global-teardown.ts` automatically:
- Collects all registered book/chapter IDs
- Deletes them via API
- Clears the registry

### API

#### Registration Functions

```typescript
// Register a book for cleanup
registerTestBook(bookId: string): void

// Register a chapter for cleanup
registerTestChapter(chapterId: string): void
```

#### Cleanup Functions

```typescript
// Clean up all registered test books
cleanupTestBooks(baseUrl: string, authToken?: string): Promise<void>

// Clean up all registered test chapters
cleanupTestChapters(baseUrl: string, authToken?: string): Promise<void>

// Clear the registry (automatically called by cleanup functions)
clearTestDataRegistry(): void
```

#### Registry Access

```typescript
// Get all registered book IDs
getTestBookIds(): string[]

// Get all registered chapter IDs
getTestChapterIds(): string[]
```

## Condition-Based Waiting

### Overview

Replace arbitrary timeouts with smart condition-based waiting using `helpers/condition-waiter.ts`.

### Available Utilities

```typescript
// Wait for a custom condition
waitForCondition(
  condition: () => boolean | Promise<boolean>,
  options?: { timeout?: number; interval?: number }
): Promise<boolean>

// Wait for text content to match
waitForTextContent(
  locator: Locator,
  expectedText: string | RegExp,
  options?: WaitOptions
): Promise<void>

// Wait for auto-save to complete (replaces 3s timeout)
waitForAutoSave(
  page: Page,
  options?: WaitOptions
): Promise<void>

// Wait for save operation to complete (replaces 1s timeout)
waitForSaveComplete(
  page: Page,
  options?: WaitOptions
): Promise<void>

// Wait for CSP validation (replaces 1s timeout for console errors)
waitForCSPValidation(
  page: Page,
  options?: WaitOptions
): Promise<string[]>

// Wait for element to be stable (no layout shifts)
waitForElementStable(
  locator: Locator,
  options?: WaitOptions
): Promise<void>

// Wait for API response with criteria
waitForAPIResponse(
  page: Page,
  urlPattern: string | RegExp,
  expectedStatus?: number,
  options?: WaitOptions
): Promise<void>

// Wait for multiple conditions in parallel
waitForAll(
  conditions: Array<() => Promise<void>>,
  options?: WaitOptions
): Promise<void>
```

### Usage Examples

#### Before (Arbitrary Timeout)

```typescript
await page.click('button:has-text("Save")');
await page.waitForTimeout(1000); // ❌ Arbitrary timeout
```

#### After (Condition-Based)

```typescript
import { waitForSaveComplete } from '../helpers/condition-waiter';

await page.click('button:has-text("Save")');
await waitForSaveComplete(page, { timeout: 5000 }); // ✅ Condition-based
```

#### Auto-Save Example

```typescript
import { waitForAutoSave } from '../helpers/condition-waiter';

// Type content
await editor.fill('Test content');

// Wait for auto-save (3s debounce + save)
await waitForAutoSave(page, { timeout: 10000 });
```

#### CSP Validation Example

```typescript
import { waitForCSPValidation } from '../helpers/condition-waiter';

await page.goto('/dashboard');

const cspErrors = await waitForCSPValidation(page, { timeout: 2000 });

expect(cspErrors).toHaveLength(0);
```

## Test Data

### Static Test Data

All static test data is defined in `test-data.fixture.ts`:

- `TEST_BOOK` - Sample book metadata
- `TEST_SUMMARY` - Sample book summary (558 characters)
- `TOC_QUESTIONS` - Sample TOC wizard Q&A
- `CHAPTER_QA_DATA` - Sample chapter Q&A for AI draft
- `FIELD_CONSTRAINTS` - Validation constraints

### Best Practices

1. **Use unique identifiers** - Add timestamps to test data
   ```typescript
   title: `Test Book - ${Date.now()}`
   ```

2. **Track all created data** - Don't create orphan data
   ```typescript
   createdBookId = bookId; // Always track
   ```

3. **Register in afterAll** - Ensure cleanup happens
   ```typescript
   test.afterAll(async () => {
     if (createdBookId) registerTestBook(createdBookId);
   });
   ```

4. **Use condition-based waiting** - No arbitrary timeouts
   ```typescript
   import { waitForAutoSave } from '../helpers/condition-waiter';
   await waitForAutoSave(page); // ✅
   // NOT: await page.waitForTimeout(3000); // ❌
   ```

5. **Handle cleanup errors gracefully** - Don't fail tests
   ```typescript
   test.afterAll(async () => {
     try {
       if (createdBookId) registerTestBook(createdBookId);
     } catch (error) {
       console.warn('Cleanup registration failed:', error);
       // Don't throw - cleanup errors shouldn't fail tests
     }
   });
   ```

## Environment Variables

- `NEXT_PUBLIC_API_URL` - API base URL (default: `http://localhost:8000`)
- `TEST_AUTH_TOKEN` - Authentication token for cleanup (optional in BYPASS_AUTH mode)
- `NEXT_PUBLIC_BYPASS_AUTH` - Enable auth bypass for testing (default: `false`)

## Integration with Playwright Config

Global teardown is configured in `playwright.config.ts`:

```typescript
export default defineConfig({
  globalTeardown: './tests/e2e/global-teardown.ts',
  // ... other config
});
```

## Troubleshooting

### Cleanup Not Running

**Issue**: Test data not being cleaned up

**Solutions**:
1. Verify `globalTeardown` is configured in `playwright.config.ts`
2. Check that data is registered in `afterAll` hook
3. Ensure module-level variables are populated
4. Check console for cleanup logs

### Arbitrary Timeout Issues

**Issue**: Tests failing due to arbitrary timeouts

**Solutions**:
1. Replace `waitForTimeout` with condition-based helpers
2. Use `waitForAutoSave` for auto-save operations
3. Use `waitForSaveComplete` for save operations
4. Use `waitForCSPValidation` for CSP checks

### Test State Pollution

**Issue**: Tests failing when run together but passing individually

**Solutions**:
1. Ensure `afterEach` clears test-specific state
2. Don't share state between test files
3. Use unique identifiers for test data
4. Register all created data for cleanup

## See Also

- `cleanup-template.ts` - Complete examples and patterns
- `../helpers/condition-waiter.ts` - Condition-based waiting utilities
- `../global-teardown.ts` - Global cleanup implementation
