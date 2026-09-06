import { test as base, Page, expect } from '@playwright/test';
import fs from 'fs';
import os from 'os';
import path from 'path';

/**
 * Authentication fixture for staging E2E tests
 *
 * Signs in to staging with Better-auth **once per worker** and shares the
 * resulting storage state with every test in that worker.
 *
 * Why once per worker (#551): better-auth rate-limits any `/sign-in*` path at
 * 3 requests per 10s per IP by default, and the window only resets after 10s of
 * silence. Signing in per test meant 11 sign-ins from one CI IP at 2-6s spacing,
 * so the run reliably tripped the limit partway through — the sign-in page
 * answered "Too many attempts. Please try again later", the redirect never came,
 * and the #83 session canary burned its 30s budget every single run. One sign-in
 * per worker stays an order of magnitude under the limit.
 */

export type AuthFixtures = {
  authenticatedPage: Page;
};

export type AuthWorkerFixtures = {
  workerStorageState: string;
};

const SIGN_IN_TIMEOUT_MS = 30_000;

/**
 * Login to staging with Better-auth
 *
 * Handles the complete login flow:
 * 1. Navigate to sign-in page
 * 2. Fill credentials
 * 3. Submit form
 * 4. Wait for redirect to dashboard
 * 5. Verify session cookie set
 */
async function loginToStaging(page: Page): Promise<void> {
  // Support both local (.env.test) and CI (GitHub Secrets) variable names
  const email = process.env.STAGING_TEST_EMAIL || process.env.TEST_USER_EMAIL;
  const password = process.env.STAGING_TEST_PASSWORD || process.env.TEST_USER_PASSWORD;

  if (!email || !password) {
    throw new Error(
      'Test credentials not found. ' +
      'Local: Set STAGING_TEST_EMAIL and STAGING_TEST_PASSWORD in .env.test. ' +
      'CI: Ensure TEST_USER_EMAIL and TEST_USER_PASSWORD GitHub Secrets are set.'
    );
  }

  console.log(`🔐 Logging in as ${email}...`);

  // Navigate to sign-in page
  await page.goto('/auth/sign-in');

  // Wait for sign-in form to load
  await page.waitForSelector('input[type="email"]', { timeout: 10000 });

  // Fill in credentials
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);

  // Submit form
  await page.click('button[type="submit"]');

  // Wait for redirect to dashboard (indicates successful login)
  try {
    await page.waitForURL(/\/dashboard/, { timeout: SIGN_IN_TIMEOUT_MS });
  } catch (error) {
    // A bare navigation timeout says nothing about *why* sign-in stalled — the
    // page's own error alert does (rate limit, bad credentials, backend down).
    // Surfacing it here is what turned #551 from a mystery into a one-line
    // diagnosis. The original error is chained, not discarded: this catch also
    // sees non-timeout failures (closed context, browser crash) whose stack is
    // the only thing that identifies them.
    throw new Error(
      `Sign-in did not reach /dashboard within ${SIGN_IN_TIMEOUT_MS}ms. ` +
      `${await readSignInError(page)}`,
      { cause: error }
    );
  }

  // Verify we're on the dashboard
  await expect(page).toHaveURL(/\/dashboard/);

  // Verify session cookie is set (Better-auth uses httpOnly cookies)
  const cookies = await page.context().cookies();
  const sessionCookie = cookies.find(
    (c) =>
      c.name === '__Secure-better-auth.session_token' ||
      c.name === 'better-auth.session_token'
  );

  if (!sessionCookie) {
    throw new Error(
      'Session cookie not found after login - authentication may have failed'
    );
  }

  console.log(`✅ Logged in successfully - session cookie: ${sessionCookie.name}`);
}

/** Read whatever the sign-in form is complaining about, if anything. */
async function readSignInError(page: Page): Promise<string> {
  const text = await page
    .locator('[role="alert"]')
    .first()
    .textContent({ timeout: 2000 })
    .catch(() => null);

  return text?.trim()
    ? `The sign-in page reports: "${text.trim()}" (current URL: ${page.url()}).`
    : `The sign-in page showed no error (current URL: ${page.url()}).`;
}

/**
 * Extended test with authenticated page fixture
 *
 * Usage:
 * ```typescript
 * test('my authenticated test', async ({ authenticatedPage }) => {
 *   // authenticatedPage is already logged in
 *   await authenticatedPage.goto('/dashboard');
 *   // ... rest of test
 * });
 * ```
 */
export const test = base.extend<AuthFixtures, AuthWorkerFixtures>({
  // Sign in once per worker and hand every test the saved session.
  workerStorageState: [
    async ({ browser }, use, workerInfo) => {
      // Deliberately NOT under `project.outputDir`: that tree is uploaded whole
      // as a CI artifact from a public repo, and this file holds a live, unexpired
      // `__Secure-better-auth.session_token`. It belongs somewhere nothing
      // collects. (See #599 for the same class of leak via failure snapshots.)
      const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), 'aa-staging-auth-'));
      const statePath = path.join(stateDir, `worker-${workerInfo.workerIndex}.json`);

      // newContext() does not inherit `use.baseURL` from the project, so the
      // relative goto() in loginToStaging needs it passed explicitly.
      const context = await browser.newContext({
        baseURL: workerInfo.project.use.baseURL,
      });
      try {
        await loginToStaging(await context.newPage());
        await context.storageState({ path: statePath });
      } finally {
        await context.close();
      }

      try {
        await use(statePath);
      } finally {
        fs.rmSync(stateDir, { recursive: true, force: true });
      }
    },
    { scope: 'worker' },
  ],

  storageState: ({ workerStorageState }, use) => use(workerStorageState),

  // Kept for spec compatibility: `page` is already authenticated via storageState.
  authenticatedPage: async ({ page }, use) => {
    await use(page);
  },
});

export { expect } from '@playwright/test';
