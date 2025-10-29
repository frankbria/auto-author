/**
 * Chapter Editor Page Object
 *
 * Handles rich text editor, AI draft generation, and chapter tabs.
 */

import { Page, expect, Locator } from '@playwright/test';
import { ChapterQAData } from '../fixtures/test-data.fixture';

export class ChapterEditorPage {
  constructor(private page: Page) {}

  /**
   * Navigate to chapter editor
   */
  async goto(bookId: string, chapterId: string): Promise<void> {
    await this.page.goto(`/dashboard/books/${bookId}/chapters/${chapterId}`);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Get editor content area
   */
  editorContent(): Locator {
    return this.page.locator('[data-testid="chapter-editor"]');
  }

  /**
   * Get word count display
   */
  wordCount(): Locator {
    return this.page.locator('[data-testid="word-count"]');
  }

  /**
   * Get auto-save indicator
   */
  autoSaveIndicator(): Locator {
    return this.page.locator('[data-testid="auto-save-status"]');
  }

  /**
   * Type content in editor
   */
  async typeContent(text: string): Promise<void> {
    await this.editorContent().click();
    await this.editorContent().fill(text);
    console.log(`✅ Typed content: ${text.substring(0, 50)}...`);
  }

  /**
   * Select all text in editor
   */
  async selectAllText(): Promise<void> {
    await this.editorContent().click();
    await this.page.keyboard.press('Control+A');
  }

  /**
   * Click Bold button
   */
  async clickBold(): Promise<void> {
    await this.page.click('[data-testid="toolbar-bold"]');
  }

  /**
   * Click Italic button
   */
  async clickItalic(): Promise<void> {
    await this.page.click('[data-testid="toolbar-italic"]');
  }

  /**
   * Select heading level
   */
  async selectHeading(level: 2 | 3 | 4): Promise<void> {
    await this.page.click('[data-testid="toolbar-heading"]');
    await this.page.click(`[data-testid="heading-${level}"]`);
  }

  /**
   * Verify auto-save shows "Saving..."
   */
  async verifySaving(): Promise<void> {
    await expect(this.autoSaveIndicator()).toContainText('Saving', { timeout: 5000 });
  }

  /**
   * Verify auto-save shows "Saved"
   */
  async verifySaved(): Promise<void> {
    await expect(this.autoSaveIndicator()).toContainText('Saved', { timeout: 3000 });
    console.log('✅ Auto-save complete');
  }

  /**
   * Wait for auto-save cycle (3s debounce + save)
   */
  async waitForAutoSave(): Promise<void> {
    await this.page.waitForTimeout(3000); // Debounce
    await this.verifySaving();
    await this.verifySaved();
  }

  /**
   * Verify word count
   */
  async verifyWordCount(expectedWords: number): Promise<void> {
    const wordCountText = await this.wordCount().textContent();
    expect(wordCountText).toContain(`${expectedWords}`);
    console.log(`✅ Word count: ${expectedWords}`);
  }

  /**
   * Open AI draft generation wizard
   */
  async openAIDraft(): Promise<void> {
    await this.page.click('[data-testid="generate-draft-button"]');
    await expect(this.page.locator('[data-testid="draft-wizard"]')).toBeVisible();
    console.log('✅ AI draft wizard opened');
  }

  /**
   * Answer Q&A questions for draft generation
   */
  async answerDraftQuestions(qaData: ChapterQAData[]): Promise<void> {
    for (let i = 0; i < qaData.length; i++) {
      const field = this.page.locator(`[data-testid="draft-question-${i}"]`);
      await field.fill(qaData[i].answer);
    }

    console.log(`✅ Answered ${qaData.length} draft questions`);
  }

  /**
   * Generate AI draft
   */
  async generateDraft(timeoutMs: number = 60000): Promise<void> {
    await this.page.click('button:has-text("Generate Draft")');

    // Wait for loading indicator
    const loadingIndicator = this.page.locator('[data-testid="generating-draft"]');
    await expect(loadingIndicator).toBeVisible({ timeout: 5000 });

    // Wait for generation to complete
    await expect(loadingIndicator).not.toBeVisible({ timeout: timeoutMs });

    console.log('✅ AI draft generated');
  }

  /**
   * Verify draft content appears
   */
  async verifyDraftContent(): Promise<void> {
    const content = await this.editorContent().textContent();
    expect(content).toBeTruthy();
    expect(content!.length).toBeGreaterThan(200);

    console.log(`✅ Draft content inserted (${content!.length} characters)`);
  }

  /**
   * Insert draft into editor
   */
  async insertDraft(): Promise<void> {
    await this.page.click('button:has-text("Insert Draft")');
    await this.verifyDraftContent();
  }

  /**
   * Open chapter tab
   */
  async openChapterTab(chapterId: string): Promise<void> {
    await this.page.click(`[data-testid="chapter-tab-${chapterId}"]`);
  }

  /**
   * Close chapter tab
   */
  async closeChapterTab(chapterId: string): Promise<void> {
    await this.page.click(`[data-testid="close-tab-${chapterId}"]`);
  }

  /**
   * Verify chapter tab is visible
   */
  async verifyTabVisible(chapterId: string): Promise<void> {
    await expect(this.page.locator(`[data-testid="chapter-tab-${chapterId}"]`)).toBeVisible();
  }

  /**
   * Verify unsaved changes indicator
   */
  async verifyUnsavedIndicator(): Promise<void> {
    await expect(this.page.locator('[data-testid="unsaved-indicator"]')).toBeVisible();
  }

  /**
   * Press keyboard shortcut
   */
  async pressShortcut(key: string): Promise<void> {
    await this.page.keyboard.press(key);
  }

  /**
   * Test rich text formatting
   */
  async testRichTextFormatting(): Promise<void> {
    // Type test text
    await this.typeContent('This is a test paragraph about urban gardening.');

    // Select text and make bold
    await this.selectAllText();
    await this.clickBold();

    // Verify bold applied
    const bold = this.editorContent().locator('strong');
    await expect(bold).toBeVisible();

    // Apply italic
    await this.clickItalic();

    // Verify italic applied
    const italic = this.editorContent().locator('em');
    await expect(italic).toBeVisible();

    // Apply heading
    await this.selectHeading(2);

    // Verify heading applied
    const heading = this.editorContent().locator('h2');
    await expect(heading).toBeVisible();

    console.log('✅ Rich text formatting test complete');
  }
}
