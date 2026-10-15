/**
 * The legacy chapter URL hands over to the book page through `?chapter=` (#855).
 *
 * It also wrote `chapter-tabs-<bookId>` to localStorage, which nothing reads:
 * the book page takes the chapter from the query string.
 */
import React, { Suspense } from 'react';
import { render, screen, act } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import ChapterContentPage from '../page';

jest.mock('next/navigation', () => ({ useRouter: jest.fn() }));
jest.mock('@/components/chapters/LazyChapterEditor', () => ({
  LazyChapterEditor: () => <div>editor</div>,
}));

describe('legacy chapter page (#855)', () => {
  const replace = jest.fn();

  beforeEach(() => {
    jest.useFakeTimers();
    replace.mockReset();
    localStorage.clear();
    (useRouter as jest.Mock).mockReturnValue({ replace, push: jest.fn() });
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('sends the reader to the book page with the chapter in the URL, and writes nothing to storage', async () => {
    const params = Promise.resolve({ bookId: 'book-1', chapterId: 'ch-2' });
    await act(async () => {
      render(
        <Suspense fallback={null}>
          <ChapterContentPage params={params} />
        </Suspense>
      );
    });
    await screen.findByText('editor');

    act(() => jest.advanceTimersByTime(2000));

    expect(replace).toHaveBeenCalledWith('/dashboard/books/book-1?chapter=ch-2');
    expect(Object.keys(localStorage)).toEqual([]);
  });
});
