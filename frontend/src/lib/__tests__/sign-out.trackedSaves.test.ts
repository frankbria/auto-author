import { authClient } from '@/lib/auth-client';
import {
  beforeSignOut,
  endSignOut,
  resetLeavingSavesForTests,
  savedNow,
  signOutCount,
  signOutOrNotify,
  trackSave,
  UNSAVED_WRITING_WARNING,
} from '@/lib/sign-out';

const mockSignOut = authClient.signOut as jest.Mock;

/**
 * #1091: saves from editors already closed (their leaving saves). A sign-out
 * waits for them, including one handed off while the handlers run, and asks
 * about one that failed even when the browser kept no backup of it.
 */
describe('signOutOrNotify and tracked saves', () => {
  let confirmSpy: jest.SpyInstance;

  beforeEach(() => {
    jest.clearAllMocks();
    endSignOut();
    resetLeavingSavesForTests();
    mockSignOut.mockResolvedValue({ data: {}, error: null });
    confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(false);
  });

  afterEach(() => confirmSpy.mockRestore());

  it('waits for a save tracked while the handlers run before signing out', async () => {
    let finishLate: (saved: boolean) => void = () => {};
    const stop = beforeSignOut(async () => {
      void trackSave('chapter:bk/A', new Promise<boolean>((resolve) => (finishLate = resolve)));
      return false;
    });

    const signedOut = signOutOrNotify();
    for (let i = 0; i < 5; i++) await Promise.resolve();
    expect(mockSignOut).not.toHaveBeenCalled();

    finishLate(true);
    expect(await signedOut).toBe(true);
    expect(mockSignOut).toHaveBeenCalledTimes(1);
    expect(confirmSpy).not.toHaveBeenCalled();
    stop();
  });

  it('also runs the handler of an editor opened while the handlers ran, and asks if it left text unsaved', async () => {
    let stopLate: () => void = () => {};
    const late = jest.fn(async () => true);
    const stop = beforeSignOut(async () => {
      stopLate = beforeSignOut(late);
      return false;
    });

    expect(await signOutOrNotify()).toBe(false);
    expect(late).toHaveBeenCalledTimes(1);
    expect(confirmSpy).toHaveBeenCalledWith(UNSAVED_WRITING_WARNING);
    stop();
    stopLate();
  });

  it('asks about a leaving save that failed before the sign-out began', async () => {
    await trackSave('summary:bk', Promise.resolve(false));

    expect(await signOutOrNotify()).toBe(false);
    expect(confirmSpy).toHaveBeenCalledWith(UNSAVED_WRITING_WARNING);
    expect(mockSignOut).not.toHaveBeenCalled();
  });

  it('does not ask once that text has been saved since', async () => {
    await trackSave('summary:bk', Promise.resolve(false));
    savedNow('summary:bk');

    expect(await signOutOrNotify()).toBe(true);
    expect(confirmSpy).not.toHaveBeenCalled();
  });

  it('a save from an editor opened before an earlier sign-out marks nothing', async () => {
    confirmSpy.mockReturnValue(true);
    await signOutOrNotify(); // the earlier sign-out
    jest.clearAllMocks();
    await trackSave('chapter:bk/A', Promise.resolve(false), signOutCount() - 1);

    expect(await signOutOrNotify()).toBe(true);
    expect(confirmSpy).not.toHaveBeenCalled();
  });
});
