import { sanitizeRedirectPath } from "@/lib/security";

/**
 * The callbackURL for an emailed verification link (#969).
 *
 * better-auth redirects to it on success and appends `?error=` on failure. A
 * protected destination would bounce a signed-out visitor to sign-in and drop
 * the error, so the link lands on the public /auth/verify-email page, which
 * reads it and otherwise forwards to the (same-origin) destination.
 */
export function verificationCallbackURL(destination: string | null): string {
  return `/auth/verify-email?next=${encodeURIComponent(sanitizeRedirectPath(destination))}`;
}
