import { test, expect } from './fixtures/auth.fixture';
import {
  createBook,
  addSummary,
  completeTocWizard,
  openChapterEditor,
  answerFirstChapterQuestion,
  readFirstChapterAnswer,
  READY_SUMMARY,
} from './fixtures/journey.helpers';

/**
 * Complete User Journey E2E Test for Staging
 *
 * Exercises the entire authoring workflow against live staging with real
 * Better-auth, end to end:
 *   1. Book creation (dashboard modal, delayed navigation)
 *   2. Summary (auto-save; fill-race hardened)
 *   3. TOC wizard (auto readiness -> clarifying questions -> review/accept)
 *   4. Chapter interview questions (generate -> answer -> persist after refresh)
 *
 * Every step uses web-first assertions / real network round-trips via
 * journey.helpers.ts — no page.waitForTimeout() and no silent isVisible skips.
 * This is the path that would catch the #83 regressions (session cookies,
 * ObjectId conversion, summary persistence, #54 answer persistence).
 */

test.describe('Complete Authoring Journey', () => {
  test('create book → summary → TOC → chapter questions → persistence', async ({
    authenticatedPage: page,
  }) => {
    test.setTimeout(300_000); // 5 minutes for the full AI-backed journey

    // 1. Create a book.
    const bookId = await createBook(page, `E2E Test Book ${Date.now()}`);
    expect(bookId).toMatch(/^[a-f0-9]+$/);

    // 2. Add a summary and advance to the TOC wizard.
    await addSummary(page, bookId, READY_SUMMARY);

    // 3. Generate and accept a table of contents.
    await completeTocWizard(page);
    await expect(page).toHaveURL(/\/edit-toc/);

    // 4. Open the first chapter, answer an interview question, and confirm it
    //    persists across a reload.
    const answer = `Journey answer ${Date.now()}`;
    await openChapterEditor(page, bookId);
    await answerFirstChapterQuestion(page, answer);

    await page.reload();
    const reloaded = await readFirstChapterAnswer(page);
    expect(reloaded, 'Chapter answer did not persist after refresh').toContain(answer);
  });
});
