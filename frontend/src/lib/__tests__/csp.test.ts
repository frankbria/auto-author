/**
 * @jest-environment node
 *
 * CSP builder tests (#190): production script-src must be nonce-based
 * (no unsafe-inline/unsafe-eval), all dead origins (Clerk, Clerk-era
 * captcha, pre-migration domains, unused font CDNs) must be gone, and
 * connect-src must derive from the configured API URL instead of
 * hardcoding localhost/wss.
 */
import { buildCsp } from '../csp';

const NONCE = 'dGVzdC1ub25jZQ==';
const PROD = { isDev: false, apiUrl: 'https://api.dev.autoauthor.app/api/v1' };
const DEV = { isDev: true, apiUrl: 'http://localhost:8000/api/v1' };

function directive(csp: string, name: string): string | undefined {
  return csp
    .split(';')
    .map((d) => d.trim())
    .find((d) => d === name || d.startsWith(`${name} `));
}

describe('buildCsp — production', () => {
  const csp = buildCsp(NONCE, PROD);

  it('script-src is nonce-based with strict-dynamic', () => {
    const scriptSrc = directive(csp, 'script-src')!;
    expect(scriptSrc).toContain(`'nonce-${NONCE}'`);
    expect(scriptSrc).toContain("'strict-dynamic'");
    expect(scriptSrc).toContain("'self'");
  });

  it('drops unsafe-inline and unsafe-eval from script-src (AC1)', () => {
    const scriptSrc = directive(csp, 'script-src')!;
    expect(scriptSrc).not.toContain('unsafe-inline');
    expect(scriptSrc).not.toContain('unsafe-eval');
  });

  it('contains no Clerk or clerk-telemetry origins anywhere (AC2)', () => {
    expect(csp).not.toMatch(/clerk/i);
  });

  it('contains no other dead origins (Clerk-era captcha, old domain, font CDNs)', () => {
    expect(csp).not.toContain('challenges.cloudflare.com');
    expect(csp).not.toContain('auto-author.dev'); // pre-migration API domain
    expect(csp).not.toContain('r2cdn.perplexity.ai');
    expect(csp).not.toContain('fonts.googleapis.com'); // next/font self-hosts
    expect(csp).not.toContain('fonts.gstatic.com');
  });

  it('connect-src derives from the configured API URL — no localhost, no wss (AC3)', () => {
    const connectSrc = directive(csp, 'connect-src')!;
    expect(connectSrc).toContain("'self'");
    expect(connectSrc).toContain('https://api.dev.autoauthor.app');
    expect(connectSrc).not.toContain('localhost');
    expect(csp).not.toContain('wss:');
    expect(csp).not.toMatch(/\bws:/);
  });

  it('keeps localhost connect-src only when the API URL itself is localhost (CI E2E shape)', () => {
    const ciCsp = buildCsp(NONCE, { isDev: false, apiUrl: 'http://localhost:8000/api/v1' });
    expect(directive(ciCsp, 'connect-src')).toContain('http://localhost:8000');
  });

  it('falls back to connect-src self only when the API URL is unparseable', () => {
    const broken = buildCsp(NONCE, { isDev: false, apiUrl: 'not a url' });
    expect(directive(broken, 'connect-src')).toBe("connect-src 'self'");
  });

  it('keeps the hardening directives', () => {
    expect(directive(csp, 'default-src')).toBe("default-src 'self'");
    expect(directive(csp, 'object-src')).toBe("object-src 'none'");
    expect(directive(csp, 'base-uri')).toBe("base-uri 'self'");
    expect(directive(csp, 'form-action')).toBe("form-action 'self'");
    expect(directive(csp, 'frame-ancestors')).toBe("frame-ancestors 'none'");
    expect(directive(csp, 'upgrade-insecure-requests')).toBe('upgrade-insecure-requests');
  });

  it('has no frame-src — default-src self covers framing (no iframes in the app)', () => {
    expect(directive(csp, 'frame-src')).toBeUndefined();
  });

  it('style-src keeps unsafe-inline without a nonce (a style nonce would disable it)', () => {
    const styleSrc = directive(csp, 'style-src')!;
    expect(styleSrc).toContain("'unsafe-inline'");
    expect(styleSrc).not.toContain('nonce-');
  });
});

describe('buildCsp — Sentry connect-src (#334)', () => {
  const DSN = 'https://abc123@o456.ingest.sentry.io/789';

  it('adds the Sentry ingest origin to connect-src when a DSN is configured', () => {
    const csp = buildCsp(NONCE, { ...PROD, sentryDsn: DSN });
    const connectSrc = directive(csp, 'connect-src')!;
    expect(connectSrc).toContain('https://o456.ingest.sentry.io');
    // API origin still present alongside it
    expect(connectSrc).toContain('https://api.dev.autoauthor.app');
  });

  it('adds no Sentry origin when no DSN is configured', () => {
    const csp = buildCsp(NONCE, PROD);
    expect(csp).not.toContain('ingest.sentry.io');
  });

  it('ignores an unparseable DSN (no origin added, no throw)', () => {
    const csp = buildCsp(NONCE, { ...PROD, sentryDsn: 'not a dsn' });
    expect(directive(csp, 'connect-src')).toBe("connect-src 'self' https://api.dev.autoauthor.app");
  });
});

describe('buildCsp — development', () => {
  const csp = buildCsp(NONCE, DEV);

  it('adds unsafe-eval for webpack HMR, but never unsafe-inline', () => {
    const scriptSrc = directive(csp, 'script-src')!;
    expect(scriptSrc).toContain("'unsafe-eval'");
    expect(scriptSrc).not.toContain('unsafe-inline');
  });

  it('allows the HMR websocket', () => {
    expect(directive(csp, 'connect-src')).toContain('ws://localhost:*');
  });

  it('still bans Clerk origins', () => {
    expect(csp).not.toMatch(/clerk/i);
  });
});
