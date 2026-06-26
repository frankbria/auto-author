/**
 * AI Draft Generation E2E (issue #55)
 *
 * Covers the full draft generation flow from the chapter editor:
 *   open dialog → pick a documented writing style → generate (mocked) →
 *   review preview → "Use This Draft" → draft text lands in the editor.
 *
 * Deterministic by design: the chapter-content load and the generate-draft
 * call are mocked via page.route(), so no real backend / OpenAI is needed.
 * Runs with BYPASS_AUTH=true (see playwright.config.ts).
 *
 * The legacy editor route auto-redirects to the tabbed interface after 2s; we
 * cancel only that one timer via an init script so the dialog stays mounted.
 */

import { test, expect } from '@playwright/test';

const BOOK_ID = 'e2e-draft-book';
const CHAPTER_ID = 'e2e-draft-chapter';
const DRAFT_HTML = '<p>This is the AI-generated chapter draft about resilience.</p>';

test.describe('AI draft generation (issue #55)', () => {
  test('generates a draft from answers and inserts it into the editor', async ({ page }) => {
    // Cancel the legacy page's 2s redirect-to-tabs timer (test-only; the draft
    // feature itself is unaffected). TipTap autosave uses a 3s debounce, so this
    // 2000ms-scoped shim does not touch editor behaviour.
    await page.addInitScript(() => {
      const original = window.setTimeout.bind(window);
      // @ts-expect-error - test shim narrows the overload deliberately
      window.setTimeout = (handler: TimerHandler, timeout?: number, ...args: unknown[]) =>
        timeout === 2000 ? 0 : original(handler, timeout as number, ...args);
    });

    // Chapter content load → empty editor.
    await page.route('**/books/*/chapters/*/content*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          content: '',
          chapter_id: CHAPTER_ID,
          book_id: BOOK_ID,
          metadata: {
            word_count: 0,
            last_modified: '2026-06-25T00:00:00Z',
            status: 'draft',
            estimated_reading_time: 0,
          },
        }),
      })
    );

    // Draft generation → deterministic narrative.
    await page.route('**/books/*/chapters/*/generate-draft', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          book_id: BOOK_ID,
          chapter_id: CHAPTER_ID,
          draft: DRAFT_HTML,
          metadata: {
            word_count: 9,
            estimated_reading_time: 1,
            generated_at: '2026-06-25 00:00:00',
            model_used: 'gpt-4',
            writing_style: 'academic',
            target_length: 2000,
            actual_length: 9,
          },
          suggestions: ['Add a concrete example.'],
          message: 'Draft generated',
        }),
      })
    );

    await page.goto(`/dashboard/books/${BOOK_ID}/chapters/${CHAPTER_ID}`);

    // Editor toolbar exposes the draft entry point once the editor mounts.
    const openButton = page.getByRole('button', { name: /generate ai draft/i });
    await expect(openButton).toBeVisible();
    await openButton.click();

    // Dialog opens with the documented styles.
    await expect(page.getByText(/Generate AI Draft for/i)).toBeVisible();

    // Pick a documented style (Academic) — proves the aligned style list (#55 AC).
    await page.getByLabel('Writing Style').click();
    await page.getByRole('option', { name: 'Academic' }).click();

    // Answer at least one question, then generate.
    await page.getByPlaceholder(/your answer/i).first().fill('Resilience is built through repeated practice.');
    await page.getByRole('button', { name: /^generate draft$/i }).click();

    // Preview renders with the generated content.
    await expect(page.getByText(/Generated Draft/i)).toBeVisible();
    await expect(page.getByText(/AI-generated chapter draft about resilience/i)).toBeVisible();

    // Use it → draft lands in the TipTap editor.
    await page.getByRole('button', { name: /use this draft/i }).click();
    await expect(page.locator('.tiptap')).toContainText('AI-generated chapter draft about resilience');
  });
});
