import { authClient } from '@/lib/auth-client';
import { apiFetch, browser, resetUnauthorizedForTests } from '../unauthorized';

/**
 * #796 — a device whose session was revoked kept looking signed in and got a
 * stream of 401s. Every backend call goes through apiFetch, and a 401 there
 * ends the dead session in this browser and sends the user to sign in.
 */
describe('apiFetch', () => {
  const mockSignOut = authClient.signOut as jest.Mock;
  const realFetch = global.fetch;
  let go: jest.SpyInstance;

  const answer = (status: number) =>
    (global.fetch = jest.fn().mockResolvedValue({ status, ok: status < 400 } as Response));

  beforeEach(() => {
    jest.clearAllMocks();
    resetUnauthorizedForTests();
    mockSignOut.mockResolvedValue({ data: {}, error: null });
    go = jest.spyOn(browser, 'go').mockImplementation(() => {});
    window.history.pushState({}, '', '/dashboard/books/b1?tab=2');
  });

  afterEach(() => {
    global.fetch = realFetch;
    go.mockRestore();
  });

  it('passes the request through and returns the response', async () => {
    answer(200);

    const response = await apiFetch('http://api/books', { method: 'POST' });

    expect(global.fetch).toHaveBeenCalledWith('http://api/books', { method: 'POST' });
    expect(response.status).toBe(200);
    expect(mockSignOut).not.toHaveBeenCalled();
    expect(go).not.toHaveBeenCalled();
  });

  it.each([403, 404, 500])('leaves a %s alone', async (status) => {
    answer(status);

    await apiFetch('http://api/books');

    expect(mockSignOut).not.toHaveBeenCalled();
    expect(go).not.toHaveBeenCalled();
  });

  it('on a 401, signs out and sends the user to sign in, back to where they were', async () => {
    answer(401);

    const response = await apiFetch('http://api/books');
    await waitForRedirect();

    // The caller still gets the response, so its own error handling runs.
    expect(response.status).toBe(401);
    expect(mockSignOut).toHaveBeenCalledTimes(1);
    expect(go).toHaveBeenCalledWith(
      `/auth/sign-in?redirect=${encodeURIComponent('/dashboard/books/b1?tab=2')}`
    );
  });

  it('handles a burst of 401s once', async () => {
    answer(401);

    await Promise.all([apiFetch('http://api/a'), apiFetch('http://api/b'), apiFetch('http://api/c')]);
    await waitForRedirect();

    expect(mockSignOut).toHaveBeenCalledTimes(1);
    expect(go).toHaveBeenCalledTimes(1);
  });

  it('still redirects when signing out fails', async () => {
    answer(401);
    mockSignOut.mockRejectedValue(new Error('offline'));

    await apiFetch('http://api/books');
    await waitForRedirect();

    expect(go).toHaveBeenCalledTimes(1);
  });

  it('does not redirect from a sign-in page to itself', async () => {
    window.history.pushState({}, '', '/auth/sign-in');
    answer(401);

    await apiFetch('http://api/books');
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(go).not.toHaveBeenCalled();
  });

  const waitForRedirect = async () => {
    for (let i = 0; i < 20 && go.mock.calls.length === 0; i++) {
      await new Promise((resolve) => setTimeout(resolve, 0));
    }
  };
});

describe('every backend caller uses apiFetch', () => {
  // A caller that kept a bare fetch() would leave a revoked session looping
  // on 401s for that part of the app.
  it.each(['src/hooks/useAuthFetch.ts', 'src/lib/api/bookClient.ts', 'src/components/profile/ProfilePictureUpload.tsx'])(
    '%s has no bare fetch call',
    (file) => {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const source = require('fs').readFileSync(require('path').resolve(process.cwd(), file), 'utf8');

      expect(source).toMatch(/\bapiFetch\(/);
      expect(source.replace(/apiFetch\(/g, '')).not.toMatch(/\bfetch\(/);
    }
  );
});
