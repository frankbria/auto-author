/**
 * Pages an account that has not accepted the current Terms can still reach
 * from the acceptance screen (#961): Settings, to cancel a subscription online
 * as Terms section 7 promises, and the profile, to download its data or delete
 * the account. They open only after the screen's own links are followed, for
 * that account in this tab, so a sign-in that lands on one is still asked.
 */
export const TERMS_EXITS = ['/dashboard/settings', '/profile'];

const KEY = 'terms-exits-open';

/** The account chose an exit link on the acceptance screen. */
export function openTermsExits(userId: string): void {
  try {
    sessionStorage.setItem(KEY, userId);
  } catch {
    // Storage blocked: the exit page asks again, and its links still show.
  }
}

/** Whether `path` is an exit this account opened from the screen. */
export function termsExitOpen(path: string | null, userId: string): boolean {
  if (!TERMS_EXITS.some((exit) => path === exit || path?.startsWith(`${exit}/`))) {
    return false;
  }
  try {
    return sessionStorage.getItem(KEY) === userId;
  } catch {
    return false;
  }
}
