import { render, screen } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import HomePage from '@/app/page';
import { useSession } from '@/lib/auth-client';

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

jest.mock('next/link', () => {
  return jest.fn(({ href, children }) => (
    <a href={href} data-testid="next-link">
      {children}
    </a>
  ));
});

// Mock better-auth
jest.mock('@/lib/auth-client', () => {
  // Create a mockUseSession function that can be controlled by tests
  const mockUseSession = jest.fn().mockReturnValue({
    data: null,
    isPending: false,
    error: null,
  });

  return {
    useSession: mockUseSession,
    authClient: {
      signIn: { email: jest.fn() },
      signUp: { email: jest.fn() },
      signOut: jest.fn(),
    },
  };
});

describe('Home Page Sign Up Integration', () => {
  const mockRouter = {
    push: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
  });

  test('renders sign-up section on the home page when not authenticated', () => {
    (useSession as jest.Mock).mockReturnValue({
      data: null,
      isPending: false,
      error: null,
    });

    render(<HomePage />);

    // When not authenticated, should show authentication UI
    // (exact selectors depend on HomePage component structure)
    expect(screen.getByText(/sign up/i) || screen.getByText(/get started/i)).toBeDefined();
  });

  test('shows loading state while authentication is being determined', () => {
    (useSession as jest.Mock).mockReturnValue({
      data: null,
      isPending: true,
      error: null,
    });

    render(<HomePage />);

    // Loading state should be visible
    expect(screen.getByText(/loading|verifying/i) || document.querySelector('.animate-spin')).toBeDefined();
  });

  test('shows authenticated content when signed in', () => {
    (useSession as jest.Mock).mockReturnValue({
      data: {
        user: {
          id: 'test-user-123',
          email: 'test@example.com',
          name: 'Test User',
        },
        session: {
          token: 'mock-jwt-token',
          id: 'session-123',
        },
      },
      isPending: false,
      error: null,
    });

    render(<HomePage />);

    // The dashboard link should be available
    expect(screen.getByText(/go to dashboard|dashboard/i) || screen.getByText(/welcome back/i)).toBeDefined();
  });

  test('does not show authenticated content when not logged in', () => {
    (useSession as jest.Mock).mockReturnValue({
      data: null,
      isPending: false,
      error: null,
    });

    render(<HomePage />);

    // Dashboard content should not be visible when not authenticated
    expect(screen.queryByText(/your books/i)).not.toBeInTheDocument();
  });
});
