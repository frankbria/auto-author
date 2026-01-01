import { test as base, Page, expect } from '@playwright/test';

/**
 * Authentication fixture for staging E2E tests
 *
 * Provides authenticated page state by logging in with Better-auth
 */

export type AuthFixtures = {
  authenticatedPage: Page;
};

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
  const email = process.env.STAGING_TEST_EMAIL;
  const password = process.env.STAGING_TEST_PASSWORD;

  if (!email || !password) {
    throw new Error(
      'STAGING_TEST_EMAIL and STAGING_TEST_PASSWORD must be set in environment'
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
  await page.waitForURL(/\/dashboard/, { timeout: 30000 });

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
export const test = base.extend<AuthFixtures>({
  authenticatedPage: async ({ page }, use) => {
    // Login before test
    await loginToStaging(page);

    // Provide authenticated page to test
    await use(page);

    // Cleanup after test (optional - could logout here)
  },
});

export { expect } from '@playwright/test';
