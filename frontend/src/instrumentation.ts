// Server/edge Sentry initialization (#334).
//
// Inert unless NEXT_PUBLIC_SENTRY_DSN is set, so CI/local/tests are unaffected.
// Next.js runs register() once per server/edge runtime; onRequestError routes
// server-side (incl. React Server Component) errors to Sentry.
import * as Sentry from '@sentry/nextjs';
import { assertSecretNotPublished } from '@/lib/auth-secret';

export async function register() {
  // Refuse to boot a deployed server on a secret published in the repo (#780).
  if (process.env.NEXT_RUNTIME === 'nodejs') assertSecretNotPublished();

  const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
  if (!dsn) return;

  if (process.env.NEXT_RUNTIME === 'nodejs' || process.env.NEXT_RUNTIME === 'edge') {
    Sentry.init({
      dsn,
      environment: process.env.NEXT_PUBLIC_ENVIRONMENT ?? process.env.NODE_ENV,
      // Errors only by default (no tracing spend); enable later via config.
      tracesSampleRate: 0,
    });
  }
}

export const onRequestError = Sentry.captureRequestError;
