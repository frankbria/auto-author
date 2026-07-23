import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import BookSummaryPage from '../page';
import bookClient from '@/lib/api/bookClient';
import { SUMMARY_MIN_WORDS, SUMMARY_MIN_CHARACTERS } from '@/lib/constants/summary-readiness';

// First tests for the summary page (issue #218). The client gate must match the
// real backend readiness gate — 30 words AND 150 characters (books.py:1150,
// ai_service.py:483) — so a summary that passes here is never bounced back by
// the TOC wizard's NOT_READY screen.

const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, back: jest.fn() }),
  useParams: () => ({ bookId: 'book-1' }),
}));

jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  default: {
    getBookSummary: jest.fn(),
    saveBookSummary: jest.fn(),
  },
}));

const mockClient = bookClient as jest.Mocked<typeof bookClient>;

/** A summary with `words` words of `wordLength` chars each. */
const summaryOf = (words: number, wordLength = 6) =>
  Array.from({ length: words }, () => 'a'.repeat(wordLength)).join(' ');

const READY_SUMMARY = summaryOf(SUMMARY_MIN_WORDS, 6); // 30 words / 209 chars

const typeSummary = (text: string) => {
  fireEvent.change(screen.getByLabelText('Book Summary'), { target: { value: text } });
};

const submitButton = () => screen.getByRole('button', { name: /continue to toc generation/i });

describe('BookSummaryPage — readiness gate (#218)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    mockClient.getBookSummary.mockResolvedValue({ summary: '', summary_history: [] } as never);
    mockClient.saveBookSummary.mockResolvedValue({ summary: '' } as never);
  });

  const renderPage = async () => {
    render(<BookSummaryPage />);
    await waitFor(() => expect(mockClient.getBookSummary).toHaveBeenCalled());
  };

  it('blocks submit for a summary that clears 150 chars but not 30 words', async () => {
    await renderPage();
    // 10 long words = 169 chars: passes the char minimum, fails the word minimum.
    const text = summaryOf(10, 16);
    expect(text.length).toBeGreaterThanOrEqual(SUMMARY_MIN_CHARACTERS);
    typeSummary(text);

    await waitFor(() => expect(submitButton()).toBeDisabled());
    expect(screen.getByText('Summary must be at least 30 words (currently 10).')).toBeInTheDocument();
  });

  it('blocks submit for a summary that clears 30 words but not 150 chars', async () => {
    await renderPage();
    // 40 two-letter words = 119 chars. This is the regression: the old
    // MIN_SUMMARY_LENGTH=30 char gate let this through, then the wizard bounced it.
    const text = Array.from({ length: 40 }, () => 'ab').join(' ');
    expect(text.length).toBeLessThan(SUMMARY_MIN_CHARACTERS);
    typeSummary(text);

    await waitFor(() => expect(submitButton()).toBeDisabled());
    expect(
      screen.getByText(`Summary must be at least 150 characters (currently ${text.length}).`)
    ).toBeInTheDocument();
  });

  it('blocks submit for the 30-character summary the old gate accepted', async () => {
    await renderPage();
    typeSummary('a'.repeat(30));
    await waitFor(() => expect(submitButton()).toBeDisabled());
  });

  it('allows submit and navigates once both minimums are met', async () => {
    await renderPage();
    typeSummary(READY_SUMMARY);

    await waitFor(() => expect(submitButton()).toBeEnabled());
    fireEvent.click(submitButton());

    await waitFor(() =>
      expect(mockClient.saveBookSummary).toHaveBeenCalledWith('book-1', READY_SUMMARY)
    );
    await waitFor(() =>
      expect(mockPush).toHaveBeenCalledWith('/dashboard/books/book-1/generate-toc')
    );
  });

  it('shows both word and character progress against the real minimums', async () => {
    await renderPage();
    typeSummary('one two three');

    expect(screen.getByText(`3 / ${SUMMARY_MIN_WORDS} words`)).toBeInTheDocument();
    expect(screen.getByText(`13 / ${SUMMARY_MIN_CHARACTERS} characters`)).toBeInTheDocument();
  });

  it('states the same minimums in the guidelines as the counter enforces', async () => {
    await renderPage();
    const guidelines = screen.getByText(/Guidelines:/i);
    expect(guidelines).toHaveTextContent('30 words');
    expect(guidelines).toHaveTextContent('150 characters');
  });

  it('never tells the user a minimum the gate does not enforce', async () => {
    await renderPage();
    // The contradictory copy this issue is about: a "30 characters" minimum and a
    // "Minimum 30 words recommended" hint two lines apart.
    expect(screen.queryByText(/Minimum: 30 characters/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Minimum 30 words recommended/i)).not.toBeInTheDocument();
  });

  it('keeps auto-saving work that is under the gate (no data loss)', async () => {
    jest.useFakeTimers();
    try {
      render(<BookSummaryPage />);
      typeSummary('too short to submit');
      jest.advanceTimersByTime(1000);
      await waitFor(() =>
        expect(mockClient.saveBookSummary).toHaveBeenCalledWith('book-1', 'too short to submit')
      );
    } finally {
      jest.useRealTimers();
    }
  });
});

// #331: the page heading hardcoded `text-gray-100` on the theme-aware
// background, so it was invisible (~1.1:1) in the shipped light theme. Pin that
// it now renders with the theme foreground token.
describe('BookSummaryPage — light-theme heading token (#331)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    mockClient.getBookSummary.mockResolvedValue({ summary: '', summary_history: [] } as never);
    mockClient.saveBookSummary.mockResolvedValue({ summary: '' } as never);
  });

  it('renders the page heading with the theme foreground token, not near-white gray', async () => {
    render(<BookSummaryPage />);
    await waitFor(() => expect(mockClient.getBookSummary).toHaveBeenCalled());

    const heading = screen.getByRole('heading', { level: 1, name: /provide a summary/i });
    expect(heading).toHaveClass('text-foreground');
    expect(heading.className).not.toMatch(/text-gray-\d/);
  });
});
