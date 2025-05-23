import { render, screen, fireEvent } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import HomePage from '@/app/page';
import { useUser } from '@clerk/nextjs';

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

// Mock Clerk components
jest.mock('@clerk/nextjs', () => {
  // Create a mockUseUser function that can be controlled by tests
  const mockUseUser = jest.fn().mockReturnValue({
    isLoaded: true,
    isSignedIn: false,
  });

  return {
    SignUpButton: jest.fn().mockImplementation(({ mode, fallbackRedirectUrl, children }) => (
      <div 
        data-testid="clerk-signup-button" 
        data-mode={mode} 
        data-redirect={fallbackRedirectUrl}
        onClick={() => {}}
      >
        {children}
      </div>
    )),
    SignInButton: jest.fn().mockImplementation(({ mode, fallbackRedirectUrl, children }) => (
      <div 
        data-testid="clerk-signin-button" 
        data-mode={mode} 
        data-redirect={fallbackRedirectUrl}
        onClick={() => {}}
      >
        {children}
      </div>
    )),
    SignOutButton: jest.fn().mockImplementation(({ children }) => (
      <div data-testid="clerk-signout-button">
        {children}
      </div>
    )),
    // Fix SignedIn to only render children when isSignedIn is true
    SignedIn: jest.fn().mockImplementation(({ children }) => {
      const { isSignedIn } = mockUseUser();
      return isSignedIn ? <div data-testid="signed-in">{children}</div> : null;
    }),
    // Fix SignedOut to only render children when isSignedIn is false
    SignedOut: jest.fn().mockImplementation(({ children }) => {
      const { isSignedIn } = mockUseUser();
      return !isSignedIn ? <div data-testid="signed-out">{children}</div> : null;
    }),
    useUser: mockUseUser,
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

  test('renders SignUpButton component on the home page', () => {
    render(<HomePage />);
    
    // Check that the SignUpButton is rendered
    const signUpButton = screen.getByTestId('clerk-signup-button');
    expect(signUpButton).toBeInTheDocument();
    
    // Check that the button has the correct text
    expect(signUpButton.textContent).toContain('Sign Up');
  });
  
  test('configures SignUpButton with modal mode and dashboard redirect', () => {
    render(<HomePage />);
    
    // Check the button configuration
    const signUpButton = screen.getByTestId('clerk-signup-button');
    expect(signUpButton).toHaveAttribute('data-mode', 'modal');
    expect(signUpButton).toHaveAttribute('data-redirect', '/dashboard');
  });
  
  test('renders sign-up and sign-in buttons when signed out', () => {
    render(<HomePage />);
    
    // Check that the signed out section is visible
    expect(screen.getByTestId('signed-out')).toBeInTheDocument();
    
    // Verify both buttons are available
    expect(screen.getByTestId('clerk-signup-button')).toBeInTheDocument();
    expect(screen.getByTestId('clerk-signin-button')).toBeInTheDocument();
  });

  test('does not show authenticated content when not logged in', () => {
    render(<HomePage />);
    
    // The SignedIn content should not be visible
    expect(screen.queryByText('Go to Dashboard')).not.toBeInTheDocument();
  });
  
  test('shows loading state while authentication is being determined', () => {
    // Mock the useUser hook to simulate loading state
    (useUser as jest.Mock).mockReturnValueOnce({
      isLoaded: false,
      isSignedIn: false,
    });
    
    render(<HomePage />);
    
    // Loading spinner should be visible
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });
  test('shows authenticated content when signed in', () => {
    // Mock the useUser hook to simulate signed in state
    // We need to replace the existing mock implementation entirely
    (useUser as jest.Mock).mockImplementation(() => ({
      isLoaded: true,
      isSignedIn: true,
    }));
    
    render(<HomePage />);
    
    // Debug the output to see what's rendered
    // screen.debug();
    
    // The signed-in section should be visible
    expect(screen.getByTestId('signed-in')).toBeInTheDocument();
    
    // Dashboard button should be available
    expect(screen.getByText('Go to Dashboard')).toBeInTheDocument();
    
    // Welcome back message should be visible with exact text match
    expect(screen.getByText(/Welcome Back/)).toBeInTheDocument();
  });
});
