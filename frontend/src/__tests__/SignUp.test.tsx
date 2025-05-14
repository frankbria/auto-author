import { render, screen } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import SignUpPage from '@/app/sign-up/[[...rest]]/page';
import { SignUp } from '@clerk/nextjs';
import { dark } from '@clerk/themes';

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

// Mock Clerk components and themes
jest.mock('@clerk/themes', () => ({
  dark: 'mock-dark-theme'
}));

jest.mock('@clerk/nextjs', () => ({
  SignUp: jest.fn().mockImplementation(({ children, ...props }) => (
    <div data-testid="clerk-signup" {...props}>
      {children || 'SignUp Component'}
    </div>
  )),
}));

describe('SignUp Component Integration', () => {
  const mockRouter = {
    push: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
  });
  test('renders Clerk SignUp component', () => {
    render(<SignUpPage />);
    
    // Check that the Clerk component is rendered
    expect(screen.getByTestId('clerk-signup')).toBeInTheDocument();
  });
  
  test('passes correct routing props to Clerk component', () => {
    render(<SignUpPage />);
    
    // Check that the SignUp component was called with the correct props
    expect(SignUp).toHaveBeenCalled();
    const callProps = (SignUp as jest.Mock).mock.calls[0][0];
    
    // Verify individual props
    expect(callProps.routing).toBe('path');
    expect(callProps.path).toBe('/sign-up');
    expect(callProps.signInUrl).toBe('/sign-in');
    expect(callProps.redirectUrl).toBe('/dashboard');
    expect(callProps.afterSignUpUrl).toBe('/dashboard');
    expect(callProps.appearance.baseTheme).toBe('mock-dark-theme');
  });
  test('renders with loading state hidden by default', () => {
    render(<SignUpPage />);
    
    // Initially, the loading state should not be visible
    const loadingText = screen.queryByText('Redirecting to dashboard');
    expect(loadingText).not.toBeInTheDocument();
  });

  test('renders with error message hidden by default', () => {
    render(<SignUpPage />);
    
    // Initially, there should be no error message
    const errorContainer = screen.queryByText(/error/i);
    expect(errorContainer).not.toBeInTheDocument();
  });
});
