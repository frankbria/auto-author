/**
 * @jest-environment node
 *
 * Middleware route-protection tests (#185): /profile must fail closed like
 * /dashboard — unauthenticated requests redirect to sign-in with a
 * ?redirect deep link back.
 */
import { NextRequest } from 'next/server';
import { middleware } from '../middleware';

const BASE = 'http://localhost:3000';

function requestFor(
  path: string,
  cookieName?: 'better-auth.session_token' | '__Secure-better-auth.session_token'
): NextRequest {
  const req = new NextRequest(`${BASE}${path}`);
  if (cookieName) {
    req.cookies.set(cookieName, 'session-token-value');
  }
  return req;
}

describe('middleware route protection', () => {
  const originalBypass = process.env.BYPASS_AUTH;

  beforeEach(() => {
    process.env.BYPASS_AUTH = 'false';
  });

  afterAll(() => {
    process.env.BYPASS_AUTH = originalBypass;
  });

  it('redirects unauthenticated /profile to sign-in with redirect param', async () => {
    const res = await middleware(requestFor('/profile'));
    expect(res.status).toBe(307);
    const location = new URL(res.headers.get('location')!);
    expect(location.pathname).toBe('/auth/sign-in');
    expect(location.searchParams.get('redirect')).toBe('/profile');
  });

  it('allows /profile through with a session cookie', async () => {
    const res = await middleware(requestFor('/profile', 'better-auth.session_token'));
    expect(res.status).toBe(200);
    expect(res.headers.get('location')).toBeNull();
  });

  it('allows /profile through with the production (HTTPS) session cookie', async () => {
    const res = await middleware(
      requestFor('/profile', '__Secure-better-auth.session_token')
    );
    expect(res.status).toBe(200);
    expect(res.headers.get('location')).toBeNull();
  });

  it('still redirects unauthenticated /dashboard (regression)', async () => {
    const res = await middleware(requestFor('/dashboard'));
    expect(res.status).toBe(307);
    const location = new URL(res.headers.get('location')!);
    expect(location.pathname).toBe('/auth/sign-in');
    expect(location.searchParams.get('redirect')).toBe('/dashboard');
  });

  it('leaves public routes alone without a session', async () => {
    const res = await middleware(requestFor('/'));
    expect(res.status).toBe(200);
    expect(res.headers.get('location')).toBeNull();
  });
});

describe('production bypass guard (#192)', () => {
  const env = process.env as Record<string, string | undefined>;
  const original = {
    BYPASS_AUTH: env.BYPASS_AUTH,
    NODE_ENV: env.NODE_ENV,
    CI: env.CI,
    E2E_ALLOW_BYPASS: env.E2E_ALLOW_BYPASS,
  };

  beforeEach(() => {
    env.BYPASS_AUTH = 'true';
    env.NODE_ENV = 'production';
    delete env.CI;
    delete env.E2E_ALLOW_BYPASS;
  });

  afterAll(() => {
    for (const [key, value] of Object.entries(original)) {
      if (value === undefined) delete env[key];
      else env[key] = value;
    }
  });

  it('throws in production even when CI=true (the #192 hole)', async () => {
    env.CI = 'true';
    await expect(middleware(requestFor('/dashboard'))).rejects.toThrow(
      /FATAL SECURITY ERROR/
    );
  });

  it('throws in production with no exemption flag', async () => {
    await expect(middleware(requestFor('/dashboard'))).rejects.toThrow(
      /FATAL SECURITY ERROR/
    );
  });

  it('allows bypass in production only with E2E_ALLOW_BYPASS=1', async () => {
    env.E2E_ALLOW_BYPASS = '1';
    const res = await middleware(requestFor('/dashboard'));
    expect(res.status).toBe(200);
    expect(res.headers.get('location')).toBeNull();
  });

  it('still bypasses outside production without the flag', async () => {
    env.NODE_ENV = 'test';
    const res = await middleware(requestFor('/dashboard'));
    expect(res.status).toBe(200);
    expect(res.headers.get('location')).toBeNull();
  });

  it('E2E_ALLOW_BYPASS alone is not a bypass — auth still enforced', async () => {
    env.BYPASS_AUTH = 'false';
    env.E2E_ALLOW_BYPASS = '1';
    const res = await middleware(requestFor('/dashboard'));
    expect(res.status).toBe(307);
    expect(new URL(res.headers.get('location')!).pathname).toBe('/auth/sign-in');
  });

  it('only the exact value "1" exempts — loose values still throw', async () => {
    env.E2E_ALLOW_BYPASS = 'true';
    await expect(middleware(requestFor('/dashboard'))).rejects.toThrow(
      /FATAL SECURITY ERROR/
    );
  });
});
