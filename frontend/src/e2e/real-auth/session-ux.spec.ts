import { expect, test } from '@playwright/test';
import { MongoClient } from 'mongodb';
import { API, DATABASE, MONGO, WEB } from '../../../playwright.real-auth.config';
import { SAME_ORIGIN, STRONG, signUpAndVerify } from './helpers';

/**
 * Session behaviour that only a real better-auth server shows (#796).
 *
 * These reach into the database for one thing each: to make time pass, or to
 * revoke a session "from another device". Everything else goes through the page.
 */

let mongo: MongoClient;
test.beforeAll(async () => {
  mongo = await new MongoClient(MONGO).connect();
});
test.afterAll(async () => {
  await mongo.close();
});
const sessions = () => mongo.db(DATABASE).collection('session');

test('a session too old to list devices asks for a fresh sign-in and can still sign out the others', async ({
  page,
  browser,
}) => {
  const email = `stale-session-${Date.now()}@example.com`;
  await signUpAndVerify(page, email);
  const { session } = await (await page.request.get('/api/auth/get-session')).json();

  // A second device signs in to the same account.
  const other = await browser.newContext();
  const signedIn = await other.request.post(`${WEB}/api/auth/sign-in/email`, {
    headers: SAME_ORIGIN,
    data: { email, password: STRONG },
  });
  expect(signedIn.status()).toBe(200);
  expect((await other.request.get(`${API}/users/me`)).status()).toBe(200);

  // Two days pass for this browser's session. better-auth only lists sessions
  // for one under a day old, and answers 403 SESSION_NOT_FRESH after that.
  await sessions().updateOne(
    { token: session.token },
    { $set: { createdAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000) } }
  );
  const listing = await page.request.get('/api/auth/list-sessions');
  expect(listing.status()).toBe(403);
  expect((await listing.json()).code).toBe('SESSION_NOT_FRESH');

  await page.goto('/dashboard/settings');
  await page.getByRole('tab', { name: 'Security' }).click();

  // The page says what to do about it, instead of an error with a Retry button.
  const prompt = page.getByRole('alert').filter({ hasText: /to see your devices/i });
  await expect(prompt).toBeVisible();
  await expect(prompt.getByRole('link', { name: 'Sign in again' })).toHaveAttribute(
    'href',
    `/auth/sign-in?redirect=${encodeURIComponent('/dashboard/settings')}`
  );

  // Signing out the other devices does not need the list, and still works.
  await page.getByRole('button', { name: 'Sign out other devices' }).click();
  await expect
    .poll(async () => (await other.request.get(`${API}/users/me`)).status())
    .toBe(401);
  expect((await page.request.get(`${API}/users/me`)).status()).toBe(200);
  await other.close();
});

test('a browser whose session was revoked is signed out and sent to sign in', async ({ page }) => {
  const email = `revoked-session-${Date.now()}@example.com`;
  await signUpAndVerify(page, email);
  const { session } = await (await page.request.get('/api/auth/get-session')).json();

  // The session is revoked from somewhere else. This browser still holds its cookie.
  await sessions().deleteOne({ token: session.token });

  // Its next visit loads the dashboard, whose first backend call answers 401.
  await page.goto('/dashboard');

  await expect(page).toHaveURL(/\/auth\/sign-in\?redirect=%2Fdashboard/);
  // The dead cookie is gone, so the middleware no longer treats it as signed in.
  const cookies = await page.context().cookies();
  expect(cookies.find((c) => c.name === 'better-auth.session_token')).toBeUndefined();
});
