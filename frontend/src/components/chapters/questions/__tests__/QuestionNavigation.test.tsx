/**
 * Tests for QuestionNavigation component.
 * Covers: rendering, Previous/Next buttons, toggle dropdown,
 * getQuestionTitle (short/long text, status indicators), jump-to-question,
 * Skip and Finish-and-restart secondary actions.
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import QuestionNavigation, { findNextUnanswered } from '../QuestionNavigation';
import { Question, QuestionType, QuestionDifficulty } from '@/types/chapter-questions';

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

const twoQuestions: Question[] = [
  makeQuestion({ id: 'q-1', question_text: 'Short question text' }),
  makeQuestion({ id: 'q-2', question_text: 'Another short question', order: 2 }),
];

const threeQuestions: Question[] = [
  makeQuestion({ id: 'q-1', question_text: 'Q1 text', order: 1 }),
  makeQuestion({ id: 'q-2', question_text: 'Q2 text', order: 2 }),
  makeQuestion({ id: 'q-3', question_text: 'Q3 text', order: 3 }),
];

const defaultProps = {
  currentIndex: 0,
  totalQuestions: 2,
  onNext: jest.fn(),
  onPrevious: jest.fn(),
  onGoToQuestion: jest.fn(),
  questions: twoQuestions,
};

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

describe('QuestionNavigation - rendering', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders Previous, Next and question counter buttons', () => {
    render(<QuestionNavigation {...defaultProps} />);
    expect(screen.getByText('Previous')).toBeInTheDocument();
    expect(screen.getByText('Next')).toBeInTheDocument();
    expect(screen.getByText('Question 1 of 2')).toBeInTheDocument();
  });

  it('Previous button is disabled at index 0', () => {
    render(<QuestionNavigation {...defaultProps} currentIndex={0} />);
    expect(screen.getByText('Previous').closest('button')).toBeDisabled();
  });

  it('Next button is disabled at the last question', () => {
    render(<QuestionNavigation {...defaultProps} currentIndex={1} totalQuestions={2} />);
    expect(screen.getByText('Next').closest('button')).toBeDisabled();
  });

  it('Previous button is enabled when not at first question', () => {
    render(<QuestionNavigation {...defaultProps} currentIndex={1} />);
    expect(screen.getByText('Previous').closest('button')).not.toBeDisabled();
  });

  it('Next button is enabled when not at last question', () => {
    render(<QuestionNavigation {...defaultProps} currentIndex={0} totalQuestions={2} />);
    expect(screen.getByText('Next').closest('button')).not.toBeDisabled();
  });

  it('shows "Skip this question" when not at last question', () => {
    render(<QuestionNavigation {...defaultProps} currentIndex={0} totalQuestions={2} />);
    expect(screen.getByText('Skip this question')).toBeInTheDocument();
  });

  it('shows "Finish and restart" when at last question', () => {
    render(<QuestionNavigation {...defaultProps} currentIndex={1} totalQuestions={2} />);
    expect(screen.getByText('Finish and restart')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// onNext and onPrevious callbacks
// ---------------------------------------------------------------------------

describe('QuestionNavigation - navigation callbacks', () => {
  beforeEach(() => jest.clearAllMocks());

  it('clicking Next calls onNext', () => {
    const onNext = jest.fn();
    render(<QuestionNavigation {...defaultProps} onNext={onNext} currentIndex={0} />);
    fireEvent.click(screen.getByText('Next').closest('button')!);
    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it('clicking Previous calls onPrevious', () => {
    const onPrevious = jest.fn();
    render(
      <QuestionNavigation {...defaultProps} onPrevious={onPrevious} currentIndex={1} />
    );
    fireEvent.click(screen.getByText('Previous').closest('button')!);
    expect(onPrevious).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// Dropdown toggle and getQuestionTitle
// ---------------------------------------------------------------------------

describe('QuestionNavigation - dropdown and getQuestionTitle', () => {
  beforeEach(() => jest.clearAllMocks());

  it('clicking the question counter button toggles the dropdown open', () => {
    render(<QuestionNavigation {...defaultProps} />);
    expect(screen.queryByRole('list')).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Question 1 of 2').closest('button')!);

    expect(screen.getByRole('list')).toBeInTheDocument();
  });

  it('clicking the counter button again closes the dropdown', () => {
    render(<QuestionNavigation {...defaultProps} />);
    const counterBtn = screen.getByText('Question 1 of 2').closest('button')!;

    fireEvent.click(counterBtn); // open
    expect(screen.getByRole('list')).toBeInTheDocument();

    fireEvent.click(counterBtn); // close
    expect(screen.queryByRole('list')).not.toBeInTheDocument();
  });

  it('getQuestionTitle renders short question text unchanged', () => {
    render(<QuestionNavigation {...defaultProps} questions={twoQuestions} />);
    fireEvent.click(screen.getByText('Question 1 of 2').closest('button')!);

    expect(screen.getByText(/Short question text/)).toBeInTheDocument();
  });

  it('getQuestionTitle truncates long question text at 50 chars', () => {
    const longText = 'A'.repeat(60);
    const questions = [
      makeQuestion({ question_text: longText }),
      makeQuestion({ id: 'q-2', order: 2 }),
    ];
    render(
      <QuestionNavigation
        {...defaultProps}
        questions={questions}
        totalQuestions={2}
      />
    );
    fireEvent.click(screen.getByText('Question 1 of 2').closest('button')!);

    // The truncated form should end with '...' (unanswered items carry a ○ prefix)
    expect(screen.getByText(/^○ 1\. .{50}\.\.\./)).toBeInTheDocument();
  });

  it('getQuestionTitle adds ✓ prefix for completed questions', () => {
    const questions = [
      makeQuestion({ response_status: 'completed' as any }),
      makeQuestion({ id: 'q-2', order: 2 }),
    ];
    render(
      <QuestionNavigation
        {...defaultProps}
        questions={questions}
        totalQuestions={2}
      />
    );
    fireEvent.click(screen.getByText('Question 1 of 2').closest('button')!);

    const items = screen.getAllByRole('listitem');
    expect(items[0].textContent).toMatch(/^✓ /);
  });

  it('getQuestionTitle adds ○ prefix and muted text for unanswered questions', () => {
    const questions = [
      makeQuestion(), // no response_status -> unanswered
      makeQuestion({ id: 'q-2', response_status: 'completed' as any, order: 2 }),
    ];
    render(
      <QuestionNavigation
        {...defaultProps}
        questions={questions}
        totalQuestions={2}
      />
    );
    fireEvent.click(screen.getByText('Question 1 of 2').closest('button')!);

    const items = screen.getAllByRole('listitem');
    expect(items[0].textContent).toMatch(/^○ /);
    expect(items[0].className).toContain('text-muted-foreground');
    // Answered item is not muted
    expect(items[1].className).not.toContain('text-muted-foreground');
  });

  it('getQuestionTitle adds ⚙️ prefix for draft questions', () => {
    const questions = [
      makeQuestion({ response_status: 'draft' as any }),
      makeQuestion({ id: 'q-2', order: 2 }),
    ];
    render(
      <QuestionNavigation
        {...defaultProps}
        questions={questions}
        totalQuestions={2}
      />
    );
    fireEvent.click(screen.getByText('Question 1 of 2').closest('button')!);

    const items = screen.getAllByRole('listitem');
    expect(items[0].textContent).toMatch(/^⚙️ /);
  });

  it('clicking a dropdown item calls onGoToQuestion with its index', () => {
    const onGoToQuestion = jest.fn();
    render(
      <QuestionNavigation
        {...defaultProps}
        onGoToQuestion={onGoToQuestion}
        questions={threeQuestions}
        totalQuestions={3}
      />
    );
    fireEvent.click(screen.getByText('Question 1 of 3').closest('button')!);

    const items = screen.getAllByRole('listitem');
    fireEvent.click(items[1]); // click second item (index 1)

    expect(onGoToQuestion).toHaveBeenCalledWith(1);
  });

  it('clicking a dropdown item closes the dropdown', () => {
    const onGoToQuestion = jest.fn();
    render(
      <QuestionNavigation
        {...defaultProps}
        onGoToQuestion={onGoToQuestion}
        questions={twoQuestions}
        totalQuestions={2}
      />
    );
    fireEvent.click(screen.getByText('Question 1 of 2').closest('button')!);
    expect(screen.getByRole('list')).toBeInTheDocument();

    const items = screen.getAllByRole('listitem');
    fireEvent.click(items[0]);

    expect(screen.queryByRole('list')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Skip and Finish-and-restart secondary actions
// ---------------------------------------------------------------------------

describe('QuestionNavigation - secondary action button', () => {
  beforeEach(() => jest.clearAllMocks());

  it('"Skip this question" calls onNext when not at last question', () => {
    const onNext = jest.fn();
    render(
      <QuestionNavigation
        {...defaultProps}
        onNext={onNext}
        currentIndex={0}
        totalQuestions={3}
        questions={threeQuestions}
      />
    );
    fireEvent.click(screen.getByText('Skip this question').closest('button')!);
    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it('"Finish and restart" calls onGoToQuestion(0) at last question', () => {
    const onGoToQuestion = jest.fn();
    render(
      <QuestionNavigation
        {...defaultProps}
        onGoToQuestion={onGoToQuestion}
        currentIndex={2}
        totalQuestions={3}
        questions={threeQuestions}
      />
    );
    fireEvent.click(screen.getByText('Finish and restart').closest('button')!);
    expect(onGoToQuestion).toHaveBeenCalledWith(0);
  });
});

// ---------------------------------------------------------------------------
// findNextUnanswered helper
// ---------------------------------------------------------------------------

describe('findNextUnanswered', () => {
  const q = (status?: string) =>
    makeQuestion({ response_status: status as any });

  it('returns the next non-completed index after currentIndex', () => {
    const questions = [q('completed'), q('completed'), q(), q()];
    expect(findNextUnanswered(questions, 0)).toBe(2);
  });

  it('treats draft as not-yet-answered', () => {
    const questions = [q('completed'), q('draft'), q('completed')];
    expect(findNextUnanswered(questions, 0)).toBe(1);
  });

  it('wraps around to the start', () => {
    const questions = [q(), q('completed'), q('completed')];
    expect(findNextUnanswered(questions, 2)).toBe(0);
  });

  it('returns -1 when every question is completed', () => {
    const questions = [q('completed'), q('completed')];
    expect(findNextUnanswered(questions, 0)).toBe(-1);
  });
});

// ---------------------------------------------------------------------------
// "Next Unanswered" navigation button
// ---------------------------------------------------------------------------

describe('QuestionNavigation - Next Unanswered button', () => {
  beforeEach(() => jest.clearAllMocks());

  it('navigates to the next unanswered question', () => {
    const onGoToQuestion = jest.fn();
    const questions = [
      makeQuestion({ id: 'q-1', response_status: 'completed' as any }),
      makeQuestion({ id: 'q-2', order: 2 }), // unanswered
      makeQuestion({ id: 'q-3', order: 3 }),
    ];
    render(
      <QuestionNavigation
        {...defaultProps}
        onGoToQuestion={onGoToQuestion}
        currentIndex={0}
        totalQuestions={3}
        questions={questions}
      />
    );
    fireEvent.click(screen.getByText('Next Unanswered').closest('button')!);
    expect(onGoToQuestion).toHaveBeenCalledWith(1);
  });

  it('is disabled when all questions are completed', () => {
    const questions = [
      makeQuestion({ id: 'q-1', response_status: 'completed' as any }),
      makeQuestion({ id: 'q-2', response_status: 'completed' as any, order: 2 }),
    ];
    render(
      <QuestionNavigation
        {...defaultProps}
        currentIndex={0}
        totalQuestions={2}
        questions={questions}
      />
    );
    expect(screen.getByText('Next Unanswered').closest('button')).toBeDisabled();
  });
});
