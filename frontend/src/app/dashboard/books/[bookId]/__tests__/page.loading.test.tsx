import React, { Suspense } from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import BookPage from '../page';
import bookClient from '@/lib/api/bookClient';


jest.mock('next/navigation', () => {
  const params = new URLSearchParams();
  return { useSearchParams: () => params };
});
jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  default: {
    getBook: jest.fn(),
    getToc: jest.fn(),
    getBookSummary: jest.fn(),
  },
}));
jest.mock('@/lib/toast', () => ({ toast: Object.assign(jest.fn(), { error: jest.fn(), success: jest.fn() }) }));
jest.mock('@/components/navigation/ChapterBreadcrumb', () => ({
  ChapterBreadcrumb: ({ bookTitle }: { bookTitle: string }) => <nav data-testid="breadcrumb">{bookTitle}</nav>,
}));
jest.mock('@/components/BookMetadataForm', () => ({ BookMetadataForm: () => null }));
jest.mock('@/components/chapters/ChapterTabs', () => ({ ChapterTabs: () => null }));
jest.mock('@/components/export/ExportOptionsModal', () => ({ ExportOptionsModal: () => null }));
jest.mock('@/components/export/ExportProgressModal', () => ({ ExportProgressModal: () => null }));

/**
 * Loading the book page (#584).
 *
 * The app router keeps this page mounted across a `[bookId]` change, so each
 * book's load has to own its result: a slow response for the book the user left
 * must not render under the book they moved to, where the metadata form would
 * then save its values against the wrong book. And Try Again, the one path from
 * the error state back to loading, must show the skeleton while it runs.
 */

const mockedClient = bookClient as jest.Mocked<typeof bookClient>;
type Book = Awaited<ReturnType<typeof bookClient.getBook>>;

const book = (id: string, title: string) =>
  ({ id, title, description: '', owner_id: 'u1', created_at: '', updated_at: '' }) as unknown as Book;

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

// React.use() reads a promise already marked fulfilled without suspending,
// which keeps Suspense out of what these tests measure. One object per book, so
// every render of a book sees the same params.
const paramsFor = new Map<string, Promise<{ bookId: string }>>();
const params = (bookId: string) => {
  if (!paramsFor.has(bookId)) {
    const value = { bookId };
    paramsFor.set(bookId, Object.assign(Promise.resolve(value), { status: 'fulfilled', value }));
  }
  return paramsFor.get(bookId)!;
};

const page = (bookId: string) => (
  <Suspense fallback={<div data-testid="suspended" />}>
    <BookPage params={params(bookId)} />
  </Suspense>
);

// The session comes from `src/__mocks__/better-auth-react.ts`, which returns one
// stable object as better-auth does. This page lists `session` in its loader's
// deps, so a mock that built a fresh object per call made it refetch in a loop
// and these tests time out. They are the tripwire for that mock.

describe('BookPage loading (#584)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedClient.getToc.mockRejectedValue(new Error('no toc'));
    mockedClient.getBookSummary.mockResolvedValue({ summary: '' } as Awaited<ReturnType<typeof bookClient.getBookSummary>>);
  });

  it('shows the skeleton while Try Again is running, then the book', async () => {
    const retry = deferred<Book>();
    mockedClient.getBook.mockRejectedValueOnce(new Error('offline')).mockReturnValueOnce(retry.promise);

    render(page('book-a'));
    await waitFor(() => expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /try again/i }));

    await waitFor(() => expect(screen.getByTestId('book-details-skeleton')).toBeInTheDocument());
    expect(screen.queryByRole('button', { name: /try again/i })).not.toBeInTheDocument();

    await act(async () => {
      retry.resolve(book('book-a', 'Book A'));
    });
    await waitFor(() => expect(screen.getByTestId('breadcrumb')).toHaveTextContent('Book A'));
  });

  it('does not render the previous book when its response lands last', async () => {
    const first = deferred<Book>();
    mockedClient.getBook.mockImplementation((id: string) =>
      id === 'book-a' ? first.promise : Promise.resolve(book('book-b', 'Book B'))
    );

    const { rerender } = render(page('book-a'));
    await waitFor(() => expect(mockedClient.getBook).toHaveBeenCalledWith('book-a'));

    rerender(page('book-b'));
    await waitFor(() => expect(screen.getByTestId('breadcrumb')).toHaveTextContent('Book B'));

    await act(async () => {
      first.resolve(book('book-a', 'Book A'));
    });

    expect(screen.getByTestId('breadcrumb')).toHaveTextContent('Book B');
  });
});
