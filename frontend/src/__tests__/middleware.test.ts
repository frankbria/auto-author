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

describe('bypass requires E2E_ALLOW_BYPASS in every environment (#272)', () => {
  const env = process.env as Record<string, string | undefined>;
  const original = {
    BYPASS_AUTH: env.BYPASS_AUTH,
    NODE_ENV: env.NODE_ENV,
    E2E_ALLOW_BYPASS: env.E2E_ALLOW_BYPASS,
  };

  beforeEach(() => {
    env.BYPASS_AUTH = 'true';
    delete env.E2E_ALLOW_BYPASS;
  });

  afterAll(() => {
    for (const [key, value] of Object.entries(original)) {
      if (value === undefined) delete env[key];
      else env[key] = value;
    }
  });

  it.each(['test', 'development', 'staging'])(
    'does not bypass with BYPASS_AUTH=true alone and NODE_ENV=%s',
    async (nodeEnv) => {
      env.NODE_ENV = nodeEnv;
      const res = await middleware(requestFor('/dashboard'));
      expect(res.status).toBe(307);
      expect(new URL(res.headers.get('location')!).pathname).toBe('/auth/sign-in');
    }
  );

  it('does not bypass with BYPASS_AUTH=true alone and NODE_ENV unset', async () => {
    delete env.NODE_ENV;
    const res = await middleware(requestFor('/dashboard'));
    expect(res.status).toBe(307);
    expect(new URL(res.headers.get('location')!).pathname).toBe('/auth/sign-in');
  });

  it('bypasses outside production when the flag is also set', async () => {
    env.NODE_ENV = 'test';
    env.E2E_ALLOW_BYPASS = '1';
    const res = await middleware(requestFor('/dashboard'));
    expect(res.status).toBe(200);
    expect(res.headers.get('location')).toBeNull();
  });

  it('only the exact value "1" enables the non-production bypass', async () => {
    env.NODE_ENV = 'test';
    env.E2E_ALLOW_BYPASS = 'true';
    const res = await middleware(requestFor('/dashboard'));
    expect(res.status).toBe(307);
    expect(new URL(res.headers.get('location')!).pathname).toBe('/auth/sign-in');
  });

  it('only the exact value "true" arms BYPASS_AUTH — case variants do not bypass', async () => {
    env.NODE_ENV = 'test';
    env.E2E_ALLOW_BYPASS = '1';
    env.BYPASS_AUTH = 'TRUE';
    const res = await middleware(requestFor('/dashboard'));
    expect(res.status).toBe(307);
    expect(new URL(res.headers.get('location')!).pathname).toBe('/auth/sign-in');
  });
});

describe('CSP header (#190)', () => {
  const env = process.env as Record<string, string | undefined>;
  const originalBypass = env.BYPASS_AUTH;
  const originalFlag = env.E2E_ALLOW_BYPASS;
  const originalNodeEnv = env.NODE_ENV;

  beforeEach(() => {
    env.BYPASS_AUTH = 'false';
    delete env.E2E_ALLOW_BYPASS;
  });

  afterAll(() => {
    if (originalBypass === undefined) delete env.BYPASS_AUTH;
    else env.BYPASS_AUTH = originalBypass;
    if (originalFlag === undefined) delete env.E2E_ALLOW_BYPASS;
    else env.E2E_ALLOW_BYPASS = originalFlag;
    if (originalNodeEnv === undefined) delete env.NODE_ENV;
    else env.NODE_ENV = originalNodeEnv;
  });

  it('sets a nonce-based CSP with no unsafe-inline/unsafe-eval and no Clerk origins', async () => {
    const res = await middleware(requestFor('/'));
    const csp = res.headers.get('content-security-policy')!;
    const scriptSrc = csp.split(';').find((d) => d.trim().startsWith('script-src'))!;
    expect(scriptSrc).toMatch(/'nonce-[A-Za-z0-9+/=]+'/);
    expect(scriptSrc).toContain("'strict-dynamic'");
    expect(scriptSrc).not.toContain('unsafe-inline');
    expect(scriptSrc).not.toContain('unsafe-eval');
    expect(csp).not.toMatch(/clerk/i);
  });

  it('sets the CSP on authenticated protected routes', async () => {
    const res = await middleware(requestFor('/dashboard', 'better-auth.session_token'));
    expect(res.status).toBe(200);
    expect(res.headers.get('content-security-policy')).toMatch(/'nonce-/);
  });

  it('sets the CSP on the BYPASS_AUTH early-return path', async () => {
    env.BYPASS_AUTH = 'true';
    env.E2E_ALLOW_BYPASS = '1'; // required in every environment since #272
    env.NODE_ENV = 'test'; // explicit — must not be production for this path
    const res = await middleware(requestFor('/dashboard'));
    expect(res.status).toBe(200);
    expect(res.headers.get('content-security-policy')).toMatch(/'nonce-/);
  });

  it('forwards x-nonce to the app matching the CSP nonce, overwriting any client-sent value', async () => {
    const req = requestFor('/');
    req.headers.set('x-nonce', 'attacker-controlled');
    const res = await middleware(req);
    // NextResponse.next({request}) exposes overridden request headers as
    // x-middleware-request-* response headers.
    const forwarded = res.headers.get('x-middleware-request-x-nonce')!;
    expect(forwarded).not.toBe('attacker-controlled');
    const cspNonce = res.headers
      .get('content-security-policy')!
      .match(/'nonce-([^']+)'/)![1];
    expect(forwarded).toBe(cspNonce);
  });

  it('generates a fresh nonce per request', async () => {
    const nonceOf = async () =>
      (await middleware(requestFor('/'))).headers
        .get('content-security-policy')!
        .match(/'nonce-([^']+)'/)![1];
    expect(await nonceOf()).not.toBe(await nonceOf());
  });
});
