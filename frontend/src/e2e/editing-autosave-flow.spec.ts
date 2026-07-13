/**
 * Editing & Auto-save Flow E2E (issue #201)
 *
 * Exercises the ChapterEditor auto-save pipeline against the real backend:
 * 3s-debounced PATCH /books/{id}/chapters/{id}/content, the save-status
 * indicator, localStorage backup on network failure, the recovery banner
 * (Restore/Dismiss), and automatic recovery once the network returns.
 *
 * Books/TOC are seeded through the deterministic API helpers (no AI), so the
 * suite runs in CI without an OpenAI key. Only save *failures* are injected
 * via page.route(); every successful save is a genuine backend round trip.
 */

import { test, expect, Page } from '@playwright/test';
import { createTestBookWithTOC, deleteTestBook } from './helpers/testData';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const CONTENT_GLOB = '**/books/*/chapters/*/content*';
// 3s debounce + network time, with CI headroom.
const SAVE_TIMEOUT = 15000;

/** Open the first sidebar chapter tab and wait for the editor to mount. */
async function openFirstChapter(page: Page) {
  const firstChapter = page.locator('[data-testid="chapter-tab"]:not([data-tab])').first();
  await firstChapter.click();
  await expect(page.getByRole('tablist', { name: /chapter editor view/i })).toBeVisible();
  await expect(page.locator('.tiptap')).toBeVisible();
}

/** Type into the TipTap editor (focuses it first). */
async function typeInEditor(page: Page, text: string) {
  await page.locator('.tiptap').click();
  await page.keyboard.type(text);
}

/** Make every PATCH to the content endpoint fail with a 500; reads pass through. */
async function injectSaveFailure(page: Page) {
  await page.route(CONTENT_GLOB, (route) => {
    if (route.request().method() === 'PATCH') {
      return route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Injected save failure (e2e)' }),
      });
    }
    return route.fallback();
  });
}

function backupKey(bookId: string, chapterId: string) {
  return `chapter-backup-${bookId}-${chapterId}`;
}

async function getBackup(page: Page, bookId: string, chapterId: string): Promise<string | null> {
  return page.evaluate((key) => localStorage.getItem(key), backupKey(bookId, chapterId));
}

test.describe('Editing & Auto-save Flow', () => {
  let bookId: string;
  let chapterId: string;

  test.beforeEach(async ({ page }) => {
    const { book, chapters } = await createTestBookWithTOC(page, {
      title: `Autosave Test Book ${Date.now()}`,
    });
    bookId = book.id;
    chapterId = chapters[0].id;
    await page.goto(`/dashboard/books/${bookId}`);
    await openFirstChapter(page);
  });

  test.afterEach(async ({ page }) => {
    if (bookId) await deleteTestBook(page, bookId);
  });

  test('auto-saves typed content to the backend and shows Saved status', async ({ page }) => {
    const saved = page.waitForResponse(
      (r) => r.request().method() === 'PATCH' && r.url().includes('/content') && r.ok(),
      { timeout: SAVE_TIMEOUT }
    );

    await typeInEditor(page, 'The quick brown fox practices urban gardening.');
    await saved;

    const indicator = page.getByTestId('save-status-indicator');
    await expect(indicator).toHaveAttribute('data-save-status', 'saved');
    await expect(indicator).toContainText(/saved/i);

    // Outcome evidence: the content genuinely persisted on the backend.
    const response = await page.request.get(
      `${API_BASE_URL}/books/${bookId}/chapters/${chapterId}/content`
    );
    expect(response.ok()).toBe(true);
    const body = await response.json();
    expect(body.content).toContain('The quick brown fox practices urban gardening.');
  });

  test('debounce collapses rapid keystrokes into a single save request', async ({ page }) => {
    let patchCount = 0;
    await page.route(CONTENT_GLOB, (route) => {
      if (route.request().method() === 'PATCH') patchCount++;
      return route.fallback();
    });

    const saved = page.waitForResponse(
      (r) => r.request().method() === 'PATCH' && r.url().includes('/content') && r.ok(),
      { timeout: SAVE_TIMEOUT }
    );
    await typeInEditor(page, 'Twenty rapid keystrokes typed well inside one debounce window.');
    await saved;

    await expect(page.getByTestId('save-status-indicator')).toHaveAttribute(
      'data-save-status',
      'saved'
    );
    expect(patchCount).toBe(1);
  });

  test('failed auto-save shows an error and backs content up to localStorage', async ({ page }) => {
    await injectSaveFailure(page);

    await typeInEditor(page, 'This paragraph must survive the outage.');

    await expect(
      page.getByText('Failed to auto-save. Content backed up locally.')
    ).toBeVisible({ timeout: SAVE_TIMEOUT });

    const backup = await getBackup(page, bookId, chapterId);
    expect(backup).not.toBeNull();
    expect(JSON.parse(backup!).content).toContain('This paragraph must survive the outage.');
  });

  test('recovery banner after reload restores backed-up content into the editor', async ({ page }) => {
    await injectSaveFailure(page);
    await typeInEditor(page, 'Recovered prose that only exists in the local backup.');
    await expect(
      page.getByText('Failed to auto-save. Content backed up locally.')
    ).toBeVisible({ timeout: SAVE_TIMEOUT });

    // Network is "restored" for the reload; the backup is still in localStorage.
    await page.unroute(CONTENT_GLOB);
    await page.reload();
    await openFirstChapter(page);

    await expect(
      page.getByText(/a local backup of your content is available/i)
    ).toBeVisible();
    await page.getByRole('button', { name: 'Restore Backup' }).click();

    await expect(page.locator('.tiptap')).toContainText(
      'Recovered prose that only exists in the local backup.'
    );
  });

  test('dismissing the recovery banner clears the backup', async ({ page }) => {
    await injectSaveFailure(page);
    await typeInEditor(page, 'Backup that the user chooses to discard.');
    await expect(
      page.getByText('Failed to auto-save. Content backed up locally.')
    ).toBeVisible({ timeout: SAVE_TIMEOUT });

    await page.unroute(CONTENT_GLOB);
    await page.reload();
    await openFirstChapter(page);

    await expect(
      page.getByText(/a local backup of your content is available/i)
    ).toBeVisible();
    await page.getByRole('button', { name: 'Dismiss' }).click();

    await expect(
      page.getByText(/a local backup of your content is available/i)
    ).toBeHidden();
    expect(await getBackup(page, bookId, chapterId)).toBeNull();
  });

  test('auto-save recovers on its own once the network returns', async ({ page }) => {
    await injectSaveFailure(page);
    await typeInEditor(page, 'Content written while the backend was down.');
    await expect(
      page.getByText('Failed to auto-save. Content backed up locally.')
    ).toBeVisible({ timeout: SAVE_TIMEOUT });

    // Restore the network; the pending auto-save retries on its own cadence.
    await page.unroute(CONTENT_GLOB);

    await expect(page.getByTestId('save-status-indicator')).toHaveAttribute(
      'data-save-status',
      'saved',
      { timeout: SAVE_TIMEOUT }
    );

    // Backup is cleared after the successful save, and the backend has the text.
    expect(await getBackup(page, bookId, chapterId)).toBeNull();
    const response = await page.request.get(
      `${API_BASE_URL}/books/${bookId}/chapters/${chapterId}/content`
    );
    const body = await response.json();
    expect(body.content).toContain('Content written while the backend was down.');
  });
});
