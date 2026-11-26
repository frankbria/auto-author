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

  it('on a 503, leaves the session alone: the backend could not check it, which is not the same as it being gone (#1007)', async () => {
    answer(503);

    const response = await apiFetch('http://api/books');
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(response.status).toBe(503);
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
  it.each(['src/hooks/useAuthFetch.ts', 'src/lib/api/bookClient.ts', 'src/lib/api/imageUpload.ts'])(
    '%s has no bare fetch call',
    (file) => {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const source = require('fs').readFileSync(require('path').resolve(process.cwd(), file), 'utf8');

      expect(source).toMatch(/\bapiFetch\(/);
      expect(source.replace(/apiFetch\(/g, '')).not.toMatch(/\bfetch\(/);
    }
  );
});

/**
 * #1316 — the backend refuses the Service to an account on older Terms. A page
 * that thinks they are accepted (a bundle from before a Terms bump) reloads, so
 * ProtectedRoute shows the acceptance screen with the current version.
 */
describe('apiFetch on TERMS_NOT_ACCEPTED', () => {
  const realFetch = global.fetch;
  let reload: jest.SpyInstance;

  // jsdom has no Response; this has the parts apiFetch reads.
  const refuse = (detail: unknown) => {
    const response = { status: 403, ok: false, json: async () => ({ detail }) };
    global.fetch = jest.fn().mockResolvedValue({ ...response, clone: () => response });
  };
  const settle = () => new Promise((resolve) => setTimeout(resolve, 0));

  beforeEach(() => {
    resetUnauthorizedForTests();
    sessionStorage.clear();
    reload = jest.spyOn(browser, 'reload').mockImplementation(() => {});
  });

  afterEach(() => {
    global.fetch = realFetch;
    reload.mockRestore();
  });

  it('reloads the page once, and the caller still gets the 403', async () => {
    refuse({ error_code: 'TERMS_NOT_ACCEPTED', message: 'Accept' });

    const responses = await Promise.all([apiFetch('http://api/books'), apiFetch('http://api/books')]);
    await settle();

    expect(responses.map((r) => r.status)).toEqual([403, 403]);
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it('does not reload again right after a reload for the same reason', async () => {
    refuse({ error_code: 'TERMS_NOT_ACCEPTED' });

    await apiFetch('http://api/books');
    await settle();
    resetUnauthorizedForTests(); // a reloaded page starts with fresh module state
    await apiFetch('http://api/books');
    await settle();

    expect(reload).toHaveBeenCalledTimes(1);
  });

  describe('when the browser blocks storage', () => {
    let navigation: jest.Mock;
    beforeEach(() => {
      jest.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
        throw new DOMException('blocked', 'SecurityError');
      });
      jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
        throw new DOMException('blocked', 'SecurityError');
      });
      // jsdom has no getEntriesByType.
      navigation = jest.fn();
      Object.defineProperty(performance, 'getEntriesByType', { value: navigation, configurable: true });
    });
    afterEach(() => {
      jest.restoreAllMocks();
      delete (performance as { getEntriesByType?: unknown }).getEntriesByType;
    });

    it('still reloads', async () => {
      navigation.mockReturnValue([{ type: 'navigate' }] as unknown as PerformanceEntryList);
      refuse({ error_code: 'TERMS_NOT_ACCEPTED' });

      await apiFetch('http://api/books');
      await settle();

      expect(reload).toHaveBeenCalledTimes(1);
    });

    it('does not reload a page that is itself that reload', async () => {
      navigation.mockReturnValue([{ type: 'reload' }] as unknown as PerformanceEntryList);
      refuse({ error_code: 'TERMS_NOT_ACCEPTED' });

      await apiFetch('http://api/books');
      await settle();

      expect(reload).not.toHaveBeenCalled();
    });
  });

  it('leaves any other 403 alone', async () => {
    refuse('Not enough permissions');

    await apiFetch('http://api/books');
    await settle();

    expect(reload).not.toHaveBeenCalled();
  });
});
