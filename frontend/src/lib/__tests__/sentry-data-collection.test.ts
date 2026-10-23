/**
 * @jest-environment node
 */
/**
 * What a real server error report carries (#1111). The Jest mock of
 * `@sentry/nextjs` builds no events, so this test loads the real server SDK,
 * runs the real `register()` against a DSN on a local HTTP server, and reads
 * the envelope the SDK sends. v11 collects IP, cookies, forwarding headers and
 * bodies unless `dataCollection` says otherwise.
 */
import { createServer, type Server } from 'http';
import type { AddressInfo } from 'net';
import type { ErrorEvent } from '@sentry/nextjs';

jest.mock('@sentry/nextjs', () =>
  jest.requireActual(
    jest
      .requireActual<typeof import('path')>('path')
      .join(process.cwd(), 'node_modules/@sentry/nextjs/build/cjs/index.server.js'),
  ),
);

const CLIENT_IP = '203.0.113.7';

let server: Server;
const envelopes: string[] = [];

beforeAll(async () => {
  server = createServer((request, response) => {
    const chunks: Buffer[] = [];
    request.on('data', (chunk: Buffer) => chunks.push(chunk));
    request.on('end', () => {
      envelopes.push(Buffer.concat(chunks).toString('utf8'));
      response.end('{}');
    });
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
});

afterAll(async () => {
  const Sentry = await import('@sentry/nextjs');
  await Sentry.close(2000);
  await new Promise((resolve) => server.close(resolve));
});

function sentEvents(): ErrorEvent[] {
  return envelopes.flatMap((envelope) => {
    const lines = envelope.split('\n');
    return lines.flatMap((line, index) =>
      line.includes('"type":"event"') ? [JSON.parse(lines[index + 1]) as ErrorEvent] : [],
    );
  });
}

it('a captured server error carries no client IP, cookies, forwarding headers or body', async () => {
  const { port } = server.address() as AddressInfo;
  process.env.NEXT_PUBLIC_SENTRY_DSN = `http://publickey@127.0.0.1:${port}/1`;
  process.env.NEXT_RUNTIME = 'nodejs';
  const { register, onRequestError } = await import('@/instrumentation');
  const Sentry = await import('@sentry/nextjs');

  await register();
  await onRequestError(
    new Error('render failed'),
    {
      path: '/dashboard/books?token=secret',
      method: 'POST',
      headers: {
        cookie: 'better-auth.session_token=abc',
        'x-forwarded-for': CLIENT_IP,
        forwarded: `for=${CLIENT_IP}`,
        'x-real-ip': CLIENT_IP,
        'user-agent': 'jest',
      },
    },
    { routerKind: 'App Router', routePath: '/dashboard/books', routeType: 'render' },
  );
  await Sentry.flush(2000);

  const [event] = sentEvents();
  expect(event?.exception?.values?.[0]?.value).toBe('render failed');
  expect(JSON.stringify(event)).not.toContain(CLIENT_IP);
  expect(event.user?.ip_address).toBeUndefined();
  const headerNames = Object.keys(event.request?.headers ?? {}).map((name) => name.toLowerCase());
  expect(headerNames).not.toEqual(expect.arrayContaining(['cookie']));
  expect(headerNames.filter((name) => /forwarded|-ip$/.test(name))).toEqual([]);
  expect(event.request?.cookies).toBeUndefined();
  expect(event.request?.data).toBeUndefined();
  // Loading the real SDK cold takes several seconds
}, 30000);
