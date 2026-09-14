// Mock for better-auth/react
//
// This is the useSession components actually get: `@/lib/auth-client` is not
// replaced by jest.mock factories in this setup (the one in jest.setup.ts
// included), so it builds its client from this module, via moduleNameMapper.
//
// One result object for every call. better-auth keeps `data` referentially
// stable between renders, and components list `session` in effect and callback
// deps; a fresh object per call made the book page refetch in a loop (#584).
const sessionResult = {
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
};
export const useSession = jest.fn(() => sessionResult);

// Export mock functions for password reset so tests can access and configure them
export const mockRequestPasswordReset = jest.fn().mockResolvedValue({
  data: {},
  error: null,
});

export const mockResetPassword = jest.fn().mockResolvedValue({
  data: {},
  error: null,
});

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
  // Password reset methods
  requestPasswordReset: mockRequestPasswordReset,
  resetPassword: mockResetPassword,
  // Account security methods (#64)
  changePassword: jest.fn().mockResolvedValue({ data: {}, error: null }),
  listSessions: jest.fn().mockResolvedValue({ data: [], error: null }),
  revokeSession: jest.fn().mockResolvedValue({ data: {}, error: null }),
  revokeOtherSessions: jest.fn().mockResolvedValue({ data: {}, error: null }),
  twoFactor: {
    enable: jest.fn().mockResolvedValue({
      data: {
        totpURI: 'otpauth://totp/Auto%20Author:test@example.com?secret=TESTSECRET',
        backupCodes: ['AAAA-1111', 'BBBB-2222'],
      },
      error: null,
    }),
    disable: jest.fn().mockResolvedValue({ data: {}, error: null }),
    verifyTotp: jest.fn().mockResolvedValue({ data: {}, error: null }),
    verifyBackupCode: jest.fn().mockResolvedValue({ data: {}, error: null }),
    generateBackupCodes: jest.fn().mockResolvedValue({
      data: { backupCodes: ['CCCC-3333', 'DDDD-4444'] },
      error: null,
    }),
  },
  useSession,
}));

export default {
  createAuthClient,
  useSession,
};
