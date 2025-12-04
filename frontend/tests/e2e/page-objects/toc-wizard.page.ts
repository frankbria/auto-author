/**
 * TOC Wizard Page Object
 *
 * Handles Table of Contents generation wizard with AI.
 */

import { Page, expect, Locator } from '@playwright/test';
import { TOCQuestion } from '../fixtures/test-data.fixture';

export class TOCWizardPage {
  constructor(private page: Page) {}

  /**
   * Navigate to TOC generation page
   */
  async goto(bookId: string): Promise<void> {
    await this.page.goto(`/dashboard/books/${bookId}/generate-toc`);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Wait for readiness check to complete (by checking for heading text)
   */
  async waitForReadinessCheck(): Promise<void> {
    // Wait for "Analyzing Your Summary" to appear
    const analyzing = this.page.locator('text=Analyzing Your Summary');
    await expect(analyzing).toBeVisible({ timeout: 5000 });

    // Wait for analysis to complete (heading disappears)
    await expect(analyzing).not.toBeVisible({ timeout: 15000 });

    console.log('✅ Summary readiness check complete');
  }

  /**
   * Verify "Not Ready" message appears (if summary is too short)
   */
  async verifyNotReadyMessage(): Promise<void> {
    await expect(this.page.locator('text=Not Ready')).toBeVisible();
  }

  /**
   * Verify proceeds to questions automatically (check for Clarifying Questions heading)
   */
  async verifyQuestionsAppear(): Promise<void> {
    await expect(this.page.locator('text=Clarifying Questions')).toBeVisible({ timeout: 10000 });

    // Verify at least one question field is visible
    const questionField = this.page.locator('[data-testid^="toc-question-"]').first();
    await expect(questionField).toBeVisible();

    console.log('✅ Clarifying questions appeared');
  }

  /**
   * Answer a single clarifying question (questions shown one at a time)
   */
  async answerQuestion(index: number, answer: string): Promise<void> {
    const questionField = this.page.locator(`[data-testid="toc-question-${index}"]`);
    await questionField.fill(answer);
  }

  /**
   * Answer all clarifying questions (navigate through them one by one)
   */
  async answerQuestions(questions: TOCQuestion[]): Promise<void> {
    for (let i = 0; i < questions.length; i++) {
      // Answer current question
      await this.answerQuestion(i, questions[i].answer);

      // Click Next button (except on last question)
      if (i < questions.length - 1) {
        await this.page.click('button:has-text("Next")');
        await this.page.waitForTimeout(500); // Brief wait for transition
      }
    }

    console.log(`✅ Answered ${questions.length} clarifying questions`);
  }

  /**
   * Click "Generate Table of Contents" button (shown on last question)
   */
  async clickGenerateTOC(): Promise<void> {
    await this.page.click('button:has-text("Generate Table of Contents")');
  }

  /**
   * Wait for TOC generation to complete (look for "Generating TOC..." text)
   */
  async waitForGeneration(timeoutMs: number = 60000): Promise<void> {
    // Wait for "Generating TOC..." to appear
    const generating = this.page.locator('text=Generating TOC...');
    await expect(generating).toBeVisible({ timeout: 5000 });

    // Wait for generation to complete (text disappears)
    await expect(generating).not.toBeVisible({ timeout: timeoutMs });

    console.log('✅ TOC generation complete');
  }

  /**
   * Generate TOC (click button and wait for completion)
   */
  async generateTOC(timeoutMs: number = 60000): Promise<void> {
    await this.clickGenerateTOC();
    await this.waitForGeneration(timeoutMs);
  }

  /**
   * Verify generated TOC appears (check for heading and TOC container)
   */
  async verifyTOCGenerated(): Promise<void> {
    // Wait for "Your Generated Table of Contents" heading
    await expect(this.page.locator('text=Your Generated Table of Contents')).toBeVisible();

    // Verify TOC container is visible
    const tocList = this.page.locator('[data-testid="generated-toc"]');
    await expect(tocList).toBeVisible();

    // Count chapters
    const chapters = this.page.locator('[data-testid="chapter-item"]');
    const chapterCount = await chapters.count();

    expect(chapterCount).toBeGreaterThan(0);

    console.log(`✅ Generated TOC with ${chapterCount} chapters`);
  }

  /**
   * Verify each chapter has a title
   */
  async verifyChapterTitles(): Promise<void> {
    const chapters = this.page.locator('[data-testid="chapter-item"]');
    const count = await chapters.count();

    for (let i = 0; i < count; i++) {
      const chapter = chapters.nth(i);
      const title = await chapter.locator('[data-testid="chapter-title"]').textContent();
      expect(title).toBeTruthy();
      expect(title!.length).toBeGreaterThan(0);
    }

    console.log('✅ All chapters have titles');
  }

  /**
   * Edit a chapter title
   */
  async editChapterTitle(index: number, newTitle: string): Promise<void> {
    const chapter = this.page.locator('[data-testid="chapter-item"]').nth(index);
    await chapter.locator('[data-testid="edit-chapter"]').click();

    const titleInput = this.page.locator('[data-testid="chapter-title-input"]');
    await titleInput.fill(newTitle);

    await this.page.click('button:has-text("Save")');

    console.log(`✅ Edited chapter ${index} title to: ${newTitle}`);
  }

  /**
   * Click "Accept & Continue" button to save TOC
   */
  async saveTOC(): Promise<void> {
    await this.page.click('button:has-text("Accept & Continue")');
    await this.page.waitForURL(/\/dashboard\/books\/[a-z0-9-]+$/);

    console.log('✅ TOC saved and redirected to book detail');
  }

  /**
   * Complete full TOC generation workflow
   */
  async completeTOCGeneration(questions: TOCQuestion[], timeoutMs: number = 60000): Promise<void> {
    await this.waitForReadinessCheck();
    await this.verifyQuestionsAppear();
    await this.answerQuestions(questions);
    await this.generateTOC(timeoutMs);
    await this.verifyTOCGenerated();
    await this.verifyChapterTitles();
    await this.saveTOC();

    console.log('✅ TOC generation workflow complete');
  }
}
