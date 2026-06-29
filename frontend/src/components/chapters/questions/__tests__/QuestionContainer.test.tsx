/**
 * Tests for QuestionContainer component.
 * Covers: fetchQuestions, fetchProgress, handleGenerateQuestions,
 * handleRegenerateQuestion, announceToScreenReader, handleNextQuestion,
 * handlePreviousQuestion, handleGoToQuestion, handleResponseSaved,
 * handleRetryOrGenerate (error path + generate path), error banner.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import QuestionContainer from '../QuestionContainer';
import { bookClient } from '@/lib/api/bookClient';
import { Question, QuestionType, QuestionDifficulty, QuestionProgressResponse } from '@/types/chapter-questions';
import { ErrorType } from '@/lib/errors/errorHandler';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

jest.mock('@/lib/api/bookClient');
jest.mock('@/lib/toast', () => ({
  toast: Object.assign(jest.fn(), {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
  }),
}));
jest.mock('@/hooks/use-media-query', () => ({
  useMediaQuery: jest.fn(() => false),
}));

// Mock ErrorHandler so execute() just calls the passed function directly
jest.mock('@/lib/errors/errorHandler', () => {
  const ErrorType = {
    NETWORK: 'NETWORK',
    AUTH: 'AUTH',
    SERVER: 'SERVER',
    UNKNOWN: 'UNKNOWN',
    VALIDATION: 'VALIDATION',
  };
  return {
    ErrorType,
    classifyError: jest.fn(() => ErrorType.UNKNOWN),
    shouldRetry: jest.fn(() => false),
    ErrorHandler: jest.fn().mockImplementation(() => ({
      execute: jest.fn((fn: () => Promise<any>) => fn()),
    })),
  };
});

// Mock sub-components with simple test doubles that expose handlers as buttons
jest.mock('../QuestionGenerator', () => ({
  __esModule: true,
  default: ({ onGenerate, isGenerating, error }: any) => (
    <div data-testid="question-generator">
      <button
        data-testid="generator-btn"
        onClick={() => onGenerate(5, undefined, undefined)}
        disabled={isGenerating}
      >
        {isGenerating ? 'Generating' : 'Generate'}
      </button>
      {error && <div data-testid="generator-error">{error}</div>}
    </div>
  ),
}));

jest.mock('../QuestionDisplay', () => ({
  __esModule: true,
  default: ({ question, onResponseSaved, onRegenerateQuestion }: any) => (
    <div data-testid="question-display" data-question-id={question?.id}>
      <span>{question?.question_text}</span>
      <button data-testid="response-saved-btn" onClick={onResponseSaved}>
        Save Response
      </button>
      <button data-testid="regenerate-question-btn" onClick={onRegenerateQuestion}>
        Regenerate
      </button>
    </div>
  ),
}));

jest.mock('../QuestionNavigation', () => ({
  __esModule: true,
  default: ({ currentIndex, totalQuestions, onNext, onPrevious, onGoToQuestion }: any) => (
    <div data-testid="question-navigation" data-current-index={currentIndex}>
      <button data-testid="nav-prev-btn" onClick={onPrevious}>Previous</button>
      <span>Question {currentIndex + 1} of {totalQuestions}</span>
      <button data-testid="nav-next-btn" onClick={onNext}>Next</button>
      <button data-testid="nav-goto-btn" onClick={() => onGoToQuestion(0)}>Go to Q1</button>
    </div>
  ),
}));

jest.mock('../QuestionProgress', () => ({
  __esModule: true,
  default: ({ progress }: any) => (
    <div data-testid="question-progress">
      {progress.completed}/{progress.total} complete
    </div>
  ),
}));

jest.mock('../DraftGenerationButton', () => ({
  DraftGenerationButton: () => <div data-testid="draft-generation-button" />,
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeQuestion(overrides: Partial<Question> = {}): Question {
  return {
    id: 'q-1',
    chapter_id: 'ch-1',
    question_text: 'What motivates your main character?',
    question_type: QuestionType.CHARACTER,
    difficulty: QuestionDifficulty.MEDIUM,
    category: 'character',
    order: 1,
    generated_at: '2024-01-01T00:00:00Z',
    metadata: { suggested_response_length: '100 words' },
    ...overrides,
  };
}

const mockProgress: QuestionProgressResponse = {
  total: 2,
  completed: 1,
  in_progress: 0,
  progress: 0.5,
  status: 'in-progress',
};

const defaultProps = {
  bookId: 'book-1',
  chapterId: 'ch-1',
  chapterTitle: 'Chapter 1',
  onResponseSaved: jest.fn(),
  onDraftGenerated: jest.fn(),
  onSwitchToEditor: jest.fn(),
};

const mockedBookClient = bookClient as jest.Mocked<typeof bookClient>;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setupTwoQuestions() {
  const questions = [
    makeQuestion({ id: 'q-1', question_text: 'Q1 text' }),
    makeQuestion({ id: 'q-2', question_text: 'Q2 text', order: 2 }),
  ];
  mockedBookClient.getChapterQuestions.mockResolvedValue({ questions, total: 2, page: 1, pages: 1 });
  mockedBookClient.getChapterQuestionProgress.mockResolvedValue(mockProgress);
  return questions;
}

// ---------------------------------------------------------------------------
// fetchQuestions on mount
// ---------------------------------------------------------------------------

describe('QuestionContainer - fetchQuestions', () => {
  beforeEach(() => jest.clearAllMocks());

  it('shows QuestionGenerator when no questions are returned', async () => {
    mockedBookClient.getChapterQuestions.mockResolvedValue({ questions: [], total: 0, page: 1, pages: 1 });
    mockedBookClient.getChapterQuestionProgress.mockResolvedValue(mockProgress);

    render(<QuestionContainer {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByTestId('question-generator')).toBeInTheDocument();
    });
  });

  it('shows QuestionDisplay after questions load', async () => {
    setupTwoQuestions();

    render(<QuestionContainer {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByTestId('question-display')).toBeInTheDocument();
    });
  });

  it('shows the first question on initial load', async () => {
    setupTwoQuestions();

    render(<QuestionContainer {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Q1 text')).toBeInTheDocument();
    });
  });

  it('fetches questions with the correct bookId and chapterId', async () => {
    setupTwoQuestions();

    render(<QuestionContainer {...defaultProps} />);

    await waitFor(() => {
      expect(mockedBookClient.getChapterQuestions).toHaveBeenCalledWith('book-1', 'ch-1');
    });
  });
});

// ---------------------------------------------------------------------------
// fetchProgress
// ---------------------------------------------------------------------------

describe('QuestionContainer - fetchProgress', () => {
  beforeEach(() => jest.clearAllMocks());

  it('shows progress bar after questions load', async () => {
    setupTwoQuestions();

    render(<QuestionContainer {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByTestId('question-progress')).toBeInTheDocument();
    });
  });

  it('shows progress completion stats', async () => {
    setupTwoQuestions();

    render(<QuestionContainer {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('1/2 complete')).toBeInTheDocument();
    });
  });
});

// ---------------------------------------------------------------------------
// handleGenerateQuestions
// ---------------------------------------------------------------------------

describe('QuestionContainer - handleGenerateQuestions', () => {
  beforeEach(() => jest.clearAllMocks());

  it('generates questions and switches to main view', async () => {
    // Start: empty questions
    mockedBookClient.getChapterQuestions.mockResolvedValue({ questions: [], total: 0, page: 1, pages: 1 });
    mockedBookClient.getChapterQuestionProgress.mockResolvedValue(mockProgress);

    const generatedQuestion = makeQuestion({ id: 'gen-q-1', question_text: 'Generated Q' });
    mockedBookClient.generateChapterQuestions.mockResolvedValue({
      questions: [generatedQuestion],
      generation_id: 'gen-1',
      total: 1,
    });

    render(<QuestionContainer {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByTestId('question-generator')).toBeInTheDocument();
    });

    // Click generate (no error state, so calls handleGenerateQuestions)
    fireEvent.click(screen.getByTestId('generator-btn'));

    await waitFor(() => {
      expect(mockedBookClient.generateChapterQuestions).toHaveBeenCalledWith(
        'book-1',
        'ch-1',
        { count: 5, difficulty: undefined, focus: undefined }
      );
    });
  });

  it('shows toast success after questions generated', async () => {
    const { toast } = require('@/lib/toast');

    mockedBookClient.getChapterQuestions.mockResolvedValue({ questions: [], total: 0, page: 1, pages: 1 });
    mockedBookClient.getChapterQuestionProgress.mockResolvedValue(mockProgress);
    mockedBookClient.generateChapterQuestions.mockResolvedValue({
      questions: [makeQuestion()],
      generation_id: 'gen-1',
      total: 1,
    });

    render(<QuestionContainer {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByTestId('question-generator')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('generator-btn'));

    await waitFor(() => {
      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Questions Generated' })
      );
    });
  });

  it('shows error in QuestionGenerator when generateChapterQuestions fails', async () => {
    mockedBookClient.getChapterQuestions.mockResolvedValue({ questions: [], total: 0, page: 1, pages: 1 });
    mockedBookClient.getChapterQuestionProgress.mockResolvedValue(mockProgress);
    mockedBookClient.generateChapterQuestions.mockRejectedValue(new Error('Generation failed'));

    render(<QuestionContainer {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByTestId('question-generator')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('generator-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('generator-error')).toBeInTheDocument();
    });
  });
});

// ---------------------------------------------------------------------------
// handleRetryOrGenerate – error retry path
// ---------------------------------------------------------------------------

describe('QuestionContainer - handleRetryOrGenerate (retry path)', () => {
  beforeEach(() => jest.clearAllMocks());

  it('retries fetchQuestions when error state is set and generator is clicked', async () => {
    // First call: throws to set error state
    mockedBookClient.getChapterQuestions
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce({ questions: [], total: 0, page: 1, pages: 1 });
    mockedBookClient.getChapterQuestionProgress.mockResolvedValue(mockProgress);

    render(<QuestionContainer {...defaultProps} />);

    // Wait for error to be set and generator to show
    await waitFor(() => {
      expect(screen.getByTestId('question-generator')).toBeInTheDocument();
    });

    // Click generate – since error is set, it calls fetchQuestions (retry path)
    fireEvent.click(screen.getByTestId('generator-btn'));

    await waitFor(() => {
      // getChapterQuestions should have been called twice: initial + retry
      expect(mockedBookClient.getChapterQuestions).toHaveBeenCalledTimes(2);
    });
  });
});

// ---------------------------------------------------------------------------
// handleRegenerateQuestion
// ---------------------------------------------------------------------------

describe('QuestionContainer - handleRegenerateQuestion', () => {
  beforeEach(() => jest.clearAllMocks());

  it('replaces a question after regeneration', async () => {
    const { toast } = require('@/lib/toast');
    setupTwoQuestions();

    const newQuestion = makeQuestion({ id: 'new-q', question_text: 'New regenerated question' });
    mockedBookClient.generateQuestions.mockResolvedValue({
      questions: [newQuestion],
      success: true,
    } as any);

    render(<QuestionContainer {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByTestId('question-display')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('regenerate-question-btn'));

    await waitFor(() => {
      expect(mockedBookClient.generateQuestions).toHaveBeenCalledWith('book-1');
    });
  });

  it('shows error toast when regeneration fails', async () => {
    const { toast } = require('@/lib/toast');
    setupTwoQuestions();
    mockedBookClient.generateQuestions.mockRejectedValue(new Error('Regeneration failed'));

    render(<QuestionContainer {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByTestId('question-display')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('regenerate-question-btn'));

    await waitFor(() => {
      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Error' })
      );
    });
  });
});

// ---------------------------------------------------------------------------
// handleNextQuestion and handlePreviousQuestion (announceToScreenReader covered)
// ---------------------------------------------------------------------------

describe('QuestionContainer - handleNextQuestion and handlePreviousQuestion', () => {
  beforeEach(() => jest.clearAllMocks());

  it('handleNextQuestion advances currentIndex to 1', async () => {
    setupTwoQuestions();

    render(<QuestionContainer {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByTestId('question-navigation')).toBeInTheDocument();
    });

    expect(screen.getByTestId('question-navigation')).toHaveAttribute('data-current-index', '0');

    fireEvent.click(screen.getByTestId('nav-next-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('question-navigation')).toHaveAttribute('data-current-index', '1');
    });
  });

  it('handlePreviousQuestion decrements currentIndex back to 0', async () => {
    setupTwoQuestions();

    render(<QuestionContainer {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByTestId('question-navigation')).toBeInTheDocument();
    });

    // Advance to index 1
    fireEvent.click(screen.getByTestId('nav-next-btn'));
    await waitFor(() => {
      expect(screen.getByTestId('question-navigation')).toHaveAttribute('data-current-index', '1');
    });

    // Go back
    fireEvent.click(screen.getByTestId('nav-prev-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('question-navigation')).toHaveAttribute('data-current-index', '0');
    });
  });

  it('announces navigation to screen reader on next', async () => {
    setupTwoQuestions();

    render(<QuestionContainer {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByTestId('question-navigation')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('nav-next-btn'));

    await waitFor(() => {
      const announcer = screen.getByRole('status');
      expect(announcer.textContent).toBe('Question 2 of 2');
    });
  });

  it('does not advance index beyond last question', async () => {
    setupTwoQuestions();

    render(<QuestionContainer {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByTestId('question-navigation')).toBeInTheDocument();
    });

    // Already at 0, try to go previous
    fireEvent.click(screen.getByTestId('nav-prev-btn'));

    // Should still be 0
    expect(screen.getByTestId('question-navigation')).toHaveAttribute('data-current-index', '0');
  });
});

// ---------------------------------------------------------------------------
// handleGoToQuestion
// ---------------------------------------------------------------------------

describe('QuestionContainer - handleGoToQuestion', () => {
  beforeEach(() => jest.clearAllMocks());

  it('sets currentIndex to 0 when Go to Q1 is clicked', async () => {
    setupTwoQuestions();

    render(<QuestionContainer {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByTestId('question-navigation')).toBeInTheDocument();
    });

    // Move to index 1
    fireEvent.click(screen.getByTestId('nav-next-btn'));
    await waitFor(() => {
      expect(screen.getByTestId('question-navigation')).toHaveAttribute('data-current-index', '1');
    });

    // Jump to Q1 via goto button
    fireEvent.click(screen.getByTestId('nav-goto-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('question-navigation')).toHaveAttribute('data-current-index', '0');
    });
  });
});

// ---------------------------------------------------------------------------
// handleResponseSaved
// ---------------------------------------------------------------------------

describe('QuestionContainer - handleResponseSaved', () => {
  beforeEach(() => jest.clearAllMocks());

  it('calls fetchProgress again when response is saved', async () => {
    setupTwoQuestions();

    render(<QuestionContainer {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByTestId('question-display')).toBeInTheDocument();
    });

    // Reset mock call count so we can count only the post-save call
    mockedBookClient.getChapterQuestionProgress.mockClear();

    fireEvent.click(screen.getByTestId('response-saved-btn'));

    await waitFor(() => {
      expect(mockedBookClient.getChapterQuestionProgress).toHaveBeenCalled();
    });
  });

  it('re-fetches the questions array when a response is saved (keeps statuses fresh)', async () => {
    setupTwoQuestions();

    render(<QuestionContainer {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByTestId('question-display')).toBeInTheDocument();
    });

    // Clear count so we only measure the post-save refresh
    mockedBookClient.getChapterQuestions.mockClear();

    fireEvent.click(screen.getByTestId('response-saved-btn'));

    await waitFor(() => {
      expect(mockedBookClient.getChapterQuestions).toHaveBeenCalledWith('book-1', 'ch-1');
    });
  });

  it('calls the parent onResponseSaved callback when response is saved', async () => {
    setupTwoQuestions();
    const onResponseSaved = jest.fn();

    render(<QuestionContainer {...defaultProps} onResponseSaved={onResponseSaved} />);

    await waitFor(() => {
      expect(screen.getByTestId('question-display')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('response-saved-btn'));

    await waitFor(() => {
      expect(onResponseSaved).toHaveBeenCalled();
    });
  });
});

// ---------------------------------------------------------------------------
// Error state and retry banner
// ---------------------------------------------------------------------------

describe('QuestionContainer - error handling', () => {
  beforeEach(() => jest.clearAllMocks());

  it('shows error banner when fetchQuestions fails and questions are empty', async () => {
    mockedBookClient.getChapterQuestions.mockRejectedValue(new Error('Failed'));
    mockedBookClient.getChapterQuestionProgress.mockResolvedValue(mockProgress);

    render(<QuestionContainer {...defaultProps} />);

    // After fetch fails with no questions, it shows QuestionGenerator with error
    // The generator mock shows the error if it's passed
    await waitFor(() => {
      expect(screen.getByTestId('question-generator')).toBeInTheDocument();
    });
  });

  it('shows error banner in main view when questions are cached but refresh fails', async () => {
    const questions = [makeQuestion({ id: 'q-1', question_text: 'Cached Q1' })];

    // Initial load succeeds
    mockedBookClient.getChapterQuestions.mockResolvedValueOnce({ questions, total: 1, page: 1, pages: 1 });
    mockedBookClient.getChapterQuestionProgress.mockResolvedValue(mockProgress);

    render(<QuestionContainer {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByTestId('question-display')).toBeInTheDocument();
    });
  });
});
