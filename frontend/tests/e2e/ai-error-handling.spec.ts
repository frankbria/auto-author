/**
 * E2E tests for AI service error handling
 *
 * Tests comprehensive error handling for AI service operations including:
 * - Rate limit errors with countdown
 * - Network errors with retry
 * - Cached content fallback
 * - Service unavailable errors
 */

import { test, expect } from '@playwright/test';
import { Page } from '@playwright/test';

// Test utilities
async function mockAIRateLimitError(page: Page, endpoint: string, retryAfter: number = 60) {
  await page.route(`**/api/v1/**/${endpoint}`, route => {
    route.fulfill({
      status: 429,
      contentType: 'application/json',
      body: JSON.stringify({
        message: 'AI service rate limit exceeded',
        status_code: 429,
        error_type: 'rate_limit',
        estimated_retry_after: retryAfter,
      }),
    });
  });
}

async function mockAICachedContentError(page: Page, endpoint: string, cachedData: unknown) {
  await page.route(`**/api/v1/**/${endpoint}`, route => {
    route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({
        message: 'AI service temporarily unavailable',
        status_code: 503,
        error_type: 'service_unavailable',
        cached_content_available: true,
        cached_content: cachedData,
      }),
    });
  });
}

async function mockAINetworkError(page: Page, endpoint: string) {
  await page.route(`**/api/v1/**/${endpoint}`, route => {
    route.abort('failed');
  });
}

async function mockAISuccess(page: Page, endpoint: string, data: unknown) {
  await page.route(`**/api/v1/**/${endpoint}`, route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(data),
    });
  });
}

test.describe('AI Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    // Set up basic auth bypass
    await page.route('**/api/v1/**', route => {
      const request = route.request();
      if (!request.url().includes('generate') && !request.url().includes('analyze')) {
        route.continue();
      }
    });
  });

  test('should show rate limit error with countdown timer', async ({ page }) => {
    // Mock rate limit error
    await mockAIRateLimitError(page, 'generate-questions', 120); // 2 minutes

    // Navigate to a page that uses AI (e.g., TOC wizard)
    await page.goto('/dashboard/books/test-book-id/toc');

    // Wait for the page to attempt AI generation
    await page.waitForSelector('[data-testid="generate-questions-button"]', { timeout: 5000 });
    await page.click('[data-testid="generate-questions-button"]');

    // Verify rate limit error notification appears
    const errorNotification = page.locator('[role="alert"]').filter({ hasText: 'rate limit' });
    await expect(errorNotification).toBeVisible({ timeout: 3000 });

    // Verify countdown timer is shown
    const countdown = page.locator('text=/Retry in \\d+:\\d+/');
    await expect(countdown).toBeVisible({ timeout: 2000 });

    // Verify initial countdown shows approximately 2 minutes
    const countdownText = await countdown.textContent();
    expect(countdownText).toMatch(/Retry in [12]:\d{2}/);

    // Wait 2 seconds and verify countdown decreased
    await page.waitForTimeout(2000);
    const newCountdownText = await countdown.textContent();
    expect(newCountdownText).toMatch(/Retry in [01]:[45]\d/);
  });

  test('should display cached content when AI service is unavailable', async ({ page }) => {
    const cachedQuestions = {
      questions: [
        'What is the target audience for your book?',
        'What are the main topics you want to cover?',
        'What tone do you want to use?',
      ],
    };

    // Mock service unavailable with cached content
    await mockAICachedContentError(page, 'generate-questions', cachedQuestions);

    await page.goto('/dashboard/books/test-book-id/toc');
    await page.waitForSelector('[data-testid="generate-questions-button"]');
    await page.click('[data-testid="generate-questions-button"]');

    // Verify cached content badge appears
    const cachedBadge = page.locator('text=/cached content/i');
    await expect(cachedBadge).toBeVisible({ timeout: 3000 });

    // Verify warning notification about cached content
    const warningNotification = page.locator('[role="alert"]').filter({ hasText: /cached|previously generated/i });
    await expect(warningNotification).toBeVisible();

    // Verify cached questions are displayed
    for (const question of cachedQuestions.questions) {
      await expect(page.locator(`text=${question}`)).toBeVisible();
    }

    // Verify "Generate Fresh" button is available
    const generateFreshButton = page.locator('button:has-text("Generate Fresh")');
    await expect(generateFreshButton).toBeVisible();
  });

  test('should show network error with retry button', async ({ page }) => {
    // Mock network error
    await mockAINetworkError(page, 'generate-questions');

    await page.goto('/dashboard/books/test-book-id/toc');
    await page.waitForSelector('[data-testid="generate-questions-button"]');
    await page.click('[data-testid="generate-questions-button"]');

    // Verify network error notification
    const errorNotification = page.locator('[role="alert"]').filter({ hasText: /network|connection/i });
    await expect(errorNotification).toBeVisible({ timeout: 3000 });

    // Verify retry button is shown
    const retryButton = page.locator('button:has-text("Retry")');
    await expect(retryButton).toBeVisible();

    // Verify suggested actions
    await expect(page.locator('text=/check.*internet.*connection/i')).toBeVisible();
  });

  test('should successfully retry after network error is resolved', async ({ page }) => {
    const successData = {
      questions: ['Question 1', 'Question 2', 'Question 3'],
    };

    // Initially mock network error
    await mockAINetworkError(page, 'generate-questions');

    await page.goto('/dashboard/books/test-book-id/toc');
    await page.waitForSelector('[data-testid="generate-questions-button"]');
    await page.click('[data-testid="generate-questions-button"]');

    // Wait for error notification
    await page.waitForSelector('[role="alert"]', { timeout: 3000 });

    // Now mock successful response
    await mockAISuccess(page, 'generate-questions', successData);

    // Click retry button
    const retryButton = page.locator('button:has-text("Retry")');
    await retryButton.click();

    // Verify success - questions are displayed
    for (const question of successData.questions) {
      await expect(page.locator(`text=${question}`)).toBeVisible({ timeout: 5000 });
    }

    // Verify error notification is dismissed
    const errorNotification = page.locator('[role="alert"]').filter({ hasText: /error/i });
    await expect(errorNotification).not.toBeVisible({ timeout: 2000 });
  });

  test('should handle rate limit retry correctly', async ({ page }) => {
    const successData = {
      questions: ['Question 1', 'Question 2'],
    };

    // Mock rate limit with short retry time for testing
    await mockAIRateLimitError(page, 'generate-questions', 5); // 5 seconds

    await page.goto('/dashboard/books/test-book-id/toc');
    await page.waitForSelector('[data-testid="generate-questions-button"]');
    await page.click('[data-testid="generate-questions-button"]');

    // Wait for countdown to appear
    await page.waitForSelector('text=/Retry in/');

    // Wait for countdown to reach 0 (5 seconds + buffer)
    await page.waitForTimeout(6000);

    // Mock successful response
    await mockAISuccess(page, 'generate-questions', successData);

    // Verify "Retry Now" button appears when countdown reaches 0
    const retryNowButton = page.locator('button:has-text("Retry Now")');
    await expect(retryNowButton).toBeVisible({ timeout: 2000 });

    // Click retry
    await retryNowButton.click();

    // Verify success
    for (const question of successData.questions) {
      await expect(page.locator(`text=${question}`)).toBeVisible({ timeout: 5000 });
    }
  });

  test('should handle TOC generation with cached content', async ({ page }) => {
    const cachedTOC = {
      toc: {
        chapters: [
          {
            id: '1',
            title: 'Introduction',
            description: 'An introduction to the topic',
            level: 1,
            order: 1,
            subchapters: [],
          },
          {
            id: '2',
            title: 'Main Content',
            description: 'The main content of the book',
            level: 1,
            order: 2,
            subchapters: [],
          },
        ],
        total_chapters: 2,
        estimated_pages: 50,
        structure_notes: 'Cached structure',
      },
      success: true,
      chapters_count: 2,
      has_subchapters: false,
    };

    // Mock cached content for TOC generation
    await mockAICachedContentError(page, 'generate-toc', cachedTOC);

    await page.goto('/dashboard/books/test-book-id/toc');

    // Assume user has answered questions and clicked generate TOC
    await page.waitForSelector('[data-testid="generate-toc-button"]');
    await page.click('[data-testid="generate-toc-button"]');

    // Verify cached content warning
    await expect(page.locator('text=/cached content/i')).toBeVisible({ timeout: 3000 });

    // Verify TOC chapters are displayed
    await expect(page.locator('text=Introduction')).toBeVisible();
    await expect(page.locator('text=Main Content')).toBeVisible();

    // Verify "Generate Fresh" option is available
    const generateFreshButton = page.locator('button:has-text("Generate Fresh")');
    await expect(generateFreshButton).toBeVisible();
  });

  test('should handle chapter draft generation errors', async ({ page }) => {
    // Mock rate limit for draft generation
    await mockAIRateLimitError(page, 'generate-draft', 180); // 3 minutes

    await page.goto('/dashboard/books/test-book-id/chapters/chapter-1');

    // Click generate draft button
    await page.waitForSelector('[data-testid="generate-draft-button"]');
    await page.click('[data-testid="generate-draft-button"]');

    // Verify rate limit error with countdown
    const errorNotification = page.locator('[role="alert"]').filter({ hasText: /rate limit/i });
    await expect(errorNotification).toBeVisible({ timeout: 3000 });

    // Verify countdown shows approximately 3 minutes
    const countdown = page.locator('text=/Retry in [23]:\\d{2}/');
    await expect(countdown).toBeVisible({ timeout: 2000 });
  });

  test('should persist error state across page navigation', async ({ page }) => {
    // Mock network error
    await mockAINetworkError(page, 'generate-questions');

    await page.goto('/dashboard/books/test-book-id/toc');
    await page.waitForSelector('[data-testid="generate-questions-button"]');
    await page.click('[data-testid="generate-questions-button"]');

    // Wait for error
    await page.waitForSelector('[role="alert"]', { timeout: 3000 });

    // Navigate away and back
    await page.goto('/dashboard');
    await page.goto('/dashboard/books/test-book-id/toc');

    // Verify we can retry the operation
    await page.waitForSelector('[data-testid="generate-questions-button"]');
    await page.click('[data-testid="generate-questions-button"]');

    // Should show error again (not cached state)
    await expect(page.locator('[role="alert"]')).toBeVisible({ timeout: 3000 });
  });

  test('should show appropriate error messages for different error types', async ({ page }) => {
    // Test validation error
    await page.route('**/api/v1/**/generate-questions', route => {
      route.fulfill({
        status: 422,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Validation error',
          status_code: 422,
          error_type: 'validation',
        }),
      });
    });

    await page.goto('/dashboard/books/test-book-id/toc');
    await page.waitForSelector('[data-testid="generate-questions-button"]');
    await page.click('[data-testid="generate-questions-button"]');

    // Verify validation error message
    await expect(page.locator('text=/invalid.*request/i')).toBeVisible({ timeout: 3000 });
    await expect(page.locator('text=/check.*input/i')).toBeVisible();
  });

  test('should handle multiple concurrent AI errors gracefully', async ({ page }) => {
    // Mock errors for multiple endpoints
    await mockAIRateLimitError(page, 'generate-questions', 60);
    await mockAINetworkError(page, 'analyze-summary');

    await page.goto('/dashboard/books/test-book-id/toc');

    // Trigger multiple AI operations
    await page.waitForSelector('[data-testid="analyze-button"]');
    await page.click('[data-testid="analyze-button"]');

    await page.waitForSelector('[data-testid="generate-questions-button"]');
    await page.click('[data-testid="generate-questions-button"]');

    // Verify both errors are shown (multiple notifications)
    const errorNotifications = page.locator('[role="alert"]');
    await expect(errorNotifications).toHaveCount(2, { timeout: 5000 });

    // Verify different error types are shown
    await expect(page.locator('text=/rate limit/i')).toBeVisible();
    await expect(page.locator('text=/network/i')).toBeVisible();
  });
});
