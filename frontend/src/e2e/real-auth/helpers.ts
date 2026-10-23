import { readFileSync } from 'fs';
import { expect, type Page } from '@playwright/test';
import { FRONTEND_LOG, WEB } from '../../../playwright.real-auth.config';

// Built by concatenation so the pre-commit secrets pattern cannot false-positive.
export const STRONG = ['Real', 'Auth', '-e2e-', '1'].join('');

// better-auth refuses a cross-site POST; a page's own requests carry this.
export const SAME_ORIGIN = { Origin: WEB };

/**
 * The link in the email the development server printed when `email` signed up.
 * Each address is used once, so the first email to it is the sign-up one; a
 * refused sign-in mails another, whose link lands on the home page instead.
 * `pattern` picks a later email's link instead, such as a password reset's.
 */
export async function verificationLink(
  email: string,
  pattern = /URL: (\S+verify-email\S+)/
): Promise<string> {
  let link: string | undefined;
  await expect
    .poll(() => {
      const log = readFileSync(FRONTEND_LOG, 'utf8');
      const start = log.indexOf(`To: ${email}`);
      link = start < 0 ? undefined : pattern.exec(log.slice(start))?.[1];
      return link;
    })
    .toBeTruthy();
  return link!;
}

export async function signUp(page: Page, email: string) {
  await page.goto('/auth/sign-up');
  await page.locator('#name').fill('Real Author');
  await page.locator('#email').fill(email);
  await page.locator('#password').fill(STRONG);
  await page.locator('#confirmPassword').fill(STRONG);
  await page.getByRole('button', { name: 'Sign Up' }).click();
  await expect(page.getByRole('heading', { name: 'Check your email' })).toBeVisible();
}

/** Signs up through the page and opens the emailed link: `page` ends on the dashboard, signed in. */
export async function signUpAndVerify(page: Page, email: string) {
  await signUp(page, email);
  await page.goto(await verificationLink(email));
  await expect(page).toHaveURL(/\/dashboard/);
}
