/**
 * Authentication Fixture
 *
 * Handles better-auth authentication for deployment tests.
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
 * Authenticate user with better-auth and wait for dashboard
 *
 * @param page Playwright page object
 * @param credentials Optional credentials (defaults to env vars)
 */
export async function authenticateUser(
  page: Page,
  credentials?: AuthCredentials
): Promise<void> {
  // Check if NEXT_PUBLIC_BYPASS_AUTH is enabled (for testing without auth)
  const bypassAuth = process.env.NEXT_PUBLIC_BYPASS_AUTH === 'true';

  if (bypassAuth) {
    console.log('⚠️ NEXT_PUBLIC_BYPASS_AUTH enabled - skipping authentication');

    // Navigate directly to dashboard
    await page.goto('/dashboard');

    // Wait for dashboard to load
    await page.waitForLoadState('networkidle');

    console.log('✅ User authenticated successfully (NEXT_PUBLIC_BYPASS_AUTH mode)');
    return;
  }

  // Normal better-auth authentication flow
  const { email, password } = credentials || getTestCredentials();

  // Navigate to sign-in page
  await page.goto('/auth/sign-in');

  // Wait for sign-in form to appear
  await page.waitForSelector('form', { timeout: 10000 });

  // Fill email field
  await page.fill('input[type="email"]', email);

  // Fill password field
  await page.fill('input[type="password"]', password);

  // Click sign in button
  await page.click('button[type="submit"]');

  // Wait for redirect to dashboard
  await page.waitForURL('**/dashboard', { timeout: 15000 });

  // Verify authentication session exists
  const hasSession = await page.evaluate(async () => {
    // better-auth stores session in cookies, check if we have session cookies
    return document.cookie.includes('better-auth');
  });

  expect(hasSession).toBeTruthy();

  console.log('✅ User authenticated successfully');
}

/**
 * Sign out the current user
 *
 * @param page Playwright page object
 */
export async function signOut(page: Page): Promise<void> {
  // Click user menu button (avatar button)
  await page.click('button[class*="rounded-full"]');

  // Click sign out option
  await page.click('text=Sign out');

  // Wait for redirect to homepage
  await page.waitForURL('/', { timeout: 10000 });

  // Verify better-auth session cleared
  const hasSession = await page.evaluate(async () => {
    return document.cookie.includes('better-auth');
  });

  expect(hasSession).toBeFalsy();

  console.log('✅ User signed out successfully');
}

/**
 * Check if user is authenticated
 *
 * @param page Playwright page object
 * @returns True if authenticated, false otherwise
 */
export async function isAuthenticated(page: Page): Promise<boolean> {
  const hasSession = await page.evaluate(async () => {
    return document.cookie.includes('better-auth');
  });

  return hasSession;
}
