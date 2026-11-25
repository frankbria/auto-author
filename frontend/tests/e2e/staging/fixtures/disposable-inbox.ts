/**
 * A throwaway inbox on mail.tm for the staging verification-email check (#971).
 *
 * mail.tm's API is public and needs no key, so the check runs with no new
 * secret. Plain `fetch` (injectable for the unit test) and no Playwright import,
 * so jest can load it: `src/__tests__/StagingDisposableInbox.test.ts`.
 *
 * Every failure names mail.tm, so a red run caused by the inbox service is not
 * mistaken for the app failing to send.
 */

export const MAIL_TM_API = 'https://api.mail.tm';

export interface Inbox {
  id: string;
  address: string;
  token: string;
}

export interface InboxMessage {
  text: string;
  html: string[];
}

type Fetch = typeof fetch;

const REQUEST_TIMEOUT_MS = 15_000;

/** A failed mail.tm request; `status` is 0 when it timed out or never answered. */
class MailTmError extends Error {
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
  }
}

async function call<T>(
  fetchImpl: Fetch,
  method: string,
  path: string,
  { token, body }: { token?: string; body?: unknown } = {}
): Promise<T> {
  // ld+json: the collection shape (`hydra:member`) this module reads.
  const headers: Record<string, string> = { Accept: 'application/ld+json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;
  let res: Response;
  try {
    res = await fetchImpl(`${MAIL_TM_API}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch (error) {
    // By name: AbortSignal.timeout rejects with a DOMException, not always an Error.
    const timedOut = (error as { name?: string } | null)?.name === 'TimeoutError';
    throw new MailTmError(
      `mail.tm ${method} ${path}: ${timedOut ? `timed out after ${REQUEST_TIMEOUT_MS}ms` : String(error)}`,
      0
    );
  }
  if (!res.ok) {
    const detail = (await res.text().catch(() => '')).slice(0, 200);
    throw new MailTmError(`mail.tm ${method} ${path}: ${res.status} ${detail}`.trim(), res.status);
  }
  if (res.status === 204) return undefined as T;
  try {
    return (await res.json()) as T;
  } catch (error) {
    // Headers arrived but the body broke off or timed out: as transient as no answer.
    throw new MailTmError(`mail.tm ${method} ${path}: unreadable body (${String(error)})`, 0);
  }
}

/** Worth polling again: rate-limited, a server error, or no answer at all. */
const transient = (error: unknown) =>
  error instanceof MailTmError && (error.status === 0 || error.status === 429 || error.status >= 500);

const random = () => Math.random().toString(36).slice(2, 12);

/** Creates a fresh mailbox on mail.tm's first active domain and signs in to it. */
export async function createInbox(fetchImpl: Fetch = fetch): Promise<Inbox> {
  const domains = await call<{ 'hydra:member': { domain: string; isActive: boolean }[] }>(
    fetchImpl,
    'GET',
    '/domains'
  );
  const domain = domains['hydra:member'].find((d) => d.isActive)?.domain;
  if (!domain) throw new Error('mail.tm offers no active domain');

  const credentials = { address: `aa-verify-${random()}@${domain}`, password: random() + random() };
  const { id } = await call<{ id: string }>(fetchImpl, 'POST', '/accounts', { body: credentials });
  const { token } = await call<{ token: string }>(fetchImpl, 'POST', '/token', { body: credentials });
  return { id, address: credentials.address, token };
}

/** Polls the inbox until a message with `subject` arrives and returns its bodies. */
export async function waitForMessage(
  inbox: Inbox,
  { subject, timeoutMs, intervalMs = 3000 }: { subject: string; timeoutMs: number; intervalMs?: number },
  fetchImpl: Fetch = fetch
): Promise<InboxMessage> {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    // One mail.tm blip in a two-minute poll must not fail the check: only an
    // error that would repeat (a refused token) ends it early.
    try {
      const list = await call<{ 'hydra:member': { id: string; subject: string }[] }>(
        fetchImpl,
        'GET',
        '/messages',
        { token: inbox.token }
      );
      const found = list['hydra:member'].find((m) => m.subject === subject);
      if (found) {
        const { text, html } = await call<Partial<InboxMessage>>(
          fetchImpl,
          'GET',
          `/messages/${found.id}`,
          { token: inbox.token }
        );
        return { text: text ?? '', html: html ?? [] };
      }
    } catch (error) {
      if (!transient(error) || Date.now() >= deadline) throw error;
    }
    if (Date.now() >= deadline) {
      throw new Error(
        `No "${subject}" email reached the mail.tm inbox ${inbox.address} within ${timeoutMs}ms`
      );
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}

/** Deletes the mailbox. */
export async function deleteInbox(inbox: Inbox, fetchImpl: Fetch = fetch): Promise<void> {
  await call(fetchImpl, 'DELETE', `/accounts/${inbox.id}`, { token: inbox.token });
}

const LINK = /https?:\/\/[^\s"'<>]+\/api\/auth\/verify-email\?[^\s"'<>]+/;

/**
 * The verification link in the email, from the text part or else the HTML href.
 * Throws unless it is on `origin`: the spec opens it in a browser, and an email
 * is input, so only a link to the site under test is followed.
 */
export function extractVerificationLink(message: InboxMessage, origin: string): string {
  const raw =
    LINK.exec(message.text)?.[0] ?? LINK.exec(message.html.join('\n'))?.[0]?.replace(/&amp;/g, '&');
  if (!raw) throw new Error('The email has no verification link');
  if (new URL(raw).origin !== origin) {
    throw new Error(`The verification link is not on ${origin}: ${new URL(raw).origin}`);
  }
  return raw;
}
