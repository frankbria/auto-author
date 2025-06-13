/**
 * End-to-End Test Suite for User Story 4.2 (Interview-Style Prompts)
 * 
 * This test suite covers complete user workflows from question generation
 * through answering to draft creation integration, ensuring the entire
 * interview-style prompts feature works cohesively.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';

// Components under test
import QuestionContainer from '../components/chapters/questions/QuestionContainer';
import ChapterTabs from '../components/chapters/ChapterTabs';
import { QuestionType, QuestionDifficulty, ResponseStatus } from '../types/chapter-questions';
import bookClient from '../lib/api/bookClient';

// Mock all API clients
jest.mock('../lib/api/bookClient', () => {
  const mockBookClient = {
    getBook: jest.fn(),
    getChapter: jest.fn(),
    getChapterQuestions: jest.fn(),
    getQuestionResponse: jest.fn(),
    saveQuestionResponse: jest.fn(),
    getChapterQuestionProgress: jest.fn(),
    generateChapterQuestions: jest.fn(),
    rateQuestion: jest.fn(),
    regenerateChapterQuestions: jest.fn(),
    updateChapterStatus: jest.fn(),
    getToc: jest.fn(),
    getChaptersMetadata: jest.fn(),
    getTabState: jest.fn(),
    saveTabState: jest.fn(),
  };
  
  return {
    __esModule: true,
    default: mockBookClient,
    bookClient: mockBookClient
  };
});

jest.mock('../lib/api/draftClient', () => ({
  draftClient: {
    generateChapterDraft: jest.fn(),
    getDraftContent: jest.fn(),
    saveDraftContent: jest.fn(),
  }
}));

// Mock notifications
jest.mock('../lib/toast', () => ({
  toast: jest.fn()
}));

// Mock router
const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    query: { bookId: 'test-book-id', chapterId: 'test-chapter-id' },
    pathname: '/books/test-book-id/chapters/test-chapter-id',
  }),
  useParams: () => ({
    bookId: 'test-book-id',
    chapterId: 'test-chapter-id',
  }),
}));

describe('Chapter Questions End-to-End Tests', () => {
  let queryClient: QueryClient;
  const user = userEvent.setup();

  const mockBook = {
    id: 'test-book-id',
    title: 'Test Book: A Comprehensive Guide',
    genre: 'Educational',
    target_audience: 'Software developers',
    description: 'A comprehensive guide for learning software development.',
    status: 'active',
    created_at: '2023-01-01T00:00:00Z',
  };

  const mockChapter = {
    id: 'test-chapter-id',
    book_id: 'test-book-id',
    title: 'Chapter 1: Getting Started',
    description: 'Introduction to the fundamentals',
    order: 1,
    status: 'draft',
    content: 'This chapter covers the basic concepts...',
    questions_generated: false,
  };

  const mockGeneratedQuestions = [
    {
      id: 'q1',
      chapter_id: 'test-chapter-id',
      question_text: 'What are the main learning objectives for this chapter?',
      question_type: QuestionType.RESEARCH,
      difficulty: QuestionDifficulty.MEDIUM,
      category: 'objectives',
      order: 1,
      generated_at: '2023-01-01T10:00:00Z',
      metadata: {
        suggested_response_length: '150-200 words',
        help_text: 'Think about what readers should achieve after reading this chapter.',
        examples: [
          'Readers should understand basic concepts',
          'Readers should be able to apply fundamental principles'
        ]
      },
      has_response: false
    },
    {
      id: 'q2',
      chapter_id: 'test-chapter-id',
      question_text: 'Who is the target audience for this content?',
      question_type: QuestionType.CHARACTER,
      difficulty: QuestionDifficulty.EASY,
      category: 'planning',
      order: 2,
      generated_at: '2023-01-01T10:00:00Z',
      metadata: {
        suggested_response_length: '100-150 words',
        help_text: 'Consider experience level, background, and goals.',
        examples: [
          'Beginner developers with basic programming knowledge',
          'Intermediate professionals looking to expand skills'
        ]
      },
      has_response: false
    },
    {
      id: 'q3',
      chapter_id: 'test-chapter-id',
      question_text: 'What practical examples should be included?',
      question_type: QuestionType.PLOT,
      difficulty: QuestionDifficulty.MEDIUM,
      category: 'examples',
      order: 3,
      generated_at: '2023-01-01T10:00:00Z',
      metadata: {
        suggested_response_length: '200-300 words',
        help_text: 'Include specific, actionable examples that readers can follow.',
        examples: [
          'Step-by-step code examples',
          'Real-world project scenarios'
        ]
      },
      has_response: false
    }
  ];

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, cacheTime: 0 },
        mutations: { retry: false },
      },
    });

    jest.clearAllMocks();

    // Setup default API responses
    (bookClient.getBook as jest.Mock).mockResolvedValue(mockBook);
    (bookClient.getChapter as jest.Mock).mockResolvedValue(mockChapter);
    (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({ questions: [] });
    (bookClient.getChapterQuestionProgress as jest.Mock).mockResolvedValue({
      total_questions: 0,
      answered_questions: 0,
      completion_percentage: 0
    });
  });

  afterEach(() => {
    queryClient.clear();
  });

  const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  );

  describe('Complete Question Generation Workflow', () => {
    test('generates questions from chapter content and displays them', async () => {
      // Mock the generation API call
      (bookClient.generateChapterQuestions as jest.Mock).mockResolvedValue({
        questions: mockGeneratedQuestions,
        generation_metadata: {
          processing_time: 2500,
          ai_model: 'gpt-4',
          total_tokens: 3500
        }
      });

      render(
        <TestWrapper>
          <QuestionContainer 
            bookId="test-book-id" 
            chapterId="test-chapter-id" 
            chapterTitle="Chapter 1: Getting Started" 
          />
        </TestWrapper>
      );

      // Initially should show generation prompt
      expect(screen.getByText(/No questions generated yet/i)).toBeInTheDocument();
      
      // Click generate questions button
      const generateButton = screen.getByText('Generate Questions');
      fireEvent.click(generateButton);

      // Should show loading state
      await waitFor(() => {
        expect(screen.getByText(/Generating questions/i)).toBeInTheDocument();
      });

      // Mock the updated questions list
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: mockGeneratedQuestions
      });

      // Should display generated questions
      await waitFor(() => {
        expect(screen.getByText('What are the main learning objectives for this chapter?')).toBeInTheDocument();
      });

      // Verify all questions are accessible
      expect(screen.getByText('Question 1 of 3')).toBeInTheDocument();
      expect(bookClient.generateChapterQuestions).toHaveBeenCalledWith(
        'test-book-id',
        'test-chapter-id',
        expect.any(Object)
      );
    });

    test('handles question generation with custom options', async () => {
      (bookClient.generateChapterQuestions as jest.Mock).mockResolvedValue({
        questions: mockGeneratedQuestions,
        generation_metadata: {
          processing_time: 1800,
          ai_model: 'gpt-4',
          total_tokens: 2800
        }
      });

      render(
        <TestWrapper>
          <QuestionContainer 
            bookId="test-book-id" 
            chapterId="test-chapter-id" 
            chapterTitle="Chapter 1: Getting Started" 
          />
        </TestWrapper>
      );

      // Open generation options
      const optionsButton = screen.getByText('Customize Questions');
      fireEvent.click(optionsButton);

      // Set custom options
      const difficultySelect = screen.getByLabelText('Question Difficulty');
      fireEvent.change(difficultySelect, { target: { value: 'hard' } });

      const countInput = screen.getByLabelText('Number of Questions');
      fireEvent.change(countInput, { target: { value: '5' } });

      const focusTextarea = screen.getByLabelText('Focus Areas');
      await user.type(focusTextarea, 'Advanced concepts, practical applications, troubleshooting');

      // Generate with custom options
      const generateButton = screen.getByText('Generate Questions');
      fireEvent.click(generateButton);

      await waitFor(() => {
        expect(bookClient.generateChapterQuestions).toHaveBeenCalledWith(
          'test-book-id',
          'test-chapter-id',
          expect.objectContaining({
            difficulty: 'hard',
            count: 5,
            focus_areas: 'Advanced concepts, practical applications, troubleshooting'
          })
        );
      });
    });
  });

  describe('Complete Question Answering Workflow', () => {
    beforeEach(() => {
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: mockGeneratedQuestions
      });
      (bookClient.getChapterQuestionProgress as jest.Mock).mockResolvedValue({
        total_questions: 3,
        answered_questions: 0,
        completion_percentage: 0
      });
      (bookClient.getQuestionResponse as jest.Mock).mockResolvedValue({
        has_response: false,
        response: null
      });
    });

    test('completes full question answering session', async () => {
      (bookClient.saveQuestionResponse as jest.Mock).mockResolvedValue({ success: true });

      render(
        <TestWrapper>
          <QuestionContainer 
            bookId="test-book-id" 
            chapterId="test-chapter-id" 
            chapterTitle="Chapter 1: Getting Started" 
          />
        </TestWrapper>
      );

      // Wait for questions to load
      await waitFor(() => {
        expect(screen.getByText('What are the main learning objectives for this chapter?')).toBeInTheDocument();
      });

      // Answer first question
      const responseTextarea = screen.getByPlaceholderText(/Type your response here/i);
      const response1 = 'The main learning objectives include understanding fundamental concepts, applying basic principles, and building a foundation for advanced topics.';
      
      await user.type(responseTextarea, response1);

      // Auto-save should trigger
      await waitFor(() => {
        expect(bookClient.saveQuestionResponse).toHaveBeenCalledWith(
          'q1',
          response1,
          ResponseStatus.COMPLETE
        );
      });

      // Move to next question
      const nextButton = screen.getByText('Next');
      fireEvent.click(nextButton);

      await waitFor(() => {
        expect(screen.getByText('Who is the target audience for this content?')).toBeInTheDocument();
      });

      // Answer second question
      await user.clear(responseTextarea);
      const response2 = 'The target audience consists of beginner to intermediate developers who want to learn modern software development practices.';
      await user.type(responseTextarea, response2);

      // Rate the question
      const rating4 = screen.getByRole('button', { name: /4 stars/i });
      fireEvent.click(rating4);

      await waitFor(() => {
        expect(bookClient.rateQuestion).toHaveBeenCalledWith('q2', 4);
      });

      // Continue to final question
      fireEvent.click(nextButton);

      await waitFor(() => {
        expect(screen.getByText('What practical examples should be included?')).toBeInTheDocument();
      });

      // Answer final question
      await user.clear(responseTextarea);
      const response3 = 'Practical examples should include step-by-step code walkthroughs, real-world project scenarios, common troubleshooting cases, and hands-on exercises.';
      await user.type(responseTextarea, response3);

      // Mark as complete
      const completeButton = screen.getByText('Mark Complete');
      fireEvent.click(completeButton);

      // Should show completion message
      await waitFor(() => {
        expect(screen.getByText(/All questions completed/i)).toBeInTheDocument();
      });

      // Verify all responses were saved
      expect(bookClient.saveQuestionResponse).toHaveBeenCalledTimes(3);
    });

    test('supports skipping questions and coming back later', async () => {
      (bookClient.saveQuestionResponse as jest.Mock).mockResolvedValue({ success: true });

      render(
        <TestWrapper>
          <QuestionContainer 
            bookId="test-book-id" 
            chapterId="test-chapter-id" 
            chapterTitle="Chapter 1: Getting Started" 
          />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('What are the main learning objectives for this chapter?')).toBeInTheDocument();
      });

      // Skip first question
      const skipButton = screen.getByText('Skip for Now');
      fireEvent.click(skipButton);

      await waitFor(() => {
        expect(bookClient.saveQuestionResponse).toHaveBeenCalledWith(
          'q1',
          '',
          ResponseStatus.SKIPPED
        );
      });

      // Should move to next question
      await waitFor(() => {
        expect(screen.getByText('Who is the target audience for this content?')).toBeInTheDocument();
      });

      // Answer this question
      const responseTextarea = screen.getByPlaceholderText(/Type your response here/i);
      await user.type(responseTextarea, 'Target audience response');

      // Go back to skipped question
      const prevButton = screen.getByText('Previous');
      fireEvent.click(prevButton);

      await waitFor(() => {
        expect(screen.getByText('What are the main learning objectives for this chapter?')).toBeInTheDocument();
      });

      // Should show it was skipped
      expect(screen.getByText(/Skipped/i)).toBeInTheDocument();

      // Now answer the skipped question
      await user.type(responseTextarea, 'Now answering the previously skipped question');

      await waitFor(() => {
        expect(bookClient.saveQuestionResponse).toHaveBeenCalledWith(
          'q1',
          'Now answering the previously skipped question',
          ResponseStatus.COMPLETE
        );
      });
    });
  });

  describe('Integration with Chapter Workflow', () => {
    test('integrates with chapter tabs and progress tracking', async () => {
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: mockGeneratedQuestions
      });
      (bookClient.getChapterQuestionProgress as jest.Mock).mockResolvedValue({
        total_questions: 3,
        answered_questions: 3,
        completion_percentage: 100
      });

      render(
        <TestWrapper>
          <ChapterTabs 
            bookId="test-book-id"
            chapterId="test-chapter-id"
            activeTab="questions"
            onTabChange={() => {}}
          />
        </TestWrapper>
      );

      // Should show completed status on questions tab
      await waitFor(() => {
        expect(screen.getByText(/Questions \(3\/3\)/i)).toBeInTheDocument();
      });

      // Should show checkmark or completion indicator
      const questionsTab = screen.getByText(/Questions/i);
      expect(questionsTab.closest('[data-tab="questions"]')).toHaveClass('completed');
    });

    test('triggers draft generation after question completion', async () => {
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: mockGeneratedQuestions
      });
      (bookClient.getChapterQuestionProgress as jest.Mock).mockResolvedValue({
        total_questions: 3,
        answered_questions: 3,
        completion_percentage: 100
      });
      (draftClient.generateChapterDraft as jest.Mock).mockResolvedValue({
        draft_content: 'Generated draft content based on question responses...',
        metadata: {
          generation_source: 'questions',
          processing_time: 3500
        }
      });

      render(
        <TestWrapper>
          <QuestionContainer 
            bookId="test-book-id" 
            chapterId="test-chapter-id" 
            chapterTitle="Chapter 1: Getting Started" 
          />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText(/All questions completed/i)).toBeInTheDocument();
      });

      // Should show option to generate draft
      const generateDraftButton = screen.getByText('Generate Chapter Draft');
      fireEvent.click(generateDraftButton);

      await waitFor(() => {
        expect(draftClient.generateChapterDraft).toHaveBeenCalledWith(
          'test-book-id',
          'test-chapter-id',
          expect.objectContaining({
            source: 'questions',
            include_responses: true
          })
        );
      });

      // Should redirect to draft tab
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith(
          '/books/test-book-id/chapters/test-chapter-id?tab=draft'
        );
      });
    });

    test('syncs with chapter status updates', async () => {
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: mockGeneratedQuestions
      });
      (bookClient.updateChapterStatus as jest.Mock).mockResolvedValue({ success: true });

      render(
        <TestWrapper>
          <QuestionContainer 
            bookId="test-book-id" 
            chapterId="test-chapter-id" 
            chapterTitle="Chapter 1: Getting Started" 
          />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('What are the main learning objectives for this chapter?')).toBeInTheDocument();
      });

      // Complete all questions (simulated)
      (bookClient.getChapterQuestionProgress as jest.Mock).mockResolvedValue({
        total_questions: 3,
        answered_questions: 3,
        completion_percentage: 100
      });

      // Trigger status update
      const completeChapterButton = screen.getByText('Mark Chapter Ready for Draft');
      fireEvent.click(completeChapterButton);

      await waitFor(() => {
        expect(bookClient.updateChapterStatus).toHaveBeenCalledWith(
          'test-chapter-id',
          'ready_for_draft'
        );
      });
    });
  });

  describe('Error Recovery and Resilience', () => {
    test('recovers from API failures gracefully', async () => {
      // Simulate API failure
      (bookClient.getChapterQuestions as jest.Mock).mockRejectedValueOnce(
        new Error('Network error')
      );

      render(
        <TestWrapper>
          <QuestionContainer 
            bookId="test-book-id" 
            chapterId="test-chapter-id" 
            chapterTitle="Chapter 1: Getting Started" 
          />
        </TestWrapper>
      );

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText(/Error loading questions/i)).toBeInTheDocument();
      });

      // Should provide retry option
      const retryButton = screen.getByText('Retry');
      
      // Mock successful retry
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValueOnce({
        questions: mockGeneratedQuestions
      });

      fireEvent.click(retryButton);

      // Should recover and show questions
      await waitFor(() => {
        expect(screen.getByText('What are the main learning objectives for this chapter?')).toBeInTheDocument();
      });
    });

    test('handles offline scenarios with data persistence', async () => {
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: mockGeneratedQuestions
      });
      (bookClient.saveQuestionResponse as jest.Mock).mockRejectedValue(
        new Error('Network unavailable')
      );

      render(
        <TestWrapper>
          <QuestionContainer 
            bookId="test-book-id" 
            chapterId="test-chapter-id" 
            chapterTitle="Chapter 1: Getting Started" 
          />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('What are the main learning objectives for this chapter?')).toBeInTheDocument();
      });

      // Try to answer question while offline
      const responseTextarea = screen.getByPlaceholderText(/Type your response here/i);
      await user.type(responseTextarea, 'This response should be saved locally');

      // Should show offline indicator
      await waitFor(() => {
        expect(screen.getByText(/Saved locally/i)).toBeInTheDocument();
      });

      // Mock coming back online
      (bookClient.saveQuestionResponse as jest.Mock).mockResolvedValue({ success: true });

      // Should sync when back online
      await waitFor(() => {
        expect(screen.getByText(/Synced/i)).toBeInTheDocument();
      });
    });

    test('handles browser refresh and session recovery', async () => {
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: mockGeneratedQuestions
      });
      (bookClient.getQuestionResponse as jest.Mock).mockResolvedValue({
        has_response: true,
        response: {
          id: 'response1',
          question_id: 'q1',
          response_text: 'Previously saved response',
          status: ResponseStatus.COMPLETE,
          created_at: '2023-01-01T10:30:00Z',
          updated_at: '2023-01-01T10:30:00Z'
        }
      });

      render(
        <TestWrapper>
          <QuestionContainer 
            bookId="test-book-id" 
            chapterId="test-chapter-id" 
            chapterTitle="Chapter 1: Getting Started" 
          />
        </TestWrapper>
      );

      // Should restore previous session
      await waitFor(() => {
        expect(screen.getByDisplayValue('Previously saved response')).toBeInTheDocument();
      });

      // Should maintain progress state
      expect(screen.getByText(/Question 1 of 3/i)).toBeInTheDocument();
    });
  });

  describe('Accessibility and User Experience', () => {
    test('supports keyboard navigation throughout workflow', async () => {
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: mockGeneratedQuestions
      });

      render(
        <TestWrapper>
          <QuestionContainer 
            bookId="test-book-id" 
            chapterId="test-chapter-id" 
            chapterTitle="Chapter 1: Getting Started" 
          />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('What are the main learning objectives for this chapter?')).toBeInTheDocument();
      });

      // Test keyboard navigation
      const responseTextarea = screen.getByPlaceholderText(/Type your response here/i);
      responseTextarea.focus();

      // Tab should move to next button
      await user.tab();
      expect(screen.getByText('Next')).toHaveFocus();

      // Enter should activate button
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(screen.getByText('Who is the target audience for this content?')).toBeInTheDocument();
      });
    });

    test('provides proper ARIA labels and screen reader support', async () => {
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: mockGeneratedQuestions
      });

      render(
        <TestWrapper>
          <QuestionContainer 
            bookId="test-book-id" 
            chapterId="test-chapter-id" 
            chapterTitle="Chapter 1: Getting Started" 
          />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('What are the main learning objectives for this chapter?')).toBeInTheDocument();
      });

      // Check ARIA labels
      expect(screen.getByRole('main')).toHaveAttribute('aria-label', 'Chapter questions');
      expect(screen.getByRole('textbox')).toHaveAttribute('aria-label', expect.stringContaining('Response'));
      expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
      expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuemax', '3');
    });

    test('maintains responsive design across viewport sizes', async () => {
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: mockGeneratedQuestions
      });

      // Test mobile viewport
      Object.defineProperty(window, 'innerWidth', { value: 375 });
      Object.defineProperty(window, 'innerHeight', { value: 667 });

      render(
        <TestWrapper>
          <QuestionContainer 
            bookId="test-book-id" 
            chapterId="test-chapter-id" 
            chapterTitle="Chapter 1: Getting Started" 
          />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('What are the main learning objectives for this chapter?')).toBeInTheDocument();
      });

      // Should adapt layout for mobile
      const container = screen.getByTestId('question-container');
      expect(container).toHaveClass('mobile-layout');

      // Test desktop viewport
      Object.defineProperty(window, 'innerWidth', { value: 1920 });
      Object.defineProperty(window, 'innerHeight', { value: 1080 });

      // Should adapt layout for desktop
      expect(container).toHaveClass('desktop-layout');
    });
  });
});
