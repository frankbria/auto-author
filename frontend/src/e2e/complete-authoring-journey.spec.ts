/**
 * Complete Authoring Journey E2E (issues #201 / #110 / #193)
 *
 * The core value-proposition flow, runnable in CI without an OpenAI key:
 *   create book → write summary → TOC wizard (clarifying questions → generate
 *   → review → accept) → open chapter → interview questions → answer & complete
 *   → generate draft → draft lands in the editor → autosaved to the backend.
 *
 * Hybrid mocking, mirroring what CI actually provides (real backend + Mongo,
 * BYPASS_AUTH, no AI key):
 *   - Deterministic endpoints are REAL: book create, summary save, TOC
 *     readiness, TOC persistence (PUT /toc via wizard Accept), clarifying
 *     question-response autosave, chapter content autosave.
 *   - AI endpoints are route-mocked: analyze-summary, book-level
 *     generate-questions, generate-toc, chapter generate-questions,
 *     generate-draft.
 *   - The chapter question store (questions list / responses / progress) is
 *     served by a stateful in-test mock, because real chapter questions can
 *     only be minted by the AI generation endpoint.
 *
 * Outcome evidence at each stage: the accepted TOC and the final draft are
 * re-read from the backend API, not just observed in the DOM.
 */

import { test, expect, Page, Route } from '@playwright/test';
import { deleteTestBook } from './helpers/testData';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const TEST_BOOK = {
  title: 'Sustainable Urban Gardening: A Practical Guide',
  genre: 'other',
  targetAudience: 'Urban dwellers interested in growing their own food',
  description: 'A practical guide to productive gardens in small urban spaces.',
  // ≥30 words and ≥150 chars so the deterministic TOC-readiness check passes.
  summary:
    'A comprehensive guide to creating and maintaining productive gardens in urban environments, ' +
    'covering container gardening, vertical growing techniques, composting, and seasonal planning ' +
    'for city residents with limited space. Readers learn to plan, plant, and harvest year-round.',
};

const CLARIFYING_QUESTIONS = [
  'Who is the primary audience for this book?',
  'What are the three most important topics to cover?',
  'What should readers be able to do after finishing the book?',
];

const CLARIFYING_ANSWERS = [
  'Beginners with no gardening experience living in apartments with limited outdoor space.',
  'Container gardening, vertical growing techniques, and seasonal planning for small spaces.',
  'Plan, plant, and maintain a productive garden in any small urban space.',
];

const TOC_CHAPTERS = [
  { id: 'toc-ch-1', title: 'Why Urban Gardening Matters', description: 'The case for growing food in cities.', level: 1, order: 0, subchapters: [] },
  { id: 'toc-ch-2', title: 'Container Gardening Fundamentals', description: 'Soil, drainage, and choosing containers.', level: 1, order: 1, subchapters: [] },
  { id: 'toc-ch-3', title: 'Vertical Growing Techniques', description: 'Trellises, towers, and wall planters.', level: 1, order: 2, subchapters: [] },
];

const CHAPTER_QUESTIONS = [
  'What are the main topics this chapter will introduce?',
  'Who are the target readers for this chapter?',
  'What key takeaways should readers leave with?',
].map((text, i) => ({
  id: `e2e-q-${i + 1}`,
  chapter_id: 'e2e-chapter',
  question_text: text,
  question_type: 'research',
  difficulty: 'medium',
  category: 'content',
  order: i,
  generated_at: '2026-07-13T00:00:00Z',
  metadata: { suggested_response_length: '2-3 paragraphs' },
}));

const CHAPTER_ANSWERS = [
  'This chapter introduces the benefits of urban gardening and space-efficient growing methods.',
  'Beginners in apartments who want to grow fresh herbs, vegetables, and fruits at home.',
  'Productive gardening is possible in small urban spaces with the right containers and planning.',
];

const DRAFT_HTML =
  '<p>Urban gardening transforms even the smallest city space into a productive source of fresh food. ' +
  'This chapter explores how container gardening and vertical growing let apartment dwellers grow herbs, ' +
  'vegetables, and fruits year-round, and why the movement matters for sustainable city living.</p>';

const json = (body: unknown) => ({
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify(body),
});

/**
 * Mock every AI endpoint plus a stateful chapter-question store.
 * Everything else goes to the real backend.
 */
async function mockAiEndpoints(page: Page) {
  // Summary analysis (AI): the wizard ignores the payload; a 200 keeps the
  // readiness path on the deterministic word/char check without console noise.
  await page.route('**/books/*/analyze-summary', (route) =>
    route.fulfill(json({ success: true }))
  );

  // Book-level clarifying questions (AI).
  await page.route('**/books/*/generate-questions', (route) =>
    route.fulfill(json({ questions: CLARIFYING_QUESTIONS }))
  );

  // TOC generation (AI). The wizard's Accept persists this via the real PUT /toc.
  // Contract pin (#105 bug class): the wizard must send the clarifying
  // answers in the request body — the real backend 400s without them.
  await page.route('**/books/*/generate-toc', (route) => {
    const body = route.request().postDataJSON() as {
      question_responses?: Array<{ question: string; answer: string }>;
    };
    const answers = (body.question_responses ?? []).map((r) => r.answer);
    if (!CLARIFYING_ANSWERS.every((a) => answers.includes(a))) {
      return route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'e2e contract violation: generate-toc missing clarifying answers',
        }),
      });
    }
    return route.fulfill(
      json({
        toc: {
          chapters: TOC_CHAPTERS,
          total_chapters: TOC_CHAPTERS.length,
          estimated_pages: 120,
          structure_notes: 'Deterministic e2e TOC',
        },
        success: true,
        chapters_count: TOC_CHAPTERS.length,
        has_subchapters: false,
      })
    );
  });

  // --- Stateful chapter-question store -----------------------------------
  let questionsGenerated = false;
  const savedResponses = new Map<string, { response_text: string; status: string }>();

  const questionWithStatus = (q: (typeof CHAPTER_QUESTIONS)[number]) => ({
    ...q,
    has_response: savedResponses.has(q.id),
    response_status: savedResponses.get(q.id)?.status,
  });

  const progressBody = () => {
    const completed = [...savedResponses.values()].filter((r) => r.status === 'completed').length;
    const inProgress = [...savedResponses.values()].filter((r) => r.status === 'draft').length;
    const total = questionsGenerated ? CHAPTER_QUESTIONS.length : 0;
    return {
      total,
      completed,
      in_progress: inProgress,
      progress: total > 0 ? completed / total : 0,
      status: completed === 0 ? 'not-started' : completed === total ? 'completed' : 'in-progress',
    };
  };

  const responseBody = (questionId: string) => {
    const saved = savedResponses.get(questionId);
    if (!saved) return { response: null, has_response: false, success: true };
    return {
      response: {
        id: `resp-${questionId}`,
        question_id: questionId,
        response_text: saved.response_text,
        word_count: saved.response_text.split(/\s+/).length,
        status: saved.status,
        created_at: '2026-07-13T00:00:00Z',
        updated_at: '2026-07-13T00:00:00Z',
        last_edited_at: '2026-07-13T00:00:00Z',
        metadata: { edit_history: [] },
      },
      has_response: true,
      success: true,
    };
  };

  // Chapter question generation (AI).
  await page.route('**/books/*/chapters/*/generate-questions', (route) => {
    questionsGenerated = true;
    return route.fulfill(
      json({
        questions: CHAPTER_QUESTIONS.map(questionWithStatus),
        generation_id: 'e2e-generation-1',
        total: CHAPTER_QUESTIONS.length,
      })
    );
  });

  // Question list (query string → URL predicate instead of a glob).
  await page.route(
    (url) => url.pathname.endsWith('/questions') && url.pathname.includes('/chapters/'),
    (route) =>
      route.fulfill(
        json({
          questions: questionsGenerated ? CHAPTER_QUESTIONS.map(questionWithStatus) : [],
          total: questionsGenerated ? CHAPTER_QUESTIONS.length : 0,
          page: 1,
          pages: 1,
        })
      )
  );

  // Per-question response save/load (PUT stores, GET serves what was stored —
  // QuestionDisplay's save verification reads it back).
  await page.route(
    (url) => /\/questions\/[^/]+\/response$/.test(url.pathname),
    (route: Route) => {
      const questionId = route.request().url().match(/\/questions\/([^/]+)\/response/)![1];
      if (route.request().method() === 'PUT') {
        const body = route.request().postDataJSON() as { response_text: string; status: string };
        savedResponses.set(questionId, body);
        return route.fulfill(
          json({ ...responseBody(questionId), message: 'Response saved' })
        );
      }
      return route.fulfill(json(responseBody(questionId)));
    }
  );

  // Progress summary.
  await page.route('**/books/*/chapters/*/question-progress', (route) =>
    route.fulfill(json(progressBody()))
  );

  // Draft generation (AI). Contract pin: the button must send the three
  // completed {question, answer} pairs — the real backend 400s otherwise.
  await page.route('**/books/*/chapters/*/generate-draft', (route) => {
    const body = route.request().postDataJSON() as {
      question_responses?: Array<{ question: string; answer: string }>;
    };
    const answers = (body.question_responses ?? []).map((r) => r.answer);
    if (
      (body.question_responses ?? []).length !== CHAPTER_QUESTIONS.length ||
      !CHAPTER_ANSWERS.every((a) => answers.includes(a))
    ) {
      return route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'e2e contract violation: generate-draft missing completed responses',
        }),
      });
    }
    return route.fulfill(
      json({
        success: true,
        draft: DRAFT_HTML,
        metadata: {
          word_count: 52,
          estimated_reading_time: 1,
          generated_at: '2026-07-13 00:00:00',
          model_used: 'gpt-4',
          writing_style: 'conversational',
          target_length: 2000,
          actual_length: 52,
        },
        suggestions: ['Add a concrete example of a balcony garden.'],
        message: 'Draft generated',
      })
    );
  });
}

test.describe('Complete Authoring Journey E2E', () => {
  test.setTimeout(120000);

  let bookId: string | undefined;

  test.afterEach(async ({ page }) => {
    if (bookId) await deleteTestBook(page, bookId);
  });

  test('user can create a book, generate a TOC, answer chapter questions, and land an AI draft in the editor', async ({ page }) => {
    await mockAiEndpoints(page);

    // ----- Step 1: create the book (real backend) -----
    await test.step('Create book with metadata', async () => {
      await page.goto('/dashboard/new-book');
      await page.getByLabel(/book title/i).fill(TEST_BOOK.title);
      await page.getByLabel(/description/i).fill(TEST_BOOK.description);
      await page.getByLabel(/genre/i).selectOption(TEST_BOOK.genre);
      await page.getByLabel(/target audience/i).fill(TEST_BOOK.targetAudience);
      await page.getByRole('button', { name: 'Create Book' }).click();

      await page.waitForURL(/\/dashboard\/books\/[^/]+$/);
      bookId = page.url().match(/books\/([a-zA-Z0-9-]+)/)![1];
      expect(bookId).toBeTruthy();
    });

    // ----- Step 2: write the summary (real backend) -----
    await test.step('Write and save the book summary', async () => {
      await page.goto(`/dashboard/books/${bookId}/summary`);

      // The page's mount fetch overwrites the field when it resolves, so a
      // single fill() can be clobbered — re-fill until the submit enables
      // (the #105 fill-race idiom from the staging helpers).
      const continueButton = page.getByRole('button', { name: 'Continue to TOC Generation' });
      await expect(async () => {
        await page.getByLabel('Book Summary').fill(TEST_BOOK.summary);
        await continueButton.click({ timeout: 2000 });
        await page.waitForURL('**/generate-toc', { timeout: 5000 });
      }).toPass({ timeout: 30000 });
    });

    // ----- Step 3: TOC wizard (mocked AI, real persistence on Accept) -----
    await test.step('Answer clarifying questions and generate the TOC', async () => {
      // Wizard auto-runs readiness (real, deterministic) then loads the
      // mocked clarifying questions.
      await expect(page.getByText(CLARIFYING_QUESTIONS[0])).toBeVisible({ timeout: 15000 });

      for (let i = 0; i < CLARIFYING_QUESTIONS.length; i++) {
        await expect(page.getByText(CLARIFYING_QUESTIONS[i])).toBeVisible();
        await page.getByPlaceholder('Type your answer here...').fill(CLARIFYING_ANSWERS[i]);
        if (i < CLARIFYING_QUESTIONS.length - 1) {
          await page.getByRole('button', { name: 'Next', exact: true }).click();
        }
      }

      await page.getByRole('button', { name: 'Generate Table of Contents' }).click();

      // Review step shows the mocked chapters.
      await expect(page.getByText(TOC_CHAPTERS[0].title)).toBeVisible({ timeout: 15000 });
      await expect(page.getByText(TOC_CHAPTERS[2].title)).toBeVisible();

      // Accept persists via the real PUT /books/{id}/toc, then navigates.
      await page.getByRole('button', { name: /accept & continue/i }).click();
      await page.waitForURL('**/edit-toc');
    });

    // ----- Step 4: TOC really persisted (backend evidence) -----
    let chapterCount = 0;
    await test.step('Verify the TOC persisted on the backend', async () => {
      const response = await page.request.get(`${API_BASE_URL}/books/${bookId}/toc`);
      expect(response.ok()).toBe(true);
      const body = await response.json();
      const titles = (body.toc?.chapters ?? []).map((c: { title: string }) => c.title);
      expect(titles).toEqual(TOC_CHAPTERS.map((c) => c.title));
      chapterCount = titles.length;
    });

    // ----- Step 5: open the first chapter's Interview Questions tab -----
    await test.step('Open the first chapter and its questions tab', async () => {
      await page.goto(`/dashboard/books/${bookId}`);

      const sidebarTabs = page.locator('[data-testid="chapter-tab"]:not([data-tab])');
      await expect(sidebarTabs).toHaveCount(chapterCount);
      await sidebarTabs.first().click();
      await expect(page.getByRole('tablist', { name: /chapter editor view/i })).toBeVisible();

      await page.locator('[data-testid="chapter-tab"][data-tab="questions"]').click();
      // No questions exist yet, so the tab shows the generator empty state.
      await expect(
        page.getByRole('button', { name: 'Generate Interview Questions' })
      ).toBeVisible();
    });

    // ----- Step 6: generate questions (mocked AI), answer and complete all 3 -----
    await test.step('Generate and answer interview questions', async () => {
      await page.getByRole('button', { name: 'Generate Interview Questions' }).click();
      await expect(page.getByText(CHAPTER_QUESTIONS[0].question_text)).toBeVisible();

      for (let i = 0; i < CHAPTER_QUESTIONS.length; i++) {
        await expect(page.getByText(CHAPTER_QUESTIONS[i].question_text)).toBeVisible();
        await page
          .getByPlaceholder('Type your response here or use voice input...')
          .fill(CHAPTER_ANSWERS[i]);
        await page.getByRole('button', { name: 'Complete Response' }).click();
        // Completed state replaces the action buttons.
        await expect(page.getByRole('button', { name: 'Edit Response' })).toBeVisible();

        if (i < CHAPTER_QUESTIONS.length - 1) {
          await page.getByRole('button', { name: /^next$/i }).click();
        }
      }

      await expect(page.getByText(/ready to generate draft/i)).toBeVisible();
    });

    // ----- Step 7: generate the draft (mocked AI) and apply it -----
    await test.step('Generate a draft from the answers and use it', async () => {
      await page.getByRole('button', { name: 'Generate Draft from Answers' }).click();
      await page.getByRole('button', { name: 'Generate Draft', exact: true }).click();

      await expect(page.getByText(/urban gardening transforms/i)).toBeVisible({ timeout: 15000 });
      await page.getByRole('button', { name: 'Use This Draft' }).click();

      // "Use This Draft" switches to the editor view with the draft inserted.
      await expect(page.locator('.tiptap')).toContainText(
        'Urban gardening transforms even the smallest city space'
      );
    });

    // ----- Step 8: the inserted draft autosaves to the real backend -----
    await test.step('Verify the draft autosaved to the backend', async () => {
      await page.waitForResponse(
        (r) => r.request().method() === 'PATCH' && r.url().includes('/content') && r.ok(),
        { timeout: 15000 }
      );

      const chapters = (await (await page.request.get(`${API_BASE_URL}/books/${bookId}/toc`)).json())
        .toc.chapters as Array<{ id: string }>;
      const contentResponse = await page.request.get(
        `${API_BASE_URL}/books/${bookId}/chapters/${chapters[0].id}/content`
      );
      expect(contentResponse.ok()).toBe(true);
      const content = await contentResponse.json();
      expect(content.content).toContain('Urban gardening transforms even the smallest city space');
    });
  });
});
