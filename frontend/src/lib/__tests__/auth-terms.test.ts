/** @jest-environment node */
// Jest cannot load better-auth's server build (ESM only), so the library is
// replaced by a recorder: what is checked below is what auth.ts hands it.
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
import { stampTermsAcceptance, termsAcceptanceFields } from '@/lib/auth-terms';
import { TERMS_VERSION } from '@/lib/constants/legal';

describe('Terms acceptance recorded at sign-up (issue #789)', () => {
  it('stamps the current Terms version and the time on the user being created', async () => {
    const before = Date.now();
    const { data } = await stampTermsAcceptance({
      name: 'Test User',
      email: 'test@example.com',
    });

    expect(data).toMatchObject({
      name: 'Test User',
      email: 'test@example.com',
      termsVersion: TERMS_VERSION,
    });
    expect(data.termsAcceptedAt).toBeInstanceOf(Date);
    expect(data.termsAcceptedAt.getTime()).toBeGreaterThanOrEqual(before);
  });

  it('overwrites a value that arrived with the user', async () => {
    const { data } = await stampTermsAcceptance({
      termsVersion: 'forged',
      termsAcceptedAt: new Date(0),
    });

    expect(data.termsVersion).toBe(TERMS_VERSION);
    expect(data.termsAcceptedAt.getTime()).toBeGreaterThan(0);
  });

  // better-auth answers 400 "<field> is not allowed to be set" for an
  // `input: false` field in a sign-up body, so the browser cannot choose them.
  it.each(['termsVersion', 'termsAcceptedAt'] as const)(
    'refuses %s from the client',
    (field) => {
      expect(termsAcceptanceFields[field].input).toBe(false);
    }
  );

  it('is wired into the better-auth instance', async () => {
    jest.spyOn(console, 'log').mockImplementation(() => {});
    const { options } = (await getAuth()) as unknown as {
      options: {
        user: { additionalFields: unknown };
        databaseHooks: { user: { create: { before: unknown } } };
      };
    };

    expect(options.user.additionalFields).toBe(termsAcceptanceFields);
    expect(options.databaseHooks.user.create.before).toBe(stampTermsAcceptance);
  });

  it('versions the Terms by an ISO date', () => {
    expect(TERMS_VERSION).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});
