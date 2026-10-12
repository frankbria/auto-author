/**
 * What the frontend's Sentry SDK may send (#809). Used by the browser's and
 * the server's `Sentry.init`.
 *
 * Without these a report carries the page address with its query string (a
 * password-reset link is `?token=…`), the server's request body and cookies,
 * and the response body that the API client puts in its error messages.
 */
import type { Breadcrumb, ErrorEvent } from '@sentry/nextjs';

const withoutQuery = (address: string) => address.split(/[?#]/)[0];

// An address inside a sentence: keep it up to its `?` or `#`.
const withoutQueries = (text: string) => text.replace(/(https?:\/\/[^\s"'<>?#]+)[?#][^\s"'<>]*/g, '$1');

// bookClient throws `Failed to <do something>: <status> <response body>`.
const withoutResponseBody = (message: string) => message.replace(/^([^\n]{0,80}?: \d{3})\s[\s\S]*$/, '$1');

const SENSITIVE_HEADERS = ['cookie', 'authorization'];

export function beforeSend(event: ErrorEvent): ErrorEvent | null {
  const request = event.request;
  if (request) {
    if (request.url) request.url = withoutQuery(request.url);
    delete request.query_string;
    delete request.data;
    delete request.cookies;
    for (const [name, value] of Object.entries(request.headers ?? {})) {
      if (SENSITIVE_HEADERS.includes(name.toLowerCase())) delete request.headers![name];
      else if (name.toLowerCase() === 'referer') request.headers![name] = withoutQuery(value);
    }
  }
  for (const failure of event.exception?.values ?? []) {
    if (failure.value) failure.value = withoutQueries(withoutResponseBody(failure.value));
  }
  if (event.message) event.message = withoutQueries(event.message);
  return event;
}

export function beforeBreadcrumb(breadcrumb: Breadcrumb): Breadcrumb | null {
  // Console output is free text: whatever the page logged, a chapter included.
  if (breadcrumb.category === 'console') return null;
  // A click is recorded as the element's path with its title, aria-label and
  // alt, which here hold book and chapter titles and the user's name. The SDK
  // does not escape them, so cut at the first one rather than try to parse.
  if (breadcrumb.category?.startsWith('ui.') && breadcrumb.message) {
    breadcrumb.message = breadcrumb.message.split('[')[0].replace(/ > $/, '');
  }
  for (const key of ['url', 'from', 'to']) {
    const address = breadcrumb.data?.[key];
    if (typeof address === 'string') breadcrumb.data![key] = withoutQuery(address);
  }
  return breadcrumb;
}
