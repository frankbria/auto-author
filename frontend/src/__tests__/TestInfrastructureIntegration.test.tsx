/**
 * Test Infrastructure Integration Validation
 * Ensures that our new test infrastructure works correctly with existing tests
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Mock Next.js router
const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    pathname: '/',
    query: {},
  }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/',
}));

// Mock Clerk authentication
jest.mock('@clerk/nextjs', () => ({
  useAuth: () => ({
    isLoaded: true,
    isSignedIn: true,
    userId: 'test-user-id',
    getToken: jest.fn().mockResolvedValue('mock-token'),
  }),
  useUser: () => ({
    isLoaded: true,
    user: {
      id: 'test-user-id',
      emailAddresses: [{ emailAddress: 'test@example.com' }],
      firstName: 'Test',
      lastName: 'User',
    },
  }),
  ClerkProvider: ({ children }: { children: React.ReactNode }) => children,
  SignInButton: ({ children }: { children: React.ReactNode }) => children,
  UserButton: () => <div data-testid="user-button">User Button</div>,
}));

// Mock fetch for API calls
global.fetch = jest.fn();

describe('Test Infrastructure Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockClear();
  });

  describe('Testing Framework Compatibility', () => {
    it('should have Jest properly configured', () => {
      expect(typeof describe).toBe('function');
      expect(typeof it).toBe('function');
      expect(typeof expect).toBe('function');
    });

    it('should have React Testing Library configured', () => {
      expect(typeof render).toBe('function');
      expect(typeof screen).toBe('object');
      expect(typeof fireEvent).toBe('object');
      expect(typeof fireEvent.click).toBe('function');
      expect(typeof userEvent.setup).toBe('function');
    });

    it('should have jest-dom matchers available', () => {
      const div = document.createElement('div');
      div.textContent = 'Hello World';
      document.body.appendChild(div); // Need to add to DOM first
      expect(div).toBeInTheDocument();
      expect(div).toHaveTextContent('Hello World');
      document.body.removeChild(div); // Clean up
    });
  });

  describe('Mock Infrastructure', () => {
    it('should have Next.js router mocked correctly', () => {
      const { useRouter } = require('next/navigation');
      const router = useRouter();
      expect(router.push).toBe(mockPush);
      expect(typeof router.pathname).toBe('string');
    });

    it('should have Clerk authentication mocked correctly', () => {
      const { useAuth, useUser } = require('@clerk/nextjs');
      const auth = useAuth();
      const user = useUser();
      
      expect(auth.isLoaded).toBe(true);
      expect(auth.isSignedIn).toBe(true);
      expect(auth.userId).toBe('test-user-id');
      expect(user.isLoaded).toBe(true);
      expect(user.user.id).toBe('test-user-id');
    });

    it('should have fetch mocked correctly', () => {
      expect(global.fetch).toBeDefined();
      expect(jest.isMockFunction(global.fetch)).toBe(true);
    });
  });

  describe('Component Rendering Tests', () => {
    it('should render basic components without errors', () => {
      const TestComponent = () => (
        <div data-testid="test-component">
          <h1>Test Component</h1>
          <button>Click me</button>
        </div>
      );

      render(<TestComponent />);
      
      expect(screen.getByTestId('test-component')).toBeInTheDocument();
      expect(screen.getByText('Test Component')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument();
    });

    it('should handle user interactions correctly', async () => {
      const handleClick = jest.fn();
      const TestComponent = () => (
        <button onClick={handleClick} data-testid="test-button">
          Click me
        </button>
      );

      const user = userEvent.setup();
      render(<TestComponent />);
      
      const button = screen.getByTestId('test-button');
      await user.click(button);
      
      expect(handleClick).toHaveBeenCalledTimes(1);
    });
  });

  describe('Async Testing Capabilities', () => {
    it('should handle async operations correctly', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'Success' }),
      });

      const TestComponent = () => {
        const [data, setData] = React.useState<{ message: string } | null>(null);
        const [loading, setLoading] = React.useState(false);

        const fetchData = async () => {
          setLoading(true);
          try {
            const response = await fetch('/api/test');
            const result = await response.json();
            setData(result);
          } finally {
            setLoading(false);
          }
        };

        return (
          <div>
            <button onClick={fetchData} disabled={loading}>
              {loading ? 'Loading...' : 'Fetch Data'}
            </button>
            {data && <div data-testid="result">{data.message}</div>}
          </div>
        );
      };

      const user = userEvent.setup();
      render(<TestComponent />);
      
      const button = screen.getByRole('button');
      await user.click(button);
      
      await waitFor(() => {
        expect(screen.getByTestId('result')).toHaveTextContent('Success');
      });
      
      expect(global.fetch).toHaveBeenCalledWith('/api/test');
    });
  });

  describe('Error Handling Tests', () => {
    it('should handle component errors gracefully', () => {
      const ErrorComponent = () => {
        throw new Error('Test error');
      };

      const ErrorBoundary = ({ children }: { children: React.ReactNode }) => {
        try {
          return <>{children}</>;
        } catch (error) {
          return <div data-testid="error-boundary">Error caught</div>;
        }
      };

      // Suppress console.error for this test
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      expect(() => {
        render(
          <ErrorBoundary>
            <ErrorComponent />
          </ErrorBoundary>
        );
      }).toThrow('Test error');
      
      consoleSpy.mockRestore();
    });
  });

  describe('Performance Testing Capabilities', () => {
    it('should measure component rendering performance', () => {
      const start = performance.now();
      
      const TestComponent = () => (
        <div>
          {Array.from({ length: 100 }, (_, i) => (
            <div key={i}>Item {i}</div>
          ))}
        </div>
      );

      render(<TestComponent />);
      
      const end = performance.now();
      const renderTime = end - start;
      
      // Expect rendering to complete within reasonable time
      expect(renderTime).toBeLessThan(100); // 100ms threshold
    });
  });

  describe('Accessibility Testing Setup', () => {
    it('should support accessibility testing patterns', () => {
      const TestComponent = () => (
        <div>
          <label htmlFor="test-input">Test Input</label>
          <input id="test-input" type="text" />
          <button aria-label="Submit form">Submit</button>
        </div>
      );

      render(<TestComponent />);
      
      // Test accessibility through roles and labels
      expect(screen.getByLabelText('Test Input')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Submit form' })).toBeInTheDocument();
      expect(screen.getByRole('textbox')).toHaveAccessibleName('Test Input');
    });
  });
});

// Helper function for testing with React Suspense
export const renderWithSuspense = (component: React.ReactElement) => {
  return render(
    <React.Suspense fallback={<div data-testid="loading">Loading...</div>}>
      {component}
    </React.Suspense>
  );
};

// Helper function for testing with error boundaries
export const renderWithErrorBoundary = (component: React.ReactElement) => {
  const ErrorBoundary = ({ children }: { children: React.ReactNode }) => {
    const [hasError, setHasError] = React.useState(false);

    React.useEffect(() => {
      const handleError = () => setHasError(true);
      window.addEventListener('error', handleError);
      return () => window.removeEventListener('error', handleError);
    }, []);

    if (hasError) {
      return <div data-testid="error-boundary">Something went wrong</div>;
    }

    return <>{children}</>;
  };

  return render(<ErrorBoundary>{component}</ErrorBoundary>);
};

// Export test utilities for use in other test files
export const testUtils = {
  renderWithSuspense,
  renderWithErrorBoundary,
  mockAuth: {
    authenticated: () => {
      const { useAuth } = require('@clerk/nextjs');
      useAuth.mockReturnValue({
        isLoaded: true,
        isSignedIn: true,
        userId: 'test-user-id',
        getToken: jest.fn().mockResolvedValue('mock-token'),
      });
    },
    unauthenticated: () => {
      const { useAuth } = require('@clerk/nextjs');
      useAuth.mockReturnValue({
        isLoaded: true,
        isSignedIn: false,
        userId: null,
        getToken: jest.fn().mockResolvedValue(null),
      });
    },
  },
};
