import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useSession } from '@/lib/auth-client';
import { useRouter } from 'next/navigation';
import Dashboard from '@/app/dashboard/page';
import bookClient from '@/lib/api/bookClient';
import { toast } from '@/lib/toast';

jest.mock('@/lib/auth-client');
jest.mock('@/lib/api/bookClient');
jest.mock('@/lib/toast', () => ({
  toast: Object.assign(jest.fn(), {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
  }),
}));
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

jest.mock('@/components/BookCreationWizard', () => ({
  BookCreationWizard: () => null,
}));

jest.mock('@/components/EmptyBookState', () => ({
  EmptyBookState: () => <div data-testid="empty-book-state">No books yet</div>,
}));

jest.mock('@/components/BookCard', () => ({
  __esModule: true,
  default: ({ book, onDelete }: any) => (
    <div data-testid={`book-card-${book.id}`}>
      <span>{book.title}</span>
      <button onClick={() => onDelete(book.id)}>Delete {book.title}</button>
    </div>
  ),
}));

/** The dashboard's page size. A page request over-fetches one extra row to learn hasMore. */
const PAGE_SIZE = 24;

const makeBooks = (count: number, offset = 0) =>
  Array.from({ length: count }, (_, i) => ({
    id: `book-${offset + i}`,
    title: `Book ${offset + i}`,
    chapters: 0,
    progress: 0,
    updated_at: '2026-01-01T00:00:00Z',
  }));

describe('Dashboard pagination (#493)', () => {
  const getUserBooks = bookClient.getUserBooks as jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
    // clearAllMocks does not drain a mockResolvedValueOnce queue, so an unconsumed
    // page from one test would answer the next test's first fetch.
    getUserBooks.mockReset();
    (useRouter as jest.Mock).mockReturnValue({ push: jest.fn() });
    (useSession as jest.Mock).mockReturnValue({
      data: { user: { id: 'user-123' }, session: { id: 'session-123' } },
      isPending: false,
      error: null,
    });
    (bookClient.deleteBook as jest.Mock).mockResolvedValue({ success: true });
  });

  it('requests one row beyond the page size so it can tell whether more exist', async () => {
    getUserBooks.mockResolvedValue(makeBooks(3));

    render(<Dashboard />);

    await waitFor(() => expect(getUserBooks).toHaveBeenCalled());
    expect(getUserBooks).toHaveBeenCalledWith({ skip: 0, limit: PAGE_SIZE + 1 });
  });

  it('hides the pager entirely when the library fits on one page', async () => {
    getUserBooks.mockResolvedValue(makeBooks(3));

    render(<Dashboard />);

    await screen.findByText('Book 0');
    expect(screen.queryByRole('navigation', { name: /pagination/i })).not.toBeInTheDocument();
  });

  it('renders only PAGE_SIZE cards even though PAGE_SIZE + 1 rows came back', async () => {
    getUserBooks.mockResolvedValue(makeBooks(PAGE_SIZE + 1));

    render(<Dashboard />);

    await screen.findByText('Book 0');
    expect(screen.getAllByText(/^Book \d+$/)).toHaveLength(PAGE_SIZE);
    expect(screen.queryByText(`Book ${PAGE_SIZE}`)).not.toBeInTheDocument();
  });

  it('shows the pager and pages forward, requesting the next offset', async () => {
    const user = userEvent.setup();
    getUserBooks
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1))
      .mockResolvedValueOnce(makeBooks(5, PAGE_SIZE));

    render(<Dashboard />);
    await screen.findByText('Book 0');

    const next = screen.getByRole('button', { name: /next page/i });
    await user.click(next);

    await waitFor(() =>
      expect(getUserBooks).toHaveBeenLastCalledWith({ skip: PAGE_SIZE, limit: PAGE_SIZE + 1 })
    );
    expect(await screen.findByText(`Book ${PAGE_SIZE}`)).toBeInTheDocument();
    expect(screen.getByText(/page 2/i)).toBeInTheDocument();
  });

  it('disables Previous on the first page and Next on the last', async () => {
    const user = userEvent.setup();
    getUserBooks
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1))
      .mockResolvedValueOnce(makeBooks(5, PAGE_SIZE));

    render(<Dashboard />);
    await screen.findByText('Book 0');

    // aria-disabled, not disabled — a real `disabled` on the just-clicked button
    // drops keyboard focus to <body> on every page change.
    expect(screen.getByRole('button', { name: /previous page/i })).toHaveAttribute(
      'aria-disabled',
      'true'
    );
    expect(screen.getByRole('button', { name: /next page/i })).toHaveAttribute(
      'aria-disabled',
      'false'
    );

    await user.click(screen.getByRole('button', { name: /next page/i }));
    await screen.findByText(`Book ${PAGE_SIZE}`);

    expect(screen.getByRole('button', { name: /previous page/i })).toHaveAttribute(
      'aria-disabled',
      'false'
    );
    expect(screen.getByRole('button', { name: /next page/i })).toHaveAttribute(
      'aria-disabled',
      'true'
    );
  });

  it('ignores a click on an aria-disabled pager button', async () => {
    const user = userEvent.setup();
    getUserBooks.mockResolvedValue(makeBooks(PAGE_SIZE + 1));

    render(<Dashboard />);
    await screen.findByText('Book 0');

    await user.click(screen.getByRole('button', { name: /previous page/i }));

    expect(getUserBooks).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/page 1/i)).toBeInTheDocument();
  });

  it('keeps the pager focusable across a page change so focus is never lost', async () => {
    const user = userEvent.setup();
    getUserBooks
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1))
      .mockResolvedValueOnce(makeBooks(5, PAGE_SIZE));

    render(<Dashboard />);
    await screen.findByText('Book 0');

    const next = screen.getByRole('button', { name: /next page/i });
    next.focus();
    await user.click(next);
    await screen.findByText(`Book ${PAGE_SIZE}`);

    expect(document.activeElement).toBe(screen.getByRole('button', { name: /next page/i }));
    expect(document.body).not.toBe(document.activeElement);
  });

  it('steps back a page when deleting the last book on a later page empties it', async () => {
    const user = userEvent.setup();
    getUserBooks
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1)) // page 1, more exist
      .mockResolvedValueOnce(makeBooks(1, PAGE_SIZE)) // page 2, single book
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE)); // stepped back to page 1

    render(<Dashboard />);
    await screen.findByText('Book 0');

    await user.click(screen.getByRole('button', { name: /next page/i }));
    await screen.findByText(`Book ${PAGE_SIZE}`);

    await user.click(screen.getByText(`Delete Book ${PAGE_SIZE}`));

    await waitFor(() =>
      expect(getUserBooks).toHaveBeenLastCalledWith({ skip: 0, limit: PAGE_SIZE + 1 })
    );
    expect(await screen.findByText('Book 0')).toBeInTheDocument();
  });

  // ----------------------------------------------------------------------- #
  // #612: an empty list after a failed refetch is not an empty library
  // ----------------------------------------------------------------------- #

  it('does not show the onboarding empty state when the step-back refetch fails', async () => {
    // The #612 sequence: page 2 holds one book, deleting it splices the list
    // empty and steps back to page 1, and page 1's refetch then fails (a 429 is
    // the realistic case). `projects` is empty and `page` is 0, which used to
    // render EmptyBookState — telling a user with a full library that they have
    // never created a book.
    const user = userEvent.setup();
    getUserBooks
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1)) // page 1, more exist
      .mockResolvedValueOnce(makeBooks(1, PAGE_SIZE)) // page 2, single book
      .mockRejectedValueOnce(new Error('Request failed: 429')); // step-back fails

    render(<Dashboard />);
    await screen.findByText('Book 0');
    await user.click(screen.getByRole('button', { name: /next page/i }));
    await screen.findByText(`Book ${PAGE_SIZE}`);

    await user.click(screen.getByText(`Delete Book ${PAGE_SIZE}`));

    // The retry affordance, not the onboarding state.
    expect(await screen.findByRole('button', { name: /try again/i })).toBeInTheDocument();
    expect(screen.queryByTestId('empty-book-state')).not.toBeInTheDocument();
  });

  it('recovers in place when the retry succeeds, without a reload', async () => {
    // AC2: the user gets an in-place retry. Before #612 the list only came back
    // on a window refocus or a full reload.
    const user = userEvent.setup();
    getUserBooks
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1))
      .mockResolvedValueOnce(makeBooks(1, PAGE_SIZE))
      .mockRejectedValueOnce(new Error('Request failed: 429'))
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE)); // the retry

    render(<Dashboard />);
    await screen.findByText('Book 0');
    await user.click(screen.getByRole('button', { name: /next page/i }));
    await screen.findByText(`Book ${PAGE_SIZE}`);
    await user.click(screen.getByText(`Delete Book ${PAGE_SIZE}`));

    await user.click(await screen.findByRole('button', { name: /try again/i }));

    expect(await screen.findByText('Book 0')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /try again/i })).not.toBeInTheDocument();
  });

  it('clears the pending flag on recovery, so a later real empty library is not mistaken for a failure', async () => {
    // Mutation M3 found this uncovered: with `setReloadPending(false)` deleted the
    // suite still passed, because after a successful retry `projects` is non-empty
    // and the render never consults the flag. It matters on the NEXT empty render
    // — a stale flag shows "Could not load your books" to someone who has genuinely
    // deleted them all.
    const user = userEvent.setup();
    getUserBooks
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1)) // page 1
      .mockResolvedValueOnce(makeBooks(1, PAGE_SIZE)) // page 2
      .mockRejectedValueOnce(new Error('Request failed: 429')) // step-back fails
      .mockResolvedValueOnce(makeBooks(1)) // retry succeeds, one book left
      .mockResolvedValueOnce([]); // that last book is deleted -> truly empty

    render(<Dashboard />);
    await screen.findByText('Book 0');
    await user.click(screen.getByRole('button', { name: /next page/i }));
    await screen.findByText(`Book ${PAGE_SIZE}`);
    await user.click(screen.getByText(`Delete Book ${PAGE_SIZE}`));
    await user.click(await screen.findByRole('button', { name: /try again/i }));
    await screen.findByText('Book 0');

    // Now empty the library for real.
    await user.click(screen.getByText('Delete Book 0'));

    expect(await screen.findByTestId('empty-book-state')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /try again/i })).not.toBeInTheDocument();
  });

  it('still shows the onboarding empty state for a genuinely empty library', () => {
    // The counterpart the fix must not break: a real empty library on page 0
    // with no failure in play still gets the onboarding state, not a retry.
    getUserBooks.mockResolvedValueOnce([]);
    render(<Dashboard />);
    return screen.findByTestId('empty-book-state');
  });

  it('keeps the pager mounted while the next page is still in flight', async () => {
    const user = userEvent.setup();
    let releasePageTwo: (books: unknown[]) => void = () => {};
    getUserBooks
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1))
      .mockReturnValueOnce(new Promise(resolve => { releasePageTwo = resolve; }));

    render(<Dashboard />);
    await screen.findByText('Book 0');

    await user.click(screen.getByRole('button', { name: /next page/i }));

    // The full-page loading skeleton must not swallow the pager mid-transition.
    expect(screen.getByRole('navigation', { name: /pagination/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /next page/i })).toHaveAttribute(
      'aria-disabled',
      'true'
    );

    releasePageTwo(makeBooks(5, PAGE_SIZE));
    expect(await screen.findByText(`Book ${PAGE_SIZE}`)).toBeInTheDocument();
  });

  it('refetches after a delete when more pages exist, to backfill the shifted-up row', async () => {
    const user = userEvent.setup();
    getUserBooks
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1))
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE, 1));

    render(<Dashboard />);
    await screen.findByText('Book 0');

    await user.click(screen.getByText('Delete Book 0'));

    await waitFor(() => expect(getUserBooks).toHaveBeenCalledTimes(2));
    expect(getUserBooks).toHaveBeenLastCalledWith({ skip: 0, limit: PAGE_SIZE + 1 });
    // Book 24 was on page 2 before the delete; the refetch pulls it onto page 1.
    expect(await screen.findByText(`Book ${PAGE_SIZE}`)).toBeInTheDocument();
  });

  it('does not refetch after a delete on a single-page library', async () => {
    const user = userEvent.setup();
    getUserBooks.mockResolvedValue(makeBooks(3));

    render(<Dashboard />);
    await screen.findByText('Book 0');

    await user.click(screen.getByText('Delete Book 0'));

    await waitFor(() => expect(screen.queryByText('Book 0')).not.toBeInTheDocument());
    expect(getUserBooks).toHaveBeenCalledTimes(1);
  });

  it('does not show the onboarding empty state on an empty later page', async () => {
    const user = userEvent.setup();
    getUserBooks
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1))
      .mockResolvedValueOnce([]);

    render(<Dashboard />);
    await screen.findByText('Book 0');

    await user.click(screen.getByRole('button', { name: /next page/i }));

    await waitFor(() => expect(screen.getByText(/page 2/i)).toBeInTheDocument());
    expect(screen.queryByTestId('empty-book-state')).not.toBeInTheDocument();
  });

  it('ignores a stale response that resolves after a newer fetch', async () => {
    // The pager buttons guard themselves while loading, but the per-card delete
    // buttons do not — two deletes in quick succession put two refetches in flight.
    const user = userEvent.setup();
    let releaseStale: (books: unknown[]) => void = () => {};
    getUserBooks
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1)) // initial page, hasMore
      .mockReturnValueOnce(new Promise(resolve => { releaseStale = resolve; })) // slow
      .mockResolvedValueOnce(makeBooks(3, 200)); // second delete's refetch, lands first

    render(<Dashboard />);
    await screen.findByText('Book 0');

    await user.click(screen.getByText('Delete Book 0'));
    await user.click(screen.getByText('Delete Book 1'));

    expect(await screen.findByText('Book 200')).toBeInTheDocument();

    // The first delete's refetch lands late carrying a pre-second-delete snapshot.
    // Flush inside act so the stale update actually gets its chance to apply —
    // asserting straight after the release passes vacuously.
    await act(async () => {
      releaseStale(makeBooks(3, 300));
      await Promise.resolve();
    });

    expect(screen.queryByText('Book 300')).not.toBeInTheDocument();
    expect(screen.getByText('Book 200')).toBeInTheDocument();
  });

  it('a stale response does not clear the loading state of the newer fetch', async () => {
    const user = userEvent.setup();
    let releaseStale: (books: unknown[]) => void = () => {};
    getUserBooks
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1))
      .mockReturnValueOnce(new Promise(resolve => { releaseStale = resolve; })) // stale
      .mockReturnValueOnce(new Promise(() => {})); // newer, still in flight

    render(<Dashboard />);
    await screen.findByText('Book 0');

    await user.click(screen.getByText('Delete Book 0'));
    await user.click(screen.getByText('Delete Book 1'));

    await act(async () => {
      releaseStale(makeBooks(3, 300));
      await Promise.resolve();
    });

    // The newer fetch is still pending, so the pager must stay inert.
    expect(screen.getByRole('button', { name: /next page/i })).toHaveAttribute(
      'aria-disabled',
      'true'
    );
  });

  it('decides the post-delete step-back from current state, not the click-time closure', async () => {
    const user = userEvent.setup();
    let resolveFirst: (v: unknown) => void = () => {};
    let resolveSecond: (v: unknown) => void = () => {};
    (bookClient.deleteBook as jest.Mock)
      .mockReturnValueOnce(new Promise(resolve => { resolveFirst = resolve; }))
      .mockReturnValueOnce(new Promise(resolve => { resolveSecond = resolve; }));

    getUserBooks
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1)) // page 1
      .mockResolvedValueOnce(makeBooks(2, PAGE_SIZE)) // page 2: exactly 2 books, no more
      .mockResolvedValueOnce(makeBooks(1, PAGE_SIZE + 1)) // first delete's refetch of page 2
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE)); // back on page 1

    render(<Dashboard />);
    await screen.findByText('Book 0');
    await user.click(screen.getByRole('button', { name: /next page/i }));
    await screen.findByText(`Book ${PAGE_SIZE}`);

    // Both deletes are clicked while two books are on screen, so both closures
    // captured length === 2. Only the second one is true by the time it resolves.
    await user.click(screen.getByText(`Delete Book ${PAGE_SIZE}`));
    await user.click(screen.getByText(`Delete Book ${PAGE_SIZE + 1}`));

    await act(async () => { resolveFirst({ success: true }); await Promise.resolve(); });
    await act(async () => { resolveSecond({ success: true }); await Promise.resolve(); });

    // Page 2 is now empty, so the second delete must step back to page 1.
    await waitFor(() =>
      expect(getUserBooks).toHaveBeenLastCalledWith({ skip: 0, limit: PAGE_SIZE + 1 })
    );
    expect(await screen.findByText('Book 0')).toBeInTheDocument();
  });

  it('steps back when two deletes empty a page within the same microtask batch', async () => {
    // No act() flush between the two resolutions, so no passive effect runs between
    // them — both continuations read the ref in the same batch. If the ref were only
    // synced from useEffect, the second delete would still see two books and refetch
    // the page it just emptied.
    const user = userEvent.setup();
    let resolveFirst: (v: unknown) => void = () => {};
    let resolveSecond: (v: unknown) => void = () => {};
    (bookClient.deleteBook as jest.Mock)
      .mockReturnValueOnce(new Promise(resolve => { resolveFirst = resolve; }))
      .mockReturnValueOnce(new Promise(resolve => { resolveSecond = resolve; }));

    getUserBooks
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1)) // page 1
      .mockResolvedValueOnce(makeBooks(2, PAGE_SIZE)) // page 2, exactly 2 books
      .mockResolvedValue(makeBooks(PAGE_SIZE)); // whatever is fetched next

    render(<Dashboard />);
    await screen.findByText('Book 0');
    await user.click(screen.getByRole('button', { name: /next page/i }));
    await screen.findByText(`Book ${PAGE_SIZE}`);

    await user.click(screen.getByText(`Delete Book ${PAGE_SIZE}`));
    await user.click(screen.getByText(`Delete Book ${PAGE_SIZE + 1}`));

    await act(async () => {
      resolveFirst({ success: true });
      resolveSecond({ success: true });
      await Promise.resolve();
      await Promise.resolve();
    });

    await waitFor(() =>
      expect(getUserBooks).toHaveBeenLastCalledWith({ skip: 0, limit: PAGE_SIZE + 1 })
    );
  });

  it('treats a 404 as an empty library on every load, not just the first', async () => {
    getUserBooks
      .mockResolvedValueOnce(makeBooks(3))
      .mockRejectedValue(new Error('Failed to fetch books: 404'));

    const { rerender } = render(<Dashboard />);
    await screen.findByText('Book 0');

    // A later refetch 404s — an empty library, not a failed page. It must not toast.
    (useSession as jest.Mock).mockReturnValue({
      data: { user: { id: 'user-123' }, session: { id: 'session-456' } },
      isPending: false,
      error: null,
    });
    rerender(<Dashboard />);

    expect(await screen.findByTestId('empty-book-state')).toBeInTheDocument();
    expect(toast.error).not.toHaveBeenCalled();
  });

  it('never rolls forward when the refetch after a step-back fails', async () => {
    const user = userEvent.setup();
    getUserBooks
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1)) // page 1
      .mockResolvedValueOnce(makeBooks(1, PAGE_SIZE)) // page 2, single book
      .mockRejectedValueOnce(new Error('Failed to fetch books: 429')) // step-back fails
      .mockResolvedValue(makeBooks(PAGE_SIZE + 1)); // any later fetch

    render(<Dashboard />);
    await screen.findByText('Book 0');
    await user.click(screen.getByRole('button', { name: /next page/i }));
    await screen.findByText(`Book ${PAGE_SIZE}`);

    await user.click(screen.getByText(`Delete Book ${PAGE_SIZE}`));

    // loadedPageRef still points at page 2, which the step-back just evacuated.
    // Rolling back to it would resurrect an emptied page — and would cost a fourth
    // fetch, which is what this counts. A bare `not.toHaveBeenLastCalledWith` would
    // pass before that fetch ever happened.
    await waitFor(() => expect(toast.error).toHaveBeenCalled());
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(getUserBooks).toHaveBeenCalledTimes(3);
    expect(getUserBooks).toHaveBeenLastCalledWith({ skip: 0, limit: PAGE_SIZE + 1 });
  });

  it('clamps back to the first page when a later page 404s', async () => {
    const user = userEvent.setup();
    getUserBooks
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1)) // page 1
      .mockRejectedValueOnce(new Error('Failed to fetch books: 404')) // page 2 is gone
      .mockResolvedValue([]); // the clamped page-1 refetch

    render(<Dashboard />);
    await screen.findByText('Book 0');

    await user.click(screen.getByRole('button', { name: /next page/i }));

    // Clamped to page 0, so this is the onboarding empty state, not "No books on
    // this page." stranded behind a pager.
    expect(await screen.findByTestId('empty-book-state')).toBeInTheDocument();
    expect(screen.queryByText(/no books on this page/i)).not.toBeInTheDocument();
  });

  it('keeps page and content in sync when a Previous navigation fails', async () => {
    const user = userEvent.setup();
    getUserBooks
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1)) // page 1
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1, PAGE_SIZE)) // page 2
      .mockRejectedValueOnce(new Error('Failed to fetch books: 429')) // back to page 1 fails
      .mockResolvedValue(makeBooks(PAGE_SIZE + 1, PAGE_SIZE));

    render(<Dashboard />);
    await screen.findByText('Book 0');
    await user.click(screen.getByRole('button', { name: /next page/i }));
    await screen.findByText(`Book ${PAGE_SIZE}`);

    await user.click(screen.getByRole('button', { name: /previous page/i }));
    await waitFor(() => expect(toast.error).toHaveBeenCalled());

    // Page 2's books are still on screen, so the indicator must still say Page 2.
    // A backward-only clamp would leave it reading "Page 1" over page-2 content,
    // with Previous disabled while later-page books are displayed.
    expect(screen.getByText(`Book ${PAGE_SIZE}`)).toBeInTheDocument();
    expect(screen.getByText(/page 2/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /previous page/i })).toHaveAttribute(
      'aria-disabled',
      'false'
    );
  });

  it('hides the pager when a 404 empties the list on page 1', async () => {
    getUserBooks
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1)) // page 1, pager shown
      .mockRejectedValue(new Error('Failed to fetch books: 404'));

    const { rerender } = render(<Dashboard />);
    await screen.findByText('Book 0');
    expect(screen.getByRole('navigation', { name: /pagination/i })).toBeInTheDocument();

    (useSession as jest.Mock).mockReturnValue({
      data: { user: { id: 'user-123' }, session: { id: 'session-789' } },
      isPending: false,
      error: null,
    });
    rerender(<Dashboard />);

    // hasMore must be cleared too, or the pager sits enabled behind the onboarding
    // empty state and Next fires another doomed fetch.
    expect(await screen.findByTestId('empty-book-state')).toBeInTheDocument();
    expect(screen.queryByRole('navigation', { name: /pagination/i })).not.toBeInTheDocument();
  });

  it('ignores a Previous click while a page fetch is still in flight', async () => {
    const user = userEvent.setup();
    getUserBooks
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1)) // page 1
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1, PAGE_SIZE)) // page 2
      .mockReturnValueOnce(new Promise(() => {})); // page 3, never settles

    render(<Dashboard />);
    await screen.findByText('Book 0');
    await user.click(screen.getByRole('button', { name: /next page/i }));
    await screen.findByText(`Book ${PAGE_SIZE}`);
    await user.click(screen.getByRole('button', { name: /next page/i })); // page 3, pending

    await user.click(screen.getByRole('button', { name: /previous page/i }));

    // Still three fetches: the guarded Previous click must not queue a fourth.
    expect(getUserBooks).toHaveBeenCalledTimes(3);
  });

  it('keeps the last good page on screen when a page change fails', async () => {
    const user = userEvent.setup();
    getUserBooks
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1))
      .mockRejectedValueOnce(new Error('Failed to fetch books: 429'))
      .mockResolvedValueOnce(makeBooks(PAGE_SIZE + 1));

    render(<Dashboard />);
    await screen.findByText('Book 0');

    await user.click(screen.getByRole('button', { name: /next page/i }));

    // Not the full-screen error branch — the grid and pager survive, rolled back
    // to the page that actually loaded.
    await waitFor(() => expect(screen.getByText(/page 1/i)).toBeInTheDocument());
    expect(screen.getByText('Book 0')).toBeInTheDocument();
    expect(screen.queryByText(/failed to load your books/i)).not.toBeInTheDocument();
    expect(toast.error).toHaveBeenCalled();
  });

  it('still shows the full-screen error when the very first load fails', async () => {
    // .env.test sets NEXT_PUBLIC_BYPASS_AUTH=true, which coerces any first-load
    // failure into an empty library. Turn it off so the real error path is reachable.
    const bypass = process.env.NEXT_PUBLIC_BYPASS_AUTH;
    process.env.NEXT_PUBLIC_BYPASS_AUTH = 'false';
    try {
      getUserBooks.mockRejectedValue(new Error('Failed to fetch books: 500'));

      render(<Dashboard />);

      expect(await screen.findByText(/failed to load your books/i)).toBeInTheDocument();
    } finally {
      process.env.NEXT_PUBLIC_BYPASS_AUTH = bypass;
    }
  });

  it('still shows the onboarding empty state for a genuinely empty library', async () => {
    getUserBooks.mockResolvedValue([]);

    render(<Dashboard />);

    expect(await screen.findByTestId('empty-book-state')).toBeInTheDocument();
  });
});
