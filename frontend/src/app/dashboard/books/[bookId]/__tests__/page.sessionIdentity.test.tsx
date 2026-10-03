import React, { Suspense, useEffect } from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
// The jest.fn from src/__mocks__/better-auth-react.ts, via the real auth client.
import { useSession } from '@/lib/auth-client';

import BookPage from '../page';
import bookClient from '@/lib/api/bookClient';

/**
 * #758: the book page reloads for a different user, not a different object.
 *
 * better-auth hands out a new session `data` object every time it refetches the
 * session (window focus, for one) even when nothing about the user changed. The
 * page keyed its load on that object, so a refetch flipped it back to its
 * skeleton, unmounting ChapterTabs and the chapter editor inside it.
 */

jest.mock('next/navigation', () => {
  const params = new URLSearchParams();
  return { useSearchParams: () => params };
});
jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  default: { getBook: jest.fn(), getToc: jest.fn(), getBookSummary: jest.fn() },
}));
jest.mock('@/lib/toast', () => ({ toast: Object.assign(jest.fn(), { error: jest.fn(), success: jest.fn() }) }));
jest.mock('@/components/navigation/ChapterBreadcrumb', () => ({ ChapterBreadcrumb: () => null }));
jest.mock('@/components/BookMetadataForm', () => ({ BookMetadataForm: () => null }));
jest.mock('@/components/export/ExportOptionsModal', () => ({ ExportOptionsModal: () => null }));
jest.mock('@/components/export/ExportProgressModal', () => ({ ExportProgressModal: () => null }));

let chapterTabsMounts = 0;
jest.mock('@/components/chapters/ChapterTabs', () => ({
  ChapterTabs: function ChapterTabs() {
    useEffect(() => {
      chapterTabsMounts += 1;
    }, []);
    return <div data-testid="chapter-tabs" />;
  },
}));

const mockedClient = bookClient as jest.Mocked<typeof bookClient>;
const mockedUseSession = useSession as unknown as jest.Mock;

type Book = Awaited<ReturnType<typeof bookClient.getBook>>;
type Toc = Awaited<ReturnType<typeof bookClient.getToc>>;

const sessionFor = (userId: string) => ({
  data: { user: { id: userId, email: `${userId}@example.com`, name: userId, image: null }, session: { id: `s-${userId}` } },
  isPending: false,
  error: null,
});
let currentSession = sessionFor('user-1');

const value = { bookId: 'book-1' };
const params = Object.assign(Promise.resolve(value), { status: 'fulfilled', value });
const page = () => (
  <Suspense fallback={null}>
    <BookPage params={params} />
  </Suspense>
);

describe('BookPage session identity (#758)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    chapterTabsMounts = 0;
    currentSession = sessionFor('user-1');
    mockedUseSession.mockImplementation(() => currentSession);
    mockedClient.getBook.mockResolvedValue({ id: 'book-1', title: 'Book', description: '', owner_id: 'user-1' } as unknown as Book);
    mockedClient.getToc.mockResolvedValue({
      toc: { chapters: [{ id: 'ch-1', title: 'One', description: '', level: 1, order: 1, subchapters: [] }] },
    } as unknown as Toc);
    mockedClient.getBookSummary.mockResolvedValue({ summary: 'S' } as Awaited<ReturnType<typeof bookClient.getBookSummary>>);
  });

  it('keeps the chapter tabs mounted when the session object changes for the same user', async () => {
    const { rerender } = render(page());
    await waitFor(() => expect(screen.getByTestId('chapter-tabs')).toBeInTheDocument());

    currentSession = sessionFor('user-1');
    rerender(page());

    expect(screen.queryByTestId('book-details-skeleton')).toBeNull();
    await act(async () => {});
    expect(screen.getByTestId('chapter-tabs')).toBeInTheDocument();
    expect(chapterTabsMounts).toBe(1);
    expect(mockedClient.getBook).toHaveBeenCalledTimes(1);
  });

  it('reloads the book when a different user signs in', async () => {
    const { rerender } = render(page());
    await waitFor(() => expect(screen.getByTestId('chapter-tabs')).toBeInTheDocument());

    currentSession = sessionFor('user-2');
    rerender(page());

    expect(screen.getByTestId('book-details-skeleton')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId('chapter-tabs')).toBeInTheDocument());
    expect(mockedClient.getBook).toHaveBeenCalledTimes(2);
  });
});
