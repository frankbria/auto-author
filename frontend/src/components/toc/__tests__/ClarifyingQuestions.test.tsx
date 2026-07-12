/**
 * Tests for ClarifyingQuestions component.
 * Covers: rendering, handleResponseChange, handleNext, handlePrevious,
 * handleSubmit, jump-to-question, load-existing-responses, auto-save debounce
 * with real persistence (saveQuestionResponses success/failure gating the
 * Auto-saved indicator, #203), and allQuestionsAnswered gate.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import ClarifyingQuestions from '../ClarifyingQuestions';
import { bookClient } from '@/lib/api/bookClient';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

jest.mock('@/lib/api/bookClient');

const mockedBookClient = bookClient as jest.Mocked<typeof bookClient>;

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const TWO_QUESTIONS = ['What is the main theme?', 'Who is the target audience?'];
const THREE_QUESTIONS = ['Q1', 'Q2', 'Q3'];

const defaultProps = {
  questions: TWO_QUESTIONS,
  onSubmit: jest.fn(),
  isLoading: false,
  bookId: 'book-1',
};

function setup(props = defaultProps) {
  return render(<ClarifyingQuestions {...props} />);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setupEmptyResponsesMock() {
  mockedBookClient.getQuestionResponses.mockResolvedValue({
    responses: [],
    status: 'not_provided',
  } as any);
  mockedBookClient.saveQuestionResponses.mockResolvedValue({
    book_id: 'book-1',
    responses_saved: 1,
    answered_at: '2024-06-01T10:00:00Z',
    ready_for_toc_generation: true,
  });
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

describe('ClarifyingQuestions - rendering', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupEmptyResponsesMock();
  });

  it('renders the heading', async () => {
    setup();
    expect(screen.getByText('Clarifying Questions')).toBeInTheDocument();
  });

  it('renders the first question on mount', async () => {
    setup();
    expect(await screen.findByText(TWO_QUESTIONS[0])).toBeInTheDocument();
  });

  it('shows an accessible skeleton while loading saved responses, then the question (#52)', async () => {
    // Hold the responses fetch open so the initial-load skeleton is observable
    let resolveLoad: (v: unknown) => void = () => {};
    mockedBookClient.getQuestionResponses.mockReturnValue(
      new Promise((resolve) => { resolveLoad = resolve; }) as any
    );

    setup();
    const skeleton = screen.getByTestId('clarifying-questions-skeleton');
    expect(skeleton).toHaveAttribute('role', 'status');
    expect(skeleton).toHaveAttribute('aria-busy', 'true');
    // Question card / textarea are not shown yet
    expect(screen.queryByPlaceholderText('Type your answer here...')).not.toBeInTheDocument();
    // Navigation is disabled during the initial load
    expect(screen.getByText('Previous')).toBeDisabled();

    await act(async () => {
      resolveLoad({ responses: [], status: 'not_provided' });
    });
    expect(await screen.findByPlaceholderText('Type your answer here...')).toBeInTheDocument();
    expect(screen.queryByTestId('clarifying-questions-skeleton')).not.toBeInTheDocument();
  });

  it('shows progress indicator', async () => {
    setup();
    expect(screen.getByText('Question 1 of 2')).toBeInTheDocument();
  });

  it('renders the question overview buttons', async () => {
    setup();
    expect(screen.getByText('Q1')).toBeInTheDocument();
    expect(screen.getByText('Q2')).toBeInTheDocument();
  });

  it('renders Previous button disabled at first question', async () => {
    setup();
    const prevBtn = screen.getByText('Previous');
    expect(prevBtn).toBeDisabled();
  });

  it('renders the auto-save hint when no saved status yet', async () => {
    setup();
    expect(screen.getByText('Responses will be saved automatically')).toBeInTheDocument();
  });

  it('renders the tips section', async () => {
    setup();
    expect(screen.getByText(/Tips for better answers/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// handleResponseChange
// ---------------------------------------------------------------------------

describe('ClarifyingQuestions - handleResponseChange', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupEmptyResponsesMock();
  });

  it('updates the textarea value when user types', async () => {
    setup();
    const textarea = await screen.findByPlaceholderText('Type your answer here...');
    fireEvent.change(textarea, { target: { value: 'My answer' } });
    expect((textarea as HTMLTextAreaElement).value).toBe('My answer');
  });

  it('shows character count after typing', async () => {
    setup();
    const textarea = await screen.findByPlaceholderText('Type your answer here...');
    fireEvent.change(textarea, { target: { value: 'Hello' } });
    expect(screen.getByText('5 characters')).toBeInTheDocument();
  });

  it('enables the Next button after typing an answer', async () => {
    setup();
    const textarea = await screen.findByPlaceholderText('Type your answer here...');
    const nextBtn = screen.getByText('Next');
    expect(nextBtn).toBeDisabled();
    fireEvent.change(textarea, { target: { value: 'Some answer' } });
    expect(nextBtn).not.toBeDisabled();
  });
});

// ---------------------------------------------------------------------------
// handleNext and handlePrevious
// ---------------------------------------------------------------------------

describe('ClarifyingQuestions - navigation', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupEmptyResponsesMock();
  });

  it('handleNext advances to the second question', async () => {
    setup();
    const textarea = await screen.findByPlaceholderText('Type your answer here...');
    fireEvent.change(textarea, { target: { value: 'Answer to Q1' } });

    const nextBtn = screen.getByText('Next');
    fireEvent.click(nextBtn);

    expect(screen.getByText(TWO_QUESTIONS[1])).toBeInTheDocument();
    expect(screen.getByText('Question 2 of 2')).toBeInTheDocument();
  });

  it('handleNext does not advance past the last question', async () => {
    setup();
    // Answer Q1 and advance to Q2
    const textarea = await screen.findByPlaceholderText('Type your answer here...');
    fireEvent.change(textarea, { target: { value: 'A1' } });
    fireEvent.click(screen.getByText('Next'));

    // We are now on Q2 (last) — Next should not be there; Generate TOC should be
    expect(screen.queryByText('Next')).not.toBeInTheDocument();
    expect(screen.getByText('Generate Table of Contents')).toBeInTheDocument();
  });

  it('handlePrevious goes back to the first question from second', async () => {
    setup();
    // Advance to Q2
    const textarea = await screen.findByPlaceholderText('Type your answer here...');
    fireEvent.change(textarea, { target: { value: 'A1' } });
    fireEvent.click(screen.getByText('Next'));

    // Now go back
    const prevBtn = screen.getByText('Previous');
    expect(prevBtn).not.toBeDisabled();
    fireEvent.click(prevBtn);

    expect(screen.getByText(TWO_QUESTIONS[0])).toBeInTheDocument();
    expect(screen.getByText('Question 1 of 2')).toBeInTheDocument();
  });

  it('handlePrevious does not go below index 0', async () => {
    setup();
    // Wait for the question to load (initial-load skeleton clears)
    expect(await screen.findByText(TWO_QUESTIONS[0])).toBeInTheDocument();
    const prevBtn = screen.getByText('Previous');
    fireEvent.click(prevBtn); // disabled but let's confirm
    // Still on Q1
    expect(screen.getByText(TWO_QUESTIONS[0])).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Jump to question (question overview)
// ---------------------------------------------------------------------------

describe('ClarifyingQuestions - jump to question', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupEmptyResponsesMock();
  });

  it('clicking Q2 overview button jumps to question 2', async () => {
    setup({ ...defaultProps, questions: THREE_QUESTIONS });

    // Overview buttons are labeled Q1, Q2, Q3 — getAll to avoid ambiguity with question text
    const overviewButtons = screen.getAllByText('Q2');
    // The overview button is the one inside the overview section (a <button>)
    const q2OverviewBtn = overviewButtons.find(el => el.tagName === 'BUTTON')!;
    fireEvent.click(q2OverviewBtn);

    // Progress counter is unambiguous
    expect(screen.getByText('Question 2 of 3')).toBeInTheDocument();
  });

  it('clicking Q1 overview when on Q2 jumps back to Q1', async () => {
    setup({ ...defaultProps, questions: THREE_QUESTIONS });

    // Advance to Q2 via textarea answer + Next
    const textarea = await screen.findByPlaceholderText('Type your answer here...');
    fireEvent.change(textarea, { target: { value: 'A1' } });
    fireEvent.click(screen.getByText('Next'));

    expect(screen.getByText('Question 2 of 3')).toBeInTheDocument();

    // Jump back to Q1 via overview
    const q1Buttons = screen.getAllByText('Q1');
    const q1OverviewBtn = q1Buttons.find(el => el.tagName === 'BUTTON')!;
    fireEvent.click(q1OverviewBtn);

    expect(screen.getByText('Question 1 of 3')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// allQuestionsAnswered and handleSubmit
// ---------------------------------------------------------------------------

describe('ClarifyingQuestions - submit', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupEmptyResponsesMock();
  });

  it('Generate TOC button is disabled when last question not answered', async () => {
    setup();
    // Answer Q1 and navigate to Q2
    const textarea = await screen.findByPlaceholderText('Type your answer here...');
    fireEvent.change(textarea, { target: { value: 'A1' } });
    fireEvent.click(screen.getByText('Next'));

    // Q2 not answered yet
    expect(screen.getByText('Generate Table of Contents')).toBeDisabled();
  });

  it('Generate TOC button is enabled when all questions answered', async () => {
    const onSubmit = jest.fn();
    setup({ ...defaultProps, onSubmit });

    // Answer Q1
    const textarea = await screen.findByPlaceholderText('Type your answer here...');
    fireEvent.change(textarea, { target: { value: 'A1' } });

    // Navigate to Q2
    fireEvent.click(screen.getByText('Next'));

    // Answer Q2
    const textarea2 = screen.getByPlaceholderText('Type your answer here...');
    fireEvent.change(textarea2, { target: { value: 'A2' } });

    expect(screen.getByText('Generate Table of Contents')).not.toBeDisabled();
  });

  it('handleSubmit calls onSubmit with all question responses', async () => {
    const onSubmit = jest.fn();
    setup({ ...defaultProps, onSubmit });

    // Answer Q1
    const textarea = await screen.findByPlaceholderText('Type your answer here...');
    fireEvent.change(textarea, { target: { value: 'Answer 1' } });
    fireEvent.click(screen.getByText('Next'));

    // Answer Q2
    const textarea2 = screen.getByPlaceholderText('Type your answer here...');
    fireEvent.change(textarea2, { target: { value: 'Answer 2' } });

    fireEvent.click(screen.getByText('Generate Table of Contents'));

    expect(onSubmit).toHaveBeenCalledWith([
      { question: TWO_QUESTIONS[0], answer: 'Answer 1' },
      { question: TWO_QUESTIONS[1], answer: 'Answer 2' },
    ]);
    // Final answers are persisted on submit too (covers the debounce window)
    expect(mockedBookClient.saveQuestionResponses).toHaveBeenCalledWith('book-1', [
      { question: TWO_QUESTIONS[0], answer: 'Answer 1' },
      { question: TWO_QUESTIONS[1], answer: 'Answer 2' },
    ]);
  });

  it('shows loading state on the submit button when isLoading=true', async () => {
    setup({ ...defaultProps, isLoading: true, questions: ['Q1'] });
    // Even with 1 question, on last question with isLoading, show spinner
    expect(screen.getByText('Generating TOC...')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// loadExistingResponses
// ---------------------------------------------------------------------------

describe('ClarifyingQuestions - load existing responses', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('pre-fills responses from existing data on mount', async () => {
    // Backend returns the TOC shape: { question, answer }
    mockedBookClient.getQuestionResponses.mockResolvedValue({
      responses: [
        { question: TWO_QUESTIONS[0], answer: 'Pre-filled answer 1' },
        { question: TWO_QUESTIONS[1], answer: 'Pre-filled answer 2' },
      ],
      answered_at: '2024-01-01T12:00:00Z',
      status: 'completed',
    });

    setup();

    await waitFor(() => {
      const textarea = screen.getByPlaceholderText('Type your answer here...');
      expect((textarea as HTMLTextAreaElement).value).toBe('Pre-filled answer 1');
    });
  });

  it('sets lastSaved from answered_at when existing responses are loaded', async () => {
    mockedBookClient.getQuestionResponses.mockResolvedValue({
      responses: [{ question: TWO_QUESTIONS[0], answer: 'Existing answer' }],
      answered_at: '2024-01-01T12:00:00Z',
      status: 'completed',
    });

    setup();

    await waitFor(() => {
      expect(screen.getByText('Auto-saved')).toBeInTheDocument();
    });
  });

  it('handles getQuestionResponses error gracefully (no crash)', async () => {
    mockedBookClient.getQuestionResponses.mockRejectedValue(new Error('Network error'));

    setup();

    await waitFor(() => {
      // Component still renders after error
      expect(screen.getByText('Clarifying Questions')).toBeInTheDocument();
    });
  });

  it('does not call getQuestionResponses when bookId is empty', async () => {
    setup({ ...defaultProps, bookId: '' });
    await act(async () => {});
    expect(mockedBookClient.getQuestionResponses).not.toHaveBeenCalled();
  });

  it('does not call getQuestionResponses when questions array is empty', async () => {
    setup({ ...defaultProps, questions: [] });
    await act(async () => {});
    expect(mockedBookClient.getQuestionResponses).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// Auto-save debounce (saveResponsesDebounced)
// ---------------------------------------------------------------------------

describe('ClarifyingQuestions - auto-save', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupEmptyResponsesMock();
  });

  it('persists via saveQuestionResponses and shows Auto-saved only after the save resolves', async () => {
    jest.useFakeTimers();

    // Hold the save promise open so we can observe the pre-resolve state
    let resolveSave: (v: unknown) => void = () => {};
    mockedBookClient.saveQuestionResponses.mockReturnValue(
      new Promise((resolve) => { resolveSave = resolve; }) as any
    );

    setup();

    await act(async () => {
      await Promise.resolve(); // flush the mount effects
    });

    const textarea = await screen.findByPlaceholderText('Type your answer here...');
    fireEvent.change(textarea, { target: { value: 'Some answer text' } });

    // Advance past the 2-second debounce — the real save call fires
    await act(async () => {
      jest.advanceTimersByTime(2100);
      await Promise.resolve();
    });

    expect(mockedBookClient.saveQuestionResponses).toHaveBeenCalledWith('book-1', [
      { question: TWO_QUESTIONS[0], answer: 'Some answer text' },
    ]);
    // Save still in flight: the indicator must NOT claim saved yet
    expect(screen.queryByText('Auto-saved')).not.toBeInTheDocument();
    expect(screen.getByText('Saving...')).toBeInTheDocument();

    await act(async () => {
      resolveSave({
        book_id: 'book-1',
        responses_saved: 1,
        answered_at: '2024-06-01T10:00:00Z',
        ready_for_toc_generation: true,
      });
    });

    await waitFor(() => {
      expect(screen.getByText('Auto-saved')).toBeInTheDocument();
    });

    jest.useRealTimers();
  });

  it('does NOT show Auto-saved when the save fails, and surfaces an error', async () => {
    jest.useFakeTimers();
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockedBookClient.saveQuestionResponses.mockRejectedValue(new Error('Network error'));

    setup();

    await act(async () => {
      await Promise.resolve();
    });

    const textarea = await screen.findByPlaceholderText('Type your answer here...');
    fireEvent.change(textarea, { target: { value: 'Doomed answer' } });

    await act(async () => {
      jest.advanceTimersByTime(2100);
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(screen.getByText(/auto-save failed/i)).toBeInTheDocument();
    });
    expect(screen.queryByText('Auto-saved')).not.toBeInTheDocument();

    consoleSpy.mockRestore();
    jest.useRealTimers();
  });

  it('recovers to Auto-saved when a later save succeeds after a failure', async () => {
    jest.useFakeTimers();
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockedBookClient.saveQuestionResponses.mockRejectedValueOnce(new Error('Network error'));

    setup();

    await act(async () => {
      await Promise.resolve();
    });

    const textarea = await screen.findByPlaceholderText('Type your answer here...');
    fireEvent.change(textarea, { target: { value: 'First try' } });

    await act(async () => {
      jest.advanceTimersByTime(2100);
      await Promise.resolve();
    });
    await waitFor(() => {
      expect(screen.getByText(/auto-save failed/i)).toBeInTheDocument();
    });

    // Next edit triggers a save that succeeds (default resolved mock)
    fireEvent.change(textarea, { target: { value: 'Second try' } });
    await act(async () => {
      jest.advanceTimersByTime(2100);
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(screen.getByText('Auto-saved')).toBeInTheDocument();
    });
    expect(screen.queryByText(/auto-save failed/i)).not.toBeInTheDocument();

    consoleSpy.mockRestore();
    jest.useRealTimers();
  });

  it('auto-save does not trigger when responses are empty', async () => {
    jest.useFakeTimers();

    setup();

    await act(async () => {
      await Promise.resolve();
    });

    // Don't type anything - responses stays empty
    await act(async () => {
      jest.advanceTimersByTime(2100);
      await Promise.resolve();
    });

    // No network call and no saved claim when there is nothing to save
    expect(mockedBookClient.saveQuestionResponses).not.toHaveBeenCalled();
    expect(screen.queryByText('Auto-saved')).not.toBeInTheDocument();

    jest.useRealTimers();
  });
});
