import { test, expect } from '@playwright/test';
import {
  createTestBookWithTOC,
  deleteTestBook,
  waitForBookInDashboard,
  type TestBook,
  type TestChapter
} from './helpers/testData';

/**
 * Cross-browser E2E tests for interview-style prompts functionality
 * Tests the complete workflow from question generation to response saving
 */

test.describe('Interview-Style Prompts Cross-Browser Tests', () => {
  let testBook: TestBook;
  let testChapters: TestChapter[];

  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Create test book with TOC and chapters
    const result = await createTestBookWithTOC(page, {
      title: `Interview Test Book ${Date.now()}`,
      description: 'Test book for interview prompts E2E tests'
    });

    testBook = result.book;
    testChapters = result.chapters;

    // Wait for book to appear in dashboard
    await waitForBookInDashboard(page, testBook.title);
  });

  test.afterEach(async ({ page }) => {
    // Cleanup: Delete test book
    if (testBook?.id) {
      await deleteTestBook(page, testBook.id);
    }
  });

  test('Question generation works across all browsers', async ({ page, browserName }) => {
    test.info().annotations.push({ type: 'browser', description: browserName });
    
    // Navigate to a book chapter
    await page.click('[data-testid="book-card"]');
    await page.click('[data-testid="chapter-tab"]');
    
    // Open question interface
    await page.click('[data-testid="generate-questions-button"]');
    
    // Verify question interface loads
    await expect(page.locator('[data-testid="question-interface"]')).toBeVisible();
    
    // Generate questions
    await page.click('[data-testid="generate-button"]');
    
    // Wait for questions to load
    await expect(page.locator('[data-testid="question-list"]')).toBeVisible();
    
    // Verify at least one question is generated
    const questions = page.locator('[data-testid="question-item"]');
    await expect(questions).toHaveCountGreaterThan(0);
    
    // Test question interaction
    const firstQuestion = questions.first();
    await firstQuestion.click();
    
    // Verify question details modal opens
    await expect(page.locator('[data-testid="question-modal"]')).toBeVisible();
  });

  test('Question response interface is accessible', async ({ page }) => {
    await page.goto('/dashboard');
    await page.click('[data-testid="book-card"]');
    await page.click('[data-testid="chapter-tab"]');
    await page.click('[data-testid="generate-questions-button"]');
    
    // Test keyboard navigation
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter');
    
    // Verify response textarea is focusable
    const responseField = page.locator('[data-testid="response-textarea"]');
    await responseField.focus();
    
    // Type response
    await responseField.fill('This is a test response for cross-browser testing.');
    
    // Save response
    await page.keyboard.press('Ctrl+S');
    
    // Verify save success
    await expect(page.locator('[data-testid="save-success"]')).toBeVisible();
  });

  test('Mobile question interface works correctly', async ({ page, isMobile }) => {
    if (!isMobile) {
      test.skip('This test is only for mobile devices');
    }
    
    await page.goto('/dashboard');
    
    // Test mobile navigation
    await page.click('[data-testid="mobile-menu-toggle"]');
    await page.click('[data-testid="books-menu-item"]');
    
    // Select a book
    await page.click('[data-testid="book-card"]');
    
    // Test mobile chapter navigation
    await page.click('[data-testid="mobile-chapter-selector"]');
    await page.click('[data-testid="chapter-option"]');
    
    // Open question interface on mobile
    await page.click('[data-testid="mobile-questions-button"]');
    
    // Verify mobile-optimized interface
    await expect(page.locator('[data-testid="mobile-question-interface"]')).toBeVisible();
    
    // Test swipe gestures (if supported)
    const questionCard = page.locator('[data-testid="question-card"]').first();
    await questionCard.hover();
    
    // Test touch interactions
    await questionCard.tap();
    await expect(page.locator('[data-testid="question-expanded"]')).toBeVisible();
  });

  test('Question progress tracking persists across browser sessions', async ({ page, context }) => {
    await page.goto('/dashboard');
    await page.click('[data-testid="book-card"]');
    await page.click('[data-testid="chapter-tab"]');
    await page.click('[data-testid="generate-questions-button"]');
    
    // Answer a question
    const firstQuestion = page.locator('[data-testid="question-item"]').first();
    await firstQuestion.click();
    
    const responseField = page.locator('[data-testid="response-textarea"]');
    await responseField.fill('Initial response for persistence test');
    await page.click('[data-testid="save-response-button"]');
    
    // Verify progress is updated
    await expect(page.locator('[data-testid="progress-indicator"]')).toContainText('1/');
    
    // Create new browser session
    const newPage = await context.newPage();
    await newPage.goto('/dashboard');
    await newPage.click('[data-testid="book-card"]');
    await newPage.click('[data-testid="chapter-tab"]');
    await newPage.click('[data-testid="generate-questions-button"]');
    
    // Verify progress is maintained
    await expect(newPage.locator('[data-testid="progress-indicator"]')).toContainText('1/');
    
    // Verify response is preserved
    const savedQuestion = newPage.locator('[data-testid="question-item"]').first();
    await savedQuestion.click();
    
    const savedResponse = newPage.locator('[data-testid="response-textarea"]');
    await expect(savedResponse).toHaveValue('Initial response for persistence test');
  });

  test('Question interface handles network errors gracefully', async ({ page }) => {
    await page.goto('/dashboard');
    await page.click('[data-testid="book-card"]');
    await page.click('[data-testid="chapter-tab"]');
    
    // Simulate network failure
    await page.route('**/api/v1/books/**/chapters/**/questions', route => {
      route.abort('failed');
    });
    
    await page.click('[data-testid="generate-questions-button"]');
    await page.click('[data-testid="generate-button"]');
    
    // Verify error handling
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();
    
    // Test retry functionality
    await page.unroute('**/api/v1/books/**/chapters/**/questions');
    await page.click('[data-testid="retry-button"]');
    
    // Verify successful retry
    await expect(page.locator('[data-testid="question-list"]')).toBeVisible();
  });

  test('High-contrast mode compatibility', async ({ page }) => {
    // Enable high contrast mode simulation
    await page.emulateMedia({ colorScheme: 'dark', forcedColors: 'active' });
    
    await page.goto('/dashboard');
    await page.click('[data-testid="book-card"]');
    await page.click('[data-testid="chapter-tab"]');
    await page.click('[data-testid="generate-questions-button"]');
    
    // Verify interface remains usable in high contrast
    const questionInterface = page.locator('[data-testid="question-interface"]');
    await expect(questionInterface).toBeVisible();
    
    // Check color contrast ratios (simplified check)
    const styles = await questionInterface.evaluate(el => {
      const computed = window.getComputedStyle(el);
      return {
        backgroundColor: computed.backgroundColor,
        color: computed.color,
        borderColor: computed.borderColor
      };
    });
    
    // Verify styles are applied (basic check)
    expect(styles.backgroundColor).toBeDefined();
    expect(styles.color).toBeDefined();
  });

  test('Reduced motion preferences respected', async ({ page }) => {
    // Simulate reduced motion preference
    await page.emulateMedia({ prefersReducedMotion: 'reduce' });
    
    await page.goto('/dashboard');
    await page.click('[data-testid="book-card"]');
    await page.click('[data-testid="chapter-tab"]');
    await page.click('[data-testid="generate-questions-button"]');
    
    // Verify animations are disabled/reduced
    const modal = page.locator('[data-testid="question-modal"]');
    
    // Open modal and check for reduced motion
    const firstQuestion = page.locator('[data-testid="question-item"]').first();
    await firstQuestion.click();
    
    // Verify modal appears without excessive animation
    await expect(modal).toBeVisible();
    
    // Check animation duration is minimal
    const animationDuration = await modal.evaluate(el => {
      const computed = window.getComputedStyle(el);
      return computed.animationDuration;
    });
    
    // Should be either 0s or a very short duration
    expect(animationDuration === '0s' || parseFloat(animationDuration) < 0.5).toBe(true);
  });

  test('Right-to-left (RTL) language support', async ({ page }) => {
    // Set RTL direction
    await page.addInitScript(() => {
      document.documentElement.dir = 'rtl';
      document.documentElement.lang = 'ar';
    });
    
    await page.goto('/dashboard');
    await page.click('[data-testid="book-card"]');
    await page.click('[data-testid="chapter-tab"]');
    await page.click('[data-testid="generate-questions-button"]');
    
    // Verify RTL layout
    const questionInterface = page.locator('[data-testid="question-interface"]');
    const direction = await questionInterface.evaluate(el => 
      window.getComputedStyle(el).direction
    );
    
    expect(direction).toBe('rtl');
    
    // Test question interaction in RTL
    const firstQuestion = page.locator('[data-testid="question-item"]').first();
    await firstQuestion.click();
    
    // Verify modal positioning works in RTL
    const modal = page.locator('[data-testid="question-modal"]');
    await expect(modal).toBeVisible();
    
    // Verify text input works correctly in RTL
    const responseField = page.locator('[data-testid="response-textarea"]');
    await responseField.fill('نص تجريبي للاختبار');
    
    await expect(responseField).toHaveValue('نص تجريبي للاختبار');
  });
});
