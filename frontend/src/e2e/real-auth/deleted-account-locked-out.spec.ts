import { expect, test } from '@playwright/test';
import { API, WEB } from '../../../playwright.real-auth.config';
import { SAME_ORIGIN, STRONG, signUpAndVerify } from './helpers';

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
  // A second device is signed in too. The sign-out after the delete ends only
  // this browser's session, so this one shows whether the delete revoked them all.
  const other = await browser.newContext();
  const signedIn = await other.request.post(`${WEB}/api/auth/sign-in/email`, {
    headers: SAME_ORIGIN,
    data: { email, password: STRONG },
  });
  expect(signedIn.status()).toBe(200);
  expect((await other.request.get(`${API}/users/me`)).status()).toBe(200);

  await page.goto('/profile');
  await page.getByRole('button', { name: 'Delete Account' }).click();
  await page.locator('#confirm-delete-account').fill(email);
  await page.getByRole('button', { name: 'Deactivate account and delete books' }).click();
  await expect(page).toHaveURL(`${WEB}/`);

  // The other device's session is gone in better-auth, not only refused by the backend.
  expect((await other.request.get(`${API}/users/me`)).status()).toBe(401);
  expect(await (await other.request.get(`${WEB}/api/auth/get-session`)).json()).toBeNull();
  await other.close();

  // The old password: better-auth itself no longer knows it. The backend
  // would refuse the deactivated account anyway, so ask better-auth directly.
  const again = await page.request.post('/api/auth/sign-in/email', {
    headers: SAME_ORIGIN,
    data: { email, password: STRONG },
  });
  expect(again.status()).not.toBe(200);

  // And through the sign-in page, as the user would.
  await page.goto('/auth/sign-in');
  await page.locator('#email').fill(email);
  await page.locator('#password').fill(STRONG);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page).toHaveURL(/\/auth\/sign-in/);
  expect(await (await page.request.get('/api/auth/get-session')).json()).toBeNull();
});
