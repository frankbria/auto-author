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

describe('Authentication State Persistence', () => {
  const mockRouter = {
    push: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    // Ensure auth bypass is disabled for these tests
    delete process.env.NEXT_PUBLIC_BYPASS_AUTH;
  });

  test('redirects to sign-in when user is not authenticated', async () => {
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

    // Expect router.push to be called with the sign-in route (better-auth uses /auth/sign-in)
    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledWith('/auth/sign-in');
    });

    // Should not render protected content
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  test('shows loading spinner while auth state is loading', async () => {
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

    // Look for the loading spinner element directly using its class
    await waitFor(() => {
      const loadingElement = document.querySelector('.animate-spin');
      expect(loadingElement).toBeInTheDocument();
    });
  });

  test('renders protected content when user is authenticated', async () => {
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
          id: 'session_123',
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

    // Should not redirect
    expect(mockRouter.push).not.toHaveBeenCalled();
  });

  test('preserves auth state across component renders', async () => {
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
          id: 'session_123',
        },
      },
      isPending: false,
      error: null,
    });

    const { rerender } = render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );

    // First render should show the content
    expect(screen.getByText('Protected Content')).toBeInTheDocument();

    // Re-render with the same auth state
    rerender(
      <ProtectedRoute>
        <div>Updated Protected Content</div>
      </ProtectedRoute>
    );

    // Should keep the authenticated state and show the updated content
    expect(screen.getByText('Updated Protected Content')).toBeInTheDocument();
    expect(mockRouter.push).not.toHaveBeenCalled();
  });
});
