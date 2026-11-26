/**
 * The legacy chapter URL is a plain server redirect (#1094): no editor mounts on
 * it, and the reader lands on the book page with that chapter open.
 */

import { test, expect } from '@playwright/test';
import { createTestBookWithTOC, deleteTestBook } from './helpers/testData';

let bookId: string | undefined;

test.afterEach(async ({ page }) => {
  if (bookId) await deleteTestBook(page, bookId);
  bookId = undefined;
});

test('the legacy chapter URL redirects to the book page with that chapter open', async ({ page }) => {
  const { book, chapters } = await createTestBookWithTOC(page, { title: `Test Book ${Date.now()}` });
  bookId = book.id;
  // The second chapter, so landing on the book's default chapter would not pass.
  const chapter = chapters[1];

  const response = await page.goto(`/dashboard/books/${book.id}/chapters/${chapter.id}`);

  // The legacy document itself was a redirect; nothing rendered there.
  expect(response?.request().redirectedFrom()?.url()).toContain(`/chapters/${chapter.id}`);
  await expect(page).toHaveURL(new RegExp(`/dashboard/books/${book.id}\\?chapter=${chapter.id}$`));

  await expect(page.getByRole('tablist', { name: /chapter editor view/i })).toBeVisible();
  await expect(page.locator('.tiptap')).toBeVisible();
  await expect(page.getByText('Redirecting to Tabbed Interface')).toHaveCount(0);
});
