/**
 * Tests for the ChapterEditor Write / Interview Questions view toggle (#105/#54).
 * Wiring the interview-questions Q&A panel into the live editor is what makes the
 * #54 "answers persist after refresh" flow reachable in the navigable app.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChapterEditor } from '../ChapterEditor';
import bookClient from '@/lib/api/bookClient';

jest.mock('@/lib/api/bookClient');
jest.mock('../DraftGenerator', () => ({
  DraftGenerator: () => <div>Draft Generator</div>,
}));
jest.mock('../StyleTransformer', () => ({
  StyleTransformer: () => <div>Style Transformer</div>,
}));
jest.mock('../questions/QuestionContainer', () => ({
  __esModule: true,
  default: ({ chapterId }: { chapterId: string }) => (
    <div data-testid="question-container">Questions for {chapterId}</div>
  ),
}));

const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;

describe('ChapterEditor view toggle', () => {
  const props = {
    bookId: 'book-1',
    chapterId: 'chapter-1',
    chapterTitle: 'Test Chapter',
    initialContent: '<p>hi</p>',
  };

  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>hi</p>' });
  });

  it('defaults to the write view (editor visible, questions hidden)', async () => {
    render(<ChapterEditor {...props} />);
    await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument());
    expect(screen.queryByTestId('question-container')).not.toBeInTheDocument();
  });

  it('shows the interview-questions panel when the Questions tab is selected', async () => {
    const user = userEvent.setup();
    render(<ChapterEditor {...props} />);
    await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument());

    await user.click(screen.getByRole('tab', { name: /interview questions/i }));

    expect(screen.getByTestId('question-container')).toBeInTheDocument();
    expect(screen.getByText('Questions for chapter-1')).toBeInTheDocument();
    // Editor body is unmounted while answering questions.
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('returns to the editor when the Write tab is selected again', async () => {
    const user = userEvent.setup();
    render(<ChapterEditor {...props} />);
    await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument());

    await user.click(screen.getByRole('tab', { name: /interview questions/i }));
    expect(screen.getByTestId('question-container')).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /^write$/i }));
    expect(screen.queryByTestId('question-container')).not.toBeInTheDocument();
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });
});
