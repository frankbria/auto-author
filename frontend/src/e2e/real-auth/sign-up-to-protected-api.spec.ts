import { readFileSync } from 'fs';
import { expect, test, type Page } from '@playwright/test';
import { API, FRONTEND_LOG, WEB } from '../../../playwright.real-auth.config';

/**
 * The one required check of real authentication (#843): no bypass anywhere.
 * A visitor signs up through the page, verifies the address with the link the
 * server emailed, and the backend then serves that user, and only that user.
 *
 * What this pins that no bypassed test can: better-auth's cookie is accepted
 * by the backend's signature check (#795), an unverified account gets nothing
 * (#792), the server-side password rule runs (#794), and data is owned by the
 * id better-auth gave the user (the #556 class of failure).
 */

// Built by concatenation so the pre-commit secrets pattern cannot false-positive.
const STRONG = ['Real', 'Auth', '-e2e-', '1'].join('');
const WEAK = 'a'.repeat(8);

// better-auth refuses a cross-site POST; a page's own requests carry this.
const SAME_ORIGIN = { Origin: WEB };

/**
 * The link in the email the development server printed when `email` signed up.
 * Each address is used once, so the first email to it is the sign-up one; a
 * refused sign-in mails another, whose link lands on the home page instead.
 */
async function verificationLink(email: string): Promise<string> {
  let link: string | undefined;
  await expect
    .poll(() => {
      const log = readFileSync(FRONTEND_LOG, 'utf8');
      const start = log.indexOf(`To: ${email}`);
      link = start < 0 ? undefined : /URL: (\S+verify-email\S+)/.exec(log.slice(start))?.[1];
      return link;
    })
    .toBeTruthy();
  return link!;
}

async function signUp(page: Page, email: string) {
  await page.goto('/auth/sign-up');
  await page.locator('#name').fill('Real Author');
  await page.locator('#email').fill(email);
  await page.locator('#password').fill(STRONG);
  await page.locator('#confirmPassword').fill(STRONG);
  await page.getByRole('button', { name: 'Sign Up' }).click();
  await expect(page.getByRole('heading', { name: 'Check your email' })).toBeVisible();
}

test('a visitor signs up, verifies their email, and the backend serves them and only them', async ({
  page,
  browser,
}) => {
  const email = `real-auth-${Date.now()}@example.com`;

  // The server refuses a weak password even when no page checks it (#794).
  const weak = await page.request.post('/api/auth/sign-up/email', {
    headers: SAME_ORIGIN,
    data: { email, password: WEAK, name: 'Real Author' },
  });
  expect(weak.status()).toBe(400);

  await signUp(page, email);

  // Signed up is not signed in (#792): no session, and the backend refuses.
  expect(await (await page.request.get('/api/auth/get-session')).json()).toBeNull();
  expect((await page.request.get(`${API}/users/me`)).status()).toBe(401);
  const unverified = await page.request.post('/api/auth/sign-in/email', {
    headers: SAME_ORIGIN,
    data: { email, password: STRONG },
  });
  expect(unverified.status()).toBe(403);
  expect((await unverified.json()).code).toBe('EMAIL_NOT_VERIFIED');

  // The emailed link verifies the address and signs this browser in.
  await page.goto(await verificationLink(email));
  await expect(page).toHaveURL(/\/dashboard/);
  const session = await (await page.request.get('/api/auth/get-session')).json();
  expect(session.user.email).toBe(email);
  expect(session.user.emailVerified).toBe(true);

  // Protected endpoints answer 200, as the user better-auth says this is.
  const me = await page.request.get(`${API}/users/me`);
  expect(me.status()).toBe(200);
  const profile = await me.json();
  expect(profile.email).toBe(email);
  expect(profile.auth_id).toBe(session.user.id);

  const created = await page.request.post(`${API}/books/`, {
    data: { title: 'Owned by the real user', genre: 'nonfiction', target_audience: 'readers' },
  });
  expect(created.status()).toBe(201);
  const book = await created.json();
  expect(book.owner_id).toBe(session.user.id);
  const mine = await (await page.request.get(`${API}/books/`)).json();
  expect(mine.map((b: { id: string }) => b.id)).toContain(book.id);

  // The session token alone is not a credential (#795): it must carry its
  // signature. The signed cookie, replayed in a fresh context, proves this way
  // of sending a cookie works, so the 401 below is the backend's refusal.
  const signed = (await page.context().cookies()).find((c) => c.name === 'better-auth.session_token')!;
  expect(decodeURIComponent(signed.value)).toMatch(new RegExp(`^${session.session.token}\\..+`));
  for (const [value, status] of [
    [signed.value, 200],
    [session.session.token, 401],
  ] as const) {
    const replay = await browser.newContext();
    await replay.addCookies([{ name: signed.name, value, domain: 'localhost', path: '/' }]);
    expect((await replay.request.get(`${API}/users/me`)).status()).toBe(status);
    await replay.close();
  }

  // A second visitor, signed up the same way, sees none of the first one's data.
  const other = await browser.newContext();
  const otherPage = await other.newPage();
  const otherEmail = `real-auth-other-${Date.now()}@example.com`;
  await signUp(otherPage, otherEmail);
  await otherPage.goto(await verificationLink(otherEmail));
  await expect(otherPage).toHaveURL(/\/dashboard/);
  expect(await (await otherPage.request.get(`${API}/books/`)).json()).toEqual([]);
  expect((await otherPage.request.get(`${API}/books/${book.id}`)).status()).not.toBe(200);
  await other.close();
});
