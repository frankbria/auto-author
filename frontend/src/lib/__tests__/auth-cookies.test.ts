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
      process.env.NEXT_PUBLIC_BETTER_AUTH_URL = 'https://app.autoauthor.app';
      expect(getCookieDomain()).toBe('.app.autoauthor.app');
    });

    it('returns undefined on an unparseable auth URL instead of throwing', () => {
      process.env.BETTER_AUTH_URL = 'not-a-url';
      const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
      expect(getCookieDomain()).toBeUndefined();
      spy.mockRestore();
    });
  });

  // Issue #778: staging (dev.autoauthor.app, api.dev.autoauthor.app) is a shared
  // box under the production domain. A production cookie must never be sent there.
  describe('production cookie scope excludes the staging box (issue #778)', () => {
    const STAGING_HOSTS = ['dev.autoauthor.app', 'api.dev.autoauthor.app'];
    let warnSpy: jest.SpyInstance;

    beforeEach(() => {
      warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    });

    afterEach(() => {
      warnSpy.mockRestore();
    });

    // RFC 6265 §5.1.3 domain-match, as the browser applies it. No Domain
    // attribute means a host-only cookie: sent to the exact issuing host only.
    function cookieReaches(domain: string | undefined, issuingHost: string, host: string) {
      if (domain === undefined) return host === issuingHost;
      const d = domain.replace(/^\./, '');
      return host === d || host.endsWith(`.${d}`);
    }

    it.each([
      ['apex frontend', 'https://autoauthor.app'],
      ['subdomain frontend', 'https://app.autoauthor.app'],
    ])('the %s cookie does not reach either staging host', (_label, url) => {
      process.env.BETTER_AUTH_URL = url;
      const domain = getCookieDomain();
      const issuingHost = new URL(url).hostname;
      for (const host of STAGING_HOSTS) {
        expect(cookieReaches(domain, issuingHost, host)).toBe(false);
      }
    });

    it('never widens an apex host into a sibling-wide domain', () => {
      process.env.BETTER_AUTH_URL = 'https://autoauthor.app';
      expect(getCookieDomain()).toBeUndefined();
    });

    it('a subdomain frontend still shares the cookie with its own api host', () => {
      process.env.BETTER_AUTH_URL = 'https://app.autoauthor.app';
      expect(cookieReaches(getCookieDomain(), 'app.autoauthor.app', 'api.app.autoauthor.app')).toBe(true);
    });

    it('the staging cookie reaches both staging hosts but not the production apex', () => {
      process.env.BETTER_AUTH_URL = 'https://dev.autoauthor.app';
      const domain = getCookieDomain();
      for (const host of STAGING_HOSTS) {
        expect(cookieReaches(domain, 'dev.autoauthor.app', host)).toBe(true);
      }
      expect(cookieReaches(domain, 'dev.autoauthor.app', 'autoauthor.app')).toBe(false);
    });
  });
});
