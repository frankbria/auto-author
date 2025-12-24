import { renderHook, act } from '@testing-library/react';
import { useSession } from '@/lib/auth-client';
import { useAuthFetch } from '@/hooks/useAuthFetch';

// Mock fetch
global.fetch = jest.fn();

// Mock better-auth's useSession hook
jest.mock('@/lib/auth-client', () => ({
  useSession: jest.fn(),
  authClient: {
    signIn: { email: jest.fn() },
    signUp: { email: jest.fn() },
    signOut: jest.fn(),
  },
}));

describe('useAuthFetch Hook', () => {
  const mockFetchResponse = { data: 'test data' };
  const mockUrl = '/test'; // This path will be appended to baseUrl in the hook

  beforeEach(() => {
    jest.clearAllMocks();

    // Mock the useSession hook to return a session with user
    (useSession as jest.Mock).mockReturnValue({
      data: {
        user: {
          id: 'test-user-123',
          email: 'test@example.com',
          name: 'Test User',
        },
        session: {
          id: 'session-123',
        },
      },
      isPending: false,
      error: null,
    });

    // Mock fetch to return a successful response
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue(mockFetchResponse),
      headers: new Headers({
        'content-type': 'application/json',
      }),
    });
  });

  test('includes credentials: include for cookie-based authentication', async () => {
    const { result } = renderHook(() => useAuthFetch());

    // Call the authFetch method
    let responseData;
    await act(async () => {
      responseData = await result.current.authFetch(mockUrl);
    });

    // Verify that fetch was called with credentials: 'include' for cookie-based auth
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/test', // The hook prepends '/api' to the path
      expect.objectContaining({
        credentials: 'include', // For cookie-based authentication
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
        }),
      })
    );

    // Verify the response data
    expect(responseData).toEqual(mockFetchResponse);
  });

  test('uses credentials: omit when skipAuth is true', async () => {
    const { result } = renderHook(() => useAuthFetch());

    await act(async () => {
      await result.current.authFetch(mockUrl, { skipAuth: true });
    });

    // Verify that fetch was called with credentials: 'omit' when skipAuth is true
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/test',
      expect.objectContaining({
        credentials: 'omit',
      })
    );
  });

  test('persists authentication across multiple requests', async () => {
    const { result } = renderHook(() => useAuthFetch());

    // First request
    await act(async () => {
      await result.current.authFetch('/api/first');
    });

    // Second request with different URL
    await act(async () => {
      await result.current.authFetch('/api/second');
    });

    // Both requests should use credentials: 'include' for cookie auth
    const calls = (global.fetch as jest.Mock).mock.calls;
    expect(calls.length).toBe(2);

    // Both calls should have credentials: 'include'
    expect(calls[0][1].credentials).toBe('include');
    expect(calls[1][1].credentials).toBe('include');

    // The session should be checked (to determine isAuthenticated status)
    expect(useSession).toHaveBeenCalled();
  });

  test('handles 401 unauthorized errors and allows retry', async () => {
    // Note: This tests error handling for 401 responses.
    // In cookie-based auth, session refresh is handled automatically by better-auth,
    // but 401 errors are still surfaced so the application can handle them
    // (e.g., by redirecting to login page).

    // Mock fetch to first return unauthorized, then success on retry
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: jest.fn().mockResolvedValue({ detail: 'Session expired' }),
        headers: new Headers({
          'content-type': 'application/json',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue(mockFetchResponse),
        headers: new Headers({
          'content-type': 'application/json',
        }),
      });

    const { result } = renderHook(() => useAuthFetch());

    await act(async () => {
      try {
        await result.current.authFetch(mockUrl);
      } catch (error) {
        // Expected to throw on the first attempt with 401 error
        const err = error as Error;
        expect(err.message).toContain('Session expired');

        // Manual retry after handling the 401 (e.g., after session refresh)
        const secondResponse = await result.current.authFetch(mockUrl);
        expect(secondResponse).toEqual(mockFetchResponse);
      }
    });
  });

  test('returns isAuthenticated based on session state', async () => {
    // With valid session
    const { result: resultWithSession } = renderHook(() => useAuthFetch());
    expect(resultWithSession.current.isAuthenticated).toBe(true);

    // Without session
    (useSession as jest.Mock).mockReturnValue({
      data: null,
      isPending: false,
      error: null,
    });

    const { result: resultWithoutSession } = renderHook(() => useAuthFetch());
    expect(resultWithoutSession.current.isAuthenticated).toBe(false);
  });

  test('handles non-JSON responses', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      text: jest.fn().mockResolvedValue('plain text response'),
      headers: new Headers({
        'content-type': 'text/plain',
      }),
    });

    const { result } = renderHook(() => useAuthFetch());

    let responseData;
    await act(async () => {
      responseData = await result.current.authFetch(mockUrl);
    });

    expect(responseData).toBe('plain text response');
  });

  test('sets error state on failure', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 500,
      json: jest.fn().mockResolvedValue({ detail: 'Internal server error' }),
      headers: new Headers({
        'content-type': 'application/json',
      }),
    });

    const { result } = renderHook(() => useAuthFetch());

    await act(async () => {
      try {
        await result.current.authFetch(mockUrl);
      } catch (error) {
        // Expected to throw
      }
    });

    expect(result.current.error).toBeTruthy();
    expect(result.current.error?.message).toContain('Internal server error');
  });
});
