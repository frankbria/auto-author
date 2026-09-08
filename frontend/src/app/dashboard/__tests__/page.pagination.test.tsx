import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useSession } from '@/lib/auth-client';
import { useRouter } from 'next/navigation';
import Dashboard from '@/app/dashboard/page';
import bookClient from '@/lib/api/bookClient';

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

    expect(screen.getByRole('button', { name: /previous page/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /next page/i })).toBeEnabled();

    await user.click(screen.getByRole('button', { name: /next page/i }));
    await screen.findByText(`Book ${PAGE_SIZE}`);

    expect(screen.getByRole('button', { name: /previous page/i })).toBeEnabled();
    expect(screen.getByRole('button', { name: /next page/i })).toBeDisabled();
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

  it('still shows the onboarding empty state for a genuinely empty library', async () => {
    getUserBooks.mockResolvedValue([]);

    render(<Dashboard />);

    expect(await screen.findByTestId('empty-book-state')).toBeInTheDocument();
  });
});
