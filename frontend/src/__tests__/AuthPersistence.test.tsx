import { render, screen, waitFor } from '@testing-library/react';
import { useAuth } from '@clerk/nextjs';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { useRouter } from 'next/navigation';

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

// Mock Clerk's useAuth hook
jest.mock('@clerk/nextjs', () => ({
  useAuth: jest.fn(),
}));

describe('Authentication State Persistence', () => {
  const mockRouter = {
    push: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
  });

  test('redirects to sign-in when user is not authenticated', async () => {
    // Mock the useAuth hook to simulate an unauthenticated state
    (useAuth as jest.Mock).mockReturnValue({
      isLoaded: true,
      userId: null,
      isSignedIn: false,
    });

    render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );

    // Expect router.push to be called with the sign-in route
    expect(mockRouter.push).toHaveBeenCalledWith('/sign-in');

    // Should not render protected content
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });
  test('shows loading spinner while auth state is loading', async () => {
    // Mock the useAuth hook to simulate a loading state
    (useAuth as jest.Mock).mockReturnValue({
      isLoaded: false,
      userId: null,
      isSignedIn: false,
    });

    render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );

    // Look for the loading spinner element directly using its class
    const loadingElement = document.querySelector('.animate-spin');
    expect(loadingElement).toBeInTheDocument();
  });

  test('renders protected content when user is authenticated', async () => {
    // Mock the useAuth hook to simulate an authenticated state
    (useAuth as jest.Mock).mockReturnValue({
      isLoaded: true,
      userId: 'user_123',
      isSignedIn: true,
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
    // Mock the useAuth hook to simulate an authenticated state
    const mockAuthState = {
      isLoaded: true,
      userId: 'user_123',
      isSignedIn: true,
      sessionId: 'session_123',
      getToken: jest.fn().mockResolvedValue('mock_token'),
    };
    
    (useAuth as jest.Mock).mockReturnValue(mockAuthState);

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
