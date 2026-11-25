/** @jest-environment node */
// Jest cannot load better-auth's server build (ESM only), so the library is
// replaced by a recorder: what is checked below is what auth.ts hands it.
jest.mock('server-only', () => ({}));
jest.mock('better-auth', () => ({
  betterAuth: (options: unknown) => ({ options }),
}));
jest.mock('better-auth/adapters/mongodb', () => ({ mongodbAdapter: jest.fn() }));
jest.mock('better-auth/plugins', () => ({ twoFactor: jest.fn(() => ({ id: 'two-factor' })) }));
jest.mock('mongodb', () => ({
  MongoClient: jest.fn(() => ({ connect: jest.fn(), db: jest.fn(() => ({})) })),
}));

import { getAuth } from '@/lib/auth';
import { sessionMiddleware } from 'better-auth/api';
import {
  acceptCurrentTerms,
  stampTermsAcceptance,
  termsAcceptance,
  termsAcceptanceFields,
} from '@/lib/auth-terms';
import { acceptedCurrentTerms, TERMS_VERSION } from '@/lib/constants/legal';

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

  // The backend reads the same document as its user (#1263).
  it('keeps users in the users collection the backend reads', async () => {
    jest.spyOn(console, 'log').mockImplementation(() => {});
    const { options } = (await getAuth()) as unknown as {
      options: { user: { modelName: string } };
    };

    expect(options.user.modelName).toBe('users');
  });

  it('versions the Terms by an ISO date', () => {
    expect(TERMS_VERSION).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});

describe('An existing account accepts a new Terms version (issue #961)', () => {
  it.each([
    ['the current version', TERMS_VERSION, true],
    ['a later version', '2999-01-01', true],
    ['an older version', '2000-01-01', false],
    ['no version (an account from before #789)', undefined, false],
    ['null', null, false],
    ['a non-string', 20261010, false],
  ])('counts %s as accepted: %s', (_label, version, accepted) => {
    expect(acceptedCurrentTerms(version)).toBe(accepted);
  });

  function fakeContext(userId = 'user-1') {
    const updateUser = jest.fn(async (_id: string, data: object) => ({ id: _id, ...data }));
    const json = jest.fn((body: unknown) => body);
    return {
      updateUser,
      json,
      ctx: {
        json,
        context: { session: { user: { id: userId } }, internalAdapter: { updateUser } },
      },
    };
  }

  it('stamps the current version and the time on the signed-in user', async () => {
    const { ctx, updateUser, json } = fakeContext('user-42');
    const before = Date.now();

    await acceptCurrentTerms(ctx);

    expect(updateUser).toHaveBeenCalledTimes(1);
    const [id, data] = updateUser.mock.calls[0];
    expect(id).toBe('user-42');
    expect(data).toEqual({ termsVersion: TERMS_VERSION, termsAcceptedAt: expect.any(Date) });
    expect((data as { termsAcceptedAt: Date }).termsAcceptedAt.getTime()).toBeGreaterThanOrEqual(before);
    expect(json).toHaveBeenCalledWith({ termsVersion: TERMS_VERSION });
  });

  // The body is never read: the server chooses what was accepted and when.
  it('ignores a version or time sent by the browser', async () => {
    const { ctx, updateUser } = fakeContext();
    await acceptCurrentTerms({
      ...ctx,
      body: { termsVersion: '1999-01-01', termsAcceptedAt: new Date(0) },
    } as typeof ctx);

    expect(updateUser.mock.calls[0][1]).toMatchObject({ termsVersion: TERMS_VERSION });
  });

  it('is a POST endpoint that requires a session', () => {
    const endpoint = termsAcceptance().endpoints.acceptTerms as unknown as {
      path: string;
      options: { method: string; use: unknown[] };
    };
    expect(endpoint.path).toBe('/terms/accept');
    expect(endpoint.options.method).toBe('POST');
    expect(endpoint.options.use).toContain(sessionMiddleware);
  });

  it('is wired into the better-auth instance', async () => {
    jest.spyOn(console, 'log').mockImplementation(() => {});
    const { options } = (await getAuth()) as unknown as {
      options: { plugins: { id: string }[] };
    };

    expect(options.plugins.map((p) => p.id)).toContain('terms-acceptance');
  });
});
