// Content-Security-Policy builder (#190).
//
// Built per-request in middleware so script-src can carry a nonce — the
// static next.config.ts headers() can't. Next.js reads the nonce from the
// CSP request header and stamps its own inline bootstrap scripts with it
// (requires dynamic rendering; the root layout reads headers() which
// forces that).

const FALLBACK_API_URL = 'http://localhost:8000/api/v1'; // same fallback as bookClient.ts

export interface CspOptions {
  isDev: boolean;
  apiUrl?: string;
  sentryDsn?: string;
}

export function buildCsp(nonce: string, { isDev, apiUrl, sentryDsn }: CspOptions): string {
  // connect-src derives from the configured API origin: prod deploys ship
  // only the real API host, while dev/CI (NEXT_PUBLIC_API_URL=localhost:8000)
  // keep localhost automatically — no generic-env keying (#192).
  let apiOrigin = '';
  try {
    apiOrigin = new URL(apiUrl ?? process.env.NEXT_PUBLIC_API_URL ?? FALLBACK_API_URL).origin;
  } catch {
    // Unparseable API URL: fail closed to same-origin only.
  }

  // Sentry (#334) sends events to its ingest host; add it to connect-src only
  // when a DSN is configured (else the browser CSP blocks event delivery). No
  // DSN => no extra origin, so nothing changes for local/CI.
  let sentryOrigin = '';
  const dsn = sentryDsn ?? process.env.NEXT_PUBLIC_SENTRY_DSN;
  if (dsn) {
    try {
      sentryOrigin = new URL(dsn).origin;
    } catch {
      // Unparseable DSN: skip it (no origin added).
    }
  }

  const directives = [
    "default-src 'self'",
    // 'unsafe-eval' in dev only: webpack HMR evals. Production is nonce +
    // strict-dynamic with no unsafe-* (the official Next.js CSP shape).
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${isDev ? " 'unsafe-eval'" : ''}`,
    // No style nonce: a nonce in style-src makes browsers ignore
    // 'unsafe-inline', which styled-components/Tailwind inline styles need.
    "style-src 'self' 'unsafe-inline'",
    "font-src 'self' data:",
    "img-src 'self' data: https: blob:",
    "media-src 'self'",
    `connect-src 'self'${apiOrigin ? ` ${apiOrigin}` : ''}${sentryOrigin ? ` ${sentryOrigin}` : ''}${isDev ? ' ws://localhost:*' : ''}`,
    "worker-src 'self' blob:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    'upgrade-insecure-requests',
  ];

  return directives.join('; ');
}
