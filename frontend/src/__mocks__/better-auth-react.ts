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

export default {
  useSession,
};
