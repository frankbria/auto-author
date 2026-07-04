import { mkdirSync } from 'fs';
import { expect } from '@playwright/test';
import { test } from './fixtures/auth.fixture';
import { createBook } from './fixtures/journey.helpers';

async function expectMeaningfulScreenshot(buffer: Buffer, label: string): Promise<void> {
  expect(buffer.length, `${label} screenshot should not be empty`).toBeGreaterThan(10_000);
}

// Mutation testing note: this is an external visual smoke/artifact test;
// its value is the generated Playwright artifact, not a local code branch mutation.
test.describe('Staging visual smoke', () => {
  test('dashboard and summary screens produce reviewable screenshots', async ({
    authenticatedPage: page,
  }) => {
    mkdirSync('tests/e2e/staging/test-results', { recursive: true });

    await page.goto('/dashboard');
    await expect(page.locator('h1, h2')).toContainText(/dashboard|books/i, {
      timeout: 15_000,
    });

    const dashboardShot = await page.screenshot({
      path: 'tests/e2e/staging/test-results/visual-smoke-dashboard.png',
      fullPage: true,
    });
    await expectMeaningfulScreenshot(dashboardShot, 'dashboard');

    const bookId = await createBook(page, `Visual Smoke Book ${Date.now()}`);
    await page.goto(`/dashboard/books/${bookId}/summary`);
    await expect(page.getByRole('textbox', { name: /book summary/i })).toBeVisible({
      timeout: 20_000,
    });

    const summaryShot = await page.screenshot({
      path: 'tests/e2e/staging/test-results/visual-smoke-summary.png',
      fullPage: true,
    });
    await expectMeaningfulScreenshot(summaryShot, 'summary');
  });
});
