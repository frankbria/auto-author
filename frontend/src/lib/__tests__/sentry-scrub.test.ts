/**
 * What the frontend's Sentry SDK may send (#809).
 *
 * The SDK was never built into an image, so nothing has been sent yet. Turned
 * on as it was, a report would carry the page address with its query string
 * (a password-reset link is `?token=…`), the server's request body and
 * cookies, and the response body that 28 client methods put in their error
 * message.
 */
import * as Sentry from '@sentry/nextjs';
import type { Breadcrumb, ErrorEvent } from '@sentry/nextjs';
import { beforeBreadcrumb, beforeSend } from '../sentry-scrub';

const TOKEN = 'RESET-TOKEN-SENTINEL';
const BODY = 'BODY-SENTINEL the chapter the server sent back';

const send = (event: Partial<ErrorEvent>) => beforeSend(event as ErrorEvent) as ErrorEvent;
const sent = (event: Partial<ErrorEvent>) => JSON.stringify(send(event));

describe('beforeSend', () => {
  it('sends the page address without its query string or fragment', () => {
    const event = send({ request: { url: `https://app.example/reset-password?token=${TOKEN}#${TOKEN}` } });

    expect(event.request?.url).toBe('https://app.example/reset-password');
  });

  it('cuts a fragment that stands alone, where a sign-in redirect can put a token', () => {
    const event = send({ request: { url: `https://app.example/auth/callback#access_token=${TOKEN}` } });

    expect(event.request?.url).toBe('https://app.example/auth/callback');
  });

  it('drops the query string, the request body and the cookies the server SDK attaches', () => {
    const event = send({
      request: {
        url: 'https://app.example/api/auth/sign-in/email',
        query_string: `token=${TOKEN}`,
        data: { password: TOKEN },
        cookies: { 'better-auth.session_token': TOKEN },
      },
    });

    expect(event.request).toEqual({ url: 'https://app.example/api/auth/sign-in/email' });
  });

  it('removes the cookie and authorization headers and the query of the referer', () => {
    const event = send({
      request: {
        headers: {
          Cookie: `better-auth.session_token=${TOKEN}`,
          authorization: `Bearer ${TOKEN}`,
          Referer: `https://app.example/reset-password?token=${TOKEN}`,
          'User-Agent': 'jest',
        },
      },
    });

    expect(event.request?.headers).toEqual({
      Referer: 'https://app.example/reset-password',
      'User-Agent': 'jest',
    });
  });

  it('cuts the response body out of a client error and keeps what failed and the status', () => {
    const event = send({
      exception: { values: [{ type: 'Error', value: `Failed to save chapter content: 500 {"detail":"${BODY}"}` }] },
    });

    expect(event.exception?.values?.[0].value).toBe('Failed to save chapter content: 500');
  });

  it('cuts it on every exception in a chain', () => {
    const text = sent({
      exception: {
        values: [
          { type: 'Error', value: `Failed to get TOC: 502 ${BODY}` },
          { type: 'Error', value: `Failed to create book: 500 ${BODY}\nand a second line of ${BODY}` },
        ],
      },
    });

    expect(text).not.toContain('BODY-SENTINEL');
  });

  it('takes the query string out of an address inside a message', () => {
    const text = sent({
      message: `Navigation to https://app.example/verify?token=${TOKEN} failed`,
      exception: { values: [{ type: 'TypeError', value: `Failed to fetch https://api.example/books?search=${TOKEN}` }] },
    });

    expect(text).not.toContain(TOKEN);
    expect(text).toContain('https://api.example/books');
  });

  it('takes it out of an address without a host, and a token out of a fragment', () => {
    const event = send({
      exception: {
        values: [
          { type: 'Error', value: `Cannot navigate to /auth/reset-password?token=${TOKEN} from here` },
          { type: 'Error', value: `Bad redirect (/auth/callback#access_token=${TOKEN}&state=1)` },
        ],
      },
    });

    expect(event.exception?.values?.map((failure) => failure.value)).toEqual([
      'Cannot navigate to /auth/reset-password from here',
      'Bad redirect (/auth/callback)',
    ]);
  });

  it.each([
    "Cannot read properties of undefined (reading 'chapters')",
    'a?.b is not a function',
    'Why did this fail? Nobody knows = nothing to cut',
  ])('leaves an ordinary error message as it is: %s', (value) => {
    expect(send({ exception: { values: [{ type: 'TypeError', value }] } }).exception?.values?.[0].value).toBe(value);
  });

  it('still sends the event', () => {
    expect(send({ message: 'Performance regression: toc_generation' })).toEqual({
      message: 'Performance regression: toc_generation',
    });
  });
});

describe('beforeBreadcrumb', () => {
  const crumb = (breadcrumb: Breadcrumb) => beforeBreadcrumb(breadcrumb);

  it('drops console output, which is free text', () => {
    expect(crumb({ category: 'console', message: `saved ${BODY}` })).toBeNull();
  });

  it.each(['fetch', 'xhr'])('keeps a %s request without its query string', (category) => {
    const kept = crumb({
      category,
      data: { method: 'GET', url: `https://api.example/api/v1/books?search=${TOKEN}`, status_code: 200 },
    });

    expect(kept?.data).toEqual({ method: 'GET', url: 'https://api.example/api/v1/books', status_code: 200 });
  });

  it('keeps a navigation without the query string of either address', () => {
    const kept = crumb({
      category: 'navigation',
      data: { from: `/reset-password?token=${TOKEN}`, to: `/dashboard?welcome=${TOKEN}#${TOKEN}` },
    });

    expect(kept?.data).toEqual({ from: '/reset-password', to: '/dashboard' });
  });

  it.each(['ui.click', 'ui.input'])('keeps where a %s landed without the attributes that hold user text', (category) => {
    // BookCard has title={book.title}; ChapterTab has aria-label="Open chapter …".
    const kept = crumb({
      category,
      message: `div.card > h3.truncate[title="${BODY} "] > it has brackets"] > span.label`,
    });

    expect(kept?.message).toBe('div.card > h3.truncate');
  });

  it('leaves a breadcrumb with no address alone', () => {
    const click: Breadcrumb = { category: 'ui.click', message: 'button.primary' };

    expect(crumb(click)).toEqual(click);
  });
});

describe('both runtimes start the SDK with the scrubbers', () => {
  const env = { ...process.env };
  const init = Sentry.init as jest.Mock;

  beforeEach(() => {
    init.mockClear();
    process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://key@sentry.invalid/1';
  });

  afterEach(() => {
    process.env = { ...env };
  });

  it('the browser', async () => {
    await import('@/instrumentation-client'); // starts the SDK when it is first loaded

    expect(init).toHaveBeenCalledWith(expect.objectContaining({ beforeSend, beforeBreadcrumb }));
  });

  it('the server', async () => {
    process.env.NEXT_RUNTIME = 'edge';
    const { register } = await import('@/instrumentation');
    await register();

    expect(init).toHaveBeenCalledWith(expect.objectContaining({ beforeSend, beforeBreadcrumb }));
  });
});
