/**
 * Rich-text formatting E2E (issue #341)
 *
 * The headline "rich text editing" capability had no test that could prove it
 * works: TipTap is globally mocked in the jsdom unit suite (`src/jest.setup.ts`),
 * so `RichTextEditor.test.tsx` can only assert that a toolbar button invokes the
 * right command — never that the command produces formatted output. The existing
 * E2E only ever inserted plain draft text.
 *
 * This spec closes that gap in a real browser with a real TipTap instance: it
 * clicks the actual toolbar and asserts the resulting marks/nodes, both in the
 * live editor DOM and in the HTML that reaches the backend. Formatting that
 * renders but never persists is still a broken feature, so both are required.
 *
 * Books/TOC are seeded through the deterministic API helpers (no AI), so this
 * runs in CI without an OpenAI key.
 */

import { test, expect, Page } from '@playwright/test';
import { createTestBookWithTOC, deleteTestBook } from './helpers/testData';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
// 3s auto-save debounce + network time, with CI headroom.
const SAVE_TIMEOUT = 15000;

/** Open the first sidebar chapter tab and wait for the editor to mount. */
async function openFirstChapter(page: Page) {
  await page.locator('[data-testid="chapter-tab"]:not([data-tab])').first().click();
  await expect(page.getByRole('tablist', { name: /chapter editor view/i })).toBeVisible();
  await expect(page.locator('.tiptap')).toBeVisible();
}

/** Type text into the real TipTap editor, then select it so marks can apply. */
async function typeAndSelectAll(page: Page, text: string) {
  await page.locator('.tiptap').click();
  await page.keyboard.type(text);
  await page.keyboard.press('ControlOrMeta+a');
}

/**
 * Poll the backend until the auto-saved chapter content contains `fragment`.
 * This is the outcome evidence: the formatting survived the round trip, rather
 * than merely having rendered in the browser.
 */
async function expectSavedContentToContain(
  page: Page,
  bookId: string,
  chapterId: string,
  fragment: string
) {
  await expect
    .poll(
      async () => {
        const response = await page.request.get(
          `${API_BASE_URL}/books/${bookId}/chapters/${chapterId}/content`
        );
        if (!response.ok()) return '';
        return (await response.json()).content ?? '';
      },
      { timeout: SAVE_TIMEOUT, message: `saved content never contained ${fragment}` }
    )
    .toContain(fragment);
}

test.describe('Rich-text formatting', () => {
  let bookId: string;
  let chapterId: string;

  test.beforeEach(async ({ page }) => {
    const { book, chapters } = await createTestBookWithTOC(page, {
      title: `Formatting Test Book ${Date.now()}`,
    });
    bookId = book.id;
    chapterId = chapters[0].id;
    await page.goto(`/dashboard/books/${bookId}`);
    await openFirstChapter(page);
  });

  test.afterEach(async ({ page }) => {
    if (bookId) await deleteTestBook(page, bookId);
  });

  test('Bold produces a <strong> mark that persists', async ({ page }) => {
    const text = 'Habits are the invisible architecture of daily life.';
    await typeAndSelectAll(page, text);

    await page.getByRole('button', { name: 'Bold', exact: true }).click();

    await expect(page.locator('.tiptap strong')).toHaveText(text);
    await expectSavedContentToContain(page, bookId, chapterId, `<strong>${text}</strong>`);
  });

  test('Heading 2 converts the paragraph to an <h2>', async ({ page }) => {
    const text = 'The Neuroscience of Habits';
    await typeAndSelectAll(page, text);

    await page.getByRole('button', { name: 'Heading 2', exact: true }).click();

    await expect(page.locator('.tiptap h2')).toHaveText(text);
    // The paragraph is replaced, not wrapped.
    await expect(page.locator('.tiptap p')).toHaveCount(0);
    await expectSavedContentToContain(page, bookId, chapterId, `<h2>${text}</h2>`);
  });

  test('Bullet List wraps the line in <ul><li>', async ({ page }) => {
    const text = 'Cue, routine, reward';
    await typeAndSelectAll(page, text);

    await page.getByRole('button', { name: 'Bullet List', exact: true }).click();

    await expect(page.locator('.tiptap ul li')).toHaveText(text);
    // The <li> fragment carries the weight — a bare '<ul>' check would be
    // satisfied by any list anywhere in the document.
    await expectSavedContentToContain(page, bookId, chapterId, `<ul><li><p>${text}</p></li></ul>`);
  });

  test('formatting is reversible — toggling Bold off removes the mark', async ({ page }) => {
    const text = 'Formatting must be undoable.';
    await typeAndSelectAll(page, text);

    const bold = page.getByRole('button', { name: 'Bold', exact: true });
    await bold.click();
    await expect(page.locator('.tiptap strong')).toHaveText(text);

    await bold.click();
    await expect(page.locator('.tiptap strong')).toHaveCount(0);
    await expect(page.locator('.tiptap')).toContainText(text);
    await expectSavedContentToContain(page, bookId, chapterId, `<p>${text}</p>`);
  });
});
