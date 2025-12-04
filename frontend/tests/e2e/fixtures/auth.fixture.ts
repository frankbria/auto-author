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
  // Clerk authentication flow
  const { email, password } = credentials || getTestCredentials();

  // Navigate to dashboard - will redirect to Clerk's hosted sign-in page
  await page.goto('/dashboard');

  // Wait for Clerk's hosted sign-in page to load
  // Clerk uses a redirect flow to their hosted domain (e.g., *.accounts.dev)
  await page.waitForSelector('text=Sign in', { timeout: 15000 });

  console.log('📧 Filling email...');

  // Fill email - use the Email address label to find the right field
  // This avoids the OAuth buttons (Apple/Google) which also have "Continue" text
  const emailInput = page.getByLabel('Email address');
  await emailInput.fill(email);

  // Wait a moment for validation
  await page.waitForTimeout(500);

  // Click the main Continue button (not OAuth buttons)
  // The submit button is typically inside a form or has specific styling
  // Use a more specific selector to avoid OAuth "Continue with X" buttons
  const continueButton = page.locator('button').filter({ hasText: /^Continue$/ }).first();
  await continueButton.click();

  // Wait for password field to appear (Clerk shows it after email validation)
  console.log('⏳ Waiting for password field...');
  await page.waitForSelector('input[type="password"]', { timeout: 10000 });

  console.log('🔑 Filling password...');

  // Fill password using specific input selector (avoid "Show password" button)
  const passwordInput = page.locator('input[type="password"]').first();
  await passwordInput.fill(password);

  // Wait a moment for validation
  await page.waitForTimeout(500);

  // Click Continue/Sign in button - use same specific selector
  const signInButton = page.locator('button').filter({ hasText: /^Continue$/ }).first();
  await signInButton.click();

  // Wait for redirect back to dashboard
  console.log('⏳ Waiting for redirect to dashboard...');
  await page.waitForURL('**/dashboard**', { timeout: 30000 });

  // Wait for page to stabilize
  await page.waitForLoadState('networkidle');

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
