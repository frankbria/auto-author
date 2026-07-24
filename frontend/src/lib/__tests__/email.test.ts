import { sendPasswordResetEmail } from '../email';

/**
 * #332 — password reset must never silently no-op and report fake success.
 * These pins cover the observability branch (unconfigured/unknown provider =>
 * loud [email] error + throw) plus the real send paths and the dev convenience.
 */
describe('sendPasswordResetEmail', () => {
  const ENV_KEYS = [
    'NODE_ENV',
    'EMAIL_SERVICE_PROVIDER',
    'EMAIL_SERVICE_API_KEY',
    'EMAIL_FROM_ADDRESS',
    'EMAIL_FROM_NAME',
  ] as const;
  // Snapshot the pristine env ONCE so per-test mutation can't corrupt it.
  const original: Record<string, string | undefined> = {};
  const realFetch = global.fetch;

  let errorSpy: jest.SpyInstance;
  let logSpy: jest.SpyInstance;
  let fetchSpy: jest.Mock;

  const params = { to: 'user@example.com', name: 'Ada', resetUrl: 'https://app/reset?token=abc' };

  beforeAll(() => {
    ENV_KEYS.forEach((k) => (original[k] = process.env[k]));
  });

  beforeEach(() => {
    // Clean slate: no ambient provider/key can mask the unconfigured assertions.
    delete process.env.EMAIL_SERVICE_PROVIDER;
    delete process.env.EMAIL_SERVICE_API_KEY;
    errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    jest.spyOn(console, 'warn').mockImplementation(() => {});
    logSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
    // fetchWithRetry only reads response.ok, so a minimal stub suffices.
    // A fresh jest.fn() per test guarantees an isolated call counter.
    fetchSpy = jest.fn().mockResolvedValue({ ok: true } as Response);
    global.fetch = fetchSpy as unknown as typeof fetch;
  });

  afterEach(() => {
    ENV_KEYS.forEach((k) => {
      if (original[k] === undefined) delete process.env[k];
      else process.env[k] = original[k];
    });
    jest.restoreAllMocks();
    global.fetch = realFetch;
  });

  it('throws and logs a loud [email] error when no provider is configured (not a fake success)', async () => {
    process.env.NODE_ENV = 'production';

    await expect(sendPasswordResetEmail(params)).rejects.toThrow(
      /EMAIL_SERVICE_PROVIDER is not configured/
    );

    expect(fetchSpy).not.toHaveBeenCalled();
    const logged = errorSpy.mock.calls.flat().join(' ');
    expect(logged).toContain('[email]');
    expect(logged).toContain('EMAIL_SERVICE_PROVIDER');
  });

  it('is observable in non-production environments too (no silent warn-and-return)', async () => {
    process.env.NODE_ENV = 'test';

    await expect(sendPasswordResetEmail(params)).rejects.toThrow(/not sent/);
    expect(errorSpy).toHaveBeenCalled();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('throws naming an unknown provider', async () => {
    process.env.NODE_ENV = 'production';
    process.env.EMAIL_SERVICE_PROVIDER = 'mailgun';

    await expect(sendPasswordResetEmail(params)).rejects.toThrow(/mailgun/);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('sends via Resend when configured', async () => {
    process.env.NODE_ENV = 'production';
    process.env.EMAIL_SERVICE_PROVIDER = 'resend';
    process.env.EMAIL_SERVICE_API_KEY = 'test-key';

    await expect(sendPasswordResetEmail(params)).resolves.toBeUndefined();

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, opts] = fetchSpy.mock.calls[0];
    expect(url).toBe('https://api.resend.com/emails');
    expect((opts as RequestInit).headers).toMatchObject({
      Authorization: 'Bearer test-key',
    });
  });

  it('throws when Resend is selected without an API key', async () => {
    process.env.NODE_ENV = 'production';
    process.env.EMAIL_SERVICE_PROVIDER = 'resend';

    await expect(sendPasswordResetEmail(params)).rejects.toThrow(/EMAIL_SERVICE_API_KEY/);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('sends via SendGrid when configured', async () => {
    process.env.NODE_ENV = 'production';
    process.env.EMAIL_SERVICE_PROVIDER = 'sendgrid';
    process.env.EMAIL_SERVICE_API_KEY = 'sg-key';

    await expect(sendPasswordResetEmail(params)).resolves.toBeUndefined();
    expect(fetchSpy).toHaveBeenCalledWith(
      'https://api.sendgrid.com/v3/mail/send',
      expect.any(Object)
    );
  });

  it('dumps to console in development with no provider (dev convenience, no send, no throw)', async () => {
    process.env.NODE_ENV = 'development';

    await expect(sendPasswordResetEmail(params)).resolves.toBeUndefined();
    expect(fetchSpy).not.toHaveBeenCalled();
    // The dev dump includes the reset URL so a developer can follow it locally.
    const logged = logSpy.mock.calls.flat().join(' ');
    expect(logged).toContain(params.resetUrl);
  });
});
