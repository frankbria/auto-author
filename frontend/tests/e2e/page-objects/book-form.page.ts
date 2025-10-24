/**
 * Book Form Page Object
 *
 * Handles book creation and editing forms.
 */

import { Page, expect, Locator } from '@playwright/test';
import { BookData } from '../fixtures/test-data.fixture';

export class BookFormPage {
  constructor(private page: Page) {}

  /**
   * Navigate to new book form
   */
  async gotoNewBook(): Promise<void> {
    await this.page.goto('/dashboard/new-book');
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Navigate to edit book form
   */
  async gotoEditBook(bookId: string): Promise<void> {
    await this.page.goto(`/dashboard/books/${bookId}/edit`);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Get form element
   */
  form(): Locator {
    return this.page.locator('form');
  }

  /**
   * Fill title field
   */
  async fillTitle(title: string): Promise<void> {
    await this.page.fill('[name="title"]', title);
  }

  /**
   * Fill description field
   */
  async fillDescription(description: string): Promise<void> {
    await this.page.fill('[name="description"]', description);
  }

  /**
   * Select genre from dropdown
   */
  async selectGenre(genre: string): Promise<void> {
    await this.page.selectOption('[name="genre"]', genre);
  }

  /**
   * Fill target audience field
   */
  async fillTargetAudience(targetAudience: string): Promise<void> {
    await this.page.fill('[name="targetAudience"]', targetAudience);
  }

  /**
   * Fill all book details
   */
  async fillBookDetails(data: BookData): Promise<void> {
    await this.fillTitle(data.title);
    await this.fillDescription(data.description);
    await this.selectGenre(data.genre);
    await this.fillTargetAudience(data.targetAudience);

    console.log('✅ Book form filled with test data');
  }

  /**
   * Submit the form
   */
  async submit(): Promise<void> {
    await this.page.click('button[type="submit"]');
  }

  /**
   * Submit form and wait for API response
   */
  async submitAndWaitForAPI(): Promise<{ status: number; bookId?: string }> {
    const [response] = await Promise.all([
      this.page.waitForResponse(
        resp => resp.url().includes('/api/v1/books') && (resp.status() === 201 || resp.status() === 200),
        { timeout: 10000 }
      ),
      this.submit()
    ]);

    const status = response.status();

    // Extract book ID from URL after redirect
    await this.page.waitForURL(/\/dashboard\/books\/[a-z0-9-]+$/, { timeout: 5000 });
    const bookId = this.page.url().split('/').pop();

    console.log(`✅ Book created with ID: ${bookId}, status: ${status}`);

    return { status, bookId };
  }

  /**
   * Verify form is visible
   */
  async verifyFormVisible(): Promise<void> {
    await expect(this.form()).toBeVisible();
  }

  /**
   * Verify form background is NOT transparent
   */
  async verifyFormNotTransparent(): Promise<void> {
    const formBg = await this.form().evaluate(el =>
      window.getComputedStyle(el).backgroundColor
    );

    // Background should not be transparent or rgba(0,0,0,0)
    expect(formBg).not.toBe('transparent');
    expect(formBg).not.toBe('rgba(0, 0, 0, 0)');

    console.log('✅ Form background is visible (not transparent)');
  }

  /**
   * Verify request includes Authorization header
   */
  async verifyAuthHeader(requestUrl: string): Promise<void> {
    const request = await this.page.waitForRequest(
      req => req.url().includes(requestUrl),
      { timeout: 5000 }
    );

    const headers = request.headers();
    expect(headers['authorization']).toContain('Bearer');

    console.log('✅ Authorization header present in request');
  }

  /**
   * Verify redirect to book detail page
   */
  async verifyRedirectToBookDetail(): Promise<string> {
    await this.page.waitForURL(/\/dashboard\/books\/[a-z0-9-]+$/);

    const bookId = this.page.url().split('/').pop() || '';
    expect(bookId).toBeTruthy();

    console.log(`✅ Redirected to book detail page: ${bookId}`);

    return bookId;
  }

  /**
   * Click edit button (on book detail page)
   */
  async clickEdit(): Promise<void> {
    await this.page.click('button:has-text("Edit")');
  }

  /**
   * Click save button (after editing)
   */
  async clickSave(): Promise<void> {
    await this.page.click('button:has-text("Save")');
    await this.page.waitForTimeout(1000); // Wait for save to complete
  }

  /**
   * Verify title is displayed
   */
  async verifyTitleDisplayed(title: string): Promise<void> {
    await expect(this.page.locator('h1')).toContainText(title);
    console.log(`✅ Title "${title}" is displayed`);
  }

  /**
   * Update book title
   */
  async updateTitle(newTitle: string): Promise<void> {
    await this.clickEdit();
    await this.fillTitle(newTitle);
    await this.clickSave();
    await this.verifyTitleDisplayed(newTitle);

    console.log(`✅ Book title updated to: ${newTitle}`);
  }
}
