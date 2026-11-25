/**
 * @jest-environment node
 */
import {
  createInbox,
  deleteInbox,
  extractVerificationLink,
  waitForMessage,
  type Inbox,
} from '../../tests/e2e/staging/fixtures/disposable-inbox';

/**
 * #971: the staging check reads the verification email from a mail.tm inbox.
 * mail.tm itself is exercised by the staging run; these pin what the helper
 * does with its answers, above all that it only ever follows a staging link.
 */

const ORIGIN = 'https://dev.autoauthor.app';
const LINK = `${ORIGIN}/api/auth/verify-email?token=abc.def&callbackURL=%2Fauth%2Fverify-email%3Fnext%3D%252Fdashboard`;

type Call = { url: string; init?: RequestInit };

/** A fetch that answers each call from `routes` (method + path) and records it. */
function fakeFetch(routes: Record<string, (call: Call) => Response>) {
  const calls: Call[] = [];
  const impl = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const call = { url, init };
    calls.push(call);
    const key = `${init?.method ?? 'GET'} ${new URL(url).pathname}`;
    const route = routes[key];
    if (!route) throw new Error(`unexpected request ${key}`);
    return route(call);
  }) as typeof fetch;
  return { impl, calls };
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });

const inbox: Inbox = { id: 'acc1', address: 'x@euploading.com', token: 'tok' };

describe('extractVerificationLink', () => {
  it('returns the staging link from the text body', () => {
    const text = `Open this link to finish creating your Auto Author account:\n${LINK}\n\nThe link expires in one hour.`;
    expect(extractVerificationLink({ text, html: [] }, ORIGIN)).toBe(LINK);
  });

  it('falls back to the html href, decoding entities', () => {
    const html = [`<p><a href="${LINK.replace('&', '&amp;')}">Verify my email address</a></p>`];
    expect(extractVerificationLink({ text: '', html }, ORIGIN)).toBe(LINK);
  });

  it('refuses a link on any other origin', () => {
    const text = 'https://evil.example/api/auth/verify-email?token=abc';
    expect(() => extractVerificationLink({ text, html: [] }, ORIGIN)).toThrow(
      /not on https:\/\/dev\.autoauthor\.app/
    );
  });

  it('says so when the email carries no verification link', () => {
    expect(() => extractVerificationLink({ text: 'hello', html: [] }, ORIGIN)).toThrow(
      /no verification link/
    );
  });
});

describe('createInbox', () => {
  it('creates an account on the first active domain and signs in to it', async () => {
    const { impl, calls } = fakeFetch({
      'GET /domains': () =>
        json({
          'hydra:member': [
            { domain: 'old.example', isActive: false },
            { domain: 'euploading.com', isActive: true },
          ],
        }),
      'POST /accounts': () => json({ id: 'acc1' }, 201),
      'POST /token': () => json({ token: 'tok', id: 'acc1' }),
    });

    const created = await createInbox(impl);

    expect(created.id).toBe('acc1');
    expect(created.token).toBe('tok');
    expect(created.address).toMatch(/^aa-verify-[a-z0-9]+@euploading\.com$/);
    const account = JSON.parse(String(calls[1].init?.body));
    const token = JSON.parse(String(calls[2].init?.body));
    expect(account.address).toBe(created.address);
    expect(token).toEqual(account);
    // Plain application/json makes mail.tm answer a bare array, with no `hydra:member`.
    expect(new Headers(calls[0].init?.headers).get('Accept')).toBe('application/ld+json');
  });

  it('names mail.tm when it refuses, so a red run is not blamed on the app', async () => {
    const { impl } = fakeFetch({
      'GET /domains': () => json({ 'hydra:member': [{ domain: 'd.example', isActive: true }] }),
      'POST /accounts': () => new Response('slow down', { status: 429 }),
    });
    await expect(createInbox(impl)).rejects.toThrow(/mail\.tm POST \/accounts: 429/);
  });

  it('fails clearly when mail.tm offers no active domain', async () => {
    const { impl } = fakeFetch({
      'GET /domains': () => json({ 'hydra:member': [] }),
    });
    await expect(createInbox(impl)).rejects.toThrow(/no active domain/);
  });
});

describe('waitForMessage', () => {
  it('polls until the subject arrives, then returns that message with the token', async () => {
    let polls = 0;
    const { impl, calls } = fakeFetch({
      'GET /messages': () => {
        polls += 1;
        return json({
          'hydra:member':
            polls < 2
              ? []
              : [
                  { id: 'm0', subject: 'Something else' },
                  { id: 'm1', subject: 'Verify your email address' },
                ],
        });
      },
      'GET /messages/m1': () => json({ text: LINK, html: [] }),
    });

    const message = await waitForMessage(
      inbox,
      { subject: 'Verify your email address', timeoutMs: 1000, intervalMs: 1 },
      impl
    );

    expect(message).toEqual({ text: LINK, html: [] });
    expect(polls).toBe(2);
    for (const call of calls) {
      expect(new Headers(call.init?.headers).get('Authorization')).toBe('Bearer tok');
    }
  });

  it('rides out a transient mail.tm error (429, 5xx) while polling', async () => {
    let polls = 0;
    const { impl } = fakeFetch({
      'GET /messages': () => {
        polls += 1;
        if (polls === 1) return new Response('slow down', { status: 429 });
        if (polls === 2) return new Response('oops', { status: 502 });
        return json({ 'hydra:member': [{ id: 'm1', subject: 'Verify your email address' }] });
      },
      'GET /messages/m1': () => json({ text: LINK, html: [] }),
    });
    const message = await waitForMessage(
      inbox,
      { subject: 'Verify your email address', timeoutMs: 1000, intervalMs: 1 },
      impl
    );
    expect(message.text).toBe(LINK);
    expect(polls).toBe(3);
  });

  it('rides out a transient error fetching the message body too', async () => {
    let bodies = 0;
    const { impl } = fakeFetch({
      'GET /messages': () =>
        json({ 'hydra:member': [{ id: 'm1', subject: 'Verify your email address' }] }),
      'GET /messages/m1': () => {
        bodies += 1;
        return bodies === 1 ? new Response('oops', { status: 502 }) : json({ text: LINK, html: [] });
      },
    });
    const message = await waitForMessage(
      inbox,
      { subject: 'Verify your email address', timeoutMs: 1000, intervalMs: 1 },
      impl
    );
    expect(message.text).toBe(LINK);
    expect(bodies).toBe(2);
  });

  it('treats a body that breaks off mid-read as transient', async () => {
    let bodies = 0;
    const { impl } = fakeFetch({
      'GET /messages': () =>
        json({ 'hydra:member': [{ id: 'm1', subject: 'Verify your email address' }] }),
      'GET /messages/m1': () => {
        bodies += 1;
        return bodies === 1 ? new Response('{"text": "cut', { status: 200 }) : json({ text: LINK, html: [] });
      },
    });
    const message = await waitForMessage(
      inbox,
      { subject: 'Verify your email address', timeoutMs: 1000, intervalMs: 1 },
      impl
    );
    expect(message.text).toBe(LINK);
  });

  it('still fails at once on a refused token', async () => {
    const { impl } = fakeFetch({
      'GET /messages': () => new Response('no', { status: 401 }),
    });
    await expect(
      waitForMessage(inbox, { subject: 'Verify your email address', timeoutMs: 1000, intervalMs: 1 }, impl)
    ).rejects.toThrow(/mail\.tm GET \/messages: 401/);
  });

  it('gives every request a timeout, and names mail.tm when one fires', async () => {
    const seen: (AbortSignal | null | undefined)[] = [];
    const impl = (async (_input: RequestInfo | URL, init?: RequestInit) => {
      seen.push(init?.signal);
      throw new DOMException('The operation was aborted due to timeout', 'TimeoutError');
    }) as typeof fetch;
    await expect(deleteInbox(inbox, impl)).rejects.toThrow(/mail\.tm DELETE \/accounts\/acc1: timed out/);
    expect(seen[0]).toBeInstanceOf(AbortSignal);
  });

  it('times out naming the subject and the wait', async () => {
    const { impl } = fakeFetch({
      'GET /messages': () => json({ 'hydra:member': [] }),
    });
    await expect(
      waitForMessage(inbox, { subject: 'Verify your email address', timeoutMs: 20, intervalMs: 5 }, impl)
    ).rejects.toThrow(/No "Verify your email address" email reached .* within 20ms/);
  });
});

describe('deleteInbox', () => {
  it('deletes the account with its token', async () => {
    const { impl, calls } = fakeFetch({
      'DELETE /accounts/acc1': () => new Response(null, { status: 204 }),
    });
    await deleteInbox(inbox, impl);
    expect(calls).toHaveLength(1);
    expect(new Headers(calls[0].init?.headers).get('Authorization')).toBe('Bearer tok');
  });
});
