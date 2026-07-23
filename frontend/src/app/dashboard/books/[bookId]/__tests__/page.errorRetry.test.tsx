import React, { Suspense } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import BookPage from '../page';
import { useSession } from '@/lib/auth-client';
import bookClient from '@/lib/api/bookClient';

// The book-overview page's error state used to offer a Try Again button wired
// to window.location.reload() — a full page reload instead of an in-place
// refetch (#215). This suite pins the refetch behavior.

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
// next/navigation is mocked globally in jest.setup.ts (useSearchParams →
// empty URLSearchParams, useRouter → push spy) — no local override needed.

const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;

// React's use(params) can't suspend-then-resume on a plain resolved Promise in
// jest; a pre-fulfilled thenable lets it read the value synchronously (#194).
function fulfilledParams<T>(value: T): Promise<T> {
  const p = Promise.resolve(value) as Promise<T> & { status: string; value: T };
  p.status = 'fulfilled';
  p.value = value;
  return p;
}

function renderPage() {
  return render(
    <Suspense fallback={null}>
      <BookPage params={fulfilledParams({ bookId: 'book-1' })} />
    </Suspense>
  );
}

describe('BookPage error → in-place refetch (#215)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useSession as jest.Mock).mockReturnValue({ data: { user: { id: 'u1' } } });
    mockBookClient.getToc.mockResolvedValue({ toc: null } as never);
    mockBookClient.getBookSummary.mockResolvedValue({ summary: '' } as never);
  });

  it('refetches in place when Try Again is clicked — no window.location.reload', async () => {
    const reload = jest.fn();
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...window.location, reload },
    });

    // First load fails → error state; retry succeeds → book renders.
    mockBookClient.getBook
      .mockRejectedValueOnce(new Error('boom'))
      .mockResolvedValueOnce({
        id: 'book-1',
        title: 'My Nonfiction Book',
        description: 'desc',
        progress: 0,
      } as never);

    renderPage();

    const retry = await screen.findByRole('button', { name: /try again/i });
    expect(mockBookClient.getBook).toHaveBeenCalledTimes(1);

    fireEvent.click(retry);

    await waitFor(() =>
      expect(
        screen.getByRole('heading', { level: 1, name: 'My Nonfiction Book' })
      ).toBeInTheDocument()
    );
    expect(mockBookClient.getBook).toHaveBeenCalledTimes(2);
    expect(reload).not.toHaveBeenCalled();
  });
});

// #331: the book title hardcoded `text-gray-100` on the theme-aware background,
// so it was invisible (~1.1:1) in the shipped light theme. Pin that the title
// renders with the theme foreground token.
describe('BookPage — light-theme title token (#331)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useSession as jest.Mock).mockReturnValue({ data: { user: { id: 'u1' } } });
    mockBookClient.getToc.mockResolvedValue({ toc: null } as never);
    mockBookClient.getBookSummary.mockResolvedValue({ summary: '' } as never);
  });

  it('renders the book title with the theme foreground token, not near-white gray', async () => {
    mockBookClient.getBook.mockResolvedValue({
      id: 'book-1',
      title: 'My Nonfiction Book',
      description: 'desc',
      progress: 0,
    } as never);

    renderPage();

    const title = await screen.findByRole('heading', {
      level: 1,
      name: 'My Nonfiction Book',
    });
    expect(title).toHaveClass('text-foreground');
    expect(title.className).not.toMatch(/text-gray-\d/);
  });
});
