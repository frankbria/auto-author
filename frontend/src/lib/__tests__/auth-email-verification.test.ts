/** @jest-environment node */
// Jest cannot load better-auth's server build (ESM only), so the library is
// replaced by a recorder: what is checked below is what auth.ts hands it.
// better-auth itself turns `requireEmailVerification` into a 403
// EMAIL_NOT_VERIFIED at sign-in; the demo for #792 shows that on a real server.
jest.mock('server-only', () => ({}));
jest.mock('better-auth', () => ({
  betterAuth: (options: unknown) => ({ options }),
}));
jest.mock('better-auth/adapters/mongodb', () => ({ mongodbAdapter: jest.fn() }));
jest.mock('better-auth/plugins', () => ({ twoFactor: jest.fn() }));
jest.mock('mongodb', () => ({
  MongoClient: jest.fn(() => ({ connect: jest.fn(), db: jest.fn(() => ({})) })),
}));
jest.mock('@/lib/email', () => ({ sendVerificationEmail: jest.fn() }));

import { getAuth } from '@/lib/auth';
import { sendVerificationEmail } from '@/lib/email';

type Options = {
  emailAndPassword: { requireEmailVerification?: boolean; autoSignIn?: boolean };
  emailVerification: {
    sendOnSignUp?: boolean;
    sendOnSignIn?: boolean;
    autoSignInAfterVerification?: boolean;
    expiresIn?: number;
    sendVerificationEmail: (data: { user: { email: string }; url: string }) => Promise<void>;
  };
};

const options = async () => {
  jest.spyOn(console, 'log').mockImplementation(() => {});
  return ((await getAuth()) as unknown as { options: Options }).options;
};

describe('Email verification is required (issue #792)', () => {
  it('refuses a session to an unverified address', async () => {
    const { emailAndPassword } = await options();

    expect(emailAndPassword.requireEmailVerification).toBe(true);
  });

  // A refused sign-in no longer mails from the server (#969): the sign-in page
  // sends the link itself, so it can aim it at the user's destination without a
  // sign-in callbackURL (which made every successful sign-in a full reload).
  it('sends the link at sign-up only, valid for one hour', async () => {
    const { emailVerification } = await options();

    expect(emailVerification).toMatchObject({
      sendOnSignUp: true,
      sendOnSignIn: false,
      autoSignInAfterVerification: true,
      expiresIn: 60 * 60,
    });
  });

  it('mails the link to the address being verified', async () => {
    const { emailVerification } = await options();

    await emailVerification.sendVerificationEmail({
      user: { email: 'new@example.com' },
      url: 'https://app/api/auth/verify-email?token=abc',
    });

    expect(sendVerificationEmail).toHaveBeenCalledWith({
      to: 'new@example.com',
      verifyUrl: 'https://app/api/auth/verify-email?token=abc',
    });
  });

  // better-auth catches the rejection and logs it; swallowing it here would
  // leave no trace of a link that was never sent.
  it('does not swallow a failed send', async () => {
    (sendVerificationEmail as jest.Mock).mockRejectedValueOnce(new Error('not sent'));
    const { emailVerification } = await options();

    await expect(
      emailVerification.sendVerificationEmail({ user: { email: 'new@example.com' }, url: 'u' })
    ).rejects.toThrow('not sent');
  });
});
