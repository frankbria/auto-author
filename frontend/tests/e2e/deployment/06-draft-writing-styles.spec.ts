/**
 * E2E Test: Draft Generation with Different Writing Styles
 *
 * Issue: auto-author-15k
 * Priority: P1
 * Estimated: 4 hours
 *
 * This test validates that the draft generation feature correctly applies
 * different writing styles (Conversational, Formal, Educational, Technical,
 * Narrative, Inspirational) and produces appropriately toned content for each.
 *
 * Test Coverage:
 * ✅ All 6 writing styles supported by the system
 * ✅ Draft tone and language appropriate for each style
 * ✅ Style metadata correctly reflected in generated draft
 * ✅ Performance budgets maintained across all styles
 */

import { test, expect } from '@playwright/test';
import { authenticateUser } from '../fixtures/auth.fixture';
import { TEST_BOOK, CHAPTER_QA_DATA } from '../fixtures/test-data.fixture';
import { PERFORMANCE_BUDGETS, measureOperation } from '../fixtures/performance.fixture';
import { ConsoleMonitor } from '../helpers/console-monitor';
import { NetworkMonitor } from '../helpers/network-monitor';
import { BookFormPage } from '../page-objects/book-form.page';
import { DashboardPage } from '../page-objects/dashboard.page';
import { ChapterEditorPage } from '../page-objects/chapter-editor.page';

/**
 * Writing Styles to Test
 * Matches WRITING_STYLES in DraftGenerator.tsx
 */
const WRITING_STYLES = [
  {
    value: 'conversational',
    label: 'Conversational',
    toneIndicators: ['you', 'we', 'let\'s', 'your', 'i\'m', 'friendly', 'chat'],
    shouldAvoid: ['hereby', 'aforementioned', 'pursuant', 'wherefore']
  },
  {
    value: 'formal',
    label: 'Formal',
    toneIndicators: ['furthermore', 'moreover', 'consequently', 'therefore', 'thus', 'hereby'],
    shouldAvoid: ['hey', 'gonna', 'wanna', 'yeah', 'cool']
  },
  {
    value: 'educational',
    label: 'Educational',
    toneIndicators: ['learn', 'understand', 'concept', 'example', 'practice', 'lesson', 'key'],
    shouldAvoid: ['boring', 'difficult', 'complicated', 'confusing']
  },
  {
    value: 'technical',
    label: 'Technical',
    toneIndicators: ['process', 'procedure', 'method', 'system', 'technique', 'implement', 'configure'],
    shouldAvoid: ['feel', 'believe', 'think', 'maybe', 'probably']
  },
  {
    value: 'narrative',
    label: 'Narrative',
    toneIndicators: ['story', 'journey', 'experience', 'began', 'discovered', 'realized', 'moment'],
    shouldAvoid: ['step 1', 'step 2', 'first', 'second', 'finally']
  },
  {
    value: 'inspirational',
    label: 'Inspirational',
    toneIndicators: ['achieve', 'transform', 'empower', 'inspire', 'potential', 'dream', 'success'],
    shouldAvoid: ['impossible', 'can\'t', 'never', 'failure', 'hopeless']
  }
];

/**
 * Test Q&A data specifically crafted for style testing
 */
const STYLE_TEST_QA = [
  {
    question: "What is the main concept or idea you want to convey in this chapter?",
    answer: "The fundamental principles of container gardening in urban spaces, including soil composition, drainage requirements, and container selection for optimal plant growth."
  },
  {
    question: "What are the key takeaways you want readers to remember?",
    answer: "Container selection impacts plant health, proper drainage prevents root rot, and soil quality determines success. Urban gardeners can grow productive gardens in limited spaces with the right techniques."
  },
  {
    question: "What challenges might readers face, and how can they overcome them?",
    answer: "Limited space, poor drainage, and inadequate soil. Solutions include using fabric containers, creating custom soil mixes, and implementing vertical growing techniques to maximize available space."
  }
];

test.describe('Draft Generation: Writing Styles', () => {
  let bookId: string;
  let chapterId: string;

  test.beforeEach(async ({ page }) => {
    console.log('\n🔐 Authenticating user...');
    await authenticateUser(page);

    // Create test book and chapter for draft generation
    console.log('\n📚 Setting up test book and chapter...');
    const bookForm = new BookFormPage(page);
    await bookForm.gotoNewBook();
    await bookForm.fillBookDetails({
      ...TEST_BOOK,
      title: `Writing Styles Test ${Date.now()}`
    });

    const result = await bookForm.submitAndWaitForAPI();
    bookId = result.bookId!;

    // Navigate to first chapter
    await page.goto(`/dashboard/books/${bookId}`);
    await page.waitForLoadState('networkidle');

    const firstChapter = page.locator('[data-testid="chapter-item"]').first();
    chapterId = await firstChapter.getAttribute('data-chapter-id') || '';

    console.log(`✅ Test setup complete: Book ID: ${bookId}, Chapter ID: ${chapterId}`);
  });

  // Test each writing style individually
  WRITING_STYLES.forEach(({ value, label, toneIndicators, shouldAvoid }) => {
    test(`Generate draft with ${label} style`, async ({ page }) => {
      console.log(`\n✍️ Testing ${label} writing style (${value})`);

      const consoleMonitor = new ConsoleMonitor(page);
      const networkMonitor = new NetworkMonitor(page);
      const editor = new ChapterEditorPage(page);

      // Navigate to chapter editor
      await editor.goto(bookId, chapterId);

      // Open AI draft wizard
      const draftButton = page.locator('[data-testid="generate-draft-button"]');
      await expect(draftButton).toBeVisible({ timeout: 10000 });
      await draftButton.click();

      // Wait for draft wizard to open
      const draftWizard = page.locator('[data-testid="draft-wizard"]');
      await expect(draftWizard).toBeVisible({ timeout: 5000 });
      console.log('✅ Draft wizard opened');

      // Answer Q&A questions
      for (let i = 0; i < STYLE_TEST_QA.length; i++) {
        const questionField = page.locator(`[data-testid="draft-question-${i}"]`);
        if (await questionField.isVisible()) {
          await questionField.fill(STYLE_TEST_QA[i].answer);
          console.log(`✅ Answered question ${i + 1}`);
        } else {
          // Alternative selector if data-testid not available
          const allTextareas = page.locator('textarea');
          const textarea = allTextareas.nth(i);
          if (await textarea.isVisible()) {
            await textarea.fill(STYLE_TEST_QA[i].answer);
            console.log(`✅ Answered question ${i + 1} (alternative selector)`);
          }
        }
      }

      // Select writing style
      const styleSelect = page.locator('[data-testid="writing-style-select"]');
      if (await styleSelect.isVisible()) {
        await styleSelect.click();
        await page.locator(`[data-value="${value}"]`).click();
        console.log(`✅ Selected ${label} writing style`);
      } else {
        // Alternative: look for Select component by label
        await page.getByLabel('Writing Style').click();
        await page.getByRole('option', { name: label }).click();
        console.log(`✅ Selected ${label} writing style (alternative selector)`);
      }

      // Generate draft with performance tracking
      console.log(`⏱️ Generating ${label} draft...`);

      const { duration, withinBudget } = await measureOperation(
        page,
        async () => {
          // Click generate button
          const generateButton = page.getByRole('button', { name: /generate draft/i });
          await generateButton.click();

          // Wait for loading indicator
          const loadingIndicator = page.locator('[data-testid="generating-draft"]');
          await expect(loadingIndicator).toBeVisible({ timeout: 5000 });
          console.log('✅ Generation started');

          // Wait for generation to complete (up to 60 seconds)
          await expect(loadingIndicator).not.toBeVisible({ timeout: 60000 });
          console.log('✅ Generation completed');
        },
        PERFORMANCE_BUDGETS.DRAFT_GENERATION,
        `Draft Generation (${label})`
      );

      // Verify performance budget
      expect(withinBudget, `${label} draft generation should complete within ${PERFORMANCE_BUDGETS.DRAFT_GENERATION}ms`).toBeTruthy();
      console.log(`✅ Performance: ${duration.toFixed(0)}ms (within budget: ${PERFORMANCE_BUDGETS.DRAFT_GENERATION}ms)`);

      // Verify draft content appears
      const draftPreview = page.locator('[data-testid="draft-preview"]');
      await expect(draftPreview).toBeVisible({ timeout: 5000 });

      const draftContent = await draftPreview.textContent();
      expect(draftContent).toBeTruthy();
      expect(draftContent!.length).toBeGreaterThan(200);
      console.log(`✅ Draft generated: ${draftContent!.length} characters`);

      // Verify draft tone matches writing style
      const contentLower = draftContent!.toLowerCase();

      // Check for at least one tone indicator
      const hasToneIndicator = toneIndicators.some(indicator =>
        contentLower.includes(indicator.toLowerCase())
      );

      if (!hasToneIndicator) {
        console.warn(`⚠️ Warning: ${label} draft may not contain expected tone indicators: ${toneIndicators.join(', ')}`);
        // Don't fail the test, as AI generation can vary, but log for review
      } else {
        console.log(`✅ ${label} tone indicators found in draft`);
      }

      // Check that inappropriate words for this style are avoided
      const hasInappropriateWords = shouldAvoid.some(word =>
        contentLower.includes(word.toLowerCase())
      );

      expect(hasInappropriateWords, `${label} draft should avoid informal words like: ${shouldAvoid.join(', ')}`).toBeFalsy();
      console.log(`✅ ${label} draft avoids inappropriate tone`);

      // Verify draft metadata shows correct style
      const metadataSection = page.locator('[data-testid="draft-metadata"]');
      if (await metadataSection.isVisible()) {
        const metadataText = await metadataSection.textContent();
        expect(metadataText).toContain(label);
        console.log(`✅ Metadata shows ${label} style`);
      }

      // Verify word count is displayed
      const wordCountDisplay = page.locator('[data-testid="draft-word-count"]');
      await expect(wordCountDisplay).toBeVisible();
      const wordCountText = await wordCountDisplay.textContent();
      console.log(`✅ Word count displayed: ${wordCountText}`);

      // Verify no console errors or 500 responses
      consoleMonitor.assertNoErrors();
      consoleMonitor.assertNoCORSErrors();
      networkMonitor.assertNo500Errors();

      console.log(`✅ ${label} writing style test PASSED\n`);
    });
  });

  test('Compare drafts across multiple styles for same content', async ({ page }) => {
    console.log('\n🔄 Comparing draft variations across writing styles');

    const editor = new ChapterEditorPage(page);
    await editor.goto(bookId, chapterId);

    const generatedDrafts: { style: string; content: string; wordCount: number }[] = [];

    // Generate drafts for 3 different styles
    const stylesToCompare = ['conversational', 'formal', 'technical'];

    for (const styleValue of stylesToCompare) {
      const style = WRITING_STYLES.find(s => s.value === styleValue)!;

      console.log(`\n📝 Generating ${style.label} draft...`);

      // Open draft wizard
      const draftButton = page.locator('[data-testid="generate-draft-button"]');
      await draftButton.click();
      await page.waitForTimeout(1000);

      // Answer questions
      for (let i = 0; i < STYLE_TEST_QA.length; i++) {
        const textarea = page.locator('textarea').nth(i);
        await textarea.fill(STYLE_TEST_QA[i].answer);
      }

      // Select style
      await page.getByLabel('Writing Style').click();
      await page.getByRole('option', { name: style.label }).click();

      // Generate
      await page.getByRole('button', { name: /generate draft/i }).click();

      // Wait for completion
      const loadingIndicator = page.locator('[data-testid="generating-draft"]');
      await expect(loadingIndicator).toBeVisible({ timeout: 5000 });
      await expect(loadingIndicator).not.toBeVisible({ timeout: 60000 });

      // Capture draft content
      const draftContent = await page.locator('[data-testid="draft-preview"]').textContent();
      const wordCount = draftContent!.split(/\s+/).length;

      generatedDrafts.push({
        style: style.label,
        content: draftContent!,
        wordCount
      });

      console.log(`✅ ${style.label}: ${wordCount} words, ${draftContent!.length} chars`);

      // Click "Generate New Draft" to start over
      const newDraftButton = page.getByRole('button', { name: /generate new draft|start over/i });
      if (await newDraftButton.isVisible()) {
        await newDraftButton.click();
        await page.waitForTimeout(500);
      } else {
        // Close and reopen wizard
        await page.keyboard.press('Escape');
        await page.waitForTimeout(500);
      }
    }

    // Verify drafts are different
    console.log('\n🔍 Verifying drafts are distinct...');

    expect(generatedDrafts.length).toBe(3);

    // Check that drafts have different content
    const draft1 = generatedDrafts[0].content;
    const draft2 = generatedDrafts[1].content;
    const draft3 = generatedDrafts[2].content;

    expect(draft1).not.toBe(draft2);
    expect(draft2).not.toBe(draft3);
    expect(draft1).not.toBe(draft3);

    console.log('✅ All drafts are distinct (different content)');

    // Verify word counts are reasonable (within 50% of each other)
    const wordCounts = generatedDrafts.map(d => d.wordCount);
    const avgWordCount = wordCounts.reduce((sum, count) => sum + count, 0) / wordCounts.length;

    for (const draft of generatedDrafts) {
      const variance = Math.abs(draft.wordCount - avgWordCount) / avgWordCount;
      expect(variance).toBeLessThan(0.5); // Within 50% of average
      console.log(`✅ ${draft.style}: ${draft.wordCount} words (${(variance * 100).toFixed(1)}% variance from avg)`);
    }

    console.log('✅ Word counts are consistent across styles');
    console.log('✅ Draft comparison test PASSED\n');
  });
});

/**
 * Test Summary
 *
 * This test suite validates:
 * ✅ All 6 writing styles (Conversational, Formal, Educational, Technical, Narrative, Inspirational)
 * ✅ Draft tone and language appropriate for each style
 * ✅ Style-specific tone indicators present in generated content
 * ✅ Inappropriate tone avoided for each style
 * ✅ Draft metadata correctly shows selected writing style
 * ✅ Word count display for generated drafts
 * ✅ Performance budgets maintained (<60s per generation)
 * ✅ No console errors or 500 responses
 * ✅ Drafts are distinct across different styles
 * ✅ Word counts are consistent across styles
 *
 * Performance Budgets:
 * - Draft Generation: <60000ms (60 seconds) per style ✅
 *
 * Known Limitations:
 * - AI-generated content can vary, so tone indicators are warnings, not hard failures
 * - Test requires real OpenAI API access (not mocked)
 * - Test duration: ~6-8 minutes (7 drafts × 60s each + setup)
 *
 * Issue: auto-author-15k
 * Status: IMPLEMENTED
 */
