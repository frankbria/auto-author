import type { Db } from 'mongodb';
import * as Sentry from '@sentry/nextjs';
import {
  endOtherSessionsOnSecondFactorChange,
  forgetTrustedDevices,
} from '../auth-second-factor';

// The real-auth Playwright specs run these against a real better-auth server;
// these pin the failure paths that need a reporter or a database to throw.

const failingDb = () =>
  ({
    collection: () => ({ deleteMany: jest.fn().mockRejectedValue(new Error('db down')) }),
  }) as unknown as Db;
const workingDb = () =>
  ({ collection: () => ({ deleteMany: jest.fn().mockResolvedValue({ deletedCount: 1 }) }) }) as unknown as Db;

const caller = { session: { token: 'caller' }, user: { id: 'u1' } };
const disableContext = (deleteSessions = jest.fn().mockResolvedValue(undefined)) => ({
  path: '/two-factor/disable',
  json: (body: Record<string, unknown>) => body,
  context: {
    returned: { status: true },
    session: caller,
    newSession: { session: { token: 'rotated' }, user: { id: 'u1' } },
    internalAdapter: {
      listSessions: jest.fn().mockResolvedValue([{ token: 'rotated' }, { token: 'other' }]),
      deleteSessions,
    },
  },
});

beforeEach(() => {
  jest.clearAllMocks();
  jest.spyOn(console, 'error').mockImplementation(() => {});
});
afterEach(() => jest.restoreAllMocks());

describe('forgetTrustedDevices', () => {
  it('resolves false, and does not throw, when the delete and the reporter both fail', async () => {
    (Sentry.captureException as jest.Mock).mockImplementationOnce(() => {
      throw new Error('reporter down');
    });
    await expect(forgetTrustedDevices(failingDb(), 'u1')).resolves.toBe(false);
  });

  it('does not throw when logging itself fails', async () => {
    (console.error as jest.Mock).mockImplementationOnce(() => {
      throw new Error('stdout closed');
    });
    await expect(forgetTrustedDevices(failingDb(), 'u1')).resolves.toBe(false);
  });

  it('resolves true when the rows are deleted', async () => {
    await expect(forgetTrustedDevices(workingDb(), 'u1')).resolves.toBe(true);
  });
});

describe('endOtherSessionsOnSecondFactorChange on disable', () => {
  it('flags trustedDevicesForgotten: false when the trusted devices could not be forgotten', async () => {
    const ctx = disableContext();
    await expect(endOtherSessionsOnSecondFactorChange(ctx, failingDb())).resolves.toEqual({
      status: true,
      trustedDevicesForgotten: false,
    });
    expect(ctx.context.internalAdapter.deleteSessions).toHaveBeenCalledWith(['other']);
  });

  it('flags both when neither step succeeds', async () => {
    const ctx = disableContext(jest.fn().mockRejectedValue(new Error('db down')));
    await expect(endOtherSessionsOnSecondFactorChange(ctx, failingDb())).resolves.toEqual({
      status: true,
      trustedDevicesForgotten: false,
      otherSessionsEnded: false,
    });
  });

  it('keeps better-auth’s answer when every step succeeds', async () => {
    await expect(endOtherSessionsOnSecondFactorChange(disableContext(), workingDb())).resolves.toBeUndefined();
  });
});
