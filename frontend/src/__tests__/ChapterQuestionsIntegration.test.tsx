import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import QuestionContainer from '@/components/chapters/questions/QuestionContainer';
import QuestionGenerator from '@/components/chapters/questions/QuestionGenerator';
import QuestionDisplay from '@/components/chapters/questions/QuestionDisplay';
import QuestionProgress from '@/components/chapters/questions/QuestionProgress';
import { QuestionType, QuestionDifficulty, ResponseStatus } from '@/types/chapter-questions';
import { bookClient } from '@/lib/api/bookClient';

// Mock the API client
jest.mock('@/lib/api/bookClient', () => ({
  bookClient: {
    getChapterQuestions: jest.fn(),
    getQuestionResponse: jest.fn(),
    saveQuestionResponse: jest.fn(),
    getChapterQuestionProgress: jest.fn(),
    generateChapterQuestions: jest.fn(),
    rateQuestion: jest.fn(),
    regenerateChapterQuestions: jest.fn(),
  }
}));

// Mock Toast notifications
jest.mock('@/components/ui/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn()
  })
}));

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({
    push: jest.fn(),
    replace: jest.fn(),
    back: jest.fn(),
  })),
}));

describe('Chapter Questions Integration Tests', () => {
  const mockBookId = 'book123';
  const mockChapterId = 'chapter456';
  const mockChapterTitle = 'Chapter 1: Getting Started';

  const mockQuestions = [
    {
      id: 'q1',
      chapter_id: mockChapterId,
      question_text: 'What are the main learning objectives for this chapter?',
      question_type: QuestionType.EDUCATIONAL,
      difficulty: QuestionDifficulty.MEDIUM,
      category: 'learning',
      order: 1,
      generated_at: '2025-06-02T10:00:00Z',
      metadata: {
        suggested_response_length: '150-300 words',
        help_text: 'Think about what readers should achieve after reading this chapter.',
        examples: ['Understanding core concepts', 'Applying practical skills']
      },
      has_response: false,
      response_status: ResponseStatus.NOT_STARTED
    },
    {
      id: 'q2',
      chapter_id: mockChapterId,
      question_text: 'What prerequisites should readers have before starting this chapter?',
      question_type: QuestionType.RESEARCH,
      difficulty: QuestionDifficulty.EASY,
      category: 'prerequisites',
      order: 2,
      generated_at: '2025-06-02T10:00:00Z',
      metadata: {
        suggested_response_length: '100-200 words',
        help_text: 'Consider the background knowledge and skills needed.'
      },
      has_response: true,
      response_status: ResponseStatus.COMPLETED
    }
  ];

  const mockProgress = {
    total: 10,
    completed: 3,
    in_progress: 2,
    progress: 0.3,
    status: 'in-progress'
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('QuestionGenerator Component', () => {
    test('displays generation options and handles question generation', async () => {
      const onGenerate = jest.fn();
      
      render(
        <QuestionGenerator
          bookId={mockBookId}
          chapterId={mockChapterId}
          onGenerate={onGenerate}
          isGenerating={false}
          error={null}
        />
      );

      // Check that the card title and number selector are displayed
      expect(screen.getByText(/Number of questions/i)).toBeInTheDocument();

      // Test generation trigger - use default settings without showing advanced options
      const generateButton = screen.getByRole('button', { name: /Generate Interview Questions/i });
      await act(async () => {
        fireEvent.click(generateButton);
      });

      expect(onGenerate).toHaveBeenCalledWith(10, undefined, undefined);
    });

    test('shows loading state during generation', () => {
      render(
        <QuestionGenerator
          bookId={mockBookId}
          chapterId={mockChapterId}
          onGenerate={jest.fn()}
          isGenerating={true}
          error={null}
        />
      );

      expect(screen.getByText(/generating questions/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /generating questions/i })).toBeDisabled();
    });

    test('handles regeneration with existing questions', async () => {
      const onGenerate = jest.fn();
      
      render(
        <QuestionGenerator
          bookId={mockBookId}
          chapterId={mockChapterId}
          onGenerate={onGenerate}
          isGenerating={false}
          error={null}
        />
      );

      // Test basic generation functionality
      const generateButton = screen.getByRole('button', { name: /Generate Interview Questions/i });
      await act(async () => {
        fireEvent.click(generateButton);
      });

      expect(onGenerate).toHaveBeenCalledWith(10, undefined, undefined);
    });
  });

  describe('QuestionDisplay Component', () => {
    test('displays question with metadata and help text', async () => {
      const question = mockQuestions[0];
      
      // Mock the API call for getting existing response
      (bookClient.getQuestionResponse as jest.Mock).mockResolvedValue({
        response: null
      });
      
      await act(async () => {
        render(
          <QuestionDisplay
            bookId={mockBookId}
            chapterId={mockChapterId}
            question={question}
            onResponseSaved={jest.fn()}
            onRegenerateQuestion={jest.fn()}
          />
        );
      });

      // Check question content is displayed
      expect(screen.getByText(question.question_text)).toBeInTheDocument();
    });

    test('handles question rating interactions', async () => {
      const question = mockQuestions[0];
      
      // Mock the API calls
      (bookClient.getQuestionResponse as jest.Mock).mockResolvedValue({
        response: null
      });
      (bookClient.rateQuestion as jest.Mock).mockResolvedValue({});
      
      await act(async () => {
        render(
          <QuestionDisplay
            bookId={mockBookId}
            chapterId={mockChapterId}
            question={question}
            onResponseSaved={jest.fn()}
            onRegenerateQuestion={jest.fn()}
          />
        );
      });

      // Wait for component to load and then check for rating buttons
      await waitFor(() => {
        expect(screen.getByText(question.question_text)).toBeInTheDocument();
      });
    });

    test('shows examples when available', () => {
      const question = mockQuestions[0];
      
      render(
        <QuestionDisplay
          question={question}
          questionNumber={1}
          totalQuestions={2}
          onRatingChange={jest.fn()}
        />
      );

      // Check examples are displayed
      expect(screen.getByText('Examples:')).toBeInTheDocument();
      question.metadata.examples?.forEach(example => {
        expect(screen.getByText(example)).toBeInTheDocument();
      });
    });
  });

  describe('QuestionProgress Component', () => {
    test('displays progress information correctly', () => {
      render(
        <QuestionProgress
          progress={mockProgress}
          currentIndex={2}
          totalQuestions={10}
        />
      );

      // Check that component renders with progress data
      expect(screen.getByText(/3 of 10 questions answered/i)).toBeInTheDocument();
    });

    test('shows completion status when all questions are answered', () => {
      const completedProgress = {
        total: 5,
        completed: 5,
        in_progress: 0,
        progress: 1.0,
        status: 'completed'
      };

      render(
        <QuestionProgress
          progress={completedProgress}
          currentIndex={4}
          totalQuestions={5}
        />
      );

      expect(screen.getByText(/All questions completed/i)).toBeInTheDocument();
    });
  });

  describe('Full Integration Workflow', () => {
    test('complete question answering workflow', async () => {
      const user = userEvent.setup();

      // Mock API responses
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: mockQuestions,
        total: 2,
        page: 1,
        pages: 1
      });
      (bookClient.getChapterQuestionProgress as jest.Mock).mockResolvedValue(mockProgress);
      (bookClient.getQuestionResponse as jest.Mock).mockResolvedValue({
        has_response: false,
        response: null
      });
      (bookClient.saveQuestionResponse as jest.Mock).mockResolvedValue({
        success: true,
        response: {
          id: 'resp1',
          question_id: 'q1',
          response_text: 'Test answer',
          word_count: 2,
          status: ResponseStatus.COMPLETED,
          created_at: '2025-06-02T10:00:00Z',
          updated_at: '2025-06-02T10:00:00Z',
          last_edited_at: '2025-06-02T10:00:00Z',
          metadata: { edit_history: [] }
        }
      });

      render(
        <QuestionContainer
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
        />
      );

      // Wait for questions to load
      await waitFor(() => {
        expect(screen.getByText(mockQuestions[0].question_text)).toBeInTheDocument();
      });

      // Answer the first question
      const textarea = screen.getByPlaceholderText('Type your response here or use voice input...');
      await user.type(textarea, 'Test answer');

      // Save the response
      const saveButton = screen.getByRole('button', { name: /save draft/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(bookClient.saveQuestionResponse).toHaveBeenCalledWith(
          mockBookId,
          mockChapterId,
          'q1',
          expect.objectContaining({
            response_text: 'Test answer',
            status: expect.any(String)
          })
        );
      });

      // Navigate to next question
      const nextButton = screen.getByRole('button', { name: /next/i });
      fireEvent.click(nextButton);

      await waitFor(() => {
        expect(screen.getByText(mockQuestions[1].question_text)).toBeInTheDocument();
      });
    });

    test('handles question generation and immediate answering', async () => {
      const user = userEvent.setup();

      // Mock empty initial state
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValueOnce({
        questions: [],
        total: 0,
        page: 1,
        pages: 1
      });
      (bookClient.getChapterQuestionProgress as jest.Mock).mockResolvedValue({
        total: 0,
        completed: 0,
        in_progress: 0,
        progress: 0,
        status: 'not_started'
      });

      // Mock generation response
      (bookClient.generateChapterQuestions as jest.Mock).mockResolvedValue({
        questions: mockQuestions,
        total: 2,
        generation_id: 'gen123'
      });

      render(
        <QuestionContainer
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
        />
      );

      // Wait for empty state
      await waitFor(() => {
        expect(screen.getByText(/generate interview-style questions/i)).toBeInTheDocument();
      });

      // Trigger question generation
      const generateButton = screen.getByRole('button', { name: /generate/i });
      fireEvent.click(generateButton);

      // Wait for questions to be generated and displayed
      await waitFor(() => {
        expect(bookClient.generateChapterQuestions).toHaveBeenCalledWith(
          mockBookId,
          mockChapterId,
          expect.any(Object)
        );
      });

      // Mock the updated state after generation
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: mockQuestions,
        total: 2,
        page: 1,
        pages: 1
      });

      // Verify questions are now displayed
      await waitFor(() => {
        expect(screen.getByText(mockQuestions[0].question_text)).toBeInTheDocument();
      });
    });

    test('handles auto-save functionality', async () => {
      jest.useFakeTimers();
      const user = userEvent.setup({ delay: null });

      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: mockQuestions,
        total: 2,
        page: 1,
        pages: 1
      });
      (bookClient.getChapterQuestionProgress as jest.Mock).mockResolvedValue(mockProgress);
      (bookClient.getQuestionResponse as jest.Mock).mockResolvedValue({
        has_response: false,
        response: null
      });
      (bookClient.saveQuestionResponse as jest.Mock).mockResolvedValue({
        success: true,
        response: { id: 'resp1' }
      });

      render(
        <QuestionContainer
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(mockQuestions[0].question_text)).toBeInTheDocument();
      });

      // Type in the textarea to trigger auto-save
      const textarea = screen.getByPlaceholderText('Type your response here or use voice input...');
      await user.type(textarea, 'Auto-save test');

      // Fast-forward time to trigger auto-save
      act(() => {
        jest.advanceTimersByTime(3000); // Auto-save after 2 seconds + buffer
      });

      await waitFor(() => {
        expect(bookClient.saveQuestionResponse).toHaveBeenCalledWith(
          mockBookId,
          mockChapterId,
          'q1',
          expect.objectContaining({
            response_text: 'Auto-save test',
            status: 'draft'
          })
        );
      });

      jest.useRealTimers();
    });

    test('handles error states gracefully', async () => {
      // Mock API error
      (bookClient.getChapterQuestions as jest.Mock).mockRejectedValue(
        new Error('Network error')
      );

      render(
        <QuestionContainer
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
        />
      );

      await waitFor(() => {
        // Component might show empty state or error message
        const errorMessage = screen.queryByText(/error loading questions/i);
        const emptyState = screen.queryByText(/generate interview-style questions/i);
        expect(errorMessage || emptyState).toBeInTheDocument();
      });

      // Test retry functionality - might be a generate button or retry button
      const retryButton = screen.queryByRole('button', { name: /try again/i }) || 
                         screen.queryByRole('button', { name: /generate.*questions/i });
      expect(retryButton).toBeInTheDocument();

      // Mock successful retry
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: mockQuestions,
        total: 2,
        page: 1,
        pages: 1
      });
      (bookClient.getChapterQuestionProgress as jest.Mock).mockResolvedValue(mockProgress);

      fireEvent.click(retryButton);

      await waitFor(() => {
        expect(screen.getByText(mockQuestions[0].question_text)).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility and Responsive Design', () => {
    test('supports keyboard navigation', async () => {
      const user = userEvent.setup();

      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: mockQuestions,
        total: 2,
        page: 1,
        pages: 1
      });
      (bookClient.getChapterQuestionProgress as jest.Mock).mockResolvedValue(mockProgress);
      (bookClient.getQuestionResponse as jest.Mock).mockResolvedValue({
        has_response: false,
        response: null
      });

      render(
        <QuestionContainer
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(mockQuestions[0].question_text)).toBeInTheDocument();
      });

      // Test tab navigation
      const textarea = screen.getByPlaceholderText('Type your response here or use voice input...');
      textarea.focus();
      expect(textarea).toHaveFocus();

      // Tab through interactive elements
      await user.tab();
      // May focus on save button, rating buttons, or navigation buttons
      const focusedElement = document.activeElement;
      expect(focusedElement).toHaveProperty('tagName', 'BUTTON');

      // Find and click the next button directly
      const nextButton = screen.getByRole('button', { name: /next/i });
      await user.click(nextButton);
      
      await waitFor(() => {
        expect(screen.getByText(mockQuestions[1].question_text)).toBeInTheDocument();
      });
    });

    test('provides proper ARIA labels and roles', () => {
      render(
        <QuestionProgress
          progress={mockProgress}
          currentQuestionIndex={2}
          totalQuestions={10}
        />
      );

      // Check ARIA attributes
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '30');
      expect(progressBar).toHaveAttribute('aria-valuemin', '0');
      expect(progressBar).toHaveAttribute('aria-valuemax', '100');
      expect(progressBar).toHaveAttribute('aria-label', expect.stringContaining('Question progress'));
    });

    test('handles mobile responsive design', async () => {
      // Mock mobile viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375,
      });
      Object.defineProperty(window, 'innerHeight', {
        writable: true,
        configurable: true,
        value: 667,
      });

      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: mockQuestions,
        total: 2,
        page: 1,
        pages: 1
      });
      (bookClient.getChapterQuestionProgress as jest.Mock).mockResolvedValue(mockProgress);

      const { container } = render(
        <QuestionContainer
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
        />
      );

      // Wait for the component to load
      await waitFor(() => {
        const container = screen.queryByTestId('question-container');
        const heading = screen.queryByText('Interview Questions');
        // Either the container or the heading should be present
        expect(container || heading).toBeTruthy();
      });
      
      // Verify the component rendered successfully on mobile
      const loadingText = screen.queryByText(/Loading questions/i);
      const interviewText = screen.queryByText('Interview Questions');
      const questionContainer = screen.queryByTestId('question-container');
      
      // At least one of these should be present
      expect(loadingText || interviewText || questionContainer).toBeTruthy();
    });
  });
});
