// Cookieless page analytics for the public pages, through a self-hosted
// GoatCounter (https://www.goatcounter.com). GoatCounter sets no cookie and
// stores no personal identifier, so it needs no cookie banner.
//
// Off unless GOATCOUNTER_URL names the GoatCounter site, e.g.
// https://stats.autoauthor.app. It is a server-side variable read on each
// request (by the page and by the CSP in middleware), not a NEXT_PUBLIC_ one,
// so turning analytics on or off needs no rebuild of the image.

/**
 * The origin of the configured GoatCounter site, or null when analytics is off
 * or the value is not a usable URL. Only https is accepted, apart from a
 * localhost address for local testing, so a typo can't send page views over
 * plain http.
 */
export function analyticsOrigin(raw: string | undefined = process.env.GOATCOUNTER_URL): string | null {
  const value = raw?.trim();
  if (!value) return null;
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    return null;
  }
  const local = url.hostname === 'localhost' || url.hostname === '127.0.0.1';
  if (url.protocol !== 'https:' && !(local && url.protocol === 'http:')) return null;
  return url.origin;
}
