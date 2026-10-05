import { test, expect } from './fixtures/auth.fixture';
import {
  seedBookWithToc,
  openChapterEditor,
  answerFirstChapterQuestion,
  readFirstChapterAnswer,
} from './fixtures/journey.helpers';

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

    const dialog = page.getByRole('dialog');
    await expect(dialog.getByPlaceholder(/enter book title/i)).toBeVisible();
    await dialog.getByPlaceholder(/enter book title/i).fill(bookTitle);

    // Capture the create response so we assert on the actual status, not the UI.
    const createResponse = page.waitForResponse(
      (res) => res.url().includes('/books') && res.request().method() === 'POST',
      { timeout: 20000 }
    );

    await dialog.getByRole('button', { name: /^create book$/i }).click();

    const res = await createResponse;
    expect(
      res.status(),
      `Book creation returned ${res.status()} (ObjectId/string conversion regression)`
    ).toBeLessThan(400);

    // The created book must be queryable after a full reload (owner_id correct).
    await page.goto('/dashboard');
    // 20s to match the sibling dashboard-visibility specs in edge-cases.spec.ts.
    // This one was the outlier at 15s and was the only one failing late in a full
    // suite run: the failure snapshot showed ZERO book cards rendered, i.e. the
    // whole list had not loaded yet — not that this book was missing. The account
    // carries ~2,700 books and the dashboard renders a 100-row page (~195 KB) with
    // no pagination UI, so first paint is slow. Tracked separately; the assertion
    // itself is unchanged.
    await expect(page.getByText(bookTitle)).toBeVisible({ timeout: 20_000 });
  });

  /**
   * Regression (Issue #54): chapter question answers were lost on page refresh.
   * Chain: seeded book + TOC -> chapter -> generate questions -> answer -> reload.
   *
   * The book, summary and TOC are seeded through the API (#916): this test is
   * about answer persistence, and driving the AI TOC wizard to get chapters cost
   * about five live OpenAI calls. The one live AI call left is the chapter
   * question generation, because an answer is saved against a real question id
   * the server issued. The answer and the reload go through the UI, with
   * web-first assertions and real save round-trips (journey.helpers.ts).
   */
  test.describe('one live AI call', () => {
    // No retries: the question generation is a live AI call (see the journey spec).
    test.describe.configure({ retries: 0 });

    test('Issue #54: chapter question answers persist after refresh', async ({
      authenticatedPage: page,
    }) => {
      test.setTimeout(180_000);

      const answer = `Persistence check ${Date.now()}`;
      const bookId = await seedBookWithToc(page, `E2E #54 Book ${Date.now()}`);
      await openChapterEditor(page, bookId);
      await answerFirstChapterQuestion(page, answer);

      await page.reload();
      const reloaded = await readFirstChapterAnswer(page);
      expect(reloaded, 'Answer was lost after refresh (Issue #54 regression)').toContain(answer);
    });
  });
});
