/**
 * E2E Test Data Helpers
 *
 * Functions for creating and cleaning up test data in E2E tests.
 * All functions work in auth bypass mode without requiring Clerk authentication.
 */

import { Page } from '@playwright/test';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

/**
 * Test book data interface
 */
export interface TestBook {
  id: string;
  title: string;
  description?: string;
  genre?: string;
  target_audience?: string;
}

/**
 * Test chapter data interface
 */
export interface TestChapter {
  id: string;
  book_id: string;
  title: string;
  order_index: number;
  content?: string;
}

/**
 * Create a test book via API
 * Works in auth bypass mode without authentication
 */
export async function createTestBook(
  page: Page,
  bookData: Partial<TestBook> = {}
): Promise<TestBook> {
  const defaultData = {
    title: `Test Book ${Date.now()}`,
    description: 'A test book created by E2E tests',
    genre: 'Fiction',
    target_audience: 'General'
  };

  const data = { ...defaultData, ...bookData };

  const response = await page.request.post(`${API_BASE_URL}/books`, {
    data,
    headers: {
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok()) {
    throw new Error(`Failed to create test book: ${response.status()} ${await response.text()}`);
  }

  return await response.json();
}

/**
 * Create a test book with TOC (Table of Contents)
 */
export async function createTestBookWithTOC(
  page: Page,
  bookData: Partial<TestBook> = {},
  chapterTitles: string[] = ['Introduction', 'Chapter 1', 'Chapter 2', 'Conclusion']
): Promise<{ book: TestBook; chapters: TestChapter[] }> {
  // Create book
  const book = await createTestBook(page, bookData);

  // Create TOC with chapters
  const tocResponse = await page.request.post(`${API_BASE_URL}/books/${book.id}/toc`, {
    data: {
      chapters: chapterTitles.map((title, index) => ({
        title,
        order_index: index
      }))
    },
    headers: {
      'Content-Type': 'application/json'
    }
  });

  if (!tocResponse.ok()) {
    throw new Error(`Failed to create TOC: ${tocResponse.status()} ${await tocResponse.text()}`);
  }

  const tocData = await tocResponse.json();
  const chapters: TestChapter[] = tocData.chapters || [];

  return { book, chapters };
}

/**
 * Create a test chapter with content
 */
export async function createTestChapter(
  page: Page,
  bookId: string,
  chapterData: Partial<TestChapter> & { title: string }
): Promise<TestChapter> {
  const response = await page.request.post(`${API_BASE_URL}/books/${bookId}/chapters`, {
    data: chapterData,
    headers: {
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok()) {
    throw new Error(`Failed to create chapter: ${response.status()} ${await response.text()}`);
  }

  return await response.json();
}

/**
 * Delete a test book and all associated data
 */
export async function deleteTestBook(page: Page, bookId: string): Promise<void> {
  const response = await page.request.delete(`${API_BASE_URL}/books/${bookId}`, {
    headers: {
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok() && response.status() !== 404) {
    console.warn(`Failed to delete test book ${bookId}: ${response.status()}`);
  }
}

/**
 * Clean up all test books created during tests
 * WARNING: This deletes ALL books with "Test Book" in the title
 */
export async function cleanupAllTestBooks(page: Page): Promise<void> {
  try {
    const response = await page.request.get(`${API_BASE_URL}/books`);

    if (!response.ok()) {
      console.warn('Failed to fetch books for cleanup');
      return;
    }

    const books: TestBook[] = await response.json();
    const testBooks = books.filter(book => book.title.includes('Test Book'));

    for (const book of testBooks) {
      await deleteTestBook(page, book.id);
    }

    console.log(`🧹 Cleaned up ${testBooks.length} test books`);
  } catch (error) {
    console.warn('Error during test book cleanup:', error);
  }
}

/**
 * Wait for a book to appear in the dashboard
 */
export async function waitForBookInDashboard(
  page: Page,
  bookTitle: string,
  timeout: number = 10000
): Promise<void> {
  await page.waitForSelector(`[data-testid="book-card"]:has-text("${bookTitle}")`, {
    timeout,
    state: 'visible'
  });
}

/**
 * Navigate to a book's editor page
 */
export async function navigateToBookEditor(
  page: Page,
  bookId: string
): Promise<void> {
  await page.goto(`/dashboard/books/${bookId}`);
  await page.waitForLoadState('networkidle');
}

/**
 * Navigate to a specific chapter in a book
 */
export async function navigateToChapter(
  page: Page,
  bookId: string,
  chapterIndex: number
): Promise<void> {
  await navigateToBookEditor(page, bookId);

  // Click on chapter tab
  await page.click(`[data-testid="chapter-tab"]:nth-of-type(${chapterIndex + 1})`);
  await page.waitForLoadState('networkidle');
}

/**
 * Update chapter content
 */
export async function updateChapterContent(
  page: Page,
  bookId: string,
  chapterId: string,
  content: string
): Promise<void> {
  const response = await page.request.patch(`${API_BASE_URL}/books/${bookId}/chapters/${chapterId}`, {
    data: { content },
    headers: {
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok()) {
    throw new Error(`Failed to update chapter: ${response.status()} ${await response.text()}`);
  }
}

/**
 * Get book data from API
 */
export async function getBook(page: Page, bookId: string): Promise<TestBook | null> {
  try {
    const response = await page.request.get(`${API_BASE_URL}/books/${bookId}`);

    if (!response.ok()) {
      return null;
    }

    return await response.json();
  } catch (error) {
    console.warn(`Failed to fetch book ${bookId}:`, error);
    return null;
  }
}

/**
 * Get all books for the current user (in bypass mode, returns all books)
 */
export async function getAllBooks(page: Page): Promise<TestBook[]> {
  try {
    const response = await page.request.get(`${API_BASE_URL}/books`);

    if (!response.ok()) {
      return [];
    }

    return await response.json();
  } catch (error) {
    console.warn('Failed to fetch books:', error);
    return [];
  }
}
