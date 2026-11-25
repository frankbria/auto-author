/**
 * Pages an account that has not accepted the current Terms can still reach
 * from the acceptance screen (#961): Settings, to cancel a subscription online
 * as Terms section 7 promises, and the profile, to download its data or delete
 * the account. They open only after the screen's own links are followed, for
 * that session in this tab, so a sign-in that lands on one is still asked,
 * however the previous session ended (sign-out, expiry, revocation).
 */
export const TERMS_EXITS = ['/dashboard/settings', '/profile'];

const KEY = 'terms-exits-open';

// Also kept in memory, so the links still work where storage is blocked
// (client-side navigation keeps this module loaded).
let openFor: string | null = null;

/** The session chose an exit link on the acceptance screen. */
export function openTermsExits(sessionId: string): void {
  openFor = sessionId;
  try {
    sessionStorage.setItem(KEY, sessionId);
  } catch {
    // Storage blocked: the in-memory grant above still holds.
  }
}

/** Sign-out: drop the grant now rather than leave a dead session's id behind. */
export function closeTermsExits(): void {
  openFor = null;
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    // Storage blocked: nothing was stored there.
  }
}

/** Whether `path` is an exit this session opened from the screen. */
export function termsExitOpen(path: string | null, sessionId: string): boolean {
  if (!TERMS_EXITS.some((exit) => path === exit || path?.startsWith(`${exit}/`))) {
    return false;
  }
  if (openFor === sessionId) return true;
  try {
    return sessionStorage.getItem(KEY) === sessionId;
  } catch {
    return false;
  }
}
