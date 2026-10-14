import { expect, test } from '@playwright/test';
import { API, WEB } from '../../../playwright.real-auth.config';
import { STRONG, signUpAndVerify } from './helpers';

/**
 * A deleted account is locked out (#763, #887): its old session cookie is
 * refused and its old password no longer signs in. The backend tests prove
 * this against a stand-in; this runs a real better-auth server.
 *
 * Here and not in the staging suite: a staging sign-up needs a mailbox to
 * verify the throwaway account, and this suite reads the link from its own
 * server's log.
 */
test('a deleted account cannot sign back in, and its old session cookie is refused', async ({
  page,
  browser,
}) => {
  const email = `deleted-locked-out-${Date.now()}@example.com`;
  await signUpAndVerify(page, email);
  const oldCookies = await page.context().cookies();
  expect((await page.request.get(`${API}/users/me`)).status()).toBe(200);

  await page.goto('/profile');
  await page.getByRole('button', { name: 'Delete Account' }).click();
  await page.locator('#confirm-delete-account').fill(email);
  await page.getByRole('button', { name: 'Deactivate account and delete books' }).click();
  await expect(page).toHaveURL(`${WEB}/`);

  // Someone kept a copy of the cookie: the backend refuses it.
  const kept = await browser.newContext();
  await kept.addCookies(oldCookies);
  expect((await kept.request.get(`${API}/users/me`)).status()).toBe(401);
  expect(await (await kept.request.get(`${WEB}/api/auth/get-session`)).json()).toBeNull();
  await kept.close();

  // The old password, through the sign-in page.
  await page.goto('/auth/sign-in');
  await page.locator('#email').fill(email);
  await page.locator('#password').fill(STRONG);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page).toHaveURL(/\/auth\/sign-in/);
  expect(await (await page.request.get('/api/auth/get-session')).json()).toBeNull();
});
