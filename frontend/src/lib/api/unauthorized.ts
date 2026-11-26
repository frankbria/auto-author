import { authClient } from "@/lib/auth-client";
import { signOutUnderway } from "@/lib/sign-out";

/** The one place this module navigates, so tests can watch it. */
export const browser = {
  go: (url: string) => window.location.assign(url),
  reload: () => window.location.reload(),
};

let handling = false;
let reloading = false;

// When this tab last reloaded for TERMS_NOT_ACCEPTED, so a page that still
// disagrees with the backend after a reload is not reloaded in a loop.
const TERMS_RELOAD_KEY = "terms-not-accepted-reload";
const TERMS_RELOAD_PAUSE_MS = 60_000;

/**
 * The backend answered 401: this browser's session is gone, because it
 * expired, was revoked from another device, or the account was closed (#796).
 * The frontend middleware only checks that a cookie exists, so without this
 * the page keeps looking signed in while every request fails.
 *
 * Signing out clears the dead cookie; then the user is sent to sign in, with
 * the page they were on as the place to come back to.
 */
async function handleUnauthorized(): Promise<void> {
  if (handling || typeof window === "undefined") return;
  // An auth page that gets a 401 is already where the user needs to be.
  if (window.location.pathname.startsWith("/auth/")) return;
  // The user is signing out on purpose, and the caller decides where to go (#886).
  if (signOutUnderway()) return;
  handling = true;
  // A failed sign-out must not strand the user on a page that cannot load.
  await Promise.resolve()
    .then(() => authClient.signOut())
    .catch(() => {});
  const here = window.location.pathname + window.location.search;
  browser.go(`/auth/sign-in?redirect=${encodeURIComponent(here)}`);
}

/**
 * The backend refused the Service because the account has not accepted the
 * current Terms (#1316). ProtectedRoute shows the acceptance screen for an
 * older version; a page that did not is from before the Terms changed, so a
 * reload brings the current bundle and session, and with them the screen.
 */
async function handleTermsRefusal(response: Response): Promise<void> {
  if (reloading || typeof window === "undefined") return;
  const body = await response.json().catch(() => null);
  if (body?.detail?.error_code !== "TERMS_NOT_ACCEPTED") return;
  const last = Number(sessionStorage.getItem(TERMS_RELOAD_KEY) ?? 0);
  if (reloading || Date.now() - last < TERMS_RELOAD_PAUSE_MS) return;
  reloading = true;
  sessionStorage.setItem(TERMS_RELOAD_KEY, String(Date.now()));
  browser.reload();
}

/**
 * `fetch` for calls to the backend API. The response is returned unchanged, so
 * callers keep their own error handling; a 401 additionally ends the session
 * in this browser, once, however many requests were in flight.
 */
export async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const response = await fetch(input, init);
  if (response.status === 401) void handleUnauthorized();
  // A clone, so the caller can still read the body.
  if (response.status === 403 && typeof response.clone === "function") {
    void handleTermsRefusal(response.clone());
  }
  return response;
}

export function resetUnauthorizedForTests(): void {
  handling = false;
  reloading = false;
}
