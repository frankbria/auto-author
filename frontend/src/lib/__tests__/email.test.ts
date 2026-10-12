import { emailProvider, sendPasswordResetEmail, sendVerificationEmail } from '../email';

/**
 * #332 — password reset must never silently no-op and report fake success.
 * These pins cover the observability branch (unconfigured/unknown provider =>
 * loud [email] error + throw) plus the real send paths and the dev convenience.
 */
// NODE_ENV is typed read-only; the tests switch it per case.
const setNodeEnv = (value: string) => {
  (process.env as Record<string, string | undefined>).NODE_ENV = value;
};

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
      else (process.env as Record<string, string | undefined>)[k] = original[k];
    });
    jest.restoreAllMocks();
    global.fetch = realFetch;
  });

  it('throws and logs a loud [email] error when no provider is configured (not a fake success)', async () => {
    setNodeEnv('production');

    await expect(sendPasswordResetEmail(params)).rejects.toThrow(
      /EMAIL_SERVICE_PROVIDER is not configured/
    );

    expect(fetchSpy).not.toHaveBeenCalled();
    const logged = errorSpy.mock.calls.flat().join(' ');
    expect(logged).toContain('[email]');
    expect(logged).toContain('EMAIL_SERVICE_PROVIDER');
  });

  it('is observable in non-production environments too (no silent warn-and-return)', async () => {
    setNodeEnv('test');

    await expect(sendPasswordResetEmail(params)).rejects.toThrow(/not sent/);
    expect(errorSpy).toHaveBeenCalled();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('throws naming an unknown provider', async () => {
    setNodeEnv('production');
    process.env.EMAIL_SERVICE_PROVIDER = 'mailgun';

    await expect(sendPasswordResetEmail(params)).rejects.toThrow(/mailgun/);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('sends via Resend when configured', async () => {
    setNodeEnv('production');
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
    setNodeEnv('production');
    process.env.EMAIL_SERVICE_PROVIDER = 'resend';

    await expect(sendPasswordResetEmail(params)).rejects.toThrow(/EMAIL_SERVICE_API_KEY/);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('sends via SendGrid when configured', async () => {
    setNodeEnv('production');
    process.env.EMAIL_SERVICE_PROVIDER = 'sendgrid';
    process.env.EMAIL_SERVICE_API_KEY = 'sg-key';

    await expect(sendPasswordResetEmail(params)).resolves.toBeUndefined();
    expect(fetchSpy).toHaveBeenCalledWith(
      'https://api.sendgrid.com/v3/mail/send',
      expect.any(Object)
    );
  });

  it('dumps to console in development with no provider (dev convenience, no send, no throw)', async () => {
    setNodeEnv('development');

    await expect(sendPasswordResetEmail(params)).resolves.toBeUndefined();
    expect(fetchSpy).not.toHaveBeenCalled();
    // The dev dump includes the reset URL so a developer can follow it locally.
    const logged = logSpy.mock.calls.flat().join(' ');
    expect(logged).toContain(params.resetUrl);
  });

  // #794: the name is user-chosen and the email comes from the genuine sender.
  it('escapes the name in the HTML part and leaves the text part as typed', async () => {
    setNodeEnv('production');
    process.env.EMAIL_SERVICE_PROVIDER = 'resend';
    process.env.EMAIL_SERVICE_API_KEY = 'test-key';
    const name = `<a href=x>Click</a> & "friends" 'here'`;

    await sendPasswordResetEmail({ ...params, name });

    const body = JSON.parse((fetchSpy.mock.calls[0][1] as RequestInit).body as string);
    expect(body.html).toContain(
      'Hi &lt;a href=x&gt;Click&lt;/a&gt; &amp; &quot;friends&quot; &#39;here&#39;,'
    );
    expect(body.html).not.toContain('<a href=x>');
    expect(body.text).toContain(`Hi ${name},`);
  });

  // #792: the verification email goes through the same delivery path.
  describe('sendVerificationEmail', () => {
    const verification = {
      to: 'new@example.com',
      verifyUrl: 'https://app/api/auth/verify-email?token=abc',
    };

    it('throws and logs a loud [email] error when no provider is configured', async () => {
      setNodeEnv('production');

      await expect(sendVerificationEmail(verification)).rejects.toThrow(
        /Verification email not sent: EMAIL_SERVICE_PROVIDER is not configured/
      );

      expect(fetchSpy).not.toHaveBeenCalled();
      expect(errorSpy.mock.calls.flat().join(' ')).toContain('[email] Verification email NOT sent');
    });

    it('sends the link to the address via Resend, in both the text and the HTML part', async () => {
      setNodeEnv('production');
      process.env.EMAIL_SERVICE_PROVIDER = 'resend';
      process.env.EMAIL_SERVICE_API_KEY = 'test-key';

      await sendVerificationEmail(verification);

      const [url, opts] = fetchSpy.mock.calls[0];
      expect(url).toBe('https://api.resend.com/emails');
      const body = JSON.parse((opts as RequestInit).body as string);
      expect(body.to).toEqual(['new@example.com']);
      expect(body.subject).toMatch(/verify your email/i);
      expect(body.text).toContain(verification.verifyUrl);
      expect(body.html).toContain(verification.verifyUrl);
    });

    it('dumps the link to the console in development with no provider', async () => {
      setNodeEnv('development');

      await expect(sendVerificationEmail(verification)).resolves.toBeUndefined();

      expect(fetchSpy).not.toHaveBeenCalled();
      expect(logSpy.mock.calls.flat().join(' ')).toContain(verification.verifyUrl);
    });
  });

  // #968: the health route reports this, so it must agree with what a send does.
  describe('emailProvider', () => {
    const cases: [string, Record<string, string>, string | null][] = [
      ['production, nothing set', { NODE_ENV: 'production' }, null],
      ['production, unknown provider', { NODE_ENV: 'production', EMAIL_SERVICE_PROVIDER: 'mailgun', EMAIL_SERVICE_API_KEY: 'k' }, null],
      ['production, Resend without a key', { NODE_ENV: 'production', EMAIL_SERVICE_PROVIDER: 'resend' }, null],
      ['production, Resend with a key', { NODE_ENV: 'production', EMAIL_SERVICE_PROVIDER: 'Resend', EMAIL_SERVICE_API_KEY: 'k' }, 'resend'],
      ['production, SendGrid with a key', { NODE_ENV: 'production', EMAIL_SERVICE_PROVIDER: 'sendgrid', EMAIL_SERVICE_API_KEY: 'k' }, 'sendgrid'],
      ['development, nothing set', { NODE_ENV: 'development' }, 'console'],
      ['production, console', { NODE_ENV: 'production', EMAIL_SERVICE_PROVIDER: 'console' }, null],
    ];

    it.each(cases)('%s', async (_name, vars, expected) => {
      Object.assign(process.env as Record<string, string | undefined>, vars);

      expect(emailProvider()).toBe(expected);

      // A send succeeds exactly when a provider is reported.
      const send = sendVerificationEmail({ to: 'a@example.com', verifyUrl: 'https://app/v' });
      if (expected === null) await expect(send).rejects.toThrow();
      else await expect(send).resolves.toBeUndefined();
    });
  });
});
