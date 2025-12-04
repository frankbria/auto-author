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
   * Get editor content area (TipTap ProseMirror editor)
   */
  editorContent(): Locator {
    return this.page.locator('.tiptap-editor .ProseMirror');
  }

  /**
   * Get word count display (character count in footer)
   */
  wordCount(): Locator {
    return this.page.locator('text=/\\d+ characters/');
  }

  /**
   * Get auto-save indicator (shows Saving... or Saved status)
   */
  autoSaveIndicator(): Locator {
    return this.page.locator('text=/Saving|Saved|Not saved yet/');
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
   * Click Bold button (by title attribute)
   */
  async clickBold(): Promise<void> {
    await this.page.click('button[title="Bold"]');
  }

  /**
   * Click Italic button (by title attribute)
   */
  async clickItalic(): Promise<void> {
    await this.page.click('button[title="Italic"]');
  }

  /**
   * Select heading level (by title attribute)
   */
  async selectHeading(level: 1 | 2 | 3): Promise<void> {
    await this.page.click(`button[title="Heading ${level}"]`);
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
    const { waitForAutoSave } = await import('../helpers/condition-waiter');
    await waitForAutoSave(this.page, { timeout: 10000 });
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
   * Open AI draft generation wizard (by button text)
   */
  async openAIDraft(): Promise<void> {
    await this.page.click('button:has-text("Generate AI Draft")');
    await expect(this.page.locator('role=dialog')).toBeVisible();
    console.log('✅ AI draft wizard opened');
  }

  /**
   * Answer Q&A questions for draft generation (use textarea placeholders)
   */
  async answerDraftQuestions(qaData: ChapterQAData[]): Promise<void> {
    // Find all answer textareas by placeholder
    const answerFields = this.page.locator('textarea[placeholder="Your answer..."]');
    const count = await answerFields.count();

    for (let i = 0; i < Math.min(qaData.length, count); i++) {
      await answerFields.nth(i).fill(qaData[i].answer);
    }

    console.log(`✅ Answered ${qaData.length} draft questions`);
  }

  /**
   * Generate AI draft (wait for LoadingStateManager component)
   */
  async generateDraft(timeoutMs: number = 60000): Promise<void> {
    await this.page.click('button:has-text("Generate Draft")');

    // Wait for loading state to appear (shows "Generating...")
    await expect(this.page.locator('text=Generating...')).toBeVisible({ timeout: 5000 });

    // Wait for generation to complete (loading disappears)
    await expect(this.page.locator('text=Generating...')).not.toBeVisible({ timeout: timeoutMs });

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
   * Insert draft into editor (click "Use This Draft" button)
   */
  async insertDraft(): Promise<void> {
    await this.page.click('button:has-text("Use This Draft")');
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
