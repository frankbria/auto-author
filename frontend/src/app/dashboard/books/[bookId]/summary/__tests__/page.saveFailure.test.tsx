import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import BookSummaryPage from '../page';
import bookClient from '@/lib/api/bookClient';

jest.mock('@/lib/api/bookClient');
jest.mock('@/lib/voice/useSpeechRecognitionSupported', () => ({
  useSpeechRecognitionSupported: () => false,
}));

let mockParams: Record<string, string> = { bookId: 'book-1' };
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
  useParams: () => mockParams,
}));

const mockedClient = bookClient as jest.Mocked<typeof bookClient>;
type SummaryResponse = Awaited<ReturnType<typeof bookClient.getBookSummary>>;

/**
 * A summary that could not be saved is not lost, and the writer is told (#832).
 *
 * The page saves a second after typing stops. When that save failed, nothing
 * said so, and the only copy of the text was the one in the browser. The next
 * visit loaded the server's older copy into the field and wrote it over the
 * browser's.
 */

const UNSAVED = 'book-summary-unsaved-book-1';
const field = () => screen.getByPlaceholderText(/Describe your book/i) as HTMLTextAreaElement;

function serverHas(summary: string) {
  mockedClient.getBookSummary.mockResolvedValue({ summary, summary_history: [] } as SummaryResponse);
}

async function opened() {
  const view = render(<BookSummaryPage />);
  await waitFor(() => expect(mockedClient.getBookSummary).toHaveBeenCalled());
  await act(async () => {});
  return view;
}

async function typeAndWaitForTheSave(text: string) {
  fireEvent.change(field(), { target: { value: text } });
  await act(async () => {
    jest.advanceTimersByTime(1000);
  });
  await act(async () => {});
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  jest.useFakeTimers();
  mockParams = { bookId: 'book-1' };
  mockedClient.saveBookSummary.mockImplementation(async (_book, summary) => ({ summary, success: true }) as never);
});

afterEach(() => {
  jest.runOnlyPendingTimers();
  jest.useRealTimers();
  jest.restoreAllMocks();
});

describe('a summary save that fails', () => {
  it('says so', async () => {
    serverHas('The saved summary');
    await opened();
    mockedClient.saveBookSummary.mockRejectedValue(new Error('Network error'));

    await typeAndWaitForTheSave('A summary the server never received');

    expect(await screen.findByText(/could not be saved/i)).toBeInTheDocument();
    expect(screen.getByText(/kept on this device/i)).toBeInTheDocument();
  });

  it('keeps the text that was not saved, apart from the working copy', async () => {
    serverHas('The saved summary');
    await opened();
    mockedClient.saveBookSummary.mockRejectedValue(new Error('Network error'));

    await typeAndWaitForTheSave('A summary the server never received');

    expect(localStorage.getItem(UNSAVED)).toBe('A summary the server never received');
  });

  it('stops saying so, and lets the kept copy go, once a save gets through', async () => {
    serverHas('The saved summary');
    await opened();
    mockedClient.saveBookSummary.mockRejectedValueOnce(new Error('Network error'));
    await typeAndWaitForTheSave('First try');
    expect(await screen.findByText(/could not be saved/i)).toBeInTheDocument();

    await typeAndWaitForTheSave('Second try');

    await waitFor(() => expect(screen.queryByText(/could not be saved/i)).not.toBeInTheDocument());
    expect(localStorage.getItem(UNSAVED)).toBeNull();
  });

  it('says nothing when the save works', async () => {
    serverHas('The saved summary');
    await opened();

    await typeAndWaitForTheSave('A summary the server received');

    expect(screen.queryByText(/could not be saved/i)).not.toBeInTheDocument();
    expect(localStorage.getItem(UNSAVED)).toBeNull();
  });
});

describe('coming back after a save failed', () => {
  it('shows the saved summary, keeps the unsaved one, and offers the choice', async () => {
    localStorage.setItem(UNSAVED, 'What I wrote last time, which was not saved');
    serverHas('The older, saved summary');

    await opened();

    expect(field()).toHaveValue('The older, saved summary');
    expect(screen.getByText(/was not saved/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /restore it/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /discard it/i })).toBeInTheDocument();
    expect(localStorage.getItem(UNSAVED)).toBe('What I wrote last time, which was not saved');
  });

  it('keeps the unsaved one through the page saving its working copy, and through typing', async () => {
    localStorage.setItem(UNSAVED, 'What I wrote last time, which was not saved');
    serverHas('The older, saved summary');
    await opened();

    await typeAndWaitForTheSave('Something else entirely');

    expect(localStorage.getItem(UNSAVED)).toBe('What I wrote last time, which was not saved');
    expect(screen.getByRole('button', { name: /restore it/i })).toBeInTheDocument();
  });

  it('restores it when asked, and saves it', async () => {
    localStorage.setItem(UNSAVED, 'What I wrote last time, which was not saved');
    serverHas('The older, saved summary');
    await opened();

    fireEvent.click(screen.getByRole('button', { name: /restore it/i }));
    await act(async () => {
      jest.advanceTimersByTime(1000);
    });
    await act(async () => {});

    expect(field()).toHaveValue('What I wrote last time, which was not saved');
    expect(mockedClient.saveBookSummary).toHaveBeenCalledWith('book-1', 'What I wrote last time, which was not saved');
    expect(screen.queryByRole('button', { name: /restore it/i })).not.toBeInTheDocument();
    expect(localStorage.getItem(UNSAVED)).toBeNull();
  });

  it('discards it when asked', async () => {
    localStorage.setItem(UNSAVED, 'What I wrote last time, which was not saved');
    serverHas('The older, saved summary');
    await opened();

    fireEvent.click(screen.getByRole('button', { name: /discard it/i }));

    expect(field()).toHaveValue('The older, saved summary');
    expect(localStorage.getItem(UNSAVED)).toBeNull();
    expect(screen.queryByRole('button', { name: /restore it/i })).not.toBeInTheDocument();
  });

  it('offers nothing when what was kept is what the server has', async () => {
    localStorage.setItem(UNSAVED, 'The same summary');
    serverHas('The same summary');

    await opened();

    expect(screen.queryByRole('button', { name: /restore it/i })).not.toBeInTheDocument();
    expect(localStorage.getItem(UNSAVED)).toBeNull();
  });

  it('offers nothing for another book', async () => {
    localStorage.setItem('book-summary-unsaved-book-2', 'Another book entirely');
    serverHas('The saved summary');

    await opened();

    expect(screen.queryByRole('button', { name: /restore it/i })).not.toBeInTheDocument();
    expect(localStorage.getItem('book-summary-unsaved-book-2')).toBe('Another book entirely');
  });
});

describe('moving on to another book', () => {
  it('leaves the first book\'s notices behind', async () => {
    localStorage.setItem(UNSAVED, 'What I wrote last time, which was not saved');
    serverHas('The older, saved summary');
    const view = await opened();
    mockedClient.saveBookSummary.mockRejectedValue(new Error('Network error'));
    await typeAndWaitForTheSave('A summary the server never received');
    expect(await screen.findByText(/could not be saved/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /restore it/i })).toBeInTheDocument();

    mockParams = { bookId: 'book-2' };
    serverHas('The second book');
    view.rerender(<BookSummaryPage />);
    await waitFor(() => expect(field()).toHaveValue('The second book'));

    expect(screen.queryByText(/could not be saved/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /restore it/i })).not.toBeInTheDocument();
  });
});

describe('a browser that will not store anything', () => {
  it('does not break typing, and says the text is in neither place when the save fails too', async () => {
    serverHas('The saved summary');
    await opened();
    jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('The quota has been exceeded.', 'QuotaExceededError');
    });
    mockedClient.saveBookSummary.mockRejectedValue(new Error('Network error'));

    await typeAndWaitForTheSave('Typed into a full browser');

    expect(field()).toHaveValue('Typed into a full browser');
    expect(await screen.findByText(/could not be saved/i)).toBeInTheDocument();
    expect(screen.getByText(/could not be kept on this device either/i)).toBeInTheDocument();
  });

  it('still saves to the server', async () => {
    serverHas('The saved summary');
    await opened();
    jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('The quota has been exceeded.', 'QuotaExceededError');
    });

    await typeAndWaitForTheSave('Typed into a full browser');

    expect(mockedClient.saveBookSummary).toHaveBeenCalledWith('book-1', 'Typed into a full browser');
    expect(screen.queryByText(/could not be saved/i)).not.toBeInTheDocument();
  });
});
