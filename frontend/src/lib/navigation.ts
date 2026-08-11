/**
 * Full-page navigation helpers.
 *
 * These wrap `window.location` for one reason: it cannot be stubbed in tests.
 * jsdom 26 (shipped with jest 30) defines `window.location` as
 * `configurable: false` to match real browsers, and `href` has no setter on
 * `Location.prototype`, so neither `Object.defineProperty(window, 'location', …)`
 * nor `jest.spyOn(window.location, 'assign')` works — both throw. Assigning
 * `href` under jsdom attempts a real navigation that jsdom declines, so a test
 * cannot even observe the attempt after the fact.
 *
 * Routing every full-page navigation through this module gives tests a seam they
 * can mock (`jest.mock('@/lib/navigation')`) while leaving runtime behaviour
 * byte-identical.
 *
 * Use Next's `useRouter()` for in-app route changes. These are only for the
 * cases that genuinely need a full document load or reload.
 */

/** Navigate the browser to `url`, replacing the current document. */
export function navigateTo(url: string): void {
  window.location.assign(url);
}

/** Reload the current document. */
export function reloadPage(): void {
  window.location.reload();
}
