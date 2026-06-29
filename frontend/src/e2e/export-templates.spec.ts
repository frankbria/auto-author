/**
 * Export Templates E2E (issue #59)
 *
 * Verifies the professional-template export flow end to end:
 * - The export dialog lists the available templates (from /export/formats).
 * - Selecting a template reveals its inline spec preview *before* export.
 * - Exporting sends the chosen template_id to the backend and completes.
 *
 * Deterministic by design: all backend calls are mocked via page.route(), so the
 * test needs only the frontend webServer. Runs with BYPASS_AUTH=true (see
 * playwright.config.ts) so /dashboard is reachable.
 */

import { test, expect } from '@playwright/test';

const BOOK_ID = 'e2e-export-templates-book';

const BOOK_BODY = {
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify({
    id: BOOK_ID,
    title: 'Template Export Book',
    description: 'A book for export template testing.',
    owner_id: 'e2e-user',
    published: false,
    created_at: '2026-06-28T00:00:00Z',
    updated_at: '2026-06-28T00:00:00Z',
  }),
};

const TEMPLATES = [
  {
    id: 'classic_fiction',
    name: 'Classic Fiction',
    description: 'Timeless 6×9 trade-paperback layout.',
    category: 'fiction',
    best_for: 'Novels',
    page_size: '6x9',
    margins: { top: 0.75, bottom: 0.75, inside: 0.65, outside: 0.6 },
    font: { family: 'serif', pdf_font: 'Times-Roman', docx_font: 'Garamond', size: 11 },
    line_height: 1.3,
    first_line_indent: 0.2,
    header: { left: '{book_title}', right: '{author}' },
    footer: { center: '{page}' },
  },
  {
    id: 'academic',
    name: 'Academic',
    description: 'Double-spaced A4 layout with wide margins.',
    category: 'academic',
    best_for: 'Theses',
    page_size: 'A4',
    margins: { top: 1.0, bottom: 1.0, inside: 1.25, outside: 1.25 },
    font: { family: 'serif', pdf_font: 'Times-Roman', docx_font: 'Times New Roman', size: 12 },
    line_height: 2.0,
    first_line_indent: 0.5,
    header: { left: '{book_title}', right: '{author}' },
    footer: { center: '{page}' },
  },
];

const FORMATS_BODY = {
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify({
    formats: [
      { format: 'pdf', name: 'PDF Document', description: '', mime_type: 'application/pdf', extension: '.pdf', available: true, options: { page_size: ['letter', 'A4'], include_empty_chapters: 'boolean' } },
      { format: 'docx', name: 'Word Document', description: '', mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', extension: '.docx', available: true, options: { include_empty_chapters: 'boolean' } },
    ],
    book_stats: { total_chapters: 2, chapters_with_content: 2, total_word_count: 1200, estimated_pages: 4 },
    templates: TEMPLATES,
  }),
};

test.describe('Export templates (issue #59)', () => {
  // The export options dialog is tall once the template list is added; use a
  // viewport that fits its footer so the "Export PDF" action stays reachable.
  test.use({ viewport: { width: 1280, height: 1500 } });

  test.skip(
    ({ browserName }) => browserName === 'webkit',
    'webkit route-mocking of the book page is flaky; flow is covered on chromium'
  );

  test('selects a template, previews it, and exports with the template_id', async ({ page }) => {
    await page.route(`**/api/v1/books/${BOOK_ID}`, (route) => route.fulfill(BOOK_BODY));
    await page.route(`**/api/v1/books/${BOOK_ID}/toc`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ toc: { chapters: [] } }) })
    );
    await page.route(`**/api/v1/books/${BOOK_ID}/summary`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ summary: '' }) })
    );
    await page.route('**/api/v1/books/*/export/formats', (route) => route.fulfill(FORMATS_BODY));

    // Capture the export request so we can assert the template_id was sent.
    let exportedUrl = '';
    await page.route('**/api/v1/books/*/export/pdf*', (route) => {
      exportedUrl = route.request().url();
      return route.fulfill({
        status: 200,
        contentType: 'application/pdf',
        headers: { 'content-disposition': 'attachment; filename="book.pdf"' },
        body: '%PDF-1.4 fake pdf body',
      });
    });

    await page.goto(`/dashboard/books/${BOOK_ID}`);

    // Open the export dialog — the template selector is present.
    await page.getByRole('button', { name: /export book/i }).first().click();
    const selector = page.getByTestId('template-selector');
    await expect(selector).toBeVisible();

    // Select the Classic Fiction template; its spec preview appears before export.
    await page.getByLabel('Classic Fiction').check();
    const preview = page.getByTestId('template-preview');
    await expect(preview).toBeVisible();
    await expect(preview).toContainText('6x9');

    // Export and confirm completion.
    await page.getByRole('button', { name: /export pdf/i }).click();
    await expect(page.getByRole('dialog').getByText(/export complete/i)).toBeVisible();

    // The backend received the chosen template.
    expect(exportedUrl).toContain('template_id=classic_fiction');
  });
});
