import { test, expect } from '@playwright/test';

/**
 * E2E tests for ChapterQuestions tab navigation
 *
 * Tests the Radix UI tabs implementation including:
 * - Tab click switching
 * - Keyboard navigation (Ctrl+1, Ctrl+2, Ctrl+Tab)
 * - Session storage persistence
 * - Accessibility compliance
 */

/**
 * These E2E tests are skipped by default as they require:
 * 1. A running backend with MongoDB connection
 * 2. Authentication setup
 * 3. Test data (books with chapters)
 *
 * To run these tests, ensure the backend is running and remove the .skip
 */
test.describe.skip('ChapterQuestions Tabs Navigation', () => {
  // Use a mock page that renders ChapterQuestions for testing
  // In a real implementation, navigate to an actual chapter page

  test.beforeEach(async ({ page }) => {
    // Navigate to a chapter questions page
    // This assumes the app has a route that displays ChapterQuestions
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
  });

  test.describe('Tab Click Navigation', () => {
    test('user can click tabs to switch between questions and editor', async ({ page }) => {
      // Navigate to a book with chapters
      await page.click('[data-testid="book-card"]');
      await page.waitForLoadState('networkidle');

      // Click on a chapter to open ChapterQuestions
      await page.click('[data-testid="chapter-tab"]');

      // Verify Interview Questions tab is visible and active
      const questionsTab = page.getByRole('tab', { name: /Interview Questions/i });
      await expect(questionsTab).toBeVisible();
      await expect(questionsTab).toHaveAttribute('aria-selected', 'true');

      // Click on Chapter Editor tab
      const editorTab = page.getByRole('tab', { name: /Chapter Editor/i });
      if (await editorTab.isVisible()) {
        await editorTab.click();

        // Verify editor tab is now active
        await expect(editorTab).toHaveAttribute('aria-selected', 'true');
        await expect(questionsTab).toHaveAttribute('aria-selected', 'false');
      }
    });

    test('active tab has visual indicator', async ({ page }) => {
      await page.click('[data-testid="book-card"]');
      await page.click('[data-testid="chapter-tab"]');

      const activeTab = page.getByRole('tab', { name: /Interview Questions/i });

      // Verify the active tab has the correct state attribute
      await expect(activeTab).toHaveAttribute('data-state', 'active');

      // Optionally check for visual styling (shadow, background)
      const hasActiveStyles = await activeTab.evaluate((el) => {
        const styles = window.getComputedStyle(el);
        return styles.boxShadow !== 'none' || styles.backgroundColor !== 'transparent';
      });
      expect(hasActiveStyles).toBe(true);
    });
  });

  test.describe('Keyboard Navigation', () => {
    test('Ctrl+1 switches to Interview Questions tab', async ({ page }) => {
      await page.click('[data-testid="book-card"]');
      await page.click('[data-testid="chapter-tab"]');

      // First switch to editor tab
      const editorTab = page.getByRole('tab', { name: /Chapter Editor/i });
      if (await editorTab.isVisible()) {
        await editorTab.click();
        await expect(editorTab).toHaveAttribute('aria-selected', 'true');

        // Press Ctrl+1
        await page.keyboard.press('Control+1');

        // Verify questions tab is active
        const questionsTab = page.getByRole('tab', { name: /Interview Questions/i });
        await expect(questionsTab).toHaveAttribute('aria-selected', 'true');
      }
    });

    test('Ctrl+2 switches to Chapter Editor tab', async ({ page }) => {
      await page.click('[data-testid="book-card"]');
      await page.click('[data-testid="chapter-tab"]');

      // Verify questions tab is active initially
      const questionsTab = page.getByRole('tab', { name: /Interview Questions/i });
      await expect(questionsTab).toHaveAttribute('aria-selected', 'true');

      // Press Ctrl+2
      await page.keyboard.press('Control+2');

      // Verify editor tab is active
      const editorTab = page.getByRole('tab', { name: /Chapter Editor/i });
      if (await editorTab.isVisible()) {
        await expect(editorTab).toHaveAttribute('aria-selected', 'true');
      }
    });

    test('Ctrl+Tab cycles through tabs', async ({ page }) => {
      await page.click('[data-testid="book-card"]');
      await page.click('[data-testid="chapter-tab"]');

      const questionsTab = page.getByRole('tab', { name: /Interview Questions/i });
      const editorTab = page.getByRole('tab', { name: /Chapter Editor/i });

      if (await editorTab.isVisible()) {
        // Verify questions tab is active initially
        await expect(questionsTab).toHaveAttribute('aria-selected', 'true');

        // Press Ctrl+Tab to go to next tab
        await page.keyboard.press('Control+Tab');
        await expect(editorTab).toHaveAttribute('aria-selected', 'true');

        // Press Ctrl+Tab again to cycle back
        await page.keyboard.press('Control+Tab');
        await expect(questionsTab).toHaveAttribute('aria-selected', 'true');
      }
    });

    test('Arrow keys navigate between tabs', async ({ page }) => {
      await page.click('[data-testid="book-card"]');
      await page.click('[data-testid="chapter-tab"]');

      const questionsTab = page.getByRole('tab', { name: /Interview Questions/i });
      const editorTab = page.getByRole('tab', { name: /Chapter Editor/i });

      if (await editorTab.isVisible()) {
        // Focus the questions tab
        await questionsTab.focus();

        // Press ArrowRight to move to editor tab
        await page.keyboard.press('ArrowRight');

        // Editor tab should be focused
        await expect(editorTab).toBeFocused();
      }
    });
  });

  test.describe('Session Storage Persistence', () => {
    test('tab state persists during session', async ({ page }) => {
      await page.click('[data-testid="book-card"]');
      await page.click('[data-testid="chapter-tab"]');

      const editorTab = page.getByRole('tab', { name: /Chapter Editor/i });
      if (await editorTab.isVisible()) {
        // Switch to editor tab
        await editorTab.click();
        await expect(editorTab).toHaveAttribute('aria-selected', 'true');

        // Verify sessionStorage was updated
        const storageValue = await page.evaluate(() => {
          // Find the storage key that matches the pattern
          for (let i = 0; i < sessionStorage.length; i++) {
            const key = sessionStorage.key(i);
            if (key && key.startsWith('chapterQuestionsTab_')) {
              return sessionStorage.getItem(key);
            }
          }
          return null;
        });

        expect(storageValue).toBe('editor');
      }
    });

    test('tab state is restored after navigation', async ({ page }) => {
      await page.click('[data-testid="book-card"]');
      await page.click('[data-testid="chapter-tab"]');

      const editorTab = page.getByRole('tab', { name: /Chapter Editor/i });
      if (await editorTab.isVisible()) {
        // Switch to editor tab
        await editorTab.click();

        // Navigate away and back
        await page.goBack();
        await page.waitForLoadState('networkidle');
        await page.click('[data-testid="chapter-tab"]');

        // Verify editor tab is still active (restored from session storage)
        await expect(editorTab).toHaveAttribute('aria-selected', 'true');
      }
    });
  });

  test.describe('Tab Content', () => {
    test('tab switching does not lose question progress', async ({ page }) => {
      await page.click('[data-testid="book-card"]');
      await page.click('[data-testid="chapter-tab"]');

      // Find a question response textarea and enter some text
      const textarea = page.getByPlaceholder(/response/i);
      if (await textarea.isVisible()) {
        await textarea.fill('Test response text');

        // Switch to editor tab and back
        const editorTab = page.getByRole('tab', { name: /Chapter Editor/i });
        if (await editorTab.isVisible()) {
          await editorTab.click();

          const questionsTab = page.getByRole('tab', { name: /Interview Questions/i });
          await questionsTab.click();

          // Verify the text is still there
          await expect(textarea).toHaveValue('Test response text');
        }
      }
    });
  });

  test.describe('Accessibility', () => {
    test('tabs have proper ARIA attributes', async ({ page }) => {
      await page.click('[data-testid="book-card"]');
      await page.click('[data-testid="chapter-tab"]');

      // Verify tablist role
      const tablist = page.getByRole('tablist');
      await expect(tablist).toBeVisible();

      // Verify tab role and aria-selected
      const questionsTab = page.getByRole('tab', { name: /Interview Questions/i });
      await expect(questionsTab).toHaveRole('tab');
      await expect(questionsTab).toHaveAttribute('aria-selected', 'true');

      // Verify tabpanel role
      const tabpanel = page.getByRole('tabpanel');
      await expect(tabpanel).toBeVisible();
      await expect(tabpanel).toHaveAttribute('aria-labelledby');
    });

    test('focus is visible on tabs', async ({ page }) => {
      await page.click('[data-testid="book-card"]');
      await page.click('[data-testid="chapter-tab"]');

      const questionsTab = page.getByRole('tab', { name: /Interview Questions/i });

      // Focus the tab
      await questionsTab.focus();
      await expect(questionsTab).toBeFocused();

      // Verify focus ring is visible (check for ring styles)
      const hasFocusRing = await questionsTab.evaluate((el) => {
        const styles = window.getComputedStyle(el);
        // Check for focus-visible ring styles
        return styles.outlineStyle !== 'none' ||
               styles.boxShadow.includes('ring') ||
               el.classList.contains('focus-visible');
      });

      // The focus indicator should be visible in some form
      expect(hasFocusRing).toBeTruthy();
    });
  });
});
