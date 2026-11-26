/**
 * Writing Style Transformation E2E (issue #58)
 *
 * Covers the full transform flow from the chapter editor:
 *   pick a style → Transform (mocked) → before/after preview → Apply (replaces
 *   editor content) → Revert (restores the original).
 *
 * Deterministic: chapter-content load and the transform-style call are mocked
 * via page.route(); no real backend / OpenAI. Runs with BYPASS_AUTH=true.
 *
 * The book and its chapter are seeded through the API and opened on the book
 * page (#1094); the AI calls and chapter content stay mocked.
 */

import { test, expect } from '@playwright/test';
import { deleteTestBook, openSeededChapter } from './helpers/testData';

let bookId: string | undefined;

test.afterEach(async ({ page }) => {
  if (bookId) await deleteTestBook(page, bookId);
  bookId = undefined;
});

const BOOK_ID = 'e2e-style-book';
const CHAPTER_ID = 'e2e-style-chapter';
const ORIGINAL = 'The cat sat on the mat.';
const TRANSFORMED = '<p>The feline assumed a seated posture upon the floor covering.</p>';

test.describe('Style transformation (issue #58)', () => {
  test('transforms a chapter, previews before/after, applies, and reverts', async ({ page }) => {
    // Chapter loads with existing content.
    await page.route('**/books/*/chapters/*/content*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          content: `<p>${ORIGINAL}</p>`,
          chapter_id: CHAPTER_ID,
          book_id: BOOK_ID,
          metadata: { word_count: 6, last_modified: '2026-06-25T00:00:00Z', status: 'draft', estimated_reading_time: 1 },
        }),
      })
    );

    // Saves (auto-save / apply) succeed.
    await page.route('**/books/*/chapters/*/content', (route) => {
      if (route.request().method() === 'PATCH' || route.request().method() === 'PUT') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) });
      }
      return route.fallback();
    });

    // Style transformation.
    await page.route('**/books/*/chapters/*/transform-style', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          book_id: BOOK_ID,
          chapter_id: CHAPTER_ID,
          transformed: TRANSFORMED,
          metadata: {
            target_style: 'academic',
            style_label: 'Academic',
            original_word_count: 6,
            transformed_word_count: 11,
            model_used: 'gpt-4',
            generated_at: '2026-06-25 00:00:00',
          },
          message: 'Style transformed successfully',
        }),
      })
    );

    ({ bookId } = await openSeededChapter(page));

    // Editor loads with the original content.
    await expect(page.locator('.tiptap')).toContainText(ORIGINAL);

    // Open the transform dialog and pick a style.
    await page.getByRole('button', { name: /transform style/i }).click();
    await page.getByLabel('Target Style').click();
    await page.getByRole('option', { name: 'Academic' }).click();
    await page.getByRole('button', { name: /^transform$/i }).click();

    // Before/after preview renders both versions (scoped to the dialog).
    const dialog = page.getByRole('dialog');
    await expect(dialog.getByText(ORIGINAL)).toBeVisible();
    await expect(dialog.getByText(/feline assumed a seated posture/i)).toBeVisible();

    // Apply → editor now shows the transformed text, not the original.
    await page.getByRole('button', { name: /apply to chapter/i }).click();
    await expect(page.locator('.tiptap')).toContainText('feline assumed a seated posture');
    await expect(page.locator('.tiptap')).not.toContainText(ORIGINAL);

    // Revert → original is restored.
    await page.getByRole('button', { name: /revert style/i }).click();
    await expect(page.locator('.tiptap')).toContainText(ORIGINAL);
    await expect(page.locator('.tiptap')).not.toContainText('feline assumed a seated posture');
  });
});
