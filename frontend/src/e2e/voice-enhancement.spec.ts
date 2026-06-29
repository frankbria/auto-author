/**
 * Voice/Dictation Enhancement E2E (issue #56)
 *
 * Covers the voice-to-enhanced workflow from the chapter editor:
 *   raw dictated text in the editor → Clean up dictation (mocked) → raw/cleaned
 *   side-by-side preview → Apply (replaces editor content) → Revert (restores raw).
 *
 * Deterministic: chapter-content load and the enhance-transcription call are
 * mocked via page.route(); no real backend / OpenAI / browser SpeechRecognition
 * (which is native and non-deterministic, unavailable headless). Runs with
 * BYPASS_AUTH=true. Mirrors the #57 content-enhancement spec.
 */

import { test, expect } from '@playwright/test';

const BOOK_ID = 'e2e-voice-book';
const CHAPTER_ID = 'e2e-voice-chapter';
// Raw dictation as it would arrive from speech-to-text: fillers, no punctuation.
const RAW = 'um so the cat you know sat on the mat';
const CLEANED = '<p>The cat sat on the mat.</p>';

test.describe('Voice enhancement (issue #56)', () => {
  test('cleans up dictation, previews raw/cleaned, applies, and reverts', async ({ page }) => {
    await page.addInitScript(() => {
      const original = window.setTimeout.bind(window);
      // @ts-expect-error - test shim narrows the overload deliberately
      window.setTimeout = (handler: TimerHandler, timeout?: number, ...args: unknown[]) =>
        timeout === 2000 ? 0 : original(handler, timeout as number, ...args);
    });

    // Chapter loads with the raw dictated content already in the editor.
    await page.route('**/books/*/chapters/*/content*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          content: `<p>${RAW}</p>`,
          chapter_id: CHAPTER_ID,
          book_id: BOOK_ID,
          metadata: { word_count: 10, last_modified: '2026-06-29T00:00:00Z', status: 'draft', estimated_reading_time: 1 },
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

    // Voice/dictation cleanup.
    await page.route('**/books/*/chapters/*/enhance-transcription', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          book_id: BOOK_ID,
          chapter_id: CHAPTER_ID,
          enhanced: CLEANED,
          metadata: {
            enhancement_type: 'transcription',
            enhancement_label: 'Dictation Cleanup',
            original_word_count: 10,
            enhanced_word_count: 6,
            model_used: 'gpt-4',
            generated_at: '2026-06-29 00:00:00',
          },
          message: 'Transcription cleaned up successfully',
        }),
      })
    );

    await page.goto(`/dashboard/books/${BOOK_ID}/chapters/${CHAPTER_ID}`);

    // Editor loads with the raw dictation.
    await expect(page.locator('.tiptap')).toContainText(RAW);

    // Open the cleanup dialog and run it.
    await page.getByRole('button', { name: /clean up dictation/i }).click();
    const dialog = page.getByRole('dialog');
    await dialog.getByRole('button', { name: /^clean up$/i }).click();

    // Raw/cleaned preview renders both versions (scoped to the dialog).
    await expect(dialog.getByText(/um so the cat/i)).toBeVisible();
    await expect(dialog.getByText(/^The cat sat on the mat\.$/i)).toBeVisible();

    // Apply → editor now shows the cleaned text, not the raw dictation.
    await page.getByRole('button', { name: /apply to chapter/i }).click();
    await expect(page.locator('.tiptap')).toContainText('The cat sat on the mat.');
    await expect(page.locator('.tiptap')).not.toContainText('um so the cat');

    // Revert → raw dictation is restored.
    await page.getByRole('button', { name: /revert enhancement/i }).click();
    await expect(page.locator('.tiptap')).toContainText(RAW);
    await expect(page.locator('.tiptap')).not.toContainText('The cat sat on the mat.');
  });
});
