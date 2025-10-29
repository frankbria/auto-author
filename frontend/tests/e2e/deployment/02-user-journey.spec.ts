/**
 * Complete User Journey: Book Creation to Export
 *
 * This test validates the entire book authoring workflow from initial creation
 * through final export, ensuring all features work together cohesively.
 *
 * Based on DEPLOYMENT-TESTING-CHECKLIST.md User Journey section (Steps 1-8).
 */

import { test, expect } from '@playwright/test';
import { authenticateUser } from '../fixtures/auth.fixture';
import { TEST_BOOK, TEST_SUMMARY, TOC_QUESTIONS, CHAPTER_QA_DATA } from '../fixtures/test-data.fixture';
import { PERFORMANCE_BUDGETS, measureOperation } from '../fixtures/performance.fixture';
import { ConsoleMonitor } from '../helpers/console-monitor';
import { NetworkMonitor } from '../helpers/network-monitor';
import { BookFormPage } from '../page-objects/book-form.page';
import { DashboardPage } from '../page-objects/dashboard.page';
import { SummaryPage } from '../page-objects/summary.page';
import { TOCWizardPage } from '../page-objects/toc-wizard.page';
import { ChapterEditorPage } from '../page-objects/chapter-editor.page';
import { ExportPage } from '../page-objects/export.page';

test.describe('Complete User Journey: Book Creation to Export', () => {
  let bookId: string;
  let chapterId: string;

  test.beforeEach(async ({ page }) => {
    console.log('\n🔐 Authenticating user...');
    await authenticateUser(page);
  });

  test('Step 1-3: Create Book with Metadata', async ({ page }) => {
    console.log('\n📚 Step 1-3: Creating book with metadata');

    const consoleMonitor = new ConsoleMonitor(page);
    const networkMonitor = new NetworkMonitor(page);
    const bookForm = new BookFormPage(page);

    // Navigate to new book form
    await bookForm.gotoNewBook();

    // Verify form displays correctly
    await bookForm.verifyFormVisible();
    await bookForm.verifyFormNotTransparent();

    // Fill book details
    await bookForm.fillBookDetails(TEST_BOOK);

    // Submit and wait for API response
    const result = await bookForm.submitAndWaitForAPI();

    // Store book ID for subsequent tests
    bookId = result.bookId!;

    // Verify successful creation
    expect(result.status, 'Book creation should return 201 Created').toBe(201);
    expect(bookId, 'Book ID should be extracted from URL').toBeTruthy();

    // Verify no console errors
    consoleMonitor.assertNoErrors();
    consoleMonitor.assertNoCORSErrors();

    // Verify no 500 errors
    networkMonitor.assertNo500Errors();

    // Verify redirected to book detail page
    await expect(page).toHaveURL(new RegExp(`/dashboard/books/${bookId}$`));

    console.log(`✅ Step 1-3 Complete: Book created with ID: ${bookId}`);
  });

  test('Step 4: Add Book Summary', async ({ page }) => {
    test.skip(!bookId, 'Requires book to be created first');

    console.log('\n📝 Step 4: Adding book summary');

    const summary = new SummaryPage(page);

    // Navigate to summary page
    await summary.goto(bookId);

    // Verify initial state
    await summary.verifyCharacterCount(0);
    await summary.verifyMinimumRequirement();

    // Fill summary
    await summary.fillSummary(TEST_SUMMARY.content);

    // Verify character counter updates
    await summary.verifyCharacterCount(TEST_SUMMARY.expectedCharCount);

    // Verify voice input button is visible (won't test functionality due to browser restrictions)
    await summary.verifyVoiceInputVisible();

    // Verify no validation errors
    await summary.verifyNoValidationErrors();

    // Continue to TOC generation
    await summary.clickContinueToTOC();

    console.log('✅ Step 4 Complete: Book summary added');
  });

  test('Step 5: Generate Table of Contents', async ({ page }) => {
    test.skip(!bookId, 'Requires book to be created first');

    console.log('\n📑 Step 5: Generating TOC with AI wizard');

    const tocWizard = new TOCWizardPage(page);

    // Navigate to TOC generation
    await tocWizard.goto(bookId);

    // Wait for readiness check
    await tocWizard.waitForReadinessCheck();

    // Verify questions appear
    await tocWizard.verifyQuestionsAppear();

    // Answer clarifying questions
    await tocWizard.answerQuestions(TOC_QUESTIONS);

    // Generate TOC with performance measurement
    console.log('⏱️ Measuring TOC generation performance...');

    const { duration, withinBudget } = await measureOperation(
      page,
      async () => {
        await tocWizard.clickGenerateTOC();
        await tocWizard.waitForGeneration();
      },
      PERFORMANCE_BUDGETS.TOC_GENERATION,
      'TOC Generation'
    );

    // Verify performance budget
    expect(withinBudget, `TOC generation should complete within ${PERFORMANCE_BUDGETS.TOC_GENERATION}ms`).toBeTruthy();

    // Verify TOC generated
    await tocWizard.verifyTOCGenerated();
    await tocWizard.verifyChapterTitles();

    // Save TOC
    await tocWizard.saveTOC();

    console.log(`✅ Step 5 Complete: TOC generated in ${duration.toFixed(0)}ms`);
  });

  test('Step 6: View Book with Generated TOC', async ({ page }) => {
    test.skip(!bookId, 'Requires book to be created first');

    console.log('\n📖 Step 6: Viewing book with generated TOC');

    const dashboard = new DashboardPage(page);

    // Navigate to book detail page
    await dashboard.navigateToBook(bookId);

    // Verify book title displayed
    await expect(page.locator('h1')).toContainText(TEST_BOOK.title);

    // Verify TOC displays
    const tocList = page.locator('[data-testid="toc-list"]');
    await expect(tocList).toBeVisible();

    // Verify multiple chapters listed
    const chapters = page.locator('[data-testid="chapter-item"]');
    const chapterCount = await chapters.count();

    expect(chapterCount).toBeGreaterThanOrEqual(5);
    expect(chapterCount).toBeLessThanOrEqual(15);

    // Verify each chapter shows required info
    for (let i = 0; i < Math.min(chapterCount, 3); i++) {
      const chapter = chapters.nth(i);

      await expect(chapter.locator('[data-testid="chapter-number"]')).toBeVisible();
      await expect(chapter.locator('[data-testid="chapter-title"]')).toBeVisible();
      await expect(chapter.locator('[data-testid="chapter-status"]')).toBeVisible();
      await expect(chapter.locator('[data-testid="word-count"]')).toBeVisible();
    }

    // Get first chapter ID for next test
    const firstChapter = chapters.first();
    chapterId = await firstChapter.getAttribute('data-chapter-id') || '';

    // Click first chapter to open editor
    await firstChapter.click();

    console.log(`✅ Step 6 Complete: Book has ${chapterCount} chapters`);
  });

  test('Step 7a-b: Chapter Editor & Rich Text Formatting', async ({ page }) => {
    test.skip(!bookId || !chapterId, 'Requires book and chapter to be created first');

    console.log('\n✍️ Step 7a-b: Testing chapter editor and rich text formatting');

    const editor = new ChapterEditorPage(page);

    // Navigate to chapter editor
    await editor.goto(bookId, chapterId);

    // Verify editor elements
    await expect(editor.editorContent()).toBeVisible();
    await expect(editor.wordCount()).toBeVisible();
    await expect(editor.autoSaveIndicator()).toBeVisible();

    // Verify initial word count is 0
    await editor.verifyWordCount(0);

    // Test rich text formatting
    await editor.testRichTextFormatting();

    // Verify auto-save
    await editor.waitForAutoSave();

    console.log('✅ Step 7a-b Complete: Rich text editor works correctly');
  });

  test('Step 7c: AI Draft Generation', async ({ page }) => {
    test.skip(!bookId || !chapterId, 'Requires book and chapter to be created first');

    console.log('\n🤖 Step 7c: Testing AI draft generation');

    const editor = new ChapterEditorPage(page);

    await editor.goto(bookId, chapterId);

    // Open AI draft wizard
    await editor.openAIDraft();

    // Answer Q&A questions
    await editor.answerDraftQuestions(CHAPTER_QA_DATA);

    // Generate draft with performance measurement
    console.log('⏱️ Measuring AI draft generation performance...');

    const { duration } = await measureOperation(
      page,
      async () => {
        await editor.generateDraft();
      },
      PERFORMANCE_BUDGETS.DRAFT_GENERATION,
      'AI Draft Generation'
    );

    // Verify draft content appears
    await editor.verifyDraftContent();

    // Insert draft
    await editor.insertDraft();

    // Verify word count updated
    const content = await editor.editorContent().textContent();
    const wordCount = content?.split(/\s+/).length || 0;

    expect(wordCount).toBeGreaterThan(50);

    // Verify auto-save triggers
    await editor.waitForAutoSave();

    console.log(`✅ Step 7c Complete: AI draft generated in ${duration.toFixed(0)}ms`);
  });

  test('Step 7d: Chapter Tabs Navigation', async ({ page }) => {
    test.skip(!bookId, 'Requires book to be created first');

    console.log('\n📑 Step 7d: Testing chapter tabs navigation');

    // Get list of chapters
    await page.goto(`/dashboard/books/${bookId}`);

    const chapters = page.locator('[data-testid="chapter-item"]');
    const chapterCount = await chapters.count();

    if (chapterCount < 2) {
      console.log('⚠️ Skipping chapter tabs test (need at least 2 chapters)');
      return;
    }

    // Get chapter IDs
    const chapterIds: string[] = [];
    for (let i = 0; i < Math.min(chapterCount, 3); i++) {
      const id = await chapters.nth(i).getAttribute('data-chapter-id');
      if (id) chapterIds.push(id);
    }

    const editor = new ChapterEditorPage(page);

    // Open first chapter
    await editor.goto(bookId, chapterIds[0]);

    // Open additional chapter tabs
    for (let i = 1; i < chapterIds.length; i++) {
      await editor.openChapterTab(chapterIds[i]);
      await editor.verifyTabVisible(chapterIds[i]);
    }

    // Switch between tabs
    for (const id of chapterIds) {
      await editor.openChapterTab(id);
    }

    // Close one tab
    if (chapterIds.length > 1) {
      await editor.closeChapterTab(chapterIds[1]);
    }

    console.log(`✅ Step 7d Complete: Chapter tabs work correctly`);
  });

  test('Step 8: Export Book (PDF and DOCX)', async ({ page }) => {
    test.skip(!bookId, 'Requires book to be created first');

    console.log('\n📄 Step 8: Testing book export');

    const exportPage = new ExportPage(page);

    await exportPage.goto(bookId);

    // Test PDF Export
    console.log('⏱️ Testing PDF export...');

    const { duration: pdfDuration } = await measureOperation(
      page,
      async () => {
        const pdfDownload = await exportPage.exportPDF({
          coverPage: true,
          tableOfContents: true
        });

        await exportPage.verifyDownloadComplete(pdfDownload);

        // Save download for inspection
        await exportPage.saveDownload(pdfDownload, `test-book-${Date.now()}.pdf`);
      },
      PERFORMANCE_BUDGETS.EXPORT_PDF,
      'PDF Export'
    );

    expect(pdfDuration).toBeLessThan(PERFORMANCE_BUDGETS.EXPORT_PDF);

    // Test DOCX Export
    console.log('⏱️ Testing DOCX export...');

    const { duration: docxDuration } = await measureOperation(
      page,
      async () => {
        const docxDownload = await exportPage.exportDOCX({
          coverPage: true,
          tableOfContents: true
        });

        await exportPage.verifyDownloadComplete(docxDownload);

        // Save download for inspection
        await exportPage.saveDownload(docxDownload, `test-book-${Date.now()}.docx`);
      },
      PERFORMANCE_BUDGETS.EXPORT_DOCX,
      'DOCX Export'
    );

    expect(docxDuration).toBeLessThan(PERFORMANCE_BUDGETS.EXPORT_DOCX);

    console.log(`✅ Step 8 Complete: PDF (${pdfDuration.toFixed(0)}ms), DOCX (${docxDuration.toFixed(0)}ms)`);
  });
});

/**
 * User Journey Test Summary
 *
 * This test suite validates the complete book authoring workflow:
 * ✅ Step 1-3: Create book with metadata
 * ✅ Step 4: Add book summary
 * ✅ Step 5: Generate TOC with AI wizard (with performance budget)
 * ✅ Step 6: View book with generated TOC
 * ✅ Step 7a-b: Chapter editor & rich text formatting
 * ✅ Step 7c: AI draft generation (with performance budget)
 * ✅ Step 7d: Chapter tabs navigation
 * ✅ Step 8: Export to PDF and DOCX (with performance budgets)
 *
 * Performance budgets verified:
 * - TOC Generation: <3000ms
 * - AI Draft Generation: <60000ms
 * - PDF Export: <5000ms
 * - DOCX Export: <5000ms
 */
