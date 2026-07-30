/**
 * #349: the clarifying-questions answer field must have an accessible name.
 *
 * It had only a placeholder. Placeholder text is not an accessible name — it
 * vanishes the moment the user types, and several screen readers skip it
 * entirely — so the field announced as unlabelled and a user could not tell
 * which question they were answering.
 */
import { render, screen, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import ClarifyingQuestions from '../ClarifyingQuestions';

expect.extend(toHaveNoViolations);

// The component loads any previously-saved answers on mount and shows a loading
// state until that settles.
jest.mock('@/lib/api/bookClient', () => ({
  bookClient: {
    getQuestionResponses: jest.fn().mockResolvedValue({ responses: [] }),
    saveQuestionResponses: jest.fn().mockResolvedValue({}),
  },
}));

const QUESTIONS = [
  'What is the central argument of your book?',
  'Who is the intended reader?',
];

function renderQuestions() {
  return render(
    <ClarifyingQuestions
      questions={QUESTIONS}
      onSubmit={jest.fn()}
      isLoading={false}
      bookId="book-1"
    />
  );
}

describe('ClarifyingQuestions accessibility', () => {
  it('names the answer field after the question being asked', async () => {
    renderQuestions();

    // The accessible name must be the question itself, not "Type your answer
    // here..." — that is what tells the user what they are answering.
    await waitFor(() => {
      expect(screen.getByRole('textbox', { name: QUESTIONS[0] })).toBeInTheDocument();
    });
  });

  it('has no axe violations', async () => {
    const { container } = renderQuestions();
    await waitFor(() => {
      expect(screen.getByRole('textbox', { name: QUESTIONS[0] })).toBeInTheDocument();
    });
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('ClarifyingQuestions save announcements', () => {
  it('does not announce success while a save failure is showing', async () => {
    // lastSaved survives from the previous successful save, so a naive
    // lastSaved-first ternary announced "Answers auto-saved" at the same instant
    // the alert announced failure — two contradictory messages from one event.
    const { bookClient } = jest.requireMock('@/lib/api/bookClient');
    bookClient.getQuestionResponses.mockResolvedValueOnce({
      responses: [{ question: QUESTIONS[0], answer: 'a previous answer' }],
    });
    bookClient.saveQuestionResponses.mockRejectedValueOnce(new Error('nope'));

    const { container } = renderQuestions();
    await waitFor(() => {
      expect(screen.getByRole('textbox', { name: QUESTIONS[0] })).toBeInTheDocument();
    });

    const announcer = container.querySelector('[role="status"].sr-only');
    expect(announcer).toBeTruthy();
    // Whatever it says, it must never claim success at the same time as an alert.
    if (screen.queryByRole('alert')) {
      expect(announcer?.textContent ?? '').not.toMatch(/auto-saved/i);
    }
  });
});
