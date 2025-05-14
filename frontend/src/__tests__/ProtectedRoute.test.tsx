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

describe('ProtectedRoute Component', () => {
  const mockRouter = {
    push: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
  });

  test('displays loading state when auth is still loading', () => {
    // Mock auth loading state
    (useAuth as jest.Mock).mockReturnValue({
      isLoaded: false,
      userId: null,
      isSignedIn: false,
    });

    render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );    // Should show a loading spinner
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  test('redirects to sign-in page when user is not authenticated', () => {
    // Mock unauthenticated state
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

    // Should redirect to sign-in
    expect(mockRouter.push).toHaveBeenCalledWith('/sign-in');
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  test('renders children when user is authenticated', () => {
    // Mock authenticated state
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
  });

  test('handles auth state changes correctly', async () => {
    // First render with loading state
    (useAuth as jest.Mock).mockReturnValue({
      isLoaded: false,
      userId: null,
      isSignedIn: false,
    });

    const { rerender } = render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );

    // Should show loading state
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();

    // Update to authenticated state
    (useAuth as jest.Mock).mockReturnValue({
      isLoaded: true,
      userId: 'user_123',
      isSignedIn: true,
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
    (useAuth as jest.Mock).mockReturnValue({
      isLoaded: true,
      userId: null,
      isSignedIn: false,
    });

    // Rerender component
    rerender(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );

    // Should redirect to sign-in
    expect(mockRouter.push).toHaveBeenCalledWith('/sign-in');
  });
});
