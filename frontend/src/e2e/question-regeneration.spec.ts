/**
 * Question regeneration E2E (issue #62)
 *
 * Confirms the regeneration UX works end-to-end in a browser:
 *   - Per-question "Generate a new question" replaces that question in place
 *   - "Regenerate All" opens the options dialog and refreshes the whole set
 *   - The regenerate button is disabled once a question hits its regeneration cap
 *
 * Deterministic: questions, progress and the regenerate endpoints are mocked via
 * page.route(); no real backend / OpenAI. Runs with BYPASS_AUTH=true. Mirrors the
 * #53 progress spec (cancel the editor's 2s auto-redirect so it stays mounted).
 */

import { test, expect } from '@playwright/test';

const BOOK_ID = 'e2e-regen-book';
const CHAPTER_ID = 'e2e-regen-chapter';

function question(id: string, order: number, text: string, regenerationCount = 0) {
  return {
    id,
    chapter_id: CHAPTER_ID,
    question_text: text,
    question_type: 'character',
    difficulty: 'medium',
    category: 'character',
    order,
    generated_at: '2026-07-01T00:00:00Z',
    metadata: { suggested_response_length: '100 words' },
    regeneration_count: regenerationCount,
  };
}

async function mockEditor(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    const original = window.setTimeout.bind(window);
    // @ts-expect-error - test shim narrows the overload deliberately
    window.setTimeout = (handler: TimerHandler, timeout?: number, ...args: unknown[]) =>
      timeout === 2000 ? 0 : original(handler, timeout as number, ...args);
  });

  await page.route('**/books/*/chapters/*/content*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        content: '<p>Chapter body</p>',
        chapter_id: CHAPTER_ID,
        book_id: BOOK_ID,
        metadata: { word_count: 2, last_modified: '2026-07-01T00:00:00Z', status: 'draft', estimated_reading_time: 1 },
      }),
    })
  );

  // Per-question response lookups (QuestionDisplay fetches these on mount).
  await page.route('**/books/*/chapters/*/questions/*/response', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ response: null, has_response: false, success: true }),
    })
  );

  await page.route('**/books/*/chapters/*/question-progress', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ total: 2, completed: 0, in_progress: 0, progress: 0, status: 'not-started' }),
    })
  );
}

test.describe('Question regeneration (issue #62)', () => {
  test('regenerates a single question in place', async ({ page }) => {
    await mockEditor(page);

    await page.route('**/books/*/chapters/*/questions?*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          questions: [question('q-1', 1, 'Original first question'), question('q-2', 2, 'Second question')],
          total: 2,
          page: 1,
          pages: 1,
        }),
      })
    );

    // Registered after the list route so it wins for the /regenerate suffix.
    await page.route('**/books/*/chapters/*/questions/*/regenerate', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(question('q-1-new', 1, 'A freshly regenerated question', 1)),
      })
    );

    await page.goto(`/dashboard/books/${BOOK_ID}/chapters/${CHAPTER_ID}`);
    await page.getByRole('tab', { name: /Interview Questions/i }).click();

    await expect(page.getByText('Original first question')).toBeVisible();

    await page.getByLabel('Generate a new question').click();

    await expect(page.getByText('A freshly regenerated question')).toBeVisible();
    await expect(page.getByTestId('regeneration-count')).toHaveText('Regenerated 1/5');
  });

  test('regenerate button is disabled at the regeneration limit', async ({ page }) => {
    await mockEditor(page);

    await page.route('**/books/*/chapters/*/questions?*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          questions: [question('q-1', 1, 'Capped question', 5)],
          total: 1,
          page: 1,
          pages: 1,
        }),
      })
    );

    await page.goto(`/dashboard/books/${BOOK_ID}/chapters/${CHAPTER_ID}`);
    await page.getByRole('tab', { name: /Interview Questions/i }).click();

    await expect(page.getByText('Capped question')).toBeVisible();
    await expect(page.getByTestId('regeneration-count')).toHaveText('Regenerated 5/5');
    await expect(page.getByLabel('Generate a new question')).toBeDisabled();
  });

  test('regenerates the whole set via the Regenerate All dialog', async ({ page }) => {
    await mockEditor(page);

    let regenerated = false;
    await page.route('**/books/*/chapters/*/questions?*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(
          regenerated
            ? { questions: [question('n-1', 1, 'Brand new set question')], total: 1, page: 1, pages: 1 }
            : { questions: [question('q-1', 1, 'Original set question')], total: 1, page: 1, pages: 1 }
        ),
      })
    );
    await page.route('**/books/*/chapters/*/regenerate-questions*', (route) => {
      regenerated = true;
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ questions: [question('n-1', 1, 'Brand new set question')], generation_id: 'g', total: 1 }),
      });
    });

    await page.goto(`/dashboard/books/${BOOK_ID}/chapters/${CHAPTER_ID}`);
    await page.getByRole('tab', { name: /Interview Questions/i }).click();

    await expect(page.getByText('Original set question')).toBeVisible();

    await page.getByRole('button', { name: /Regenerate All/i }).click();
    // Confirm in the dialog (the dialog's own "Regenerate" button).
    await page.getByRole('button', { name: /^Regenerate$/i }).click();

    await expect(page.getByText('Brand new set question')).toBeVisible();
  });
});
