/**
 * Tests for QuestionProgress component.
 * Covers: status label, progress bar value, and per-question dot colouring
 * (which must reflect each question's response_status, not positional order).
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import QuestionProgress from '../QuestionProgress';
import {
  Question,
  QuestionProgressResponse,
  QuestionType,
  QuestionDifficulty,
} from '@/types/chapter-questions';

function makeQuestion(overrides: Partial<Question> = {}): Question {
  return {
    id: 'q-1',
    chapter_id: 'ch-1',
    question_text: 'A question',
    question_type: QuestionType.CHARACTER,
    difficulty: QuestionDifficulty.MEDIUM,
    category: 'character',
    order: 1,
    generated_at: '2024-01-01T00:00:00Z',
    metadata: { suggested_response_length: '100 words' },
    ...overrides,
  };
}

const baseProgress: QuestionProgressResponse = {
  total: 3,
  completed: 1,
  in_progress: 0,
  progress: 1 / 3,
  status: 'in-progress',
};

function getDots(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll('[data-slot="progress-dot"]'));
}

describe('QuestionProgress - status and bar', () => {
  it('shows "X of Y questions answered" while in progress', () => {
    render(
      <QuestionProgress progress={baseProgress} currentIndex={0} totalQuestions={3} />
    );
    expect(screen.getByText('1 of 3 questions answered')).toBeInTheDocument();
  });

  it('sets progressbar aria-valuenow from the 0-1 progress value', () => {
    render(
      <QuestionProgress progress={baseProgress} currentIndex={0} totalQuestions={3} />
    );
    // 1/3 -> 33
    expect(screen.getByTestId('question-progressbar')).toHaveAttribute('aria-valuenow', '33');
  });
});

describe('QuestionProgress - per-question dots', () => {
  it('colours dots by each question response_status, not by position', () => {
    // Out-of-order: only the 3rd question is completed.
    const questions = [
      makeQuestion({ id: 'q-1' }),
      makeQuestion({ id: 'q-2', response_status: 'draft' as any }),
      makeQuestion({ id: 'q-3', response_status: 'completed' as any }),
    ];

    const { container } = render(
      <QuestionProgress
        progress={baseProgress}
        currentIndex={0}
        totalQuestions={3}
        questions={questions}
      />
    );

    const dots = getDots(container);
    // q-1 unanswered + current -> blue; q-2 draft -> amber; q-3 completed -> green
    expect(dots[0].className).toContain('bg-blue-600');
    expect(dots[1].className).toContain('bg-amber-600');
    expect(dots[2].className).toContain('bg-green-600');
  });

  it('falls back to positional colouring when no questions array is given', () => {
    const { container } = render(
      <QuestionProgress
        progress={{ ...baseProgress, completed: 2 }}
        currentIndex={2}
        totalQuestions={3}
      />
    );

    const dots = getDots(container);
    // First two positions completed (green), third is current (blue)
    expect(dots[0].className).toContain('bg-green-600');
    expect(dots[1].className).toContain('bg-green-600');
    expect(dots[2].className).toContain('bg-blue-600');
  });
});
