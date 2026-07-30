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
