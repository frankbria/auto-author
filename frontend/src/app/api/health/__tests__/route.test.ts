/** @jest-environment node */
import { GET } from '../route';

/**
 * #968 — since #792 nobody can finish signing up without the verification
 * email, and a missing provider is invisible to the user. This route is the one
 * place outside the container that says whether email can be sent.
 */
describe('GET /api/health', () => {
  const ENV_KEYS = ['NODE_ENV', 'EMAIL_SERVICE_PROVIDER', 'EMAIL_SERVICE_API_KEY'] as const;
  const original: Record<string, string | undefined> = {};
  const env = process.env as Record<string, string | undefined>;

  beforeAll(() => ENV_KEYS.forEach((k) => (original[k] = env[k])));
  beforeEach(() => {
    env.NODE_ENV = 'production';
    delete env.EMAIL_SERVICE_PROVIDER;
    delete env.EMAIL_SERVICE_API_KEY;
  });
  afterAll(() =>
    ENV_KEYS.forEach((k) => {
      if (original[k] === undefined) delete env[k];
      else env[k] = original[k];
    })
  );

  it('reports a configured provider by name', async () => {
    env.EMAIL_SERVICE_PROVIDER = 'resend';
    env.EMAIL_SERVICE_API_KEY = 'test-key';

    const response = GET();

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      status: 'ok',
      email: { configured: true, provider: 'resend' },
    });
  });

  it.each([
    ['no provider is set', {}],
    ['the provider is unknown', { EMAIL_SERVICE_PROVIDER: 'mailgun', EMAIL_SERVICE_API_KEY: 'k' }],
    ['the provider has no API key', { EMAIL_SERVICE_PROVIDER: 'resend' }],
  ])('reports email as not configured when %s', async (_case, vars) => {
    Object.assign(env, vars);

    expect(await GET().json()).toEqual({
      status: 'ok',
      email: { configured: false, provider: null },
    });
  });

  it('never returns the key and is not cached', async () => {
    env.EMAIL_SERVICE_PROVIDER = 'resend';
    env.EMAIL_SERVICE_API_KEY = 'test-key';

    const response = GET();

    expect(await response.text()).not.toContain('test-key');
    expect(response.headers.get('cache-control')).toBe('no-store');
  });
});
