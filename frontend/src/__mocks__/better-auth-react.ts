// Mock for better-auth/react
export const useSession = jest.fn(() => ({
  data: {
    user: {
      id: 'test-user-id',
      email: 'test@example.com',
      name: 'Test User',
      image: null,
    },
    session: {
      token: 'test-token',
      id: 'test-session-id',
      expiresAt: new Date(Date.now() + 86400000),
      fresh: true,
    },
  },
  isPending: false,
  error: null,
}));

export const createAuthClient = jest.fn(() => ({
  signIn: {
    email: jest.fn().mockResolvedValue({
      data: {
        user: {
          id: 'test-user-id',
          email: 'test@example.com',
          name: 'Test User',
        },
        session: {
          token: 'test-token',
          id: 'test-session-id',
        },
      },
      error: null,
    }),
    social: jest.fn().mockResolvedValue({
      data: {
        user: {
          id: 'test-user-id',
          email: 'test@example.com',
          name: 'Test User',
        },
        session: {
          token: 'test-token',
          id: 'test-session-id',
        },
      },
      error: null,
    }),
  },
  signUp: {
    email: jest.fn().mockResolvedValue({
      data: {
        user: {
          id: 'test-user-id',
          email: 'test@example.com',
          name: 'Test User',
        },
        session: {
          token: 'test-token',
          id: 'test-session-id',
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
        id: 'test-user-id',
        email: 'test@example.com',
        name: 'Test User',
      },
      session: {
        token: 'test-token',
        id: 'test-session-id',
        expiresAt: new Date(Date.now() + 86400000),
        fresh: true,
      },
    },
    error: null,
  }),
  useSession,
}));

export default {
  createAuthClient,
  useSession,
};
