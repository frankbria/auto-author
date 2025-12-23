import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import { DraftGenerationButton } from '@/components/chapters/questions/DraftGenerationButton';
import { bookClient } from '@/lib/api/bookClient';
import { ResponseStatus } from '@/types/chapter-questions';

// Mock the API client
jest.mock('@/lib/api/bookClient', () => ({
  bookClient: {
    getChapterQAResponses: jest.fn(),
    generateChapterDraft: jest.fn(),
  }
}));

// Mock Toast notifications
jest.mock('@/components/ui/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn()
  })
}));

// Mock loading components
jest.mock('@/components/loading', () => ({
  LoadingStateManager: ({ isLoading, message }: { isLoading: boolean; message: string }) => (
    isLoading ? <div data-testid="loading-state">{message}</div> : null
  )
}));

jest.mock('@/lib/loading', () => ({
  createProgressTracker: () => () => ({ progress: 50, estimatedTimeRemaining: 10 })
}));

// Mock DOMPurify
jest.mock('dompurify', () => ({
  sanitize: (content: string) => content
}));

describe('DraftGenerationButton', () => {
  const mockBookId = 'book123';
  const mockChapterId = 'chapter456';
  const mockChapterTitle = 'Test Chapter';

  const mockQAResponses = {
    responses: [
      { question: 'What is the main topic?', answer: 'The main topic is testing', questionId: 'q1', status: 'completed' },
      { question: 'Who is the target audience?', answer: 'Developers learning testing', questionId: 'q2', status: 'completed' },
      { question: 'What are the key takeaways?', answer: 'Understanding test patterns', questionId: 'q3', status: 'completed' },
    ],
    totalQuestions: 5,
    completedCount: 3,
    inProgressCount: 1
  };

  const mockDraftResponse = {
    success: true,
    book_id: mockBookId,
    chapter_id: mockChapterId,
    draft: '<p>This is the generated draft content based on your answers.</p>',
    metadata: {
      word_count: 150,
      estimated_reading_time: 1,
      generated_at: '2025-12-23T10:00:00Z',
      model_used: 'gpt-4',
      writing_style: 'conversational',
      target_length: 2000,
      actual_length: 150
    },
    suggestions: ['Add more examples', 'Consider adding a summary section'],
    message: 'Draft generated successfully'
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (bookClient.getChapterQAResponses as jest.Mock).mockResolvedValue(mockQAResponses);
    (bookClient.generateChapterDraft as jest.Mock).mockResolvedValue(mockDraftResponse);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Button State', () => {
    it('shows button as disabled when not enough responses are completed', () => {
      render(
        <DraftGenerationButton
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
          completedCount={2}
          totalQuestions={10}
        />
      );

      const button = screen.getByRole('button', { name: /generate draft from answers/i });
      expect(button).toBeDisabled();
    });

    it('shows button as enabled when minimum responses are completed', () => {
      render(
        <DraftGenerationButton
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
          completedCount={3}
          totalQuestions={10}
        />
      );

      const button = screen.getByRole('button', { name: /generate draft from answers/i });
      expect(button).not.toBeDisabled();
    });

    it('shows correct progress text', () => {
      render(
        <DraftGenerationButton
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
          completedCount={5}
          totalQuestions={10}
        />
      );

      expect(screen.getByText(/5 of 10 questions completed/i)).toBeInTheDocument();
    });

    it('shows ready message when enough responses are completed', () => {
      render(
        <DraftGenerationButton
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
          completedCount={5}
          totalQuestions={10}
        />
      );

      expect(screen.getByText(/ready to generate draft/i)).toBeInTheDocument();
    });

    it('shows need more responses message when not enough completed', () => {
      render(
        <DraftGenerationButton
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
          completedCount={1}
          totalQuestions={10}
          minimumResponses={3}
        />
      );

      expect(screen.getByText(/need 2 more responses/i)).toBeInTheDocument();
    });
  });

  describe('Dialog Behavior', () => {
    it('opens dialog when button is clicked', async () => {
      render(
        <DraftGenerationButton
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
          completedCount={5}
          totalQuestions={10}
        />
      );

      const button = screen.getByRole('button', { name: /generate draft from answers/i });
      await userEvent.click(button);

      expect(screen.getByText(/generate ai draft for/i)).toBeInTheDocument();
    });

    it('shows writing style options in dialog', async () => {
      render(
        <DraftGenerationButton
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
          completedCount={5}
          totalQuestions={10}
        />
      );

      const button = screen.getByRole('button', { name: /generate draft from answers/i });
      await userEvent.click(button);

      expect(screen.getByLabelText(/writing style/i)).toBeInTheDocument();
    });

    it('shows target word count options', async () => {
      render(
        <DraftGenerationButton
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
          completedCount={5}
          totalQuestions={10}
        />
      );

      const button = screen.getByRole('button', { name: /generate draft from answers/i });
      await userEvent.click(button);

      expect(screen.getByText(/target word count/i)).toBeInTheDocument();
    });
  });

  describe('Draft Generation', () => {
    it('calls API to generate draft when generate button is clicked', async () => {
      render(
        <DraftGenerationButton
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
          completedCount={5}
          totalQuestions={10}
        />
      );

      // Open dialog
      const openButton = screen.getByRole('button', { name: /generate draft from answers/i });
      await userEvent.click(openButton);

      // Click generate
      const generateButton = screen.getByRole('button', { name: /^generate draft$/i });
      await userEvent.click(generateButton);

      await waitFor(() => {
        expect(bookClient.getChapterQAResponses).toHaveBeenCalledWith(mockBookId, mockChapterId);
      });

      await waitFor(() => {
        expect(bookClient.generateChapterDraft).toHaveBeenCalled();
      });
    });

    it('shows preview after draft is generated', async () => {
      render(
        <DraftGenerationButton
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
          completedCount={5}
          totalQuestions={10}
        />
      );

      // Open dialog
      const openButton = screen.getByRole('button', { name: /generate draft from answers/i });
      await userEvent.click(openButton);

      // Click generate
      const generateButton = screen.getByRole('button', { name: /^generate draft$/i });
      await userEvent.click(generateButton);

      await waitFor(() => {
        expect(screen.getByText(/this is the generated draft content/i)).toBeInTheDocument();
      });
    });

    it('shows word count and reading time in preview', async () => {
      render(
        <DraftGenerationButton
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
          completedCount={5}
          totalQuestions={10}
        />
      );

      // Open dialog and generate
      const openButton = screen.getByRole('button', { name: /generate draft from answers/i });
      await userEvent.click(openButton);
      const generateButton = screen.getByRole('button', { name: /^generate draft$/i });
      await userEvent.click(generateButton);

      await waitFor(() => {
        expect(screen.getByText(/150 words/i)).toBeInTheDocument();
        expect(screen.getByText(/1 min read/i)).toBeInTheDocument();
      });
    });

    it('shows suggestions when available', async () => {
      render(
        <DraftGenerationButton
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
          completedCount={5}
          totalQuestions={10}
        />
      );

      // Open dialog and generate
      const openButton = screen.getByRole('button', { name: /generate draft from answers/i });
      await userEvent.click(openButton);
      const generateButton = screen.getByRole('button', { name: /^generate draft$/i });
      await userEvent.click(generateButton);

      await waitFor(() => {
        expect(screen.getByText(/add more examples/i)).toBeInTheDocument();
      });
    });
  });

  describe('Draft Usage', () => {
    it('calls onDraftGenerated callback when Use This Draft is clicked', async () => {
      const onDraftGenerated = jest.fn();

      render(
        <DraftGenerationButton
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
          completedCount={5}
          totalQuestions={10}
          onDraftGenerated={onDraftGenerated}
        />
      );

      // Open dialog and generate
      const openButton = screen.getByRole('button', { name: /generate draft from answers/i });
      await userEvent.click(openButton);
      const generateButton = screen.getByRole('button', { name: /^generate draft$/i });
      await userEvent.click(generateButton);

      await waitFor(() => {
        expect(screen.getByText(/this is the generated draft content/i)).toBeInTheDocument();
      });

      // Click use this draft
      const useButton = screen.getByRole('button', { name: /use this draft/i });
      await userEvent.click(useButton);

      expect(onDraftGenerated).toHaveBeenCalledWith(mockDraftResponse.draft);
    });

    it('calls onSwitchToEditor when draft is used', async () => {
      const onDraftGenerated = jest.fn();
      const onSwitchToEditor = jest.fn();

      render(
        <DraftGenerationButton
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
          completedCount={5}
          totalQuestions={10}
          onDraftGenerated={onDraftGenerated}
          onSwitchToEditor={onSwitchToEditor}
        />
      );

      // Open dialog and generate
      const openButton = screen.getByRole('button', { name: /generate draft from answers/i });
      await userEvent.click(openButton);
      const generateButton = screen.getByRole('button', { name: /^generate draft$/i });
      await userEvent.click(generateButton);

      await waitFor(() => {
        expect(screen.getByText(/this is the generated draft content/i)).toBeInTheDocument();
      });

      // Click use this draft
      const useButton = screen.getByRole('button', { name: /use this draft/i });
      await userEvent.click(useButton);

      expect(onSwitchToEditor).toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    it('shows error message when draft generation fails', async () => {
      (bookClient.generateChapterDraft as jest.Mock).mockRejectedValue(new Error('API Error'));

      render(
        <DraftGenerationButton
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
          completedCount={5}
          totalQuestions={10}
        />
      );

      // Open dialog and generate
      const openButton = screen.getByRole('button', { name: /generate draft from answers/i });
      await userEvent.click(openButton);
      const generateButton = screen.getByRole('button', { name: /^generate draft$/i });
      await userEvent.click(generateButton);

      await waitFor(() => {
        expect(screen.getByText(/api error/i)).toBeInTheDocument();
      });
    });

    it('shows error when not enough completed responses', async () => {
      (bookClient.getChapterQAResponses as jest.Mock).mockResolvedValue({
        responses: [
          { question: 'Q1', answer: 'A1', questionId: 'q1', status: 'completed' },
        ],
        totalQuestions: 5,
        completedCount: 1,
        inProgressCount: 0
      });

      render(
        <DraftGenerationButton
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
          completedCount={5}
          totalQuestions={10}
          minimumResponses={3}
        />
      );

      // Open dialog and generate
      const openButton = screen.getByRole('button', { name: /generate draft from answers/i });
      await userEvent.click(openButton);
      const generateButton = screen.getByRole('button', { name: /^generate draft$/i });
      await userEvent.click(generateButton);

      await waitFor(() => {
        expect(screen.getByText(/need at least 3 completed responses/i)).toBeInTheDocument();
      });
    });
  });

  describe('Regeneration', () => {
    it('allows regenerating draft with different options', async () => {
      render(
        <DraftGenerationButton
          bookId={mockBookId}
          chapterId={mockChapterId}
          chapterTitle={mockChapterTitle}
          completedCount={5}
          totalQuestions={10}
        />
      );

      // Open dialog and generate
      const openButton = screen.getByRole('button', { name: /generate draft from answers/i });
      await userEvent.click(openButton);
      const generateButton = screen.getByRole('button', { name: /^generate draft$/i });
      await userEvent.click(generateButton);

      await waitFor(() => {
        expect(screen.getByText(/this is the generated draft content/i)).toBeInTheDocument();
      });

      // Click regenerate
      const regenerateButton = screen.getByRole('button', { name: /regenerate/i });
      await userEvent.click(regenerateButton);

      // Should be back to options - wait for the state to update
      await waitFor(() => {
        expect(screen.getByLabelText(/writing style/i)).toBeInTheDocument();
      });
    });
  });
});
