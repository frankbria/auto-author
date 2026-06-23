/**
 * TOC Generation Resilience E2E (issue #48)
 *
 * Verifies the hardened TOC generation flow:
 * - A backend AI failure (e.g. a timeout surfacing as 503) shows the backend's
 *   error message and a retry option instead of a generic dead-end.
 * - Retrying after a transient failure recovers and advances the wizard.
 *
 * Deterministic by design: all backend calls are mocked via page.route(), so the
 * test needs only the frontend webServer (no real OpenAI / backend). Runs with
 * BYPASS_AUTH=true (see playwright.config.ts) so /dashboard is reachable.
 */

import { test, expect } from '@playwright/test';

const BOOK_ID = 'e2e-toc-book';
const TIMEOUT_MESSAGE = 'AI service temporarily unavailable. Please try again.';

const TIMEOUT_503 = {
  status: 503,
  contentType: 'application/json',
  body: JSON.stringify({
    detail: {
      message: TIMEOUT_MESSAGE,
      error_code: 'AI_NETWORK_ERROR',
      retry_after: 30,
      retryable: true,
      correlation_id: 'e2e-toc-1',
    },
  }),
};

const READY_BODY = {
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify({
    is_ready_for_toc: true,
    confidence_score: 0.9,
    analysis: 'Looks good',
    suggestions: [],
    word_count: 120,
    character_count: 600,
    meets_minimum_requirements: true,
  }),
};

const QUESTIONS_BODY = {
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify({
    book_id: BOOK_ID,
    questions: ['What is the main theme?', 'Who is the target audience?'],
    generated_at: '2026-06-22T00:00:00Z',
    total_questions: 2,
  }),
};

test.describe('TOC generation resilience (issue #48)', () => {
  test('surfaces the backend error message with a retry option, and recovers on retry', async ({
    page,
  }) => {
    // analyze-summary failure is intentionally swallowed by the wizard; mock it harmlessly.
    await page.route('**/api/v1/books/*/analyze-summary', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
    );

    await page.route('**/api/v1/books/*/generate-questions', (route) =>
      route.fulfill(QUESTIONS_BODY)
    );
    // Readiness check fails (timeout→503) until we explicitly flip it below. Using a
    // hard failure (not a call counter) keeps this robust to React StrictMode's
    // double-invoked mount effect in dev and the single invoke in CI's prod build.
    await page.route('**/api/v1/books/*/toc-readiness', (route) =>
      route.fulfill(TIMEOUT_503)
    );

    await page.goto(`/dashboard/books/${BOOK_ID}/generate-toc`);

    // The backend's actual message is surfaced (not a generic hardcoded string)...
    await expect(page.getByText(TIMEOUT_MESSAGE)).toBeVisible();
    // ...alongside a retry control.
    const retryButton = page.getByRole('button', { name: /try again/i });
    await expect(retryButton).toBeVisible();

    // Recovery: readiness now passes, so retrying advances the wizard to questions.
    await page.unroute('**/api/v1/books/*/toc-readiness');
    await page.route('**/api/v1/books/*/toc-readiness', (route) =>
      route.fulfill(READY_BODY)
    );
    await retryButton.click();

    await expect(page.getByText(TIMEOUT_MESSAGE)).toBeHidden();
    await expect(page.getByPlaceholder(/type your answer here/i)).toBeVisible();
  });
});
