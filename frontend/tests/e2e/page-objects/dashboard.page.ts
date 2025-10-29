/**
 * Dashboard Page Object
 *
 * Handles dashboard navigation and book list interactions.
 */

import { Page, expect, Locator } from '@playwright/test';

export class DashboardPage {
  constructor(private page: Page) {}

  /**
   * Navigate to dashboard
   */
  async goto(): Promise<void> {
    await this.page.goto('/dashboard');
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Get the books list element
   */
  booksList(): Locator {
    return this.page.locator('[data-testid="books-list"]');
  }

  /**
   * Click "New Book" button
   */
  async clickNewBook(): Promise<void> {
    await this.page.click('button:has-text("New Book")');
    await this.page.waitForURL('**/dashboard/new-book');
  }

  /**
   * Wait for books API call to complete
   */
  async waitForBooksAPI(): Promise<void> {
    await this.page.waitForResponse(
      resp => resp.url().includes('/api/v1/books') && resp.status() === 200,
      { timeout: 10000 }
    );
  }

  /**
   * Verify books list is visible
   */
  async verifyBooksListVisible(): Promise<void> {
    await expect(this.booksList()).toBeVisible();
  }

  /**
   * Get a book by title
   */
  getBookByTitle(title: string): Locator {
    return this.page.locator(`[data-testid="book-item"]:has-text("${title}")`);
  }

  /**
   * Click on a book to view details
   */
  async clickBook(title: string): Promise<void> {
    await this.getBookByTitle(title).click();
    await this.page.waitForURL(/\/dashboard\/books\/[a-z0-9-]+$/);
  }

  /**
   * Click delete button for a book
   */
  async clickDeleteBook(bookId: string): Promise<void> {
    // Find the book row
    const bookRow = this.page.locator(`[data-testid="book-${bookId}"]`);

    // Click three-dot menu
    await bookRow.locator('[data-testid="book-menu"]').click();

    // Click delete option
    await this.page.click('text=Delete');
  }

  /**
   * Verify book appears in list
   */
  async verifyBookInList(title: string): Promise<void> {
    await expect(this.getBookByTitle(title)).toBeVisible();
    console.log(`✅ Book "${title}" found in list`);
  }

  /**
   * Verify book does NOT appear in list
   */
  async verifyBookNotInList(title: string): Promise<void> {
    await expect(this.getBookByTitle(title)).not.toBeVisible();
    console.log(`✅ Book "${title}" not in list (as expected)`);
  }

  /**
   * Get count of books in list
   */
  async getBooksCount(): Promise<number> {
    const books = this.page.locator('[data-testid="book-item"]');
    return await books.count();
  }

  /**
   * Verify dashboard page loads correctly
   */
  async verifyDashboardLoaded(): Promise<void> {
    // Verify URL
    await expect(this.page).toHaveURL(/\/dashboard$/);

    // Verify page elements
    await this.verifyBooksListVisible();

    console.log('✅ Dashboard loaded successfully');
  }

  /**
   * Navigate to book detail page by ID
   */
  async navigateToBook(bookId: string): Promise<void> {
    await this.page.goto(`/dashboard/books/${bookId}`);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Refresh dashboard
   */
  async refresh(): Promise<void> {
    await this.page.reload();
    await this.page.waitForLoadState('networkidle');
  }
}
