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

// Export mock functions for password reset so tests can access and configure them
export const mockForgetPassword = jest.fn().mockResolvedValue({
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
  forgetPassword: mockForgetPassword,
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
