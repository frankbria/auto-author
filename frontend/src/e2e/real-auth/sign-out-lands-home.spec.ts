import { expect, test } from '@playwright/test';
import { WEB } from '../../../playwright.real-auth.config';
import { signUpAndVerify } from './helpers';

/**
 * Leaving on purpose from a protected page lands on the home page (#886).
 *
 * The session store drops the session as soon as sign-out starts, and the
 * page guard used to redirect first: the user landed on sign-in with a link
 * back to the page they had just left.
 */

test('signing out from the dashboard lands on the home page', async ({ page }) => {
  await signUpAndVerify(page, `sign-out-home-${Date.now()}@example.com`);

  await page.getByRole('button', { name: 'Account menu' }).click();
  await page.getByRole('menuitem', { name: 'Sign out' }).click();

  await expect(page).toHaveURL(`${WEB}/`);
});

test('deleting the account from the profile page lands on the home page', async ({ page }) => {
  const email = `delete-home-${Date.now()}@example.com`;
  await signUpAndVerify(page, email);

  await page.goto('/profile');
  await page.getByRole('button', { name: 'Delete Account' }).click();
  await page.locator('#confirm-delete-account').fill(email);
  await page.getByRole('button', { name: 'Deactivate account and delete books' }).click();

  await expect(page).toHaveURL(`${WEB}/`);
});
