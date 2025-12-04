/**
 * Test Cleanup Template
 *
 * Use this template for test suites that create data.
 * Copy the cleanup patterns into your test files.
 */

import { test, expect } from '@playwright/test';
import { registerTestBook, registerTestChapter } from './test-data.fixture';

/**
 * TEMPLATE: Test Suite with Cleanup
 *
 * Use this pattern in your test files to ensure proper cleanup.
 */

// Track test data at module level
let createdBookId: string | null = null;
let createdChapterIds: string[] = [];

test.describe('Example Test Suite with Cleanup', () => {
  /**
   * afterEach hook - Clean up after each test
   *
   * Use this for test-specific cleanup that should happen after EVERY test.
   */
  test.afterEach(async () => {
    // Example: Clear test state between tests
    // This ensures tests don't share state
    console.log('🧹 Test-specific cleanup complete');
  });

  /**
   * afterAll hook - Clean up after all tests complete
   *
   * Use this for suite-level cleanup that should happen ONCE after all tests.
   */
  test.afterAll(async () => {
    // Register created books/chapters for global cleanup
    if (createdBookId) {
      registerTestBook(createdBookId);
    }

    createdChapterIds.forEach(id => registerTestChapter(id));

    console.log('🧹 Suite-level cleanup complete');
  });

  test('Example test that creates data', async ({ page }) => {
    // Your test code here...

    // When you create a book, track it:
    const bookId = 'test-book-id-123';
    createdBookId = bookId;

    // When you create chapters, track them:
    const chapterId = 'test-chapter-id-456';
    createdChapterIds.push(chapterId);

    // Your assertions...
    expect(true).toBe(true);
  });

  test('Example test that does NOT create data', async ({ page }) => {
    // Tests that only read data don't need to register anything

    // Your test code here...
    expect(true).toBe(true);
  });
});

/**
 * USAGE NOTES:
 *
 * 1. Module-level variables (createdBookId, createdChapterIds):
 *    - Declared at the top of the file
 *    - Track data created during test execution
 *    - Shared across tests in the same file
 *
 * 2. afterEach hook:
 *    - Runs after EACH test in the suite
 *    - Use for test-specific cleanup
 *    - Ensures test isolation
 *
 * 3. afterAll hook:
 *    - Runs ONCE after ALL tests complete
 *    - Use for suite-level cleanup
 *    - Register data for global cleanup
 *
 * 4. Global teardown:
 *    - Configured in playwright.config.ts
 *    - Runs after ALL test files complete
 *    - Cleans up all registered test data
 *
 * 5. Best practices:
 *    - Always track created data in module-level variables
 *    - Register for cleanup in afterAll hook
 *    - Use descriptive test data (e.g., "Test Book - " + timestamp)
 *    - Handle cleanup errors gracefully (don't fail tests)
 */

/**
 * EXAMPLE: Real-world test with cleanup
 */
test.describe('Book Creation with Cleanup', () => {
  let testBookId: string | null = null;

  test.afterAll(async () => {
    if (testBookId) {
      registerTestBook(testBookId);
      console.log(`📝 Registered book ${testBookId} for cleanup`);
    }
  });

  test('should create a book successfully', async ({ page }) => {
    // Navigate to new book form
    await page.goto('/dashboard/new-book');

    // Fill form and submit
    await page.fill('[name="title"]', `Test Book - ${Date.now()}`);
    await page.fill('[name="description"]', 'Test description');
    await page.click('button[type="submit"]');

    // Wait for redirect and extract book ID
    await page.waitForURL(/\/dashboard\/books\/[a-z0-9-]+$/);
    testBookId = page.url().split('/').pop() || null;

    // Verify book was created
    expect(testBookId).toBeTruthy();
    console.log(`✅ Created test book: ${testBookId}`);
  });
});

/**
 * ANTI-PATTERNS TO AVOID:
 *
 * ❌ DON'T share state between test files via global variables
 * ❌ DON'T use beforeAll to create data without afterAll cleanup
 * ❌ DON'T rely on test execution order for data dependencies
 * ❌ DON'T create data without tracking it for cleanup
 * ❌ DON'T use arbitrary timeouts instead of condition-based waiting
 *
 * ✅ DO use module-level variables within a single test file
 * ✅ DO register all created data for cleanup
 * ✅ DO use afterAll hooks for cleanup
 * ✅ DO make tests independent and isolated
 * ✅ DO use condition-based waiting from helpers/condition-waiter.ts
 */
