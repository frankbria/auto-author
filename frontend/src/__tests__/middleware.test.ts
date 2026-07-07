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
