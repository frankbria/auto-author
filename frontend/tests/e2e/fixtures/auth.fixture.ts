/**
 * Authentication Fixture
 *
 * Handles Clerk authentication for deployment tests.
 * Requires TEST_USER_EMAIL and TEST_USER_PASSWORD environment variables.
 */

import { Page, expect } from '@playwright/test';

export interface AuthCredentials {
  email: string;
  password: string;
}

/**
 * Get test user credentials from environment variables
 */
export function getTestCredentials(): AuthCredentials {
  const email = process.env.TEST_USER_EMAIL;
  const password = process.env.TEST_USER_PASSWORD;

  if (!email || !password) {
    throw new Error(
      'Test credentials not configured. Please set TEST_USER_EMAIL and TEST_USER_PASSWORD environment variables.'
    );
  }

  return { email, password };
}

/**
 * Authenticate user with Clerk and wait for dashboard
 *
 * @param page Playwright page object
 * @param credentials Optional credentials (defaults to env vars)
 */
export async function authenticateUser(
  page: Page,
  credentials?: AuthCredentials
): Promise<void> {
  const { email, password } = credentials || getTestCredentials();

  // Navigate to homepage
  await page.goto('/');

  // Click Sign In button
  await page.click('text=Sign In');

  // Wait for Clerk modal to appear
  await page.waitForSelector('[data-clerk-modal]', { timeout: 10000 });

  // Fill email/identifier
  await page.fill('input[name="identifier"]', email);
  await page.click('button:has-text("Continue")');

  // Wait for password field and fill it
  await page.waitForSelector('input[name="password"]', { timeout: 5000 });
  await page.fill('input[name="password"]', password);

  // Click sign in button
  await page.click('button:has-text("Sign in")');

  // Wait for redirect to dashboard
  await page.waitForURL('**/dashboard', { timeout: 15000 });

  // Verify authentication token exists
  const authToken = await page.evaluate(() =>
    localStorage.getItem('clerk-token') || sessionStorage.getItem('clerk-token')
  );

  expect(authToken).toBeTruthy();

  console.log('✅ User authenticated successfully');
}

/**
 * Sign out the current user
 *
 * @param page Playwright page object
 */
export async function signOut(page: Page): Promise<void> {
  // Click user menu
  await page.click('[data-testid="user-menu"]');

  // Click sign out
  await page.click('text=Sign Out');

  // Wait for redirect to homepage
  await page.waitForURL('/', { timeout: 10000 });

  // Verify Clerk session cleared
  const authToken = await page.evaluate(() =>
    localStorage.getItem('clerk-token') || sessionStorage.getItem('clerk-token')
  );

  expect(authToken).toBeNull();

  console.log('✅ User signed out successfully');
}

/**
 * Check if user is authenticated
 *
 * @param page Playwright page object
 * @returns True if authenticated, false otherwise
 */
export async function isAuthenticated(page: Page): Promise<boolean> {
  const authToken = await page.evaluate(() =>
    localStorage.getItem('clerk-token') || sessionStorage.getItem('clerk-token')
  );

  return authToken !== null;
}
