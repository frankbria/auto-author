import { createHash } from 'crypto';

/**
 * SHA-256 of BETTER_AUTH_SECRET values that were published in this public repo
 * (#780). Hashes, never the literals. Keep in sync with backend/app/core/config.py.
 */
export const PUBLISHED_SECRET_SHA256 = new Set<string>([
  'fb89705a13a017d46d0df597a15f0e7d4e5470bb331805dd91db4da49dd6ddfe',
]);

const DEPLOYED = new Set(['production', 'prod', 'staging']);

/** Throws when a deployed environment is running with a published secret. */
export function assertSecretNotPublished(env: NodeJS.ProcessEnv = process.env): void {
  const secret = env.BETTER_AUTH_SECRET;
  if (!secret) return;
  const deployed = [env.ENVIRONMENT, env.NODE_ENV, env.NEXT_PUBLIC_ENVIRONMENT].some((m) =>
    DEPLOYED.has((m ?? '').toLowerCase()),
  );
  if (deployed && PUBLISHED_SECRET_SHA256.has(createHash('sha256').update(secret).digest('hex'))) {
    throw new Error(
      'FATAL: BETTER_AUTH_SECRET is a value that was published in this public repository. ' +
        "Rotate it: python -c 'import secrets; print(secrets.token_urlsafe(64))'",
    );
  }
}
