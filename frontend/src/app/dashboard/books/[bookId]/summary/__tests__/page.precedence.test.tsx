import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import BookSummaryPage from '../page';
import bookClient from '@/lib/api/bookClient';

jest.mock('@/lib/api/bookClient');
jest.mock('@/lib/voice/useSpeechRecognitionSupported', () => ({
  useSpeechRecognitionSupported: () => false,
}));

const mockPush = jest.fn();
let mockParams: Record<string, string> = { bookId: 'book-1' };
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
  useParams: () => mockParams,
}));

const mockedClient = bookClient as jest.Mocked<typeof bookClient>;
type SummaryResponse = Awaited<ReturnType<typeof bookClient.getBookSummary>>;

/**
 * Which copy of a book summary wins (#718).
 *
 * The server copy is the source of truth and replaces the field when it loads,
 * except over anything the user typed while it was loading. A draft kept in
 * localStorage is the fallback when the load fails. A book change starts from
 * that book's state, never the previous book's text.
 */

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

const field = () => screen.getByPlaceholderText(/Describe your book/i) as HTMLTextAreaElement;

describe('BookSummaryPage summary precedence (#718)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    mockParams = { bookId: 'book-1' };
    mockedClient.saveBookSummary.mockResolvedValue({ summary: '', success: true } as never);
  });

  it('keeps what the user typed while the summary was loading', async () => {
    const load = deferred<SummaryResponse>();
    mockedClient.getBookSummary.mockReturnValue(load.promise);
    render(<BookSummaryPage />);

    fireEvent.change(field(), { target: { value: 'Typed during the load' } });

    await act(async () => {
      load.resolve({ summary: 'Server copy', summary_history: [] } as SummaryResponse);
    });

    expect(field()).toHaveValue('Typed during the load');
  });

  it('shows the server copy when it loads, even with a local draft stored', async () => {
    localStorage.setItem('book-summary-book-1', 'Old local draft');
    mockedClient.getBookSummary.mockResolvedValue({ summary: 'Server copy', summary_history: [] } as SummaryResponse);

    render(<BookSummaryPage />);

    await waitFor(() => expect(field()).toHaveValue('Server copy'));
  });

  it('falls back to the local draft when the load fails', async () => {
    localStorage.setItem('book-summary-book-1', 'Local draft');
    mockedClient.getBookSummary.mockRejectedValue(new Error('offline'));

    render(<BookSummaryPage />);

    await waitFor(() => expect(field()).toHaveValue('Local draft'));
  });

  it('does not push a fallback draft to the server until the user edits it', async () => {
    // From the pre-PR review: the server stays the source of truth. A load can
    // fail transiently while the server holds a newer copy, so restoring the old
    // draft must not overwrite it on its own; only a deliberate edit saves.
    localStorage.setItem('book-summary-book-1', 'Old local draft');
    mockedClient.getBookSummary.mockRejectedValue(new Error('transient'));

    render(<BookSummaryPage />);
    await waitFor(() => expect(field()).toHaveValue('Old local draft'));

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 1200));
    });
    expect(mockedClient.saveBookSummary).not.toHaveBeenCalled();

    fireEvent.change(field(), { target: { value: 'Old local draft, now edited' } });
    await waitFor(
      () => expect(mockedClient.saveBookSummary).toHaveBeenCalledWith('book-1', 'Old local draft, now edited'),
      { timeout: 2500 }
    );
  });

  it('does not carry the previous book’s text into the next book', async () => {
    mockedClient.getBookSummary.mockResolvedValueOnce({ summary: 'Book one summary', summary_history: [] } as SummaryResponse);
    const second = deferred<SummaryResponse>();
    mockedClient.getBookSummary.mockReturnValueOnce(second.promise);

    const { rerender } = render(<BookSummaryPage />);
    await waitFor(() => expect(field()).toHaveValue('Book one summary'));

    mockParams = { bookId: 'book-2' };
    rerender(<BookSummaryPage />);

    await waitFor(() => expect(field()).toHaveValue(''));
    // Nor is it written into book two's local draft while book two loads.
    expect(localStorage.getItem('book-summary-book-2')).not.toBe('Book one summary');

    await act(async () => {
      second.resolve({ summary: 'Book two summary', summary_history: [] } as SummaryResponse);
    });
    expect(field()).toHaveValue('Book two summary');
  });

  it('keeps the next book’s draft for its failed load after switching from a loaded book', async () => {
    // From the pre-PR review: the switch render clears the field while the
    // previous book still reads as loaded, so auto-save could write '' over the
    // next book's draft before that book's load failed and fell back to it.
    localStorage.setItem('book-summary-book-2', 'Book two draft');
    mockedClient.getBookSummary
      .mockResolvedValueOnce({ summary: 'Book one summary', summary_history: [] } as SummaryResponse)
      .mockRejectedValueOnce(new Error('offline'));

    const { rerender } = render(<BookSummaryPage />);
    await waitFor(() => expect(field()).toHaveValue('Book one summary'));

    mockParams = { bookId: 'book-2' };
    rerender(<BookSummaryPage />);

    await waitFor(() => expect(field()).toHaveValue('Book two draft'));
  });

  it('keeps a book’s draft when the user returns to it before the other book loads', async () => {
    // From the third pre-PR review: A loads, the user goes to B and back to A
    // before B settles. Keyed by book alone, A still read as loaded on its second
    // visit, so auto-save could erase A's draft before that visit's load failed.
    mockedClient.getBookSummary
      .mockResolvedValueOnce({ summary: 'Book one summary', summary_history: [] } as SummaryResponse)
      .mockReturnValueOnce(new Promise<SummaryResponse>(() => {}))
      .mockRejectedValueOnce(new Error('offline'));

    const { rerender } = render(<BookSummaryPage />);
    await waitFor(() => expect(field()).toHaveValue('Book one summary'));

    mockParams = { bookId: 'book-2' };
    rerender(<BookSummaryPage />);
    localStorage.setItem('book-summary-book-1', 'Book one draft');
    mockParams = { bookId: 'book-1' };
    rerender(<BookSummaryPage />);

    await waitFor(() => expect(field()).toHaveValue('Book one draft'));
  });

  it('ignores the previous book’s load when it lands after the switch', async () => {
    const first = deferred<SummaryResponse>();
    mockedClient.getBookSummary
      .mockReturnValueOnce(first.promise)
      .mockResolvedValueOnce({ summary: 'Book two summary', summary_history: [] } as SummaryResponse);

    const { rerender } = render(<BookSummaryPage />);
    mockParams = { bookId: 'book-2' };
    rerender(<BookSummaryPage />);
    await waitFor(() => expect(field()).toHaveValue('Book two summary'));

    await act(async () => {
      first.resolve({ summary: 'Book one summary', summary_history: [] } as SummaryResponse);
    });

    expect(field()).toHaveValue('Book two summary');
  });
});
