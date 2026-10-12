/** @jest-environment node */
// Jest cannot load better-auth's server build (ESM only), so the library is
// replaced by a recorder: what is checked below is what auth.ts hands it.
// That better-auth then deletes the sessions is shown by the demo for #793.
jest.mock('server-only', () => ({}));
jest.mock('better-auth', () => ({
  betterAuth: (options: unknown) => ({ options }),
}));
jest.mock('better-auth/adapters/mongodb', () => ({ mongodbAdapter: jest.fn() }));
jest.mock('better-auth/plugins', () => ({ twoFactor: jest.fn() }));
jest.mock('mongodb', () => ({
  MongoClient: jest.fn(() => ({ connect: jest.fn(), db: jest.fn(() => ({})) })),
}));

import { getAuth } from '@/lib/auth';

type Options = {
  emailAndPassword: { revokeSessionsOnPasswordReset?: boolean };
  session: { cookieCache?: { enabled?: boolean } };
};

const options = async () => {
  jest.spyOn(console, 'log').mockImplementation(() => {});
  return ((await getAuth()) as unknown as { options: Options }).options;
};

describe('A revoked session stops working at once (issue #793)', () => {
  it('tells better-auth to revoke sessions when a password is reset', async () => {
    // better-auth defaults this to false: a session an attacker already holds
    // would survive the reset that was meant to lock them out.
    expect((await options()).emailAndPassword.revokeSessionsOnPasswordReset).toBe(true);
  });

  it('does not cache sessions in a cookie', async () => {
    // With the cache on, get-session keeps answering from the cookie for up to
    // five minutes after the session row is deleted.
    expect((await options()).session.cookieCache?.enabled ?? false).toBe(false);
  });
});
