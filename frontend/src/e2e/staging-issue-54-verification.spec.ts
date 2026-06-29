/**
 * Staging Verification Test - Issue #54
 *
 * Tests question response persistence on staging server
 * Verifies: https://github.com/frankbria/auto-author/issues/54
 *
 * Test Flow:
 * 1. Create a book with summary
 * 2. Generate TOC
 * 3. Navigate to first chapter
 * 4. Generate chapter questions
 * 5. Answer 5 questions
 * 6. Refresh the page
 * 7. Verify all 5 answers are still visible
 *
 * Success Criteria:
 * - All 5 answers persist after page refresh
 * - No data loss occurs
 *
 * Failure Indicates:
 * - Issue #54 is a REAL BLOCKER (P0)
 * - Question response integration is broken
 */

import { test, expect, Page } from '@playwright/test';

// Test configuration
const BASE_URL = process.env.BASE_URL || 'https://dev.autoauthor.app';
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.dev.autoauthor.app/api/v1';

// Test data
const TEST_BOOK = {
  title: `E2E Test Book - Issue #54 - ${Date.now()}`,
  subtitle: 'Question Persistence Verification',
  summary: `This is a comprehensive book about test automation and quality assurance.
  It covers various testing methodologies, tools, and best practices for modern software development.
  The book aims to help developers and QA professionals build reliable test suites that catch bugs early
  and maintain software quality throughout the development lifecycle.`,
};

const TEST_ANSWERS = [
  'This is test answer number one for persistence verification',
  'Second answer - testing data persistence across page refresh',
  'Third answer - verifying question response integration',
  'Fourth answer - ensuring answers save to backend database',
  'Fifth answer - final verification of persistence functionality',
];

/**
 * Helper: Wait for network idle (no requests for 500ms)
 */
async function waitForNetworkIdle(page: Page, timeout = 5000) {
  let requestCount = 0;
  const startTime = Date.now();

  page.on('request', () => requestCount++);
  page.on('requestfinished', () => requestCount--);
  page.on('requestfailed', () => requestCount--);

  while (Date.now() - startTime < timeout) {
    await page.waitForTimeout(500);
    if (requestCount === 0) {
      return;
    }
  }
}

/**
 * Helper: Create a book via UI
 */
async function createBook(page: Page) {
  console.log('Creating book...');

  // Navigate to dashboard
  await page.goto(BASE_URL);
  await page.waitForLoadState('networkidle');

  // Click "Create New Book" button
  // Try multiple selectors in case UI has multiple buttons
  const createButton = page.getByRole('button', { name: /create.*book|new book/i }).first();
  await expect(createButton).toBeVisible({ timeout: 10000 });
  await createButton.click();

  // Fill in book details
  await page.getByLabel(/title/i).first().fill(TEST_BOOK.title);
  await page.getByLabel(/subtitle/i).first().fill(TEST_BOOK.subtitle);

  // Submit form
  const submitButton = page.getByRole('button', { name: /create|save|submit/i });
  await submitButton.click();

  // Wait for book to be created
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);

  console.log('Book created successfully');
}

/**
 * Helper: Add summary to book
 */
async function addSummary(page: Page) {
  console.log('Adding book summary...');

  // Look for summary editor/field
  const summaryField = page.locator('textarea, [contenteditable="true"]').filter({ hasText: /summary|description/i }).first();

  if (await summaryField.count() > 0) {
    await summaryField.fill(TEST_BOOK.summary);
  } else {
    // Try alternative selector
    const textArea = page.getByLabel(/summary|description/i).first();
    await textArea.fill(TEST_BOOK.summary);
  }

  // Save summary
  const saveButton = page.getByRole('button', { name: /save|update/i }).first();
  if (await saveButton.isVisible()) {
    await saveButton.click();
    await waitForNetworkIdle(page);
  }

  console.log('Summary added successfully');
}

/**
 * Helper: Generate TOC
 */
async function generateTOC(page: Page) {
  console.log('Generating TOC...');

  // Click "Generate TOC" button
  const tocButton = page.getByRole('button', { name: /generate.*toc|table.*contents/i }).first();
  await expect(tocButton).toBeVisible({ timeout: 10000 });
  await tocButton.click();

  // Wait for TOC generation (can take up to 30s per Issue #48)
  await page.waitForLoadState('networkidle', { timeout: 35000 });

  // Verify TOC appeared
  await expect(page.locator('text=/chapter|section/i').first()).toBeVisible({ timeout: 10000 });

  console.log('TOC generated successfully');
}

/**
 * Helper: Navigate to first chapter
 */
async function navigateToFirstChapter(page: Page) {
  console.log('Navigating to first chapter...');

  // Click first chapter in TOC
  const firstChapter = page.locator('[data-chapter-id], [role="tab"]').first();
  await firstChapter.click();

  await page.waitForLoadState('networkidle');

  console.log('Navigated to first chapter');
}

/**
 * Helper: Generate chapter questions
 */
async function generateQuestions(page: Page) {
  console.log('Generating chapter questions...');

  // Click "Generate Questions" button
  const generateButton = page.getByRole('button', { name: /generate.*question/i }).first();
  await expect(generateButton).toBeVisible({ timeout: 10000 });
  await generateButton.click();

  // Wait for questions to load
  await page.waitForLoadState('networkidle', { timeout: 30000 });

  // Verify questions appeared
  const questions = page.locator('[data-question-id], .question-item, [role="group"]');
  await expect(questions.first()).toBeVisible({ timeout: 10000 });

  const questionCount = await questions.count();
  console.log(`Generated ${questionCount} questions`);

  return questionCount;
}

/**
 * Helper: Answer questions
 */
async function answerQuestions(page: Page, answers: string[]) {
  console.log(`Answering ${answers.length} questions...`);

  for (let i = 0; i < answers.length; i++) {
    console.log(`  Answering question ${i + 1}...`);

    // Find answer input field for this question
    // Try multiple selectors
    const answerFields = page.locator('textarea, input[type="text"], [contenteditable="true"]').filter({
      hasText: /answer|response/i
    });

    const answerField = answerFields.nth(i);

    if (await answerField.count() === 0) {
      // Alternative: Find all visible text inputs
      const allInputs = page.locator('textarea:visible, input[type="text"]:visible');
      await allInputs.nth(i).fill(answers[i]);
    } else {
      await answerField.fill(answers[i]);
    }

    // Wait for auto-save (3s debounce per CLAUDE.md)
    await page.waitForTimeout(3500);
  }

  console.log('All questions answered');
}

/**
 * Helper: Verify answers persist after refresh
 */
async function verifyAnswersPersist(page: Page, expectedAnswers: string[]) {
  console.log('Verifying answers persist after refresh...');

  // Refresh the page
  await page.reload();
  await page.waitForLoadState('networkidle');

  // Wait for questions to load
  await page.waitForTimeout(2000);

  // Check each answer
  for (let i = 0; i < expectedAnswers.length; i++) {
    const expectedAnswer = expectedAnswers[i];

    console.log(`  Checking answer ${i + 1}: "${expectedAnswer.substring(0, 30)}..."`);

    // Look for the answer text on the page
    const answerExists = await page.locator(`text="${expectedAnswer}"`).count() > 0;

    if (!answerExists) {
      console.error(`  ❌ Answer ${i + 1} NOT FOUND after refresh!`);
      return false;
    }

    console.log(`  ✅ Answer ${i + 1} found`);
  }

  console.log('✅ All answers persisted successfully!');
  return true;
}

/**
 * Main Test: Issue #54 Verification
 */
test('Issue #54: Question answers persist after page refresh', async ({ page }) => {
  test.setTimeout(180000); // 3 minute timeout for full flow

  console.log('\n=== Starting Issue #54 Verification ===\n');
  console.log(`Testing against: ${BASE_URL}`);
  console.log(`API URL: ${API_URL}`);

  try {
    // Step 1: Create book
    await createBook(page);

    // Step 2: Add summary
    await addSummary(page);

    // Step 3: Generate TOC
    await generateTOC(page);

    // Step 4: Navigate to first chapter
    await navigateToFirstChapter(page);

    // Step 5: Generate questions
    const questionCount = await generateQuestions(page);
    expect(questionCount).toBeGreaterThanOrEqual(5);

    // Step 6: Answer first 5 questions
    await answerQuestions(page, TEST_ANSWERS);

    // Step 7: Verify persistence
    const persistenceResult = await verifyAnswersPersist(page, TEST_ANSWERS);

    // Assert persistence
    expect(persistenceResult).toBe(true);

    console.log('\n=== ✅ Issue #54 VERIFICATION PASSED ===');
    console.log('Result: Question answers persist correctly after page refresh');
    console.log('Status: NOT A BLOCKER - Feature works as expected\n');

  } catch (error) {
    console.error('\n=== ❌ Issue #54 VERIFICATION FAILED ===');
    console.error('Result: Question answers DO NOT persist after page refresh');
    console.error('Status: P0 BLOCKER - Data loss bug confirmed');
    console.error(`Error: ${error}`);
    console.error('\n');

    throw error;
  }
});

/**
 * Cleanup Test: Delete test book
 */
test.afterAll(async ({ browser }) => {
  // Optional: Clean up test data
  // Could use API to delete test book if needed
  console.log('Test cleanup completed');
});
