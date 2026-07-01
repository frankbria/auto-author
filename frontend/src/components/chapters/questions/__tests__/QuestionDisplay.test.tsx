/**
 * Tests for QuestionDisplay component.
 * Covers: rendering for all question types and difficulties, help text, examples,
 * suggested length, mark-as-completed flow, edit-response flow, rating, regeneration,
 * initial response loading, and word-count tracking.
 *
 * Note: Save-draft error handling, offline queueing, and retry scenarios are
 * covered by the companion file QuestionDisplay.enhanced.test.tsx.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import QuestionDisplay from '../QuestionDisplay';
import { Question, QuestionType, QuestionDifficulty, ResponseStatus } from '@/types/chapter-questions';
import { bookClient } from '@/lib/api/bookClient';
import { retryQueue } from '@/lib/utils/retryQueue';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------
jest.mock('@/lib/api/bookClient');
jest.mock('@/lib/utils/retryQueue');
jest.mock('@/hooks/useOnlineStatus', () => ({
  useOnlineStatus: jest.fn(() => ({ isOnline: true, wasOffline: false })),
}));
jest.mock('@/lib/toast', () => ({
  toast: Object.assign(jest.fn(), {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
  }),
}));

const mockedBookClient = bookClient as jest.Mocked<typeof bookClient>;
const mockedRetryQueue = retryQueue as jest.Mocked<typeof retryQueue>;

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeQuestion(overrides: Partial<Question> = {}): Question {
  return {
    id: 'q-1',
    chapter_id: 'chapter-1',
    question_text: 'What motivates your main character?',
    question_type: QuestionType.CHARACTER,
    difficulty: QuestionDifficulty.MEDIUM,
    category: 'character',
    order: 1,
    generated_at: '2024-01-01T00:00:00Z',
    metadata: {
      suggested_response_length: '100-200 words',
      help_text: 'Think about backstory and goals',
      examples: ['Fear of failure', 'Desire for recognition'],
    },
    ...overrides,
  };
}

const defaultProps = {
  bookId: 'book-1',
  chapterId: 'chapter-1',
  question: makeQuestion(),
  onResponseSaved: jest.fn(),
  onRegenerateQuestion: jest.fn(),
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Set up default bookClient mocks for a test that doesn't need pre-loaded response */
function setupDefaultMocks() {
  mockedBookClient.getQuestionResponse.mockResolvedValue({
    has_response: false,
    response: null,
    success: false,
  } as any);
  mockedBookClient.saveQuestionResponse.mockResolvedValue({} as any);
  mockedBookClient.rateQuestion.mockResolvedValue({} as any);
  mockedRetryQueue.add = jest.fn();
}

// ---------------------------------------------------------------------------
// Basic rendering
// ---------------------------------------------------------------------------

describe('QuestionDisplay - basic rendering', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useRealTimers();
    setupDefaultMocks();
  });

  it('renders the question text', () => {
    render(<QuestionDisplay {...defaultProps} />);
    expect(screen.getByText('What motivates your main character?')).toBeInTheDocument();
  });

  it('renders the question type in the heading', () => {
    render(<QuestionDisplay {...defaultProps} />);
    expect(screen.getByText(/character Question/i)).toBeInTheDocument();
  });

  it('renders the difficulty text', () => {
    render(<QuestionDisplay {...defaultProps} />);
    expect(screen.getByText('Medium')).toBeInTheDocument();
  });

  it('renders help text when provided', () => {
    render(<QuestionDisplay {...defaultProps} />);
    expect(screen.getByText('Think about backstory and goals')).toBeInTheDocument();
  });

  it('renders examples list when provided', () => {
    render(<QuestionDisplay {...defaultProps} />);
    expect(screen.getByText('Examples:')).toBeInTheDocument();
    expect(screen.getByText('Fear of failure')).toBeInTheDocument();
    expect(screen.getByText('Desire for recognition')).toBeInTheDocument();
  });

  it('renders suggested response length', () => {
    render(<QuestionDisplay {...defaultProps} />);
    expect(screen.getByText(/Suggested length: 100-200 words/)).toBeInTheDocument();
  });

  it('renders fallback text when suggested_response_length is absent', () => {
    const question = makeQuestion({ metadata: { suggested_response_length: '' } });
    render(<QuestionDisplay {...defaultProps} question={question} />);
    // getSuggestedLength returns '' which is falsy → 'No specific length requirement'
    expect(screen.getByText(/No specific length requirement/)).toBeInTheDocument();
  });

  it('does not render help-text section when help_text is absent', () => {
    const question = makeQuestion({
      metadata: { suggested_response_length: '50 words' },
    });
    render(<QuestionDisplay {...defaultProps} question={question} />);
    expect(screen.queryByText('Think about backstory and goals')).not.toBeInTheDocument();
  });

  it('does not render examples section when examples array is empty', () => {
    const question = makeQuestion({
      metadata: { suggested_response_length: '50 words', examples: [] },
    });
    render(<QuestionDisplay {...defaultProps} question={question} />);
    expect(screen.queryByText('Examples:')).not.toBeInTheDocument();
  });

  it('shows "Save Draft" and "Complete Response" buttons initially', () => {
    render(<QuestionDisplay {...defaultProps} />);
    expect(screen.getByText('Save Draft')).toBeInTheDocument();
    expect(screen.getByText('Complete Response')).toBeInTheDocument();
  });

  it('shows the completion hint text when not completed', () => {
    render(<QuestionDisplay {...defaultProps} />);
    expect(
      screen.getByText(/Remember to click 'Complete Response'/i)
    ).toBeInTheDocument();
  });

  it('shows rating and regenerate action buttons', () => {
    render(<QuestionDisplay {...defaultProps} />);
    expect(screen.getByLabelText('Rate question as poor')).toBeInTheDocument();
    expect(screen.getByLabelText('Rate question as good')).toBeInTheDocument();
    expect(screen.getByLabelText('Generate a new question')).toBeInTheDocument();
  });

  it('shows initial word count as 0', () => {
    render(<QuestionDisplay {...defaultProps} />);
    expect(screen.getByText('0 words')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Question type icon variations (exercises getQuestionTypeIcon branches)
// ---------------------------------------------------------------------------

describe('QuestionDisplay - question type variations', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupDefaultMocks();
  });

  it('renders PLOT type question', () => {
    const q = makeQuestion({ question_type: QuestionType.PLOT });
    render(<QuestionDisplay {...defaultProps} question={q} />);
    expect(screen.getByText(/plot Question/i)).toBeInTheDocument();
  });

  it('renders SETTING type question', () => {
    const q = makeQuestion({ question_type: QuestionType.SETTING });
    render(<QuestionDisplay {...defaultProps} question={q} />);
    expect(screen.getByText(/setting Question/i)).toBeInTheDocument();
  });

  it('renders THEME type question', () => {
    const q = makeQuestion({ question_type: QuestionType.THEME });
    render(<QuestionDisplay {...defaultProps} question={q} />);
    expect(screen.getByText(/theme Question/i)).toBeInTheDocument();
  });

  it('renders RESEARCH type question', () => {
    const q = makeQuestion({ question_type: QuestionType.RESEARCH });
    render(<QuestionDisplay {...defaultProps} question={q} />);
    expect(screen.getByText(/research Question/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Difficulty variations (exercises getDifficultyInfo branches)
// ---------------------------------------------------------------------------

describe('QuestionDisplay - difficulty variations', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupDefaultMocks();
  });

  it('renders EASY difficulty', () => {
    const q = makeQuestion({ difficulty: QuestionDifficulty.EASY });
    render(<QuestionDisplay {...defaultProps} question={q} />);
    expect(screen.getByText('Easy')).toBeInTheDocument();
  });

  it('renders MEDIUM difficulty', () => {
    const q = makeQuestion({ difficulty: QuestionDifficulty.MEDIUM });
    render(<QuestionDisplay {...defaultProps} question={q} />);
    expect(screen.getByText('Medium')).toBeInTheDocument();
  });

  it('renders HARD difficulty', () => {
    const q = makeQuestion({ difficulty: QuestionDifficulty.HARD });
    render(<QuestionDisplay {...defaultProps} question={q} />);
    expect(screen.getByText('Hard')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Word count (exercises word-count useEffect)
// ---------------------------------------------------------------------------

describe('QuestionDisplay - word count', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupDefaultMocks();
  });

  it('updates word count as user types', () => {
    render(<QuestionDisplay {...defaultProps} />);
    const textarea = screen.getByLabelText(/your response/i);

    fireEvent.change(textarea, { target: { value: 'Hello world test' } });
    expect(screen.getByText('3 words')).toBeInTheDocument();
  });

  it('counts words correctly ignoring extra whitespace', () => {
    render(<QuestionDisplay {...defaultProps} />);
    const textarea = screen.getByLabelText(/your response/i);

    fireEvent.change(textarea, { target: { value: '  one   two  three  ' } });
    expect(screen.getByText('3 words')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Mark as completed
// ---------------------------------------------------------------------------

describe('QuestionDisplay - mark as completed', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupDefaultMocks();
  });

  it('shows error when trying to complete with empty response', async () => {
    render(<QuestionDisplay {...defaultProps} />);
    // Don't type anything
    const completeButton = screen.getByText('Complete Response');
    expect(completeButton).toBeDisabled();
  });

  it('enables Complete Response button only when response text is present', () => {
    render(<QuestionDisplay {...defaultProps} />);
    const textarea = screen.getByLabelText(/your response/i);
    const completeButton = screen.getByText('Complete Response');

    expect(completeButton).toBeDisabled();
    fireEvent.change(textarea, { target: { value: 'My complete response' } });
    expect(completeButton).not.toBeDisabled();
  });

  it('calls saveQuestionResponse with COMPLETED status on mark-complete click', async () => {
    render(<QuestionDisplay {...defaultProps} />);
    const textarea = screen.getByLabelText(/your response/i);
    fireEvent.change(textarea, { target: { value: 'My complete response' } });

    fireEvent.click(screen.getByText('Complete Response'));

    await waitFor(() => {
      expect(mockedBookClient.saveQuestionResponse).toHaveBeenCalledWith(
        'book-1',
        'chapter-1',
        'q-1',
        expect.objectContaining({ status: ResponseStatus.COMPLETED })
      );
    });
  });

  it('shows "Edit Response" button after successful completion', async () => {
    render(<QuestionDisplay {...defaultProps} />);
    const textarea = screen.getByLabelText(/your response/i);
    fireEvent.change(textarea, { target: { value: 'My complete response' } });

    fireEvent.click(screen.getByText('Complete Response'));

    await waitFor(() => {
      expect(screen.getByText('Edit Response')).toBeInTheDocument();
    });
  });

  it('shows completion hint text after completion', async () => {
    render(<QuestionDisplay {...defaultProps} />);
    const textarea = screen.getByLabelText(/your response/i);
    fireEvent.change(textarea, { target: { value: 'My complete response' } });

    fireEvent.click(screen.getByText('Complete Response'));

    await waitFor(() => {
      expect(screen.getByText(/You've completed this question/i)).toBeInTheDocument();
    });
  });

  it('calls onResponseSaved after successful completion', async () => {
    const onResponseSaved = jest.fn();
    render(<QuestionDisplay {...defaultProps} onResponseSaved={onResponseSaved} />);
    const textarea = screen.getByLabelText(/your response/i);
    fireEvent.change(textarea, { target: { value: 'My complete response' } });

    fireEvent.click(screen.getByText('Complete Response'));

    await waitFor(() => {
      expect(onResponseSaved).toHaveBeenCalled();
    });
  });

  it('shows "Save Draft" and "Complete Response" again after clicking "Edit Response"', async () => {
    render(<QuestionDisplay {...defaultProps} />);
    const textarea = screen.getByLabelText(/your response/i);
    fireEvent.change(textarea, { target: { value: 'My complete response' } });

    fireEvent.click(screen.getByText('Complete Response'));

    await waitFor(() => {
      expect(screen.getByText('Edit Response')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Edit Response'));
    expect(screen.getByText('Save Draft')).toBeInTheDocument();
    expect(screen.getByText('Complete Response')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Rating a question
// ---------------------------------------------------------------------------

describe('QuestionDisplay - rating', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupDefaultMocks();
  });

  it('calls rateQuestion with rating=1 when thumbs-down is clicked', async () => {
    render(<QuestionDisplay {...defaultProps} />);
    fireEvent.click(screen.getByLabelText('Rate question as poor'));

    await waitFor(() => {
      expect(mockedBookClient.rateQuestion).toHaveBeenCalledWith(
        'book-1',
        'chapter-1',
        'q-1',
        expect.objectContaining({ rating: 1 })
      );
    });
  });

  it('calls rateQuestion with rating=5 when thumbs-up is clicked', async () => {
    render(<QuestionDisplay {...defaultProps} />);
    fireEvent.click(screen.getByLabelText('Rate question as good'));

    await waitFor(() => {
      expect(mockedBookClient.rateQuestion).toHaveBeenCalledWith(
        'book-1',
        'chapter-1',
        'q-1',
        expect.objectContaining({ rating: 5 })
      );
    });
  });

  it('handles rateQuestion API error gracefully without crashing (line 426)', async () => {
    mockedBookClient.rateQuestion.mockRejectedValue(new Error('Rate limit exceeded'));

    render(<QuestionDisplay {...defaultProps} />);
    fireEvent.click(screen.getByLabelText('Rate question as poor'));

    // Component should not crash and Save Draft button should still be present
    await waitFor(() => {
      expect(screen.getByText('Save Draft')).toBeInTheDocument();
    });
  });
});

// ---------------------------------------------------------------------------
// Regenerate question
// ---------------------------------------------------------------------------

describe('QuestionDisplay - regenerate question', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupDefaultMocks();
  });

  it('calls onRegenerateQuestion with the question id when regenerate is clicked', () => {
    const onRegenerateQuestion = jest.fn();
    render(
      <QuestionDisplay
        {...defaultProps}
        onRegenerateQuestion={onRegenerateQuestion}
      />
    );
    fireEvent.click(screen.getByLabelText('Generate a new question'));
    expect(onRegenerateQuestion).toHaveBeenCalledWith('q-1');
  });

  it('shows the regeneration count once a question has been regenerated', () => {
    render(
      <QuestionDisplay
        {...defaultProps}
        question={makeQuestion({ regeneration_count: 2 })}
      />
    );
    expect(screen.getByTestId('regeneration-count')).toHaveTextContent('Regenerated 2/5');
  });

  it('does not show a count for a never-regenerated question', () => {
    render(<QuestionDisplay {...defaultProps} question={makeQuestion({ regeneration_count: 0 })} />);
    expect(screen.queryByTestId('regeneration-count')).not.toBeInTheDocument();
  });

  it('disables regenerate while a regeneration is in flight', () => {
    const onRegenerateQuestion = jest.fn();
    render(
      <QuestionDisplay
        {...defaultProps}
        onRegenerateQuestion={onRegenerateQuestion}
        isRegenerating
      />
    );
    const button = screen.getByLabelText('Generate a new question');
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(onRegenerateQuestion).not.toHaveBeenCalled();
  });

  it('disables regenerate and does not fire the handler once the limit is reached', () => {
    const onRegenerateQuestion = jest.fn();
    render(
      <QuestionDisplay
        {...defaultProps}
        question={makeQuestion({ regeneration_count: 5 })}
        onRegenerateQuestion={onRegenerateQuestion}
      />
    );
    const button = screen.getByLabelText('Generate a new question');
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(onRegenerateQuestion).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// Initial response loading (useEffect on mount)
// ---------------------------------------------------------------------------

describe('QuestionDisplay - loading existing response', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedRetryQueue.add = jest.fn();
  });

  it('pre-fills textarea with existing draft response', async () => {
    mockedBookClient.getQuestionResponse.mockResolvedValue({
      has_response: true,
      response: {
        response_text: 'Pre-existing draft text',
        status: ResponseStatus.DRAFT,
      },
      success: true,
    } as any);
    mockedBookClient.saveQuestionResponse.mockResolvedValue({} as any);

    render(<QuestionDisplay {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('Pre-existing draft text')).toBeInTheDocument();
    });
  });

  it('marks question as completed when loaded response has COMPLETED status', async () => {
    mockedBookClient.getQuestionResponse.mockResolvedValue({
      has_response: true,
      response: {
        response_text: 'Completed response text',
        status: ResponseStatus.COMPLETED,
      },
      success: true,
    } as any);
    mockedBookClient.saveQuestionResponse.mockResolvedValue({} as any);

    render(<QuestionDisplay {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Edit Response')).toBeInTheDocument();
    });
  });

  it('sets correct word count from loaded response', async () => {
    mockedBookClient.getQuestionResponse.mockResolvedValue({
      has_response: true,
      response: {
        response_text: 'one two three four five',
        status: ResponseStatus.DRAFT,
      },
      success: true,
    } as any);
    mockedBookClient.saveQuestionResponse.mockResolvedValue({} as any);

    render(<QuestionDisplay {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('5 words')).toBeInTheDocument();
    });
  });

  it('handles failed getQuestionResponse gracefully (no crash)', async () => {
    mockedBookClient.getQuestionResponse.mockRejectedValue(new Error('Network error'));
    render(<QuestionDisplay {...defaultProps} />);
    // Component should still render without crashing
    await waitFor(() => {
      expect(screen.getByText('Save Draft')).toBeInTheDocument();
    });
  });
});

// ---------------------------------------------------------------------------
// Default difficulty case (branch coverage – getDifficultyInfo default)
// ---------------------------------------------------------------------------

describe('QuestionDisplay - default difficulty branch', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupDefaultMocks();
  });

  it('renders "Medium" for an unrecognised difficulty value (default case)', () => {
    // Cast to QuestionDifficulty to bypass TypeScript enum – hits the `default:` branch
    const q = makeQuestion({ difficulty: 'unknown_level' as QuestionDifficulty });
    render(<QuestionDisplay {...defaultProps} question={q} />);
    expect(screen.getByText('Medium')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Verification success path (saveOperation lines 193-212)
// ---------------------------------------------------------------------------

describe('QuestionDisplay - save verification paths', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedRetryQueue.add = jest.fn();
  });

  it('executes verification success path when saved text matches', async () => {
    // Call 1 (mount): no existing response
    mockedBookClient.getQuestionResponse.mockResolvedValueOnce({
      has_response: false,
      response: null,
    } as any);
    // Call 2 (verification after save): matching text → hits lines 193-212
    mockedBookClient.getQuestionResponse.mockResolvedValueOnce({
      has_response: true,
      response: { response_text: 'verified draft', status: 'draft' },
    } as any);
    mockedBookClient.saveQuestionResponse.mockResolvedValue({} as any);

    render(<QuestionDisplay {...defaultProps} />);
    const textarea = screen.getByLabelText(/your response/i);
    fireEvent.change(textarea, { target: { value: 'verified draft' } });
    fireEvent.click(screen.getByText('Save Draft'));

    await waitFor(() => {
      expect(screen.getByText(/saved successfully/i)).toBeInTheDocument();
    });
  });

  it('shows data-mismatch toast when verification response text differs', async () => {
    const { toast } = require('@/lib/toast');

    // Call 1 (mount)
    mockedBookClient.getQuestionResponse.mockResolvedValueOnce({
      has_response: false,
      response: null,
    } as any);
    // Call 2 (verification): DIFFERENT text → triggers mismatch branch (lines 197-206)
    mockedBookClient.getQuestionResponse.mockResolvedValueOnce({
      has_response: true,
      response: { response_text: 'server stored something else', status: 'draft' },
    } as any);
    mockedBookClient.saveQuestionResponse.mockResolvedValue({} as any);

    render(<QuestionDisplay {...defaultProps} />);
    const textarea = screen.getByLabelText(/your response/i);
    fireEvent.change(textarea, { target: { value: 'what I typed' } });
    fireEvent.click(screen.getByText('Save Draft'));

    // Mismatch toast is fired during save (component still shows saved)
    await waitFor(() => {
      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Warning: Data Mismatch' })
      );
    });
  });
});

// ---------------------------------------------------------------------------
// Offline queue callbacks (lines 248-264 and 350-366)
// ---------------------------------------------------------------------------

describe('QuestionDisplay - offline queue callbacks', () => {
  const { useOnlineStatus } = require('@/hooks/useOnlineStatus');

  beforeEach(() => {
    jest.clearAllMocks();
    mockedBookClient.saveQuestionResponse.mockResolvedValue({} as any);
    mockedBookClient.rateQuestion.mockResolvedValue({} as any);
    // getQuestionResponse for mount
    mockedBookClient.getQuestionResponse.mockResolvedValue({
      has_response: false,
      response: null,
    } as any);
    useOnlineStatus.mockReturnValue({ isOnline: false, wasOffline: false });
  });

  afterEach(() => {
    useOnlineStatus.mockReturnValue({ isOnline: true, wasOffline: false });
  });

  it('fires draft onSuccess callback, updating save status to saved', async () => {
    let capturedCallbacks: any = null;
    mockedRetryQueue.add = jest.fn((_id, _fn, callbacks) => {
      capturedCallbacks = callbacks;
    });
    const onResponseSaved = jest.fn();

    render(<QuestionDisplay {...defaultProps} onResponseSaved={onResponseSaved} />);
    const textarea = screen.getByLabelText(/your response/i);
    fireEvent.change(textarea, { target: { value: 'offline draft text' } });
    fireEvent.click(screen.getByText('Save Draft'));

    await waitFor(() => {
      expect(capturedCallbacks).not.toBeNull();
    });

    // Manually invoke the queued onSuccess callback
    await act(async () => {
      capturedCallbacks.onSuccess();
    });

    await waitFor(() => {
      expect(screen.getByText(/saved successfully/i)).toBeInTheDocument();
    });
    expect(onResponseSaved).toHaveBeenCalled();
  });

  it('fires draft onError callback with NETWORK error, shows network message', async () => {
    let capturedCallbacks: any = null;
    mockedRetryQueue.add = jest.fn((_id, _fn, callbacks) => {
      capturedCallbacks = callbacks;
    });

    render(<QuestionDisplay {...defaultProps} />);
    const textarea = screen.getByLabelText(/your response/i);
    fireEvent.change(textarea, { target: { value: 'offline draft text' } });
    fireEvent.click(screen.getByText('Save Draft'));

    await waitFor(() => {
      expect(capturedCallbacks).not.toBeNull();
    });

    // Network error (TypeError with 'fetch' in message → ErrorType.NETWORK)
    await act(async () => {
      capturedCallbacks.onError(new TypeError('fetch connection reset'));
    });

    await waitFor(() => {
      expect(screen.getByText(/Network error. Save will retry/i)).toBeInTheDocument();
    });
  });

  it('fires draft onError callback for non-network error, shows generic message', async () => {
    let capturedCallbacks: any = null;
    mockedRetryQueue.add = jest.fn((_id, _fn, callbacks) => {
      capturedCallbacks = callbacks;
    });

    render(<QuestionDisplay {...defaultProps} />);
    const textarea = screen.getByLabelText(/your response/i);
    fireEvent.change(textarea, { target: { value: 'offline draft text' } });
    fireEvent.click(screen.getByText('Save Draft'));

    await waitFor(() => expect(capturedCallbacks).not.toBeNull());

    await act(async () => {
      capturedCallbacks.onError(new Error('Some other failure'));
    });

    await waitFor(() => {
      expect(screen.getByText(/Failed to save draft after multiple/i)).toBeInTheDocument();
    });
  });

  it('fires complete onSuccess callback, marking question as completed', async () => {
    let capturedCallbacks: any = null;
    mockedRetryQueue.add = jest.fn((_id, _fn, callbacks) => {
      capturedCallbacks = callbacks;
    });
    const onResponseSaved = jest.fn();

    render(<QuestionDisplay {...defaultProps} onResponseSaved={onResponseSaved} />);
    const textarea = screen.getByLabelText(/your response/i);
    fireEvent.change(textarea, { target: { value: 'offline complete text' } });
    fireEvent.click(screen.getByText('Complete Response'));

    await waitFor(() => expect(capturedCallbacks).not.toBeNull());

    await act(async () => {
      capturedCallbacks.onSuccess();
    });

    await waitFor(() => {
      expect(screen.getByText('Edit Response')).toBeInTheDocument();
    });
    expect(onResponseSaved).toHaveBeenCalled();
  });

  it('fires complete onError callback with NETWORK, shows network completion message', async () => {
    let capturedCallbacks: any = null;
    mockedRetryQueue.add = jest.fn((_id, _fn, callbacks) => {
      capturedCallbacks = callbacks;
    });

    render(<QuestionDisplay {...defaultProps} />);
    const textarea = screen.getByLabelText(/your response/i);
    fireEvent.change(textarea, { target: { value: 'offline complete text' } });
    fireEvent.click(screen.getByText('Complete Response'));

    await waitFor(() => expect(capturedCallbacks).not.toBeNull());

    await act(async () => {
      capturedCallbacks.onError(new TypeError('fetch failed'));
    });

    await waitFor(() => {
      expect(screen.getByText(/Network error. Completion will retry/i)).toBeInTheDocument();
    });
  });

  it('fires complete onError callback for non-network, shows generic completion failure', async () => {
    let capturedCallbacks: any = null;
    mockedRetryQueue.add = jest.fn((_id, _fn, callbacks) => {
      capturedCallbacks = callbacks;
    });

    render(<QuestionDisplay {...defaultProps} />);
    const textarea = screen.getByLabelText(/your response/i);
    fireEvent.change(textarea, { target: { value: 'offline complete text' } });
    fireEvent.click(screen.getByText('Complete Response'));

    await waitFor(() => expect(capturedCallbacks).not.toBeNull());

    await act(async () => {
      capturedCallbacks.onError(new Error('Unknown failure'));
    });

    await waitFor(() => {
      expect(screen.getByText(/Failed to complete response after/i)).toBeInTheDocument();
    });
  });
});

// ---------------------------------------------------------------------------
// Auto-save timer (line 317)
// ---------------------------------------------------------------------------

describe('QuestionDisplay - auto-save', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupDefaultMocks();
  });

  it('auto-saves after 3 seconds of inactivity', async () => {
    jest.useFakeTimers();

    mockedBookClient.saveQuestionResponse.mockResolvedValue({} as any);

    render(<QuestionDisplay {...defaultProps} />);
    const textarea = screen.getByLabelText(/your response/i);

    fireEvent.change(textarea, { target: { value: 'auto save this' } });

    // Advance past the 3-second auto-save debounce
    await act(async () => {
      jest.advanceTimersByTime(3100);
    });

    await waitFor(() => {
      expect(mockedBookClient.saveQuestionResponse).toHaveBeenCalled();
    });

    jest.useRealTimers();
  });
});

// ---------------------------------------------------------------------------
// Save Draft - error type classification
// ---------------------------------------------------------------------------

describe('QuestionDisplay - save draft error classification', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedBookClient.getQuestionResponse.mockResolvedValue({
      has_response: false,
      response: null,
      success: false,
    } as any);
    mockedRetryQueue.add = jest.fn();
  });

  it('shows validation error message when API returns 400', async () => {
    const err = Object.assign(new Error('Bad request'), { status: 400 });
    mockedBookClient.saveQuestionResponse.mockRejectedValue(err);

    render(<QuestionDisplay {...defaultProps} />);
    const textarea = screen.getByLabelText(/your response/i);
    fireEvent.change(textarea, { target: { value: 'Some text' } });

    fireEvent.click(screen.getByText('Save Draft'));

    await waitFor(() => {
      expect(screen.getByText(/Invalid response format/i)).toBeInTheDocument();
    });
  });

  it('shows save failed generic message for unknown errors', async () => {
    mockedBookClient.saveQuestionResponse.mockRejectedValue(
      new Error('Unknown error')
    );

    render(<QuestionDisplay {...defaultProps} />);
    const textarea = screen.getByLabelText(/your response/i);
    fireEvent.change(textarea, { target: { value: 'Some text' } });

    fireEvent.click(screen.getByText('Save Draft'));

    await waitFor(() => {
      expect(screen.getByText(/Failed to save draft/i)).toBeInTheDocument();
    });
  });

  it('shows auth error message in handleMarkCompleted for 401 status', async () => {
    const authError = Object.assign(new Error('Unauthorized'), { status: 401 });
    mockedBookClient.saveQuestionResponse.mockRejectedValue(authError);

    render(<QuestionDisplay {...defaultProps} />);
    const textarea = screen.getByLabelText(/your response/i);
    fireEvent.change(textarea, { target: { value: 'my complete answer' } });

    fireEvent.click(screen.getByText('Complete Response'));

    await waitFor(() => {
      expect(screen.getByText(/Authentication error. Please sign in again/i)).toBeInTheDocument();
    });
  });

  it('retry button routes to handleMarkCompleted when lastAction was "complete"', async () => {
    // First mark-complete attempt fails
    const err = new Error('Server error');
    mockedBookClient.saveQuestionResponse.mockRejectedValueOnce(err);
    // Second attempt (retry of complete) succeeds
    mockedBookClient.saveQuestionResponse.mockResolvedValueOnce({} as any);

    render(<QuestionDisplay {...defaultProps} />);
    const textarea = screen.getByLabelText(/your response/i);
    fireEvent.change(textarea, { target: { value: 'My response text' } });

    // Try to complete → fails
    fireEvent.click(screen.getByText('Complete Response'));

    await waitFor(() => {
      expect(screen.getByText(/save failed/i)).toBeInTheDocument();
    });

    // Click retry – should retry the complete (not draft) operation
    fireEvent.click(screen.getByText('Retry'));

    await waitFor(() => {
      expect(mockedBookClient.saveQuestionResponse).toHaveBeenLastCalledWith(
        'book-1',
        'chapter-1',
        'q-1',
        expect.objectContaining({ status: ResponseStatus.COMPLETED })
      );
    });
  });
});
