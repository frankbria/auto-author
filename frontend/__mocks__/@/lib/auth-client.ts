/**
 * Better Auth Mock for Unit Tests
 * Replaces Clerk mocks with better-auth session structure
 */

export const useSession = jest.fn(() => ({
  data: {
    user: {
      id: "test-user-123",
      email: "test@example.com",
      name: "Test User",
      image: null,
      createdAt: new Date("2025-01-01T00:00:00Z"),
    },
    session: {
      token: "mock-jwt-token",
      id: "session-123",
      expiresAt: new Date(Date.now() + 86400000), // 24 hours from now
      fresh: true,
    },
  },
  isPending: false,
  error: null,
}));

export const authClient = {
  signIn: {
    email: jest.fn().mockResolvedValue({
      data: {
        user: {
          id: "test-user-123",
          email: "test@example.com",
          name: "Test User",
        },
        session: {
          token: "mock-jwt-token",
          id: "session-123",
        },
      },
      error: null,
    }),
  },
  signUp: {
    email: jest.fn().mockResolvedValue({
      data: {
        user: {
          id: "test-user-123",
          email: "test@example.com",
          name: "Test User",
        },
        session: {
          token: "mock-jwt-token",
          id: "session-123",
        },
      },
      error: null,
    }),
  },
  signOut: jest.fn().mockResolvedValue({
    data: {},
    error: null,
  }),
  getSession: jest.fn().mockResolvedValue({
    data: {
      user: {
        id: "test-user-123",
        email: "test@example.com",
        name: "Test User",
      },
      session: {
        token: "mock-jwt-token",
        id: "session-123",
      },
    },
    error: null,
  }),
  forgetPassword: jest.fn().mockResolvedValue({
    data: {},
    error: null,
  }),
  resetPassword: jest.fn().mockResolvedValue({
    data: {},
    error: null,
  }),
};

// Export convenience methods
export const signIn = authClient.signIn;
export const signUp = authClient.signUp;
export const signOut = authClient.signOut;
export const forgetPassword = authClient.forgetPassword;
export const resetPassword = authClient.resetPassword;
