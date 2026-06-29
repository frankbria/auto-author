/**
 * Content Enhancement E2E (issue #57)
 *
 * Covers the full enhancement flow from the chapter editor:
 *   pick a type → Enhance (mocked) → before/after preview → Apply (replaces
 *   editor content) → Revert (restores the original).
 *
 * Deterministic: chapter-content load and the enhance-text call are mocked via
 * page.route(); no real backend / OpenAI. Runs with BYPASS_AUTH=true.
 *
 * The legacy editor route auto-redirects to the tabbed interface after 2s; we
 * cancel only that one timer so the editor stays mounted. Mirrors the #58
 * style-transformation spec.
 */

import { test, expect } from '@playwright/test';

const BOOK_ID = 'e2e-enhance-book';
const CHAPTER_ID = 'e2e-enhance-chapter';
const ORIGINAL = 'The cat sat on the mat.';
const ENHANCED = '<p>The cat sat upon the mat.</p>';

test.describe('Content enhancement (issue #57)', () => {
  test('enhances a chapter, previews before/after, applies, and reverts', async ({ page }) => {
    await page.addInitScript(() => {
      const original = window.setTimeout.bind(window);
      // @ts-expect-error - test shim narrows the overload deliberately
      window.setTimeout = (handler: TimerHandler, timeout?: number, ...args: unknown[]) =>
        timeout === 2000 ? 0 : original(handler, timeout as number, ...args);
    });

    // Chapter loads with existing content.
    await page.route('**/books/*/chapters/*/content*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          content: `<p>${ORIGINAL}</p>`,
          chapter_id: CHAPTER_ID,
          book_id: BOOK_ID,
          metadata: { word_count: 6, last_modified: '2026-06-28T00:00:00Z', status: 'draft', estimated_reading_time: 1 },
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

    // Content enhancement.
    await page.route('**/books/*/chapters/*/enhance-text', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          book_id: BOOK_ID,
          chapter_id: CHAPTER_ID,
          enhanced: ENHANCED,
          metadata: {
            enhancement_type: 'grammar',
            enhancement_label: 'Grammar',
            original_word_count: 6,
            enhanced_word_count: 6,
            model_used: 'gpt-4',
            generated_at: '2026-06-28 00:00:00',
          },
          message: 'Text enhanced successfully',
        }),
      })
    );

    await page.goto(`/dashboard/books/${BOOK_ID}/chapters/${CHAPTER_ID}`);

    // Editor loads with the original content.
    await expect(page.locator('.tiptap')).toContainText(ORIGINAL);

    // Open the enhance dialog and pick a type.
    await page.getByRole('button', { name: /^enhance$/i }).click();
    await page.getByLabel('Enhancement Type').click();
    await page.getByRole('option', { name: 'Grammar' }).click();
    // The dialog footer's submit button is also "Enhance"; target the dialog one.
    const dialog = page.getByRole('dialog');
    await dialog.getByRole('button', { name: /^enhance$/i }).click();

    // Before/after preview renders both versions (scoped to the dialog).
    await expect(dialog.getByText(ORIGINAL)).toBeVisible();
    await expect(dialog.getByText(/cat sat upon the mat/i)).toBeVisible();

    // Apply → editor now shows the enhanced text, not the original.
    await page.getByRole('button', { name: /apply to chapter/i }).click();
    await expect(page.locator('.tiptap')).toContainText('cat sat upon the mat');
    await expect(page.locator('.tiptap')).not.toContainText(ORIGINAL);

    // Revert → original is restored.
    await page.getByRole('button', { name: /revert enhancement/i }).click();
    await expect(page.locator('.tiptap')).toContainText(ORIGINAL);
    await expect(page.locator('.tiptap')).not.toContainText('cat sat upon the mat');
  });
});
