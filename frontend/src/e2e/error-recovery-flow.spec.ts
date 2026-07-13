/**
 * Error Recovery Flow E2E (issue #201)
 *
 * Pins the error-recovery behavior that actually ships:
 *
 * 1. Book creation has NO automatic retry (`bookClient.createBook` is a plain
 *    fetch): a failure surfaces a classified error notification with a manual
 *    Retry action, the user stays on the form with input intact, and exactly
 *    one request is sent. Manual Retry succeeds once the network recovers.
 *    (The previous, always-skipped version of this suite asserted exponential
 *    backoff on this path — behavior that never existed.)
 *
 * 2. Question-response saves DO retry with exponential backoff: the internal
 *    ErrorHandler makes exactly 3 attempts (1s/2s backoff) before surfacing a
 *    persistent error with a Retry button (#197). Manual Retry recovers.
 *
 * Runs in CI against the real backend (BYPASS_AUTH, no AI key); failures are
 * injected with page.route().
 */

import { test, expect, Page } from '@playwright/test';
import { createTestBookWithTOC, deleteTestBook } from './helpers/testData';

const QUESTION = {
  id: 'e2e-err-q-1',
  chapter_id: 'e2e-chapter',
  question_text: 'What single idea should this chapter leave with the reader?',
  question_type: 'research',
  difficulty: 'medium',
  category: 'content',
  order: 0,
  generated_at: '2026-07-13T00:00:00Z',
  metadata: { suggested_response_length: '1-2 paragraphs' },
};

const json = (body: unknown) => ({
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify(body),
});

// Opens the BookCreationWizard modal from the dashboard (the canonical create
// flow — the orphaned /dashboard/new-book page was removed in #205) and fills
// the form. Genre/target audience are Radix selects: click trigger, pick option.
async function fillNewBookForm(page: Page, title: string) {
  await page.goto('/dashboard');
  await page.getByRole('button', { name: 'Create New Book' }).first().click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await dialog.getByLabel(/book title/i).fill(title);
  await dialog.getByLabel(/genre/i).click();
  await page.getByRole('option', { name: 'Other' }).click();
  await dialog.getByLabel(/target audience/i).click();
  await page.getByRole('option', { name: 'General' }).click();
}

test.describe('Error Recovery Flow', () => {
  test.describe('book creation (no auto-retry, manual recovery)', () => {
    let bookId: string | undefined;

    test.afterEach(async ({ page }) => {
      if (bookId) await deleteTestBook(page, bookId);
      bookId = undefined;
    });

    test('server error shows a notification, keeps the form, sends exactly one request; resubmit recovers', async ({ page }) => {
      const title = `Error Recovery Book ${Date.now()}`;
      let postCount = 0;
      await page.route('**/books/', (route) => {
        if (route.request().method() !== 'POST') return route.fallback();
        postCount++;
        return route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Injected create failure (e2e)' }),
        });
      });

      await fillNewBookForm(page, title);
      await page.getByRole('button', { name: 'Create Book' }).click();

      // Classified error notification; no navigation, no automatic retry.
      await expect(page.locator('[data-sonner-toast]')).toBeVisible();
      expect(page.url()).not.toMatch(/\/dashboard\/books\//);
      expect(postCount).toBe(1);
      // The dialog stays open with input intact, so the user can just resubmit.
      const dialog = page.getByRole('dialog');
      await expect(dialog).toBeVisible();
      await expect(dialog.getByLabel(/book title/i)).toHaveValue(title);

      // Network restored → resubmitting the intact form succeeds for real.
      await page.unroute('**/books/');
      await page.getByRole('button', { name: 'Create Book' }).click();
      await page.waitForURL(/\/dashboard\/books\/[^/]+$/);
      bookId = page.url().match(/books\/([a-zA-Z0-9-]+)/)![1];
      expect(bookId).toBeTruthy();
    });

    test('network failure surfaces a retryable notification; the Retry action recovers', async ({ page }) => {
      const title = `Network Failure Book ${Date.now()}`;
      let postCount = 0;
      let failCreates = true;
      await page.route('**/books/', (route) => {
        if (route.request().method() !== 'POST') return route.fallback();
        if (failCreates) {
          postCount++;
          // Network-level failure → classified TRANSIENT → retryable toast.
          return route.abort('failed');
        }
        return route.fallback();
      });

      await fillNewBookForm(page, title);
      await page.getByRole('button', { name: 'Create Book' }).click();

      const toast = page.locator('[data-sonner-toast]');
      await expect(toast).toBeVisible();
      const retryButton = toast.getByRole('button', { name: /retry/i });
      await expect(retryButton).toBeVisible();
      expect(page.url()).not.toMatch(/\/dashboard\/books\//);
      await expect(page.getByRole('dialog')).toBeVisible();
      // No automatic retry storm — one user action, one request.
      expect(postCount).toBe(1);

      // Network restored → the toast's Retry action re-submits and succeeds.
      failCreates = false;
      await retryButton.click();
      await page.waitForURL(/\/dashboard\/books\/[^/]+$/);
      bookId = page.url().match(/books\/([a-zA-Z0-9-]+)/)![1];
      expect(bookId).toBeTruthy();
    });
  });

  test.describe('question-response save (retry with backoff)', () => {
    let bookId: string;

    test.beforeEach(async ({ page }) => {
      const { book } = await createTestBookWithTOC(page, {
        title: `Retry Backoff Book ${Date.now()}`,
      });
      bookId = book.id;
    });

    test.afterEach(async ({ page }) => {
      if (bookId) await deleteTestBook(page, bookId);
    });

    test('failed save retries exactly 3 times with backoff, then manual Retry recovers', async ({ page }) => {
      // Minimal stateful question store: one mocked question; saves fail
      // until the "network" is restored.
      let generated = false;
      let failSaves = true;
      let putCount = 0;
      let savedText: string | null = null;

      const storedResponse = () => ({
        id: 'resp-1',
        question_id: QUESTION.id,
        response_text: savedText,
        word_count: 10,
        status: 'draft',
        created_at: '2026-07-13T00:00:00Z',
        updated_at: '2026-07-13T00:00:00Z',
        last_edited_at: '2026-07-13T00:00:00Z',
        metadata: { edit_history: [] },
      });

      await page.route('**/books/*/chapters/*/generate-questions', (route) => {
        generated = true;
        return route.fulfill(json({ questions: [QUESTION], generation_id: 'e2e-gen', total: 1 }));
      });
      await page.route(
        (url) => url.pathname.endsWith('/questions') && url.pathname.includes('/chapters/'),
        (route) =>
          route.fulfill(
            json({
              questions: generated ? [{ ...QUESTION, has_response: !!savedText }] : [],
              total: generated ? 1 : 0,
              page: 1,
              pages: 1,
            })
          )
      );
      await page.route('**/books/*/chapters/*/question-progress', (route) =>
        route.fulfill(
          json({
            total: generated ? 1 : 0,
            completed: 0,
            in_progress: savedText ? 1 : 0,
            progress: 0,
            status: savedText ? 'in-progress' : 'not-started',
          })
        )
      );
      await page.route(
        (url) => /\/questions\/[^/]+\/response$/.test(url.pathname),
        (route) => {
          if (route.request().method() === 'PUT') {
            putCount++;
            if (failSaves) {
              // A network-level failure (aborted request), not an HTTP 500:
              // bookClient throws plain Errors without a .status, which
              // classify as UNKNOWN (not retryable). Only NETWORK errors
              // exercise the ErrorHandler backoff — same failure mode as
              // the #197 demo (backend killed mid-session).
              return route.abort('failed');
            }
            savedText = (route.request().postDataJSON() as { response_text: string }).response_text;
            return route.fulfill(
              json({ response: storedResponse(), success: true, message: 'Response saved' })
            );
          }
          // GET: serve back what was stored (the save-verification read).
          return route.fulfill(
            json(
              savedText
                ? { response: storedResponse(), has_response: true, success: true }
                : { response: null, has_response: false, success: true }
            )
          );
        }
      );

      // Open the chapter's questions tab and mint the mocked question.
      await page.goto(`/dashboard/books/${bookId}`);
      await page.locator('[data-testid="chapter-tab"]:not([data-tab])').first().click();
      await expect(page.getByRole('tablist', { name: /chapter editor view/i })).toBeVisible();
      await page.locator('[data-testid="chapter-tab"][data-tab="questions"]').click();
      await page.getByRole('button', { name: 'Generate Interview Questions' }).click();
      await expect(page.getByText(QUESTION.question_text)).toBeVisible();

      // Save while the endpoint is down.
      await page
        .getByPlaceholder('Type your response here or use voice input...')
        .fill('An answer written during the outage.');
      await page.getByRole('button', { name: 'Save Draft' }).click();

      // Settled error state: persistent message + Retry button. The internal
      // ErrorHandler backs off 1s/2s between attempts (~7s to settle).
      const retryButton = page.getByRole('button', { name: 'Retry', exact: true });
      await expect(retryButton).toBeVisible({ timeout: 20000 });
      const errorMessage = page.getByText(/network error\. please check your connection/i);
      await expect(errorMessage).toBeVisible();

      // Retry-with-backoff evidence: exactly 3 automatic attempts, no more.
      expect(putCount).toBe(3);

      // Network restored → manual Retry saves and clears the error.
      failSaves = false;
      await retryButton.click();
      await expect(retryButton).toBeHidden({ timeout: 15000 });
      await expect(errorMessage).toBeHidden();
      expect(savedText).toBe('An answer written during the outage.');
    });
  });
});
