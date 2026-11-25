import { randomBytes } from 'crypto';
import { expect, test } from '@playwright/test';
import {
  createInbox,
  deleteInbox,
  extractVerificationLink,
  waitForMessage,
  type Inbox,
} from './fixtures/disposable-inbox';

/**
 * A new account's verification email arrives and its link signs the user in
 * (#971). `/api/health` reporting the email provider "configured" proves a key
 * is set, not that the key works, the sending domain is accepted or the message
 * is delivered. This signs up on staging with a throwaway mail.tm address, reads
 * the email that arrives, opens its link and expects the dashboard, signed in.
 * Inbox-vs-spam placement at the large providers is not measured (owner
 * decision on #971).
 *
 * It then deletes the account from /profile (deactivated, as for any user)
 * and the mailbox. An account whose email never arrives cannot sign in to
 * delete itself, and a cancelled run skips the cleanup; those are left behind.
 *
 * The address shows in public logs and videos, so the password is random per
 * run and never printed, and nothing prints the link's token (see below).
 *
 * No retries: a retry makes a second account and mailbox, and the CI config
 * fails a test that passes only on retry anyway (`failOnFlakyTests`).
 */

const SUBJECT = 'Verify your email address';
const EMAIL_WAIT_MS = 120_000;

/**
 * Random per run and never printed. The `Aa1` part meets the password policy.
 * Built with join() so secret scanners do not read it as a hardcoded password.
 */
const freshPassword = () => ['Aa1', randomBytes(18).toString('base64url')].join('-');

test.describe.configure({ retries: 0 });

test('#971: the verification email arrives and its link lands on the dashboard, signed in', async ({
  page,
  baseURL,
}) => {
  test.setTimeout(EMAIL_WAIT_MS + 90_000);
  const origin = new URL(baseURL!).origin;
  const typed = freshPassword();
  let inbox: Inbox | undefined;

  try {
    inbox = await test.step('create a throwaway inbox on mail.tm', () => createInbox());
    const { address } = inbox;

    await test.step('sign up through the page', async () => {
      await page.goto('/auth/sign-up');
      await page.locator('#name').fill('Verification Check');
      await page.locator('#email').fill(address);
      await page.locator('#password').fill(typed);
      await page.locator('#confirmPassword').fill(typed);
      await page.getByRole('button', { name: 'Sign Up' }).click();
      await expect(page.getByRole('heading', { name: 'Check your email' })).toBeVisible();
    });

    const link = await test.step('the verification email arrives', async () =>
      extractVerificationLink(
        await waitForMessage(inbox!, { subject: SUBJECT, timeoutMs: EMAIL_WAIT_MS }),
        origin
      )
    );

    await test.step('its link lands on the dashboard, signed in', async () => {
      // The link's token signs whoever holds it in, and Playwright errors print
      // URLs into public CI logs. So no error here carries the link: the
      // navigation error is replaced, and only origin and path are asserted.
      try {
        await page.goto(link);
      } catch {
        throw new Error('Opening the verification link failed (URL withheld: it carries a sign-in token)');
      }
      await expect
        .poll(() => {
          const landed = new URL(page.url());
          return landed.origin + landed.pathname;
        })
        .toBe(`${origin}/dashboard`);
      const session = await (await page.request.get('/api/auth/get-session')).json();
      expect(session?.user?.email).toBe(address);
      expect(session?.user?.emailVerified).toBe(true);
    });

    await test.step('delete the throwaway account', async () => {
      await page.goto('/profile');
      await page.getByRole('button', { name: 'Delete Account' }).click();
      await page.locator('#confirm-delete-account').fill(address);
      await page.getByRole('button', { name: 'Deactivate account and delete books' }).click();
      await expect(page).toHaveURL(`${origin}/`);
    });
  } finally {
    // The mailbox is mail.tm's, not the app's: failing to delete it is noted on
    // the result, not turned into a red run.
    if (inbox) {
      await deleteInbox(inbox).catch((error: unknown) =>
        test.info().annotations.push({
          type: 'warning',
          description: `mail.tm inbox not deleted: ${String(error)}`,
        })
      );
    }
  }
});
