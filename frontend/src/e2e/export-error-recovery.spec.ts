/**
 * Export Error Recovery E2E (issue #49)
 *
 * Verifies the hardened export flow:
 * - A backend export failure (e.g. a validation 400) surfaces the backend's
 *   actual error message in the progress modal alongside a retry control,
 *   instead of a generic dead-end.
 * - Retrying after the failure recovers and completes the export.
 *
 * Deterministic by design: all backend calls are mocked via page.route(), so the
 * test needs only the frontend webServer. Runs with BYPASS_AUTH=true (see
 * playwright.config.ts) so /dashboard is reachable.
 */

import { test, expect } from '@playwright/test';

const BOOK_ID = 'e2e-export-book';

const VALIDATION_MESSAGE =
  'This book has no chapter content yet. Add content to at least one chapter.';

const BOOK_BODY = {
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify({
    id: BOOK_ID,
    title: 'Export Recovery Book',
    description: 'A book for export error-recovery testing.',
    owner_id: 'e2e-user',
    published: false,
    created_at: '2026-06-22T00:00:00Z',
    updated_at: '2026-06-22T00:00:00Z',
  }),
};

const FORMATS_BODY = {
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify({
    formats: [
      { format: 'pdf', name: 'PDF Document', description: '', mime_type: 'application/pdf', extension: '.pdf', available: true, options: { page_size: ['letter', 'A4'], include_empty_chapters: 'boolean' } },
      { format: 'docx', name: 'Word Document', description: '', mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', extension: '.docx', available: true, options: { include_empty_chapters: 'boolean' } },
    ],
    book_stats: {
      total_chapters: 2,
      chapters_with_content: 1,
      total_word_count: 1200,
      estimated_pages: 4,
    },
  }),
};

test.describe('Export error recovery (issue #49)', () => {
  // The export options dialog is tall; use a viewport that fits its footer so
  // the "Export PDF" action is reachable across all device projects.
  test.use({ viewport: { width: 1280, height: 1300 } });

  // This is a deterministic flow test (CI gates on chromium). Skip on the
  // webkit engine, where route-mocking the heavier book page intermittently
  // leaves getBook unintercepted ("Loading book details..." never resolves).
  test.skip(
    ({ browserName }) => browserName === 'webkit',
    'webkit route-mocking of the book page is flaky; flow is covered on chromium'
  );

  test('surfaces the backend error with a retry option, and recovers on retry', async ({
    page,
  }) => {
    // Page-load data (book renders; TOC/summary are best-effort).
    await page.route(`**/api/v1/books/${BOOK_ID}`, (route) => route.fulfill(BOOK_BODY));
    await page.route(`**/api/v1/books/${BOOK_ID}/toc`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ toc: { chapters: [] } }) })
    );
    await page.route(`**/api/v1/books/${BOOK_ID}/summary`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ summary: '' }) })
    );
    await page.route('**/api/v1/books/*/export/formats', (route) => route.fulfill(FORMATS_BODY));

    // First export attempt fails with a backend validation error (non-retryable,
    // so it surfaces immediately); the retry succeeds with a real PDF blob.
    let exportSucceeds = false;
    await page.route('**/api/v1/books/*/export/pdf*', (route) => {
      if (exportSucceeds) {
        return route.fulfill({
          status: 200,
          contentType: 'application/pdf',
          headers: { 'content-disposition': 'attachment; filename="book.pdf"' },
          body: '%PDF-1.4 fake pdf body',
        });
      }
      return route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ detail: VALIDATION_MESSAGE }),
      });
    });

    await page.goto(`/dashboard/books/${BOOK_ID}`);

    // Open the export options modal and start a PDF export.
    await page.getByRole('button', { name: /export book/i }).first().click();
    await page.getByRole('button', { name: /export pdf/i }).click();

    // The backend's actual message is surfaced in the progress dialog, with a
    // retry control (scoped to the dialog — the same message also appears in
    // stacked error toasts).
    const failedDialog = page.getByRole('dialog', { name: /export failed/i });
    await expect(failedDialog).toBeVisible();
    await expect(failedDialog.getByText(VALIDATION_MESSAGE)).toBeVisible();
    const retryButton = failedDialog.getByRole('button', { name: /retry export/i });
    await expect(retryButton).toBeVisible();

    // Recovery: the next export succeeds and the modal reports completion.
    exportSucceeds = true;
    await retryButton.click();
    await page.getByRole('button', { name: /export pdf/i }).click();

    await expect(
      page.getByRole('dialog').getByText(/export complete/i)
    ).toBeVisible();
  });
});
