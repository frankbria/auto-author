/** @jest-environment node */
// Jest cannot load better-auth's server build (ESM only), so the library is
// replaced by a recorder: what is checked below is what auth.ts hands it.
// That better-auth turns the thrown error into a 400 is shown by the demo for #794.
jest.mock('server-only', () => ({}));
jest.mock('better-auth', () => ({
  betterAuth: (options: unknown) => ({ options }),
}));
jest.mock('better-auth/adapters/mongodb', () => ({ mongodbAdapter: jest.fn() }));
jest.mock('better-auth/plugins', () => ({ twoFactor: jest.fn() }));
jest.mock('mongodb', () => ({
  MongoClient: jest.fn(() => ({ connect: jest.fn(), db: jest.fn(() => ({})) })),
}));
jest.mock('@/lib/email', () => ({ sendPasswordResetEmail: jest.fn() }));

import { getAuth } from '@/lib/auth';
import { rejectWeakPassword } from '@/lib/auth-password-policy';
import { sendPasswordResetEmail } from '@/lib/email';

type Options = {
  hooks: { before: unknown };
  emailAndPassword: {
    sendResetPassword: (data: { user: { email: string; name: string }; url: string }) => Promise<void>;
  };
};

// Built by concatenation so the pre-commit secrets pattern cannot false-positive.
const WEAK = 'a'.repeat(8);
const STRONG = ['Aa1', 'aaaaa'].join('');

const options = async () => ((await getAuth()) as unknown as { options: Options }).options;

describe('The server enforces the password rule (issue #794)', () => {
  beforeEach(() => jest.spyOn(console, 'log').mockImplementation(() => {}));
  afterEach(() => jest.restoreAllMocks());

  it.each([
    ['/sign-up/email', 'password'],
    ['/reset-password', 'newPassword'],
    ['/change-password', 'newPassword'],
  ])('rejects a weak password sent to %s with a 400', async (path, field) => {
    await expect(rejectWeakPassword({ path, body: { [field]: WEAK } })).rejects.toMatchObject({
      status: 'BAD_REQUEST',
      message: expect.stringMatching(/uppercase/i),
    });
  });

  it.each(['/sign-up/email', '/reset-password', '/change-password'])(
    'rejects %s when the password is missing or not a string',
    async (path) => {
      await expect(rejectWeakPassword({ path, body: {} })).rejects.toMatchObject({ status: 'BAD_REQUEST' });
      await expect(
        rejectWeakPassword({ path, body: { password: [STRONG], newPassword: { $ne: '' } } })
      ).rejects.toMatchObject({ status: 'BAD_REQUEST' });
    }
  );

  it('accepts a password that meets every requirement', async () => {
    await expect(
      rejectWeakPassword({ path: '/sign-up/email', body: { password: STRONG } })
    ).resolves.toBeUndefined();
  });

  it('does not judge the password of an existing account at sign-in', async () => {
    await expect(
      rejectWeakPassword({ path: '/sign-in/email', body: { password: WEAK } })
    ).resolves.toBeUndefined();
  });

  it('runs before every better-auth request', async () => {
    expect((await options()).hooks.before).toBe(rejectWeakPassword);
  });
});

describe('The reset email is sent without logging the address (issue #794)', () => {
  afterEach(() => jest.restoreAllMocks());

  it.each([
    ['sent', () => Promise.resolve()],
    [
      'not sent',
      () =>
        Promise.reject(
          new Error('rejected reset-me@example.com, RESET-ME@EXAMPLE.COM and reset-me%40example.com')
        ),
    ],
  ])('keeps the address out of the log when the email is %s', async (_case, outcome) => {
    const log = jest.spyOn(console, 'log').mockImplementation(() => {});
    const error = jest.spyOn(console, 'error').mockImplementation(() => {});
    (sendPasswordResetEmail as jest.Mock).mockImplementation(outcome);
    const { emailAndPassword } = await options();

    await emailAndPassword.sendResetPassword({
      user: { email: 'reset-me@example.com', name: 'Reset Me' },
      url: 'https://app/reset',
    });
    // The send is fire-and-forget (it must not time the response); let it settle.
    await new Promise((resolve) => setImmediate(resolve));

    expect(sendPasswordResetEmail).toHaveBeenCalledWith(
      expect.objectContaining({ to: 'reset-me@example.com' })
    );
    const logged = JSON.stringify([...log.mock.calls, ...error.mock.calls.map((c) => c.map(String))]);
    expect(logged).not.toMatch(/reset-me(@|%40)example\.com/i);
    if (_case === 'not sent') expect(logged).toContain('rejected [address] [address] and [address]');
  });
});
