/**
 * The Terms of Service version a new account accepts (#789): the date /terms
 * last changed. /terms shows it as "Last updated", so change it with the copy.
 * An account whose recorded version is older is asked to accept again (#961).
 */
export const TERMS_VERSION = '2026-11-25';

/** TERMS_VERSION as /terms and the acceptance screen show it, e.g. "November 25, 2026". */
export const TERMS_LAST_UPDATED = new Date(`${TERMS_VERSION}T00:00:00Z`).toLocaleDateString(
  'en-US',
  { dateStyle: 'long', timeZone: 'UTC' }
);

/**
 * Whether an account's recorded Terms version is the current one (#961).
 * Versions are ISO dates, so they compare as strings. A missing version, as on
 * an account created before #789, counts as older.
 */
export function acceptedCurrentTerms(version: unknown): boolean {
  return typeof version === 'string' && version >= TERMS_VERSION;
}
