/**
 * System Integration Test for Auto Author
 * 
 * This test validates the complete authoring workflow from book creation
 * through chapter draft generation, using real API calls.
 * 
 * This is the gold standard test - if this passes, the core system is working.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';

// Import actual API clients (not mocks for this test)
import { bookClient } from '@/lib/api/bookClient';
import { aiClient } from '@/lib/api/aiClient';

// Test configuration
const TEST_TIMEOUT = 300000; // 5 minutes for full integration test
const AI_RESPONSE_TIMEOUT = 60000; // 1 minute for individual AI responses

// Test data
const TEST_BOOK = {
  title: 'The Psychology of Habit Formation: A Practical Guide',
  genre: 'Non-Fiction',
  target_audience: 'Adults interested in personal development',
  description: 'A comprehensive guide to understanding how habits are formed in the brain and practical strategies for building positive habits and breaking negative ones.',
};

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  useParams: jest.fn(),
}));

describe('Auto Author System Integration Test', () => {
  let queryClient: QueryClient;
  let bookId: string;
  let chapterId: string;
  const user = userEvent.setup();

  beforeAll(() => {
    // Increase Jest timeout for this test suite
    jest.setTimeout(TEST_TIMEOUT);
  });

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    (useRouter as jest.Mock).mockReturnValue({
      push: jest.fn(),
      replace: jest.fn(),
    });
  });

  afterAll(async () => {
    // Cleanup: Delete test book if it was created
    if (bookId) {
      try {
        await bookClient.deleteBook(bookId);
      } catch (error) {
        console.error('Failed to cleanup test book:', error);
      }
    }
  });

  const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );

  test('Complete authoring workflow from book creation to chapter draft', async () => {
    console.log('🚀 Starting System Integration Test...');

    // Step 1: Create a book using the API
    console.log('📚 Step 1: Creating book...');
    const createBookResponse = await bookClient.createBook({
      title: TEST_BOOK.title,
      author_name: 'Test Author',
      genre: TEST_BOOK.genre,
      target_audience: TEST_BOOK.target_audience,
      description: TEST_BOOK.description,
      language: 'English',
      estimated_word_count: 50000,
    });

    expect(createBookResponse).toHaveProperty('id');
    bookId = createBookResponse.id;
    console.log(`✅ Book created with ID: ${bookId}`);

    // Step 2: Generate book summary questions
    console.log('❓ Step 2: Generating book summary questions...');
    const summaryQuestions = await aiClient.generateBookSummaryQuestions(bookId);
    
    expect(summaryQuestions).toBeDefined();
    expect(summaryQuestions.questions).toBeInstanceOf(Array);
    expect(summaryQuestions.questions.length).toBeGreaterThan(0);
    console.log(`✅ Generated ${summaryQuestions.questions.length} summary questions`);

    // Step 3: Answer summary questions
    console.log('✍️ Step 3: Answering summary questions...');
    const summaryAnswers = summaryQuestions.questions.map((q: any, index: number) => ({
      question_id: q.id,
      question_text: q.question_text,
      answer: index === 0 
        ? 'Adults aged 25-55 interested in personal development and understanding behavior change'
        : index === 1
        ? 'Readers will understand the neurological basis of habits and gain practical tools for change'
        : 'This book combines neuroscience research with actionable strategies for lasting change',
    }));

    const summaryResponse = await aiClient.submitBookSummaryAnswers(bookId, summaryAnswers);
    expect(summaryResponse).toHaveProperty('summary');
    console.log('✅ Summary answers submitted and processed');

    // Step 4: Generate Table of Contents
    console.log('📑 Step 4: Generating Table of Contents...');
    const tocResponse = await aiClient.generateTOC(bookId, {
      chapter_count: 10,
      include_introduction: true,
      include_conclusion: true,
    });

    expect(tocResponse).toHaveProperty('chapters');
    expect(tocResponse.chapters).toBeInstanceOf(Array);
    expect(tocResponse.chapters.length).toBeGreaterThan(0);
    console.log(`✅ Generated TOC with ${tocResponse.chapters.length} chapters`);

    // Step 5: Create chapters from TOC
    console.log('📖 Step 5: Creating chapters from TOC...');
    const createdChapters = await bookClient.createChaptersFromTOC(bookId, tocResponse.chapters);
    
    expect(createdChapters).toBeInstanceOf(Array);
    expect(createdChapters.length).toBeGreaterThan(0);
    chapterId = createdChapters[0].id;
    console.log(`✅ Created ${createdChapters.length} chapters`);

    // Step 6: Generate chapter questions
    console.log('❓ Step 6: Generating questions for Chapter 1...');
    const chapterQuestions = await bookClient.generateChapterQuestions(bookId, chapterId, {
      count: 5,
      difficulty: 'mixed',
    });

    expect(chapterQuestions).toHaveProperty('questions');
    expect(chapterQuestions.questions).toBeInstanceOf(Array);
    expect(chapterQuestions.questions.length).toBeGreaterThan(0);
    console.log(`✅ Generated ${chapterQuestions.questions.length} chapter questions`);

    // Step 7: Answer chapter questions
    console.log('✍️ Step 7: Answering chapter questions...');
    for (const question of chapterQuestions.questions) {
      let answer = '';
      
      if (question.question_text.toLowerCase().includes('main points')) {
        answer = 'Introduce habits concept, explain neuroscience basis, preview book framework';
      } else if (question.question_text.toLowerCase().includes('open') || question.question_text.toLowerCase().includes('hook')) {
        answer = 'Open with relatable morning routine scenario showing habit struggles';
      } else if (question.question_text.toLowerCase().includes('example')) {
        answer = 'Morning routines, driving routes, smartphone checking, eating patterns';
      } else {
        answer = 'This chapter establishes the foundation for understanding habit formation';
      }

      await bookClient.saveQuestionResponse(bookId, chapterId, question.id, {
        response_text: answer,
        status: 'completed',
      });
    }
    console.log('✅ All chapter questions answered');

    // Step 8: Generate chapter draft
    console.log('📝 Step 8: Generating chapter draft from answers...');
    const draftResponse = await bookClient.generateChapterDraft(bookId, chapterId, {
      questions_and_answers: chapterQuestions.questions.map((q: any) => ({
        question: q.question_text,
        answer: 'Sample answer for testing', // In real test, use actual answers
      })),
      writing_style: 'educational',
      target_word_count: 2000,
    });

    expect(draftResponse).toHaveProperty('draft');
    expect(draftResponse.draft).toBeTruthy();
    expect(draftResponse.draft.length).toBeGreaterThan(500);
    expect(draftResponse.draft.toLowerCase()).toContain('habit');
    console.log(`✅ Generated draft with ${draftResponse.draft.length} characters`);

    // Step 9: Save draft to chapter
    console.log('💾 Step 9: Saving draft to chapter...');
    await bookClient.updateChapter(chapterId, {
      content: draftResponse.draft,
      status: 'draft',
    });
    console.log('✅ Draft saved successfully');

    // Step 10: Verify complete workflow
    console.log('🔍 Step 10: Verifying complete workflow...');
    
    // Verify book exists
    const book = await bookClient.getBook(bookId);
    expect(book.title).toBe(TEST_BOOK.title);
    
    // Verify chapters exist
    const chapters = await bookClient.getChapters(bookId);
    expect(chapters.length).toBeGreaterThan(0);
    
    // Verify chapter has content
    const chapter = await bookClient.getChapter(chapterId);
    expect(chapter.content).toBeTruthy();
    expect(chapter.content.length).toBeGreaterThan(500);
    
    console.log('✅ System Integration Test PASSED!');
    console.log(`📊 Summary:`);
    console.log(`   - Book: ${book.title}`);
    console.log(`   - Chapters: ${chapters.length}`);
    console.log(`   - Draft Length: ${chapter.content.length} characters`);
    console.log(`   - Questions Generated: ${chapterQuestions.questions.length}`);
  }, TEST_TIMEOUT);

  test('Verify AI services are responsive', async () => {
    // Quick smoke test to ensure AI services are available
    console.log('🔌 Testing AI service connectivity...');
    
    try {
      // Test a simple AI call
      const testResponse = await aiClient.testConnection();
      expect(testResponse).toHaveProperty('status');
      expect(testResponse.status).toBe('ok');
      console.log('✅ AI services are responsive');
    } catch (error) {
      console.error('❌ AI services are not responding:', error);
      throw error;
    }
  });
});

/**
 * Instructions for running this test:
 * 
 * 1. Ensure backend is running with real AI credentials
 * 2. Set environment variables:
 *    - OPENAI_API_KEY
 *    - Any other required API keys
 * 3. Run: npm test SystemIntegration.test.tsx
 * 
 * This test will:
 * - Create real data in the database
 * - Make real API calls to AI services
 * - Validate the entire workflow
 * - Clean up test data after completion
 */