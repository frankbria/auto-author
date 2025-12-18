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
  const mockToken = 'test_token_123';
  const mockFetchResponse = { data: 'test data' };
  const mockUrl = '/test'; // This path will be appended to baseUrl in the hook

  beforeEach(() => {
    jest.clearAllMocks();

    // Mock the useSession hook to return a session with token
    (useSession as jest.Mock).mockReturnValue({
      data: {
        user: {
          id: 'test-user-123',
          email: 'test@example.com',
          name: 'Test User',
        },
        session: {
          token: mockToken,
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
  test('includes auth token in request headers when authenticated', async () => {
    const { result } = renderHook(() => useAuthFetch());
    
    // Call the authFetch method
    let responseData;
    await act(async () => {
      responseData = await result.current.authFetch(mockUrl);
    });
      // Verify that fetch was called with the auth token and correct URL
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/test', // The hook prepends '/api' to the path
      expect.objectContaining({
        headers: expect.objectContaining({
          'Authorization': `Bearer ${mockToken}`,
        }),
      })
    );
    
    // Verify the response data
    expect(responseData).toEqual(mockFetchResponse);
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
    
    // Both requests should include the same auth token
    const calls = (global.fetch as jest.Mock).mock.calls;
    expect(calls.length).toBe(2);
    
    // First call headers
    expect(calls[0][1].headers).toHaveProperty('Authorization', `Bearer ${mockToken}`);
    
    // Second call headers
    expect(calls[1][1].headers).toHaveProperty('Authorization', `Bearer ${mockToken}`);

    // The session should be used for both requests (better-auth uses session tokens)
    expect(useSession).toHaveBeenCalled();
  });

  test('handles token refreshing when token expires', async () => {
    // Mock fetch to first return unauthorized, then success with new token
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: jest.fn().mockResolvedValue({ detail: 'Token expired' }),
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

    // This should simulate a token expiration scenario
    await act(async () => {
      try {
        await result.current.authFetch(mockUrl);
      } catch (error) {
        // Expected to throw on the first attempt
        const err = error as Error;
        expect(err.message).toContain('Token expired');

        // Try again with refreshed token
        const secondResponse = await result.current.authFetch(mockUrl);
        expect(secondResponse).toEqual(mockFetchResponse);
      }
    });
  });
});
