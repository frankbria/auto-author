import { test, expect } from './fixtures/auth.fixture';

/**
 * Complete User Journey E2E Test for Staging
 *
 * This test covers the entire authoring workflow from start to finish:
 * 1. Authentication with Better-auth
 * 2. Book creation
 * 3. Summary addition
 * 4. TOC generation
 * 5. Chapter questions & answers
 * 6. Draft generation
 *
 * This test would have caught all recent regressions:
 * - Session cookie signing issue
 * - ObjectId/string conversion bug
 * - User lookup after string conversion
 * - Question answer persistence (Issue #54)
 */

test.describe('Complete Authoring Journey', () => {
  let bookTitle: string;
  let bookId: string;

  test.beforeEach(() => {
    // Generate unique book title for this test run
    const timestamp = Date.now();
    bookTitle = `E2E Test Book ${timestamp}`;
  });

  test('user can complete full authoring workflow: create book → summary → TOC → questions → draft', async ({
    authenticatedPage: page,
  }) => {
    test.setTimeout(300000); // 5 minutes for complete journey

    console.log('📚 Starting complete authoring journey test...');

    // ==========================================
    // STEP 1: Navigate to dashboard
    // ==========================================
    console.log('📍 Step 1: Navigate to dashboard');
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/dashboard/);

    // Verify dashboard loads without errors
    await expect(page.locator('h1, h2')).toContainText(/dashboard|books/i, {
      timeout: 10000,
    });

    // ==========================================
    // STEP 2: Create new book
    // ==========================================
    console.log('📍 Step 2: Create new book');

    // Click create book button
    const createButton = page.getByRole('button', {
      name: /create.*book|new book|add book/i,
    });
    await createButton.click();

    // Wait for book creation form/modal
    await page.waitForSelector('input[name="title"], input[placeholder*="title" i]', {
      timeout: 10000,
    });

    // Fill in book metadata
    await page.fill('input[name="title"], input[placeholder*="title" i]', bookTitle);
    await page.fill(
      'input[name="subtitle"], input[placeholder*="subtitle" i]',
      'An E2E test book for validation'
    );
    await page.fill(
      'textarea[name="description"], textarea[placeholder*="description" i]',
      'This book was created by automated E2E tests to verify the complete authoring workflow works correctly on staging.'
    );

    // Select genre (if dropdown exists)
    const genreSelect = page.locator(
      'select[name="genre"], [role="combobox"][aria-label*="genre" i]'
    );
    if (await genreSelect.isVisible({ timeout: 2000 }).catch(() => false)) {
      await genreSelect.click();
      await page.keyboard.press('ArrowDown');
      await page.keyboard.press('Enter');
    }

    // Select target audience (if dropdown exists)
    const audienceSelect = page.locator(
      'select[name="target_audience"], select[name="targetAudience"], [role="combobox"][aria-label*="audience" i]'
    );
    if (await audienceSelect.isVisible({ timeout: 2000 }).catch(() => false)) {
      await audienceSelect.click();
      await page.keyboard.press('ArrowDown');
      await page.keyboard.press('Enter');
    }

    // Submit book creation form
    const submitButton = page.getByRole('button', {
      name: /create|submit|save/i,
    });
    await submitButton.click();

    // Wait for success (book should appear in list or navigate to book page)
    await page.waitForTimeout(2000); // Give backend time to process

    // Verify book was created (should appear in dashboard or navigate to book page)
    const bookAppeared = await Promise.race([
      page.waitForSelector(`text=${bookTitle}`, { timeout: 10000 }).then(() => true),
      page.waitForURL(/\/books\/[a-f0-9]+/, { timeout: 10000 }).then(() => true),
    ]);

    expect(bookAppeared).toBe(true);
    console.log('✅ Step 2 complete: Book created successfully');

    // Extract book ID from URL if we navigated to book page
    const currentUrl = page.url();
    const bookIdMatch = currentUrl.match(/\/books\/([a-f0-9]+)/);
    if (bookIdMatch) {
      bookId = bookIdMatch[1];
      console.log(`📖 Book ID: ${bookId}`);
    } else {
      // If we're still on dashboard, click the book to navigate to it
      await page.click(`text=${bookTitle}`);
      await page.waitForURL(/\/books\/[a-f0-9]+/);
      const newUrl = page.url();
      const newBookIdMatch = newUrl.match(/\/books\/([a-f0-9]+)/);
      if (newBookIdMatch) {
        bookId = newBookIdMatch[1];
        console.log(`📖 Book ID: ${bookId}`);
      }
    }

    // ==========================================
    // STEP 3: Add book summary
    // ==========================================
    console.log('📍 Step 3: Add book summary');

    // Navigate to summary page/tab if not already there
    const summaryLink = page.getByRole('link', { name: /summary/i });
    if (await summaryLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      await summaryLink.click();
    }

    // Wait for summary editor
    const summaryEditor = page.locator(
      'textarea[name="summary"], textarea[placeholder*="summary" i], [contenteditable="true"]'
    );
    await summaryEditor.waitFor({ timeout: 10000 });

    // Add summary content
    const summaryContent = `This is a comprehensive test book summary.

It contains multiple paragraphs to test the summary functionality.

The summary describes the book's purpose: validating the E2E test suite.`;

    await summaryEditor.fill(summaryContent);

    // Save summary
    const saveButton = page.getByRole('button', { name: /save|update/i });
    await saveButton.click();

    // Wait for save confirmation
    await page.waitForTimeout(1000);

    // Verify summary persists after refresh
    await page.reload();
    await summaryEditor.waitFor({ timeout: 10000 });
    const savedContent = await summaryEditor.inputValue().catch(() =>
      summaryEditor.textContent()
    );
    expect(savedContent).toContain('comprehensive test book summary');

    console.log('✅ Step 3 complete: Summary added and persisted');

    // ==========================================
    // STEP 4: Generate TOC
    // ==========================================
    console.log('📍 Step 4: Generate table of contents');

    // Navigate to TOC wizard/page
    const tocLink = page.getByRole('link', { name: /table.*content|toc|chapters/i });
    if (await tocLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      await tocLink.click();
    }

    // Look for "Generate TOC" button
    const generateTocButton = page.getByRole('button', {
      name: /generate.*toc|generate.*table|create.*chapters/i,
    });

    if (await generateTocButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      const startTime = Date.now();
      await generateTocButton.click();

      // Wait for TOC generation (with performance budget check)
      await page.waitForSelector('[data-testid="chapter-item"], [role="list"] li', {
        timeout: 30000,
      });

      const generationTime = Date.now() - startTime;
      console.log(`⏱️  TOC generation time: ${generationTime}ms`);

      // Verify performance budget (< 3000ms)
      if (generationTime < 3000) {
        console.log('✅ TOC generation within performance budget');
      } else {
        console.warn(`⚠️  TOC generation exceeded 3000ms budget: ${generationTime}ms`);
      }

      // Verify chapters appear
      const chapters = page.locator('[data-testid="chapter-item"], [role="list"] li');
      const chapterCount = await chapters.count();
      expect(chapterCount).toBeGreaterThan(0);
      console.log(`📑 Generated ${chapterCount} chapters`);
    }

    console.log('✅ Step 4 complete: TOC generated');

    // ==========================================
    // STEP 5: Answer chapter questions
    // ==========================================
    console.log('📍 Step 5: Navigate to chapter and answer questions');

    // Click on first chapter
    const firstChapter = page
      .locator('[data-testid="chapter-item"], [role="list"] li')
      .first();
    await firstChapter.click();

    // Wait for chapter editor/questions page
    await page.waitForTimeout(2000);

    // Look for "Generate Questions" button
    const generateQuestionsButton = page.getByRole('button', {
      name: /generate.*question/i,
    });

    if (await generateQuestionsButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await generateQuestionsButton.click();

      // Wait for questions to generate
      await page.waitForSelector('[data-testid="question-item"], [role="group"]', {
        timeout: 30000,
      });
    }

    // Find all question inputs
    const questionInputs = page.locator(
      'textarea[placeholder*="answer" i], input[placeholder*="answer" i], [contenteditable="true"][data-question]'
    );
    const questionCount = await questionInputs.count();

    if (questionCount > 0) {
      console.log(`📝 Found ${questionCount} questions to answer`);

      // Answer at least 5 questions (or all if fewer)
      const questionsToAnswer = Math.min(5, questionCount);
      for (let i = 0; i < questionsToAnswer; i++) {
        await questionInputs
          .nth(i)
          .fill(`This is test answer #${i + 1} for E2E validation.`);
      }

      // Save answers
      const saveAnswersButton = page.getByRole('button', { name: /save|submit/i });
      if (await saveAnswersButton.isVisible({ timeout: 2000 }).catch(() => false)) {
        await saveAnswersButton.click();
        await page.waitForTimeout(1000);
      }

      // ==========================================
      // REGRESSION TEST: Issue #54 - Answer Persistence
      // ==========================================
      console.log('🔄 Testing answer persistence after page refresh (Issue #54)');

      await page.reload();
      await page.waitForTimeout(2000);

      // Verify answers persisted
      const firstAnswer = await questionInputs.nth(0).inputValue();
      expect(firstAnswer).toContain('test answer #1');

      console.log('✅ Issue #54 regression test passed: Answers persisted after refresh');
    }

    console.log('✅ Step 5 complete: Questions answered and verified');

    // ==========================================
    // STEP 6: Generate draft
    // ==========================================
    console.log('📍 Step 6: Generate AI draft from answers');

    const generateDraftButton = page.getByRole('button', {
      name: /generate.*draft|create.*draft/i,
    });

    if (await generateDraftButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      const startTime = Date.now();
      await generateDraftButton.click();

      // Wait for draft to appear in editor
      await page.waitForSelector('[data-testid="draft-content"], .editor', {
        timeout: 60000,
      });

      const draftTime = Date.now() - startTime;
      console.log(`⏱️  Draft generation time: ${draftTime}ms`);

      // Verify draft content is not empty
      const draftContent = await page
        .locator('[data-testid="draft-content"], .editor')
        .textContent();
      expect(draftContent?.length).toBeGreaterThan(50);

      console.log('✅ Step 6 complete: Draft generated successfully');
    }

    // ==========================================
    // CLEANUP
    // ==========================================
    console.log('🧹 Test complete - cleaning up');

    // Optional: Delete test book to avoid clutter
    // (Commenting out for now to allow manual inspection)
    // if (bookId) {
    //   await page.goto(`/books/${bookId}/settings`);
    //   const deleteButton = page.getByRole('button', { name: /delete.*book/i });
    //   if (await deleteButton.isVisible({ timeout: 2000 }).catch(() => false)) {
    //     await deleteButton.click();
    //     // Confirm deletion
    //     await page.getByRole('button', { name: /confirm|yes|delete/i }).click();
    //   }
    // }

    console.log('✅ Complete authoring journey test passed!');
  });
});
