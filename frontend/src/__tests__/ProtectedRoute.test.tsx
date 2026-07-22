import { render, screen, waitFor } from '@testing-library/react';
import { useSession } from '@/lib/auth-client';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { useRouter, usePathname } from 'next/navigation';

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  usePathname: jest.fn(),
}));

// Mock better-auth's useSession hook
jest.mock('@/lib/auth-client', () => ({
  useSession: jest.fn(),
  authClient: {
    signIn: { email: jest.fn() },
    signUp: { email: jest.fn() },
    signOut: jest.fn(),
  },
}));

describe('ProtectedRoute Component', () => {
  const mockRouter = {
    push: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    (usePathname as jest.Mock).mockReturnValue('/dashboard');
    // Ensure auth bypass is disabled for these tests
    delete process.env.NEXT_PUBLIC_BYPASS_AUTH;
  });

  test('displays loading state when auth is still loading', async () => {
    // Mock loading state
    (useSession as jest.Mock).mockReturnValue({
      data: null,
      isPending: true,
      error: null,
    });

    render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );
    // Should show a loading spinner
    await waitFor(() => {
      const spinner = document.querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
    });
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  test('redirects to sign-in with a ?redirect deep-link back to the current path (#239)', async () => {
    (usePathname as jest.Mock).mockReturnValue('/dashboard');
    // Mock unauthenticated state
    (useSession as jest.Mock).mockReturnValue({
      data: null,
      isPending: false,
      error: null,
    });

    render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );

    // On a client-side session expiry the user must land back where they were,
    // not at a bare sign-in page (matches the middleware's ?redirect behavior).
    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledWith(
        '/auth/sign-in?redirect=%2Fdashboard'
      );
    });
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  test('encodes the current path (incl. nested/query) into the ?redirect param (#239)', async () => {
    (usePathname as jest.Mock).mockReturnValue('/dashboard/books/abc123');
    (useSession as jest.Mock).mockReturnValue({
      data: null,
      isPending: false,
      error: null,
    });

    render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );

    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledWith(
        '/auth/sign-in?redirect=%2Fdashboard%2Fbooks%2Fabc123'
      );
    });
  });

  test('renders children when user is authenticated', () => {
    // Mock authenticated state
    (useSession as jest.Mock).mockReturnValue({
      data: {
        user: {
          id: 'user_123',
          email: 'test@example.com',
          name: 'Test User',
        },
        session: {
          token: 'test-token',
          id: 'session-123',
        },
      },
      isPending: false,
      error: null,
    });

    render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );

    // Should render protected content
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  test.skip('handles auth state changes correctly', async () => {
    // First render with loading state
    (useSession as jest.Mock).mockReturnValue({
      data: null,
      isPending: true,
      error: null,
    });

    const { rerender } = render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );

    // Should show loading state
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();

    // Update to authenticated state
    (useSession as jest.Mock).mockReturnValue({
      data: {
        user: {
          id: 'user_123',
          email: 'test@example.com',
          name: 'Test User',
        },
        session: {
          token: 'test-token',
          id: 'session-123',
        },
      },
      isPending: false,
      error: null,
    });

    // Rerender component
    rerender(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );

    // Should now show protected content
    await waitFor(() => {
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
    });

    // Update to unauthenticated state
    (useSession as jest.Mock).mockReturnValue({
      data: null,
      isPending: false,
      error: null,
    });

    // Rerender component
    rerender(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );

    // Should redirect to sign-in with the ?redirect deep-link (#239)
    expect(mockRouter.push).toHaveBeenCalledWith('/auth/sign-in?redirect=%2Fdashboard');
  });
});
