import { test, expect } from './fixtures/auth.fixture';
import type { Page } from '@playwright/test';

/**
 * Dedicated regression tests for the bugs that motivated Issue #83.
 *
 * Each test maps to a specific production regression that slipped past manual
 * testing. Run against live staging with real Better-auth via the auth fixture.
 *
 *   1. Session cookie signing + user lookup  -> "no 401 on authenticated routes"
 *   2. ObjectId/string conversion            -> "book creation succeeds & persists"
 *   3. Question answer persistence (#54)      -> "chapter answers survive a refresh"
 *
 * These intentionally assert on real network responses (status codes / save
 * round-trips) rather than arbitrary timeouts, per the project's test standards.
 */

// API calls go to the api.* host; match on the path so we don't depend on env.
const API_PATH = '/api/v1';

test.describe('Issue #83 regressions', () => {
  /**
   * Regression: signed session cookies were not parsed correctly and the
   * subsequent ObjectId->string conversion broke user lookup, producing 401s
   * on the dashboard. If auth is wired correctly, no API call should 401.
   */
  test('session + user lookup: authenticated routes never return 401', async ({
    authenticatedPage: page,
  }) => {
    const unauthorized: string[] = [];
    page.on('response', (res) => {
      if (res.url().includes(API_PATH) && res.status() === 401) {
        unauthorized.push(`${res.status()} ${res.request().method()} ${res.url()}`);
      }
    });

    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/dashboard/);
    // Dashboard chrome must render for an authenticated user.
    await expect(page.locator('h1, h2')).toContainText(/dashboard|books/i, {
      timeout: 15000,
    });

    // A refresh re-validates the session cookie end-to-end.
    await page.reload();
    await expect(page.locator('h1, h2')).toContainText(/dashboard|books/i, {
      timeout: 15000,
    });

    expect(
      unauthorized,
      `Authenticated API calls returned 401 (session/user-lookup regression):\n${unauthorized.join('\n')}`
    ).toEqual([]);
  });

  /**
   * Regression: owner_id was stored as an ObjectId instead of a string, so book
   * creation failed Pydantic validation (422/500) and books vanished on reload.
   * Verify the create request succeeds and the book persists across a refresh.
   */
  test('ObjectId conversion: book creation succeeds and persists', async ({
    authenticatedPage: page,
  }) => {
    const bookTitle = `E2E Regression Book ${Date.now()}`;

    await page.goto('/dashboard');

    await page
      .getByRole('button', { name: /create.*book|new book|add book/i })
      .first()
      .click();

    await page.waitForSelector('input[name="title"], input[placeholder*="title" i]', {
      timeout: 10000,
    });
    await page.fill('input[name="title"], input[placeholder*="title" i]', bookTitle);

    // Capture the create response so we assert on the actual status, not the UI.
    const createResponse = page.waitForResponse(
      (res) =>
        res.url().includes('/books') &&
        res.request().method() === 'POST',
      { timeout: 20000 }
    );

    await page.getByRole('button', { name: /create|submit|save/i }).first().click();

    const res = await createResponse;
    expect(
      res.status(),
      `Book creation returned ${res.status()} (ObjectId/string conversion regression)`
    ).toBeLessThan(400);

    // The created book must be queryable after a full reload (owner_id correct).
    await page.goto('/dashboard');
    await expect(page.getByText(bookTitle)).toBeVisible({ timeout: 15000 });
  });

  /**
   * Regression (Issue #54): chapter question answers were lost on page refresh.
   * Full chain: create book -> summary -> TOC -> chapter -> answer -> reload.
   */
  test('Issue #54: chapter question answers persist after refresh', async ({
    authenticatedPage: page,
  }) => {
    test.setTimeout(300000);

    const answer = `Persistence check ${Date.now()}`;
    await createBookWithSummary(page, `E2E #54 Book ${Date.now()}`);
    await generateToc(page);
    await openFirstChapter(page);
    await generateQuestions(page);

    const answerField = page
      .locator('textarea[placeholder*="answer" i], input[placeholder*="answer" i], [contenteditable="true"][data-question]')
      .first();
    await answerField.waitFor({ timeout: 15000 });

    // Wait for the save round-trip instead of a fixed debounce timeout.
    const saved = page.waitForResponse(
      (res) =>
        /\/questions\/.*\/response|\/questions\/responses\/batch/.test(res.url()) &&
        ['POST', 'PUT', 'PATCH'].includes(res.request().method()) &&
        res.status() < 400,
      { timeout: 20000 }
    );
    await answerField.fill(answer);
    await answerField.blur();
    await saved;

    await page.reload();
    const reloaded = page
      .locator('textarea[placeholder*="answer" i], input[placeholder*="answer" i], [contenteditable="true"][data-question]')
      .first();
    await reloaded.waitFor({ timeout: 15000 });
    const value = (await reloaded.inputValue().catch(() => reloaded.textContent())) ?? '';
    expect(value, 'Answer was lost after refresh (Issue #54 regression)').toContain(answer);
  });
});

// --- shared helpers (kept local; the journey spec has its own copies) ---

async function createBookWithSummary(page: Page, title: string): Promise<void> {
  await page.goto('/dashboard');
  await page
    .getByRole('button', { name: /create.*book|new book|add book/i })
    .first()
    .click();
  await page.waitForSelector('input[name="title"], input[placeholder*="title" i]', {
    timeout: 10000,
  });
  await page.fill('input[name="title"], input[placeholder*="title" i]', title);
  await page.getByRole('button', { name: /create|submit|save/i }).first().click();
  await page.waitForURL(/\/books\/[a-f0-9]+/, { timeout: 15000 });

  await page
    .getByRole('button', { name: /start with book summary|complete book summary|book summary/i })
    .first()
    .click();
  await page.waitForURL(/\/summary/, { timeout: 10000 });

  const editor = page.getByRole('textbox', { name: /book summary/i });
  await editor.waitFor({ timeout: 10000 });
  await editor.fill(
    'A regression test book summary with enough content to drive table-of-contents generation on staging.'
  );
  await page.getByRole('button', { name: /save|update/i }).first().click();
}

async function generateToc(page: Page): Promise<void> {
  const tocLink = page.getByRole('link', { name: /table.*content|toc|chapters/i });
  if (await tocLink.isVisible({ timeout: 5000 }).catch(() => false)) {
    await tocLink.click();
  }
  await page
    .getByRole('button', { name: /generate.*toc|generate.*table|create.*chapters/i })
    .first()
    .click();
  await page.waitForSelector('[data-testid="chapter-item"], [role="list"] li', {
    timeout: 35000,
  });
}

async function openFirstChapter(page: Page): Promise<void> {
  await page.locator('[data-testid="chapter-item"], [role="list"] li').first().click();
}

async function generateQuestions(page: Page): Promise<void> {
  const btn = page.getByRole('button', { name: /generate.*question/i });
  if (await btn.isVisible({ timeout: 8000 }).catch(() => false)) {
    await btn.click();
  }
  await page.waitForSelector(
    'textarea[placeholder*="answer" i], input[placeholder*="answer" i], [contenteditable="true"][data-question]',
    { timeout: 35000 }
  );
}
