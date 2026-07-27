import { getCookieDomain, getDefaultCookieAttributes } from '@/lib/auth-cookies';

describe('auth cookie attributes (issue #339)', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv };
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  describe('getDefaultCookieAttributes', () => {
    it('uses sameSite "lax" so the session cookie is not sent on cross-site requests', () => {
      // The backend authenticates from request.cookies, and multipart uploads are
      // CORS-"simple" (no preflight) — with "none" a cross-site form POST would
      // ride the victim's cookie and execute server-side.
      expect(getDefaultCookieAttributes().sameSite).toBe('lax');
    });

    it('keeps the cookie httpOnly and secure', () => {
      const attrs = getDefaultCookieAttributes();
      expect(attrs.httpOnly).toBe(true);
      expect(attrs.secure).toBe(true);
    });

    it('carries the cookie domain so api.<host> still receives it', () => {
      process.env.BETTER_AUTH_URL = 'https://dev.autoauthor.app';
      expect(getDefaultCookieAttributes().domain).toBe('.dev.autoauthor.app');
    });
  });

  describe('getCookieDomain', () => {
    it('returns undefined on localhost so the browser scopes the cookie itself', () => {
      process.env.BETTER_AUTH_URL = 'http://localhost:3000';
      expect(getCookieDomain()).toBeUndefined();
    });

    it('returns undefined when no auth URL is configured', () => {
      delete process.env.BETTER_AUTH_URL;
      delete process.env.NEXT_PUBLIC_BETTER_AUTH_URL;
      expect(getCookieDomain()).toBeUndefined();
    });

    it('prefixes a dot so the cookie is shared with subdomains', () => {
      process.env.BETTER_AUTH_URL = 'https://dev.autoauthor.app';
      expect(getCookieDomain()).toBe('.dev.autoauthor.app');
    });

    it('falls back to NEXT_PUBLIC_BETTER_AUTH_URL', () => {
      delete process.env.BETTER_AUTH_URL;
      process.env.NEXT_PUBLIC_BETTER_AUTH_URL = 'https://autoauthor.app';
      expect(getCookieDomain()).toBe('.autoauthor.app');
    });

    it('returns undefined on an unparseable auth URL instead of throwing', () => {
      process.env.BETTER_AUTH_URL = 'not-a-url';
      const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
      expect(getCookieDomain()).toBeUndefined();
      spy.mockRestore();
    });
  });
});
