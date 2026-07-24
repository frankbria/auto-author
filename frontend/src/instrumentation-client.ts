// Client Sentry initialization (#334). Next.js auto-loads this on the client
// (15.3+). Inert unless NEXT_PUBLIC_SENTRY_DSN is set; when set, Sentry installs
// global handlers so client errors reach the service instead of the console.
import * as Sentry from '@sentry/nextjs';

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
if (dsn) {
  Sentry.init({
    dsn,
    environment: process.env.NEXT_PUBLIC_ENVIRONMENT ?? process.env.NODE_ENV,
    tracesSampleRate: 0,
  });
}
