/**
 * Pages an account that has not accepted the current Terms can still reach
 * from the acceptance screen (#961): Settings, to cancel a subscription online
 * as Terms section 7 promises, and the profile, to download its data or delete
 * the account. They open only after the screen's own links are followed, for
 * that account in this tab, until sign-out, so a sign-in that lands on one is
 * still asked.
 */
export const TERMS_EXITS = ['/dashboard/settings', '/profile'];

const KEY = 'terms-exits-open';

// Also kept in memory, so the links still work where storage is blocked
// (client-side navigation keeps this module loaded).
let openFor: string | null = null;

/** The account chose an exit link on the acceptance screen. */
export function openTermsExits(userId: string): void {
  openFor = userId;
  try {
    sessionStorage.setItem(KEY, userId);
  } catch {
    // Storage blocked: the in-memory grant above still holds.
  }
}

/** Sign-out: the next sign-in in this tab is asked again. */
export function closeTermsExits(): void {
  openFor = null;
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    // Storage blocked: nothing was stored there.
  }
}

/** Whether `path` is an exit this account opened from the screen. */
export function termsExitOpen(path: string | null, userId: string): boolean {
  if (!TERMS_EXITS.some((exit) => path === exit || path?.startsWith(`${exit}/`))) {
    return false;
  }
  if (openFor === userId) return true;
  try {
    return sessionStorage.getItem(KEY) === userId;
  } catch {
    return false;
  }
}
