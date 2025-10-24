/**
 * Summary Page Object
 *
 * Handles book summary form and voice input interactions.
 */

import { Page, expect, Locator } from '@playwright/test';

export class SummaryPage {
  constructor(private page: Page) {}

  /**
   * Navigate to summary page for a book
   */
  async goto(bookId: string): Promise<void> {
    await this.page.goto(`/dashboard/books/${bookId}/summary`);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Get summary textarea
   */
  summaryField(): Locator {
    return this.page.locator('textarea[name="summary"]');
  }

  /**
   * Get character counter
   */
  characterCounter(): Locator {
    return this.page.locator('[data-testid="character-counter"]');
  }

  /**
   * Get voice input button
   */
  voiceInputButton(): Locator {
    return this.page.locator('[data-testid="voice-input-button"]');
  }

  /**
   * Fill summary content
   */
  async fillSummary(content: string): Promise<void> {
    await this.summaryField().fill(content);
    console.log(`✅ Summary filled (${content.length} characters)`);
  }

  /**
   * Verify character counter shows correct count
   */
  async verifyCharacterCount(expectedCount: number): Promise<void> {
    const counterText = await this.characterCounter().textContent();
    expect(counterText).toContain(`${expectedCount}`);
    console.log(`✅ Character counter shows ${expectedCount} characters`);
  }

  /**
   * Verify minimum requirement message
   */
  async verifyMinimumRequirement(): Promise<void> {
    await expect(this.page.locator('text=Minimum: 30 characters')).toBeVisible();
  }

  /**
   * Click voice input button
   */
  async clickVoiceInput(): Promise<void> {
    await this.voiceInputButton().click();
  }

  /**
   * Verify voice input button is visible
   */
  async verifyVoiceInputVisible(): Promise<void> {
    await expect(this.voiceInputButton()).toBeVisible();
    console.log('✅ Voice input button is visible');
  }

  /**
   * Click continue to TOC generation
   */
  async clickContinueToTOC(): Promise<void> {
    await this.page.click('button:has-text("Continue to TOC Generation")');
    await this.page.waitForURL(/\/generate-toc$/);
    console.log('✅ Navigated to TOC generation');
  }

  /**
   * Verify no validation errors
   */
  async verifyNoValidationErrors(): Promise<void> {
    const errorMessages = this.page.locator('[role="alert"]');
    await expect(errorMessages).toHaveCount(0);
  }

  /**
   * Complete summary form with test data
   */
  async completeSummary(content: string): Promise<void> {
    await this.fillSummary(content);
    await this.verifyCharacterCount(content.length);
    await this.verifyNoValidationErrors();
    await this.clickContinueToTOC();
  }
}
