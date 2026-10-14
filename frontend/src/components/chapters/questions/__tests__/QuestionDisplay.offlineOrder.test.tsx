/**
 * A question's queued offline saves land in the order they were made (#873).
 *
 * The real RetryQueue drains here; only the network is stood in for. A draft
 * write is slower than a completion, so a parallel drain lets the draft land
 * last and the stored status ends up `draft` while the screen says completed.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import QuestionDisplay from '../QuestionDisplay';
import { Question, QuestionType, QuestionDifficulty, ResponseStatus } from '@/types/chapter-questions';
import { bookClient } from '@/lib/api/bookClient';
import { retryQueue } from '@/lib/utils/retryQueue';

jest.mock('@/lib/api/bookClient');
jest.mock('@/hooks/useOnlineStatus', () => ({
  useOnlineStatus: jest.fn(() => ({ isOnline: false, wasOffline: false })),
}));
jest.mock('@/components/ui/use-toast', () => ({
  useToast: () => ({ toast: jest.fn() }),
}));

const question: Question = {
  id: 'question-1',
  book_id: 'book-1',
  chapter_id: 'chapter-1',
  question_type: QuestionType.CHARACTER,
  difficulty: QuestionDifficulty.MEDIUM,
  question_text: 'Who is this book for?',
  metadata: { help_text: '', examples: [], suggested_response_length: '' },
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

// What the server holds: the last write to land wins.
let stored: { response_text: string; status: ResponseStatus } | null;

beforeEach(() => {
  jest.clearAllMocks();
  retryQueue.clear();
  stored = null;
  (bookClient.getQuestionResponse as jest.Mock).mockImplementation(async () =>
    stored ? { has_response: true, response: stored, success: true } : { has_response: false, response: null, success: true }
  );
  (bookClient.saveQuestionResponse as jest.Mock).mockImplementation(
    async (_b: string, _c: string, _q: string, body: { response_text: string; status: ResponseStatus }) => {
      // A draft write takes longer than a completion.
      if (body.status === ResponseStatus.DRAFT) await new Promise(r => setTimeout(r, 50));
      stored = { ...body };
      return { success: true };
    }
  );
});

function renderQuestion() {
  render(
    <QuestionDisplay
      bookId="book-1"
      chapterId="chapter-1"
      question={question}
      onResponseSaved={jest.fn()}
      onRegenerateQuestion={jest.fn()}
    />
  );
  return screen.getByLabelText(/your response/i);
}

async function reconnect() {
  await retryQueue.processQueue();
  await waitFor(() => expect(retryQueue.size()).toBe(0));
}

it('a draft queued before Complete Response does not overwrite the completion', async () => {
  const textarea = renderQuestion();
  fireEvent.change(textarea, { target: { value: 'Busy founders' } });
  await waitFor(() => expect(retryQueue.size()).toBe(1), { timeout: 5000 });

  fireEvent.click(screen.getByRole('button', { name: /complete response/i }));
  await waitFor(() => expect(retryQueue.size()).toBe(2));

  await reconnect();
  expect(stored?.status).toBe(ResponseStatus.COMPLETED);
}, 15000);

it('editing after a queued Complete Response does not turn it back into a draft', async () => {
  const user = userEvent.setup();
  const textarea = renderQuestion();
  fireEvent.change(textarea, { target: { value: 'Busy founders' } });
  fireEvent.click(screen.getByRole('button', { name: /complete response/i }));
  await waitFor(() => expect(retryQueue.size()).toBe(1));

  await user.type(textarea, ' and their teams');
  // Past the 3-second autosave window.
  await new Promise(r => setTimeout(r, 3500));

  await reconnect();
  expect(stored?.status).toBe(ResponseStatus.COMPLETED);
}, 15000);

it('a queued completion still locks the answer after switching question and back', async () => {
  const props = { bookId: 'book-1', chapterId: 'chapter-1', onResponseSaved: jest.fn(), onRegenerateQuestion: jest.fn() };
  const { rerender } = render(<QuestionDisplay {...props} question={question} />);
  fireEvent.change(screen.getByLabelText(/your response/i), { target: { value: 'Busy founders' } });
  fireEvent.click(screen.getByRole('button', { name: /complete response/i }));
  await waitFor(() => expect(retryQueue.size()).toBe(1));

  rerender(<QuestionDisplay {...props} question={{ ...question, id: 'question-2' }} />);
  rerender(<QuestionDisplay {...props} question={question} />);

  await waitFor(() => expect(screen.getByLabelText(/your response/i)).toBeDisabled());
});
