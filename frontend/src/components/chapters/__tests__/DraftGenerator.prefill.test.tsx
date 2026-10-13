/**
 * "Generate AI Draft" in the editor's toolbar starts from the chapter's
 * interview answers (#834).
 *
 * It opened with five sample questions and empty answers, whatever the writer
 * had already answered in the Interview Questions tab of the same chapter, and
 * a draft was written from whatever was retyped there.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import { DraftGenerator } from '../DraftGenerator';
import bookClient from '@/lib/api/bookClient';

jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  default: {
    getChapterQAResponses: jest.fn(),
    generateChapterDraftWithErrorHandling: jest.fn(),
    getUserProfile: jest.fn().mockResolvedValue({ preferences: {} }),
  },
}));
jest.mock('@/lib/toast', () => ({ toast: Object.assign(jest.fn(), { error: jest.fn(), success: jest.fn() }) }));
jest.mock('@/hooks/useUserPreferences', () => ({ useUserPreferences: () => null }));

const mockedClient = bookClient as jest.Mocked<typeof bookClient>;
type Saved = Awaited<ReturnType<typeof bookClient.getChapterQAResponses>>;

const saved = (...pairs: Array<[string, string, string?]>): Saved => ({
  responses: pairs.map(([question, answer, status], index) => ({
    question, answer, questionId: `q${index + 1}`, status: status ?? 'completed',
  })),
  totalQuestions: pairs.length,
  completedCount: pairs.filter(([, , status]) => (status ?? 'completed') === 'completed').length,
  inProgressCount: pairs.filter(([, , status]) => status === 'draft').length,
});

const questions = () => screen.getAllByRole('textbox', { name: /^Question \d+$/ }).map(input => (input as HTMLInputElement).value);
const answers = () => screen.getAllByRole('textbox', { name: /^Answer to question \d+$/ }).map(input => (input as HTMLTextAreaElement).value);

async function opened(props: Partial<React.ComponentProps<typeof DraftGenerator>> = {}) {
  const view = render(<DraftGenerator bookId="book-1" chapterId="chapter-1" chapterTitle="The Keeper" {...props} />);
  fireEvent.click(screen.getByRole('button', { name: /generate ai draft/i }));
  await screen.findByRole('dialog');
  return view;
}

beforeEach(() => {
  jest.clearAllMocks();
  mockedClient.generateChapterDraftWithErrorHandling.mockResolvedValue({
    data: {
      success: true, book_id: 'book-1', chapter_id: 'chapter-1', draft: '<p>A draft.</p>',
      metadata: { word_count: 2, estimated_reading_time: 1, generated_at: '', model_used: '', writing_style: '', target_length: 2000, actual_length: 2 },
      suggestions: [],
    },
  } as never);
});

describe('the toolbar draft generator', () => {
  it('opens with the chapter\'s saved interview answers', async () => {
    mockedClient.getChapterQAResponses.mockResolvedValue(
      saved(['Who keeps the light?', 'An old man named Tam.'], ['What does he find?', 'A letter in a bottle.']),
    );

    await opened();

    await waitFor(() => expect(questions()).toEqual(['Who keeps the light?', 'What does he find?']));
    expect(answers()).toEqual(['An old man named Tam.', 'A letter in a bottle.']);
    expect(mockedClient.getChapterQAResponses).toHaveBeenCalledWith('book-1', 'chapter-1');
  });

  it('includes an answer that is still a draft', async () => {
    mockedClient.getChapterQAResponses.mockResolvedValue(
      saved(['Who keeps the light?', 'An old man named Tam.'], ['What does he find?', 'Not sure yet, maybe a', 'draft']),
    );

    await opened();

    await waitFor(() => expect(answers()).toEqual(['An old man named Tam.', 'Not sure yet, maybe a']));
  });

  it('writes the draft from those answers', async () => {
    mockedClient.getChapterQAResponses.mockResolvedValue(saved(['Who keeps the light?', 'An old man named Tam.']));
    await opened();
    await waitFor(() => expect(answers()).toEqual(['An old man named Tam.']));

    fireEvent.click(screen.getByRole('button', { name: /^generate draft$/i }));

    await waitFor(() => expect(mockedClient.generateChapterDraftWithErrorHandling).toHaveBeenCalled());
    expect(mockedClient.generateChapterDraftWithErrorHandling.mock.calls[0][2].question_responses).toEqual([
      { question: 'Who keeps the light?', answer: 'An old man named Tam.' },
    ]);
  });

  it('falls back to the sample questions for a chapter with no answers yet', async () => {
    mockedClient.getChapterQAResponses.mockResolvedValue(saved());

    await opened();

    await waitFor(() => expect(mockedClient.getChapterQAResponses).toHaveBeenCalled());
    expect(questions()).toHaveLength(5);
    expect(questions()[0]).toMatch(/main concept or idea/i);
    expect(answers()).toEqual(['', '', '', '', '']);
  });

  it('falls back to the sample questions when the answers cannot be read', async () => {
    mockedClient.getChapterQAResponses.mockRejectedValue(new Error('Network error'));

    await opened();

    await waitFor(() => expect(mockedClient.getChapterQAResponses).toHaveBeenCalled());
    expect(questions()).toHaveLength(5);
    expect(screen.getByRole('dialog')).not.toHaveTextContent(/network error/i);
  });

  it('does not write over what the writer has typed while the answers were loading', async () => {
    let arrive!: (value: Saved) => void;
    mockedClient.getChapterQAResponses.mockReturnValue(new Promise<Saved>((resolve) => { arrive = resolve; }));
    await opened();

    fireEvent.change(screen.getByRole('textbox', { name: 'Answer to question 1' }), { target: { value: 'Typed before they arrived' } });
    arrive(saved(['Who keeps the light?', 'An old man named Tam.']));
    await waitFor(() => expect(mockedClient.getChapterQAResponses).toHaveBeenCalled());
    await Promise.resolve();

    expect(answers()[0]).toBe('Typed before they arrived');
    expect(questions()).toHaveLength(5);
  });

  it('reads the answers of the chapter it is opened for, each time it is opened', async () => {
    mockedClient.getChapterQAResponses.mockResolvedValue(saved(['Who keeps the light?', 'An old man named Tam.']));
    const view = await opened();
    await waitFor(() => expect(answers()).toEqual(['An old man named Tam.']));
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());

    mockedClient.getChapterQAResponses.mockResolvedValue(saved(['What does the sea say?', 'It says wait.']));
    view.rerender(<DraftGenerator bookId="book-1" chapterId="chapter-2" chapterTitle="The First Letter" />);
    fireEvent.click(screen.getByRole('button', { name: /generate ai draft/i }));

    await waitFor(() => expect(questions()).toEqual(['What does the sea say?']));
    expect(mockedClient.getChapterQAResponses).toHaveBeenLastCalledWith('book-1', 'chapter-2');
  });
});
