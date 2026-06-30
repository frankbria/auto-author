/**
 * Tests for page-level skeleton loaders added for issue #52
 * (comprehensive loading indicators & progress tracking).
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { useSession } from '@/lib/auth-client';
import { useRouter } from 'next/navigation';
import Dashboard from '@/app/dashboard/page';
import DashboardLoading from '@/app/dashboard/loading';
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
jest.mock('next/navigation', () => ({ useRouter: jest.fn() }));
jest.mock('@/components/BookCreationWizard', () => ({
  BookCreationWizard: () => null,
}));
jest.mock('@/components/EmptyBookState', () => ({
  EmptyBookState: () => <div>empty</div>,
}));
jest.mock('@/components/BookCard', () => ({
  __esModule: true,
  default: () => <div data-testid="book-card" />,
}));

describe('Dashboard route loading.tsx skeleton (#52)', () => {
  it('renders an accessible skeleton', () => {
    render(<DashboardLoading />);
    const skeleton = screen.getByTestId('dashboard-route-skeleton');
    expect(skeleton).toHaveAttribute('role', 'status');
    expect(skeleton).toHaveAttribute('aria-busy', 'true');
    expect(screen.getByText('Loading your dashboard...')).toBeInTheDocument();
  });
});

describe('Dashboard page skeleton (#52)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue({ push: jest.fn() });
    (useSession as jest.Mock).mockReturnValue({
      data: { user: { id: 'u1', email: 'a@b.c', name: 'A' } },
      isPending: false,
      error: null,
    });
  });

  it('shows the accessible book-grid skeleton while books are loading, then content', async () => {
    let resolveBooks: (v: unknown) => void = () => {};
    (bookClient.getUserBooks as jest.Mock).mockReturnValue(
      new Promise((resolve) => { resolveBooks = resolve; })
    );

    render(<Dashboard />);

    const skeleton = screen.getByTestId('dashboard-skeleton');
    expect(skeleton).toHaveAttribute('role', 'status');
    expect(skeleton).toHaveAttribute('aria-busy', 'true');
    expect(screen.getByText('Loading your books...')).toBeInTheDocument();

    await waitFor(() => {}); // flush
    resolveBooks([{ id: 'b1', title: 'Book' }]);

    await waitFor(() => {
      expect(screen.queryByTestId('dashboard-skeleton')).not.toBeInTheDocument();
    });
  });
});
