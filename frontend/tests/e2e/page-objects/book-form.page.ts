/**
 * Book Form Page Object
 *
 * Handles book creation and editing forms.
 */

import { Page, expect, Locator } from '@playwright/test';
import { BookData } from '../fixtures/test-data.fixture';
import { GENRE_OPTIONS, TARGET_AUDIENCE_OPTIONS } from '../../../src/lib/constants/book-metadata';

export class BookFormPage {
  constructor(private page: Page) {}

  /**
   * Open the BookCreationWizard modal from the dashboard — the canonical
   * create flow (the /dashboard/new-book page was removed in #205).
   */
  async gotoNewBook(): Promise<void> {
    await this.page.goto('/dashboard');
    await this.page.waitForLoadState('networkidle');
    await this.page.getByRole('button', { name: 'Create New Book' }).first().click();
    await expect(this.page.getByRole('dialog')).toBeVisible();
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
    await this.page.fill('textarea[name="description"]', description);
  }

  /**
   * Select genre from the wizard's Radix select (accepts a canonical value
   * slug or label; unknown values fall back to 'Other').
   */
  async selectGenre(genre: string): Promise<void> {
    const label =
      GENRE_OPTIONS.find(o => o.value === genre || o.label === genre)?.label ?? 'Other';
    await this.page.getByRole('dialog').getByLabel(/genre/i).click();
    await this.page.getByRole('option', { name: label }).click();
  }

  /**
   * Select target audience from the wizard's Radix select (fixed options —
   * free-text audiences fall back to 'General').
   */
  async fillTargetAudience(targetAudience: string): Promise<void> {
    const label =
      TARGET_AUDIENCE_OPTIONS.find(o => o.value === targetAudience || o.label === targetAudience)
        ?.label ?? 'General';
    await this.page.getByRole('dialog').getByLabel(/target audience/i).click();
    await this.page.getByRole('option', { name: label }).click();
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

    // Extract book ID from response body
    const responseBody = await response.json();
    const bookId = responseBody.id;

    // Wait for redirect to book detail page (the dashboard's onSuccess
    // handler pushes after a 1.5s success-toast delay)
    await this.page.waitForURL(`/dashboard/books/${bookId}`, { timeout: 10000 });

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
