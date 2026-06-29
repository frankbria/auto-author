/**
 * Chapter question progress tracking E2E (issue #53)
 *
 * Confirms the progress-tracking UI works end-to-end in a browser:
 *   - "X of Y questions answered" + progress bar render from real data
 *   - "Next Unanswered" jumps to the first not-completed question
 *   - "Next Unanswered" is disabled when every question is completed
 *
 * Deterministic: the chapter content, questions list and progress summary are
 * mocked via page.route(); no real backend / OpenAI. Runs with BYPASS_AUTH=true.
 * Mirrors the #57 content-enhancement spec (cancel only the editor's 2s
 * auto-redirect timer so the editor stays mounted).
 */

import { test, expect } from '@playwright/test';

const BOOK_ID = 'e2e-progress-book';
const CHAPTER_ID = 'e2e-progress-chapter';

function question(id: string, order: number, text: string, status?: 'completed' | 'draft') {
  return {
    id,
    chapter_id: CHAPTER_ID,
    question_text: text,
    question_type: 'character',
    difficulty: 'medium',
    category: 'character',
    order,
    generated_at: '2026-06-29T00:00:00Z',
    metadata: { suggested_response_length: '100 words' },
    ...(status ? { response_status: status, has_response: true } : {}),
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
        metadata: { word_count: 2, last_modified: '2026-06-29T00:00:00Z', status: 'draft', estimated_reading_time: 1 },
      }),
    })
  );
}

test.describe('Chapter question progress tracking (issue #53)', () => {
  test('shows "X of Y answered" and jumps to the next unanswered question', async ({ page }) => {
    await mockEditor(page);

    // Q1 completed, Q2 unanswered, Q3 completed (out of order → positional logic would be wrong).
    const questions = [
      question('q-1', 1, 'First question', 'completed'),
      question('q-2', 2, 'Second question'),
      question('q-3', 3, 'Third question', 'completed'),
    ];

    await page.route('**/books/*/chapters/*/questions?*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ questions, total: 3, page: 1, pages: 1 }),
      })
    );
    await page.route('**/books/*/chapters/*/question-progress', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ total: 3, completed: 2, in_progress: 0, progress: 2 / 3, status: 'in-progress' }),
      })
    );

    await page.goto(`/dashboard/books/${BOOK_ID}/chapters/${CHAPTER_ID}`);
    await page.getByRole('tab', { name: /Interview Questions/i }).click();

    // Progress summary + bar reflect real data.
    await expect(page.getByText('2 of 3 questions answered')).toBeVisible();
    await expect(page.getByTestId('question-progressbar')).toHaveAttribute('aria-valuenow', '67');

    // Starts on Q1 (target the navigation counter button specifically).
    await expect(page.getByRole('button', { name: /Question 1 of 3/i })).toBeVisible();

    // "Next Unanswered" jumps to Q2 (the only not-completed question).
    await page.getByRole('button', { name: /Next Unanswered/i }).click();
    await expect(page.getByRole('button', { name: /Question 2 of 3/i })).toBeVisible();
    await expect(page.getByText('Second question')).toBeVisible();
  });

  test('"Next Unanswered" is disabled when all questions are completed', async ({ page }) => {
    await mockEditor(page);

    const questions = [
      question('q-1', 1, 'First question', 'completed'),
      question('q-2', 2, 'Second question', 'completed'),
    ];

    await page.route('**/books/*/chapters/*/questions?*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ questions, total: 2, page: 1, pages: 1 }),
      })
    );
    await page.route('**/books/*/chapters/*/question-progress', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ total: 2, completed: 2, in_progress: 0, progress: 1, status: 'completed' }),
      })
    );

    await page.goto(`/dashboard/books/${BOOK_ID}/chapters/${CHAPTER_ID}`);
    await page.getByRole('tab', { name: /Interview Questions/i }).click();

    await expect(page.getByText('All questions completed')).toBeVisible();
    await expect(page.getByRole('button', { name: /Next Unanswered/i })).toBeDisabled();
  });
});
