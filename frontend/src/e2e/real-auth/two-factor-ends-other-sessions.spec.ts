import { createHmac } from 'crypto';
import { expect, test, type APIRequestContext } from '@playwright/test';
import { WEB } from '../../../playwright.real-auth.config';
import { SAME_ORIGIN, STRONG, verificationLink } from './helpers';

/**
 * A change to the second factor or the password ends every other way back in
 * (#972). Each "device" is a cookie jar driving better-auth's HTTP API
 * directly, so nothing here depends on the settings page doing a second request.
 */

type Jar = APIRequestContext;
let jars: Jar[] = [];
let newJar: () => Promise<Jar>;

test.beforeEach(({ playwright }) => {
  newJar = async () => {
    const jar = await playwright.request.newContext({ baseURL: WEB, extraHTTPHeaders: SAME_ORIGIN });
    jars.push(jar);
    return jar;
  };
});
test.afterEach(async () => {
  await Promise.all(jars.map((jar) => jar.dispose()));
  jars = [];
});

/** RFC 6238 code for an otpauth `secret` (base32), as an authenticator app shows it. */
function totp(secret: string): string {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  const bits = [...secret.replace(/=+$/, '')]
    .map((c) => alphabet.indexOf(c).toString(2).padStart(5, '0'))
    .join('');
  const key = Buffer.from(bits.match(/.{8}/g)!.map((byte) => parseInt(byte, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30_000)));
  const mac = createHmac('sha1', key).update(counter).digest();
  const offset = mac[mac.length - 1] & 15;
  return String((mac.readUInt32BE(offset) & 0x7fffffff) % 1_000_000).padStart(6, '0');
}

const isSignedIn = async (jar: Jar) =>
  (await (await jar.get('/api/auth/get-session')).json()) !== null;

async function signIn(jar: Jar, email: string, password = STRONG) {
  const res = await jar.post('/api/auth/sign-in/email', { data: { email, password } });
  expect(res.status()).toBe(200);
  return (await res.json()) as { twoFactorRedirect?: boolean };
}

/** Signs in through the second factor, as the verify-2fa page does. */
async function signInWithCode(jar: Jar, email: string, secret: string, trustDevice = false) {
  expect((await signIn(jar, email)).twoFactorRedirect).toBe(true);
  const res = await jar.post('/api/auth/two-factor/verify-totp', {
    data: { code: totp(secret), trustDevice },
  });
  expect(res.status()).toBe(200);
  expect(await isSignedIn(jar)).toBe(true);
}

/** A verified account, signed in on the returned jar. */
async function newAccount(prefix: string) {
  const email = `${prefix}-${Date.now()}@example.com`;
  const jar = await newJar();
  const res = await jar.post('/api/auth/sign-up/email', {
    data: { name: 'Two Factor', email, password: STRONG },
  });
  expect(res.status()).toBe(200);
  await jar.get(await verificationLink(email));
  expect(await isSignedIn(jar)).toBe(true);
  return { email, jar };
}

/** Enables TOTP on `jar`'s account with direct API calls; returns the secret. */
async function enableTwoFactor(jar: Jar) {
  const started = await jar.post('/api/auth/two-factor/enable', { data: { password: STRONG } });
  expect(started.status()).toBe(200);
  const secret = new URL((await started.json()).totpURI).searchParams.get('secret')!;
  const verified = await jar.post('/api/auth/two-factor/verify-totp', {
    data: { code: totp(secret) },
  });
  expect(verified.status()).toBe(200);
  return secret;
}

test('enabling 2FA ends the account’s other sessions and keeps the one that enabled it', async () => {
  const { email, jar } = await newAccount('tfa-enable');
  const other = await newJar();
  await signIn(other, email);

  await enableTwoFactor(jar);

  expect(await isSignedIn(other)).toBe(false);
  expect(await isSignedIn(jar)).toBe(true);
});

test('disabling 2FA ends the account’s other sessions and keeps the one that disabled it', async () => {
  const { email, jar } = await newAccount('tfa-disable');
  const secret = await enableTwoFactor(jar);
  const other = await newJar();
  await signInWithCode(other, email, secret);

  const res = await jar.post('/api/auth/two-factor/disable', { data: { password: STRONG } });
  expect(res.status()).toBe(200);

  expect(await isSignedIn(other)).toBe(false);
  expect(await isSignedIn(jar)).toBe(true);
});

test('signing in through the second factor leaves the account’s other sessions alone', async () => {
  const { email, jar } = await newAccount('tfa-sign-in');
  const secret = await enableTwoFactor(jar);
  const other = await newJar();
  await signInWithCode(other, email, secret);

  const third = await newJar();
  await signInWithCode(third, email, secret);

  expect(await isSignedIn(jar)).toBe(true);
  expect(await isSignedIn(other)).toBe(true);
});

test('regenerating backup codes ends the other sessions; a refused attempt does not', async () => {
  const { email, jar } = await newAccount('tfa-backup-codes');
  const secret = await enableTwoFactor(jar);
  const other = await newJar();
  await signInWithCode(other, email, secret);

  const refused = await jar.post('/api/auth/two-factor/generate-backup-codes', {
    data: { password: `${STRONG}-wrong` },
  });
  expect(refused.status()).not.toBe(200);
  expect(await isSignedIn(other)).toBe(true);

  const res = await jar.post('/api/auth/two-factor/generate-backup-codes', {
    data: { password: STRONG },
  });
  expect(res.status()).toBe(200);

  expect(await isSignedIn(other)).toBe(false);
  expect(await isSignedIn(jar)).toBe(true);
});

test('a password reset stops a trusted device from skipping the second factor', async () => {
  const { email, jar } = await newAccount('tfa-trusted-reset');
  const secret = await enableTwoFactor(jar);
  const trusted = await newJar();
  await signInWithCode(trusted, email, secret, true);
  // The trust works: the next sign-in on this device skips the code.
  expect((await signIn(trusted, email)).twoFactorRedirect).toBeUndefined();

  const requested = await (await newJar()).post('/api/auth/request-password-reset', {
    data: { email, redirectTo: '/auth/reset-password' },
  });
  expect(requested.status()).toBe(200);
  const link = await verificationLink(email, /URL: (\S+\/reset-password\/\S+)/);
  const token = new URL(link).pathname.split('/').pop();
  const newPassword = `${STRONG}-Reset2`;
  const reset = await (await newJar()).post('/api/auth/reset-password', {
    data: { token, newPassword },
  });
  expect(reset.status()).toBe(200);

  expect((await signIn(trusted, email, newPassword)).twoFactorRedirect).toBe(true);
});
