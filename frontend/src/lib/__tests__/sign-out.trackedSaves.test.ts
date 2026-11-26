import { authClient } from '@/lib/auth-client';
import { beforeSignOut, endSignOut, signOutOrNotify, trackSave } from '@/lib/sign-out';

const mockSignOut = authClient.signOut as jest.Mock;

/**
 * #1091: a save handed off while the beforeSignOut handlers run (an editor that
 * closes mid-sign-out) is waited for too, not only the ones already running.
 */
describe('signOutOrNotify and tracked saves', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    endSignOut();
    mockSignOut.mockResolvedValue({ data: {}, error: null });
  });

  it('waits for a save tracked while the handlers run before signing out', async () => {
    let finishLate: () => void = () => {};
    const stop = beforeSignOut(async () => {
      void trackSave(new Promise<void>((resolve) => (finishLate = resolve)));
      return false;
    });

    const signedOut = signOutOrNotify();
    for (let i = 0; i < 5; i++) await Promise.resolve();
    expect(mockSignOut).not.toHaveBeenCalled();

    finishLate();
    expect(await signedOut).toBe(true);
    expect(mockSignOut).toHaveBeenCalledTimes(1);
    stop();
  });
});
