import { render, screen, waitFor } from '@testing-library/react';
import { useSession } from '@/lib/auth-client';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { useRouter } from 'next/navigation';

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
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

  test('redirects to sign-in page when user is not authenticated', async () => {
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

    // Should redirect to sign-in (better-auth uses /auth/sign-in)
    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledWith('/auth/sign-in');
    });
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
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

    // Should redirect to sign-in (better-auth uses /auth/sign-in)
    expect(mockRouter.push).toHaveBeenCalledWith('/auth/sign-in');
  });
});
