import { Page, expect } from '@playwright/test';

/**
 * Shared, web-first helpers for the staging authoring journey (Issue #105).
 *
 * Every step asserts on real DOM state or real network round-trips — no
 * page.waitForTimeout() and no silent `if (isVisible)` skips (both forbidden by
 * CLAUDE.md). Selectors mirror the actual components, not guesses:
 *   - book create  -> BookCreationWizard dialog
 *   - summary      -> /summary page (auto-saves on a 1s debounce; no Save button)
 *   - TOC wizard   -> auto readiness -> ClarifyingQuestions -> TocReview
 *   - chapter Q&A  -> ChapterEditor "Interview Questions" tab -> QuestionContainer
 */

// Book detail URL after creation, e.g. /dashboard/books/<objectId>
const BOOK_DETAIL_RE = /\/dashboard\/books\/[a-f0-9]+(?:[/?#]|$)/;

// AI-backed steps on staging can take a while (readiness + generation chains).
const AI_TIMEOUT = 90_000;

/**
 * Create a book through the dashboard modal and return its id.
 *
 * The dashboard closes the modal and navigates to the book detail page after a
 * ~1.5s success delay (handleBookCreated), so we assert on the create POST first
 * and then wait for the eventual navigation rather than an immediate URL change.
 */
export async function createBook(page: Page, title: string): Promise<string> {
  await page.goto('/dashboard');
  await expect(page).toHaveURL(/\/dashboard/);

  await page
    .getByRole('button', { name: /create.*book|new book|add book/i })
    .first()
    .click();

  const dialog = page.getByRole('dialog');
  const titleInput = dialog.getByPlaceholder(/enter book title/i);
  await expect(titleInput).toBeVisible();
  await titleInput.fill(title);

  const createResponse = page.waitForResponse(
    (res) => res.url().includes('/books') && res.request().method() === 'POST',
    { timeout: 30_000 }
  );
  await dialog.getByRole('button', { name: /^create book$/i }).click();

  const res = await createResponse;
  expect(res.status(), `Book creation returned ${res.status()}`).toBeLessThan(400);

  await page.waitForURL(BOOK_DETAIL_RE, { timeout: 30_000 });
  const match = page.url().match(/\/books\/([a-f0-9]+)/);
  expect(match, `Could not extract book id from ${page.url()}`).not.toBeNull();
  return match![1];
}

/**
 * Add a summary and advance to the TOC wizard.
 *
 * The summary page loads the existing summary on mount (GET) and a localStorage
 * effect can clear freshly-typed text — the "fill race" from #105. We wait for
 * that load to settle, then fill and verify the value actually stuck before
 * submitting via "Continue to TOC Generation".
 */
export async function addSummary(page: Page, bookId: string, summary: string): Promise<void> {
  const summaryLoaded = page
    .waitForResponse(
      (res) =>
        /\/books\/[a-f0-9]+\/summary/.test(res.url()) && res.request().method() === 'GET',
      { timeout: 20_000 }
    )
    .catch(() => null); // a brand-new book may 404 the summary GET; either way the load settled

  await page.goto(`/dashboard/books/${bookId}/summary`);
  await summaryLoaded;
  // Let any trailing load/restore effects (which can reset the field) settle.
  await page.waitForLoadState('networkidle').catch(() => {});

  const editor = page.getByRole('textbox', { name: /book summary/i });
  await expect(editor).toBeVisible();

  // The load effect's setSummary can clear the field AFTER a one-shot fill, so
  // re-fill until the value sticks AND the submit button actually enables
  // (enabled === summary valid && not loading). toPass retries the whole block.
  const continueBtn = page.getByRole('button', { name: /continue to toc generation/i });
  await expect(async () => {
    if ((await editor.inputValue()) !== summary) {
      await editor.fill(summary);
    }
    await expect(continueBtn).toBeEnabled({ timeout: 2_000 });
  }).toPass({ timeout: 20_000 });

  await continueBtn.click();
  await page.waitForURL(/\/generate-toc/, { timeout: 20_000 });
}

/**
 * Drive the TOC wizard end to end: it auto-runs the readiness check and
 * auto-generates the clarifying questions, so we wait for the question UI,
 * answer every question, generate, then accept on the review screen.
 */
export async function completeTocWizard(page: Page): Promise<void> {
  const answerBox = page.getByPlaceholder(/type your answer here/i);
  await expect(
    answerBox,
    'Clarifying questions never appeared (summary may have been judged NOT_READY)'
  ).toBeVisible({ timeout: AI_TIMEOUT });

  // ClarifyingQuestions shows one question at a time with a Q1..Qn overview.
  const overview = page.getByRole('button', { name: /^Q\d+$/ });
  const questionCount = await overview.count();
  for (let i = 0; i < questionCount; i++) {
    await overview.nth(i).click();
    await answerBox.fill(`Detailed answer #${i + 1} to guide table-of-contents generation.`);
  }

  const generate = page.getByRole('button', { name: /generate table of contents/i });
  await expect(generate).toBeEnabled();
  await generate.click();

  const accept = page.getByRole('button', { name: /accept & continue/i });
  await expect(accept).toBeVisible({ timeout: AI_TIMEOUT });
  await accept.click();
  await page.waitForURL(/\/edit-toc/, { timeout: 30_000 });
}

/**
 * Open the book's first chapter in the tabbed editor. useChapterTabs auto-opens
 * the first chapter, so the editor (and its Write / Interview Questions tabs)
 * renders without extra clicks.
 */
export async function openChapterEditor(page: Page, bookId: string): Promise<void> {
  await page.goto(`/dashboard/books/${bookId}`);
  await expect(page.getByRole('tab', { name: /interview questions/i })).toBeVisible({
    timeout: 30_000,
  });
}

/**
 * Switch to the Interview Questions tab, generate questions if needed, answer the
 * first one, and wait for the save PUT to land. Returns the saved answer text.
 */
export async function answerFirstChapterQuestion(page: Page, answer: string): Promise<void> {
  await page.getByRole('tab', { name: /interview questions/i }).click();

  // Fresh chapter -> the generator is shown; generate the interview questions.
  const generateBtn = page.getByRole('button', { name: /generate interview questions/i });
  await expect(generateBtn).toBeVisible({ timeout: 15_000 });
  await generateBtn.click();

  const responseBox = page.getByPlaceholder(/type your response here/i);
  await expect(responseBox).toBeVisible({ timeout: AI_TIMEOUT });
  await responseBox.fill(answer);

  // QuestionDisplay saves via PUT .../questions/{id}/response; wait for the round-trip.
  const saved = page.waitForResponse(
    (res) =>
      /\/questions\/[^/]+\/response$/.test(res.url()) &&
      res.request().method() === 'PUT' &&
      res.status() < 400,
    { timeout: 30_000 }
  );
  await page.getByRole('button', { name: /complete response/i }).click();
  await saved;
}

/**
 * Re-open the Interview Questions tab after a reload and read back the persisted
 * answer (QuestionDisplay prefills from getQuestionResponse on mount).
 */
export async function readFirstChapterAnswer(page: Page): Promise<string> {
  await page.getByRole('tab', { name: /interview questions/i }).click();
  const responseBox = page.getByPlaceholder(/type your response here/i);
  await expect(responseBox).toBeVisible({ timeout: 30_000 });
  return responseBox.inputValue();
}
