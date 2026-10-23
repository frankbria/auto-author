/**
 * "Download my data" (#966): the page asks for a single-use token first, so a
 * refusal shows as a toast on the profile page instead of the API's JSON, and
 * only a granted token sends the browser to the file.
 */
import { downloadAccountData } from '@/hooks/useProfileApi';
import { browser, resetUnauthorizedForTests } from '@/lib/api/unauthorized';
import { toast } from '@/lib/toast';

jest.mock('@/lib/toast', () => ({ toast: jest.fn() }));
jest.mock('@/lib/auth-client', () => ({ authClient: { signOut: jest.fn() } }));

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

function reply(status: number, body: unknown, headers: Record<string, string> = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ 'content-type': 'application/json', ...headers }),
    json: jest.fn().mockResolvedValue(body),
  };
}

describe('downloadAccountData', () => {
  let go: jest.SpyInstance;

  beforeEach(() => {
    jest.clearAllMocks();
    resetUnauthorizedForTests();
    global.fetch = jest.fn();
    go = jest.spyOn(browser, 'go').mockImplementation(() => {});
  });

  afterEach(() => go.mockRestore());

  const exportNavigations = () =>
    go.mock.calls.filter(([url]) => String(url).includes('/users/me/export'));

  it('POSTs for a token with the session cookie, then navigates to the file with it', async () => {
    (global.fetch as jest.Mock).mockResolvedValue(reply(200, { token: 'tok/+=1' }));

    await downloadAccountData();

    const [url, init] = (global.fetch as jest.Mock).mock.calls[0];
    expect(url).toBe(`${API}/users/me/export/token`);
    expect(init).toMatchObject({ method: 'POST', credentials: 'include' });
    expect(go).toHaveBeenCalledWith(`${API}/users/me/export?token=tok%2F%2B%3D1`);
    expect(toast).not.toHaveBeenCalled();
  });

  it('a rate-limited request shows a toast with the wait and stays on the page', async () => {
    (global.fetch as jest.Mock).mockResolvedValue(
      reply(429, { detail: 'Rate limit exceeded. Try again in 1500 seconds.' }, { 'Retry-After': '1500' })
    );

    await downloadAccountData();

    expect(go).not.toHaveBeenCalled();
    expect(toast).toHaveBeenCalledTimes(1);
    const shown = (toast as unknown as jest.Mock).mock.calls[0][0];
    expect(shown.variant).toBe('destructive');
    expect(`${shown.title} ${shown.description}`).toMatch(/25 minutes/);
  });

  it('an expired session shows a toast and never navigates to the export', async () => {
    (global.fetch as jest.Mock).mockResolvedValue(reply(401, { detail: 'Not authenticated' }));

    await downloadAccountData();

    expect(exportNavigations()).toEqual([]);
    expect(toast).toHaveBeenCalledTimes(1);
    const shown = (toast as unknown as jest.Mock).mock.calls[0][0];
    expect(`${shown.title} ${shown.description}`).toMatch(/session has expired/i);
  });

  it('any other failure, or no network, shows a toast and does not navigate', async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(reply(500, { detail: 'boom' }))
      .mockRejectedValueOnce(new TypeError('Failed to fetch'));

    await downloadAccountData();
    await downloadAccountData();

    expect(go).not.toHaveBeenCalled();
    expect(toast).toHaveBeenCalledTimes(2);
  });
});
