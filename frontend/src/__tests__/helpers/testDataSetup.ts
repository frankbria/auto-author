/**
 * Test data setup helpers for E2E tests
 *
 * These helpers use API calls to set up test data instead of going through the UI,
 * which is 10-30x faster and more reliable.
 *
 * @example
 * // Instead of: Click through UI to create book, fill form, submit
 * // Use: const book = await createTestBook(token);
 */

// Note: Update these imports once the actual API client is implemented
// import { bookClient } from '@/lib/api/bookClient';

interface TestBook {
  id: string;
  title: string;
  genre: string;
  summary: string;
  author_name?: string;
  target_audience?: string;
}

interface TestChapter {
  id: string;
  title: string;
  order: number;
  content?: string;
  book_id: string;
}

/**
 * Create a test book via API (bypassing UI)
 *
 * @param token - Authentication token
 * @param overrides - Custom book properties
 * @returns Created book object
 */
export async function createTestBook(
  token: string,
  overrides?: Partial<TestBook>
): Promise<TestBook> {
  const defaultBook = {
    title: `Test Book ${Date.now()}`,
    genre: 'non-fiction',
    summary: 'Test book summary for E2E testing',
    author_name: 'Test Author',
    target_audience: 'Test audience',
    ...overrides
  };

  // TODO: Replace with actual API call once bookClient is available
  // return await bookClient.createBook(defaultBook, token);

  // Placeholder for now - would make actual API call
  return {
    id: `test-book-${Date.now()}`,
    ...defaultBook
  };
}

/**
 * Create a test chapter via API
 *
 * @param bookId - Book ID to create chapter in
 * @param token - Authentication token
 * @param overrides - Custom chapter properties
 * @returns Created chapter object
 */
export async function createTestChapter(
  bookId: string,
  token: string,
  overrides?: Partial<TestChapter>
): Promise<TestChapter> {
  const defaultChapter = {
    title: `Test Chapter ${Date.now()}`,
    order: 1,
    content: '',
    book_id: bookId,
    ...overrides
  };

  // TODO: Replace with actual API call once bookClient is available
  // return await bookClient.createChapter(bookId, defaultChapter, token);

  // Placeholder for now
  return {
    id: `test-chapter-${Date.now()}`,
    ...defaultChapter
  };
}

/**
 * Delete a test book via API (cleanup)
 *
 * @param bookId - Book ID to delete
 * @param token - Authentication token
 */
export async function deleteTestBook(
  bookId: string,
  token: string
): Promise<void> {
  // TODO: Replace with actual API call once bookClient is available
  // await bookClient.deleteBook(bookId, token);

  // Placeholder for now
  console.log(`[Test Cleanup] Would delete book ${bookId}`);
}

/**
 * Factory for creating test books with common configurations
 */
export const testBookFactory = {
  /**
   * Create a non-fiction book for testing
   */
  nonFiction: (token: string, title?: string) =>
    createTestBook(token, {
      genre: 'non-fiction',
      title: title || 'Test Non-Fiction Book',
      summary: 'A test non-fiction book for E2E testing'
    }),

  /**
   * Create a fiction book for testing
   */
  fiction: (token: string, title?: string) =>
    createTestBook(token, {
      genre: 'fiction',
      title: title || 'Test Fiction Book',
      summary: 'A test fiction book for E2E testing'
    }),

  /**
   * Create a book with multiple chapters
   */
  withChapters: async (token: string, chapterCount: number = 3) => {
    const book = await createTestBook(token);

    const chapters = await Promise.all(
      Array.from({ length: chapterCount }, (_, i) =>
        createTestChapter(book.id, token, {
          title: `Chapter ${i + 1}`,
          order: i + 1
        })
      )
    );

    return { book, chapters };
  }
};

/**
 * Example usage in E2E tests:
 *
 * ```typescript
 * test('user can edit a chapter', async ({ page }) => {
 *   // Setup test data via API (fast)
 *   const { book, chapters } = await testBookFactory.withChapters(token, 3);
 *
 *   // Navigate directly to the chapter editor
 *   await page.goto(`/dashboard/books/${book.id}/chapters/${chapters[0].id}`);
 *
 *   // Test the editing functionality
 *   await page.fill('.editor', 'New content');
 *   await waitForCondition(() => page.locator('[data-save-status="saved"]').isVisible());
 *
 *   // Cleanup
 *   await deleteTestBook(book.id, token);
 * });
 * ```
 */
