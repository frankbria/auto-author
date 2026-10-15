import React from 'react';
import { render, screen, act } from '@testing-library/react';
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

// The wizard's only part here: it reports a created book.
jest.mock('@/components/BookCreationWizard', () => ({
  BookCreationWizard: ({ onSuccess }: { onSuccess: (bookId: string) => void }) => (
    <button onClick={() => onSuccess('new-book')}>finish wizard</button>
  ),
}));

jest.mock('@/components/EmptyBookState', () => ({
  EmptyBookState: () => <div data-testid="empty-book-state">No books yet</div>,
}));

describe('Dashboard redirect after creating a book (#855)', () => {
  const push = jest.fn();

  beforeEach(() => {
    push.mockReset();
    (useRouter as jest.Mock).mockReturnValue({ push });
    (useSession as jest.Mock).mockReturnValue({
      data: { user: { id: 'user-123' }, session: { id: 'session-123' } },
      isPending: false,
      error: null,
    });
    (bookClient.getUserBooks as jest.Mock).mockResolvedValue([]);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('opens the new book after the toast has been seen', async () => {
    render(<Dashboard />);
    const finish = await screen.findByText('finish wizard');
    // Fake timers only from here: the page's own load waits on real ones.
    jest.useFakeTimers();
    act(() => finish.click());

    act(() => jest.advanceTimersByTime(1500));

    expect(push).toHaveBeenCalledWith('/dashboard/books/new-book');
  });

  it('does not navigate from a dashboard that has unmounted', async () => {
    const { unmount } = render(<Dashboard />);
    const finish = await screen.findByText('finish wizard');
    // Fake timers only from here: the page's own load waits on real ones.
    jest.useFakeTimers();
    act(() => finish.click());

    unmount();
    jest.advanceTimersByTime(1500);

    expect(push).not.toHaveBeenCalled();
  });
});
