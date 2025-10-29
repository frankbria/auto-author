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
   * Wait for readiness check to complete
   */
  async waitForReadinessCheck(): Promise<void> {
    // Wait for loading indicator to appear and disappear
    const loadingIndicator = this.page.locator('[data-testid="loading-indicator"]');

    await expect(loadingIndicator).toBeVisible({ timeout: 5000 });
    await expect(loadingIndicator).not.toBeVisible({ timeout: 10000 });

    console.log('✅ Summary readiness check complete');
  }

  /**
   * Verify "Not Ready" message appears (if summary is too short)
   */
  async verifyNotReadyMessage(): Promise<void> {
    await expect(this.page.locator('text=Not Ready')).toBeVisible();
  }

  /**
   * Verify proceeds to questions automatically
   */
  async verifyQuestionsAppear(): Promise<void> {
    const questions = this.page.locator('[data-testid="toc-question"]');
    const questionCount = await questions.count();

    expect(questionCount).toBeGreaterThanOrEqual(5);
    expect(questionCount).toBeLessThanOrEqual(10);

    console.log(`✅ ${questionCount} clarifying questions appeared`);
  }

  /**
   * Answer a single clarifying question
   */
  async answerQuestion(index: number, answer: string): Promise<void> {
    const questionField = this.page.locator(`[data-testid="toc-question-${index}"]`);
    await questionField.fill(answer);
  }

  /**
   * Answer all clarifying questions
   */
  async answerQuestions(questions: TOCQuestion[]): Promise<void> {
    for (let i = 0; i < questions.length; i++) {
      await this.answerQuestion(i, questions[i].answer);
    }

    console.log(`✅ Answered ${questions.length} clarifying questions`);
  }

  /**
   * Click "Generate TOC" button
   */
  async clickGenerateTOC(): Promise<void> {
    await this.page.click('button:has-text("Generate TOC")');
  }

  /**
   * Wait for TOC generation to complete
   */
  async waitForGeneration(timeoutMs: number = 60000): Promise<void> {
    // Wait for loading indicator
    const loadingIndicator = this.page.locator('[data-testid="generating-toc"]');
    await expect(loadingIndicator).toBeVisible({ timeout: 5000 });

    // Wait for generation to complete
    await expect(loadingIndicator).not.toBeVisible({ timeout: timeoutMs });

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
   * Verify generated TOC appears
   */
  async verifyTOCGenerated(): Promise<void> {
    const tocList = this.page.locator('[data-testid="generated-toc"]');
    await expect(tocList).toBeVisible();

    const chapters = this.page.locator('[data-testid="chapter-item"]');
    const chapterCount = await chapters.count();

    expect(chapterCount).toBeGreaterThanOrEqual(5);
    expect(chapterCount).toBeLessThanOrEqual(15);

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
   * Click "Save TOC" or "Confirm" button
   */
  async saveTOC(): Promise<void> {
    await this.page.click('button:has-text("Save TOC")');
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
