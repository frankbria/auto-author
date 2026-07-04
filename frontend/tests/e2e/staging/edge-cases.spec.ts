import { Page, expect } from '@playwright/test';
import { test } from './fixtures/auth.fixture';
import { addSummary, createBook, READY_SUMMARY } from './fixtures/journey.helpers';

const API_BASE_URL =
  process.env.STAGING_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'https://api.dev.autoauthor.app/api/v1';

async function createBookOnPage(page: Page, title: string): Promise<string> {
  const id = await createBook(page, title);
  expect(id).toMatch(/^[a-f0-9]+$/);
  return id;
}

async function updateToc(page: Page, bookId: string, chapterCount: number): Promise<void> {
  const toc = {
    chapters: Array.from({ length: chapterCount }, (_, index) => ({
      id: `edge-ch-${index + 1}`,
      title: `Edge Case Chapter ${index + 1}`,
      description: `Generated staging edge-case chapter ${index + 1}`,
      level: 1,
      order: index + 1,
      status: 'draft',
      word_count: 0,
      estimated_reading_time: 0,
      subchapters: [],
    })),
    total_chapters: chapterCount,
    estimated_pages: chapterCount * 10,
    structure_notes: 'Staging edge-case large TOC smoke data',
  };

  const response = await page.request.put(`${API_BASE_URL}/books/${bookId}/toc`, {
    data: toc,
  });

  expect(response.status(), await response.text()).toBeLessThan(400);
}

async function expectAuthenticatedDashboard(page: Page): Promise<void> {
  await page.goto('/dashboard');
  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.locator('h1, h2')).toContainText(/dashboard|books/i, {
    timeout: 15_000,
  });
}

// Mutation testing note: these specs validate live staging environment behavior and
// cross-process browser/network effects; local production-code mutation is not practical.
test.describe('Staging edge cases', () => {
  test('session expiration redirects protected pages back to sign-in', async ({
    authenticatedPage: page,
  }) => {
    await expectAuthenticatedDashboard(page);

    await page.context().clearCookies();
    await page.goto('/dashboard');

    await expect(page).toHaveURL(/\/auth\/sign-in|\/sign-in|\/login/, {
      timeout: 20_000,
    });
    await expect(page.locator('input[type="email"]')).toBeVisible();
  });

  test('concurrent book creation succeeds for separate tabs in the same session', async ({
    authenticatedPage: page,
  }) => {
    const secondPage = await page.context().newPage();
    const timestamp = Date.now();

    try {
      const [firstBookId, secondBookId] = await Promise.all([
        createBookOnPage(page, `Concurrent Edge Book A ${timestamp}`),
        createBookOnPage(secondPage, `Concurrent Edge Book B ${timestamp}`),
      ]);

      expect(firstBookId).not.toBe(secondBookId);
    } finally {
      await secondPage.close();
    }
  });

  test('network interruption during TOC readiness shows retryable error UI', async ({
    authenticatedPage: page,
  }) => {
    const bookId = await createBookOnPage(page, `Network Edge Book ${Date.now()}`);
    let abortedReadiness = false;

    await page.route(/\/api\/v1\/books\/[^/]+\/toc-readiness$/, async (route) => {
      if (!abortedReadiness) {
        abortedReadiness = true;
        await route.abort('internetdisconnected');
        return;
      }
      await route.continue();
    });

    await addSummary(page, bookId, READY_SUMMARY);

    await expect(page.getByRole('heading', { name: /something went wrong/i })).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByRole('button', { name: /try again/i })).toBeVisible();
  });

  test('large table of contents with 50 chapters renders and saves from edit screen', async ({
    authenticatedPage: page,
  }) => {
    const bookId = await createBookOnPage(page, `Large TOC Edge Book ${Date.now()}`);
    await updateToc(page, bookId, 50);

    await page.goto(`/dashboard/books/${bookId}/edit-toc`);
    await expect(page.getByRole('heading', { name: /edit table of contents/i })).toBeVisible();
    await expect(page.locator('input[value^="Edge Case Chapter"]')).toHaveCount(50, {
      timeout: 20_000,
    });

    const saveResponse = page.waitForResponse(
      (response) =>
        response.url().includes(`/books/${bookId}/toc`) &&
        response.request().method() === 'PUT' &&
        response.status() < 400,
      { timeout: 30_000 }
    );

    await page.getByRole('button', { name: /save & continue/i }).click();
    await saveResponse;
    await expect(page).toHaveURL(new RegExp(`/dashboard/books/${bookId}(?:[/?#]|$)`));
  });

  test('Unicode metadata is preserved in dashboard rendering', async ({ authenticatedPage: page }) => {
    const title = `Unicode Edge Café 東京 🚀 ${Date.now()}`;
    await createBookOnPage(page, title);

    await page.goto('/dashboard');
    await expect(page.getByText(title)).toBeVisible({ timeout: 20_000 });
  });

  test('XSS-like book metadata is rendered as inert text, not executable markup', async ({
    authenticatedPage: page,
  }) => {
    const marker = `xss-edge-${Date.now()}`;
    const xssTitle = `<img src=x onerror="window.__${marker}=true"> ${marker}`;

    await createBookOnPage(page, xssTitle);
    await page.goto('/dashboard');

    await expect(page.getByText(marker)).toBeVisible({ timeout: 20_000 });
    const executed = await page.evaluate((key) => Boolean((window as unknown as Record<string, unknown>)[`__${key}`]), marker);
    expect(executed).toBe(false);
  });
});
