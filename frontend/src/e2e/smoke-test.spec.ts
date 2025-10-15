/**
 * Smoke Test - Verify basic app functionality
 * Simplified test to diagnose authentication and routing issues
 */

import { test, expect } from '@playwright/test';

test.describe('Smoke Test', () => {
  test('can load homepage and navigate to dashboard', async ({ page }) => {
    // Set a reasonable timeout
    test.setTimeout(60000);

    console.log('Step 1: Navigate to homepage');
    await page.goto('/');

    // Take screenshot for debugging
    await page.screenshot({ path: 'test-results/01-homepage.png' });
    console.log('  ✓ Homepage loaded');

    // Wait for page to stabilize
    await page.waitForLoadState('networkidle', { timeout: 10000 });
    console.log('  ✓ Network idle');

    // Check what URL we're on
    const currentUrl = page.url();
    console.log(`  Current URL: ${currentUrl}`);

    // Try to navigate directly to dashboard (skip auth for now)
    console.log('Step 2: Navigate to dashboard');
    await page.goto('/dashboard');
    await page.screenshot({ path: 'test-results/02-dashboard.png' });

    const dashboardUrl = page.url();
    console.log(`  Dashboard URL: ${dashboardUrl}`);

    // Check if we got redirected to sign-in
    const isSignInPage = dashboardUrl.includes('sign-in') || dashboardUrl.includes('auth');

    if (isSignInPage) {
      console.log('  ⚠️  Redirected to authentication page');
      console.log('  This is expected behavior - authentication is required');
    } else {
      console.log('  ✓ Reached dashboard without authentication');

      // Look for dashboard indicators
      const hasDashboardContent = await page.locator('text=/dashboard|books|create/i').first().isVisible().catch(() => false);
      console.log(`  Has dashboard content: ${hasDashboardContent}`);
    }
  });

  test('can make API call to backend', async ({ request }) => {
    console.log('Testing backend API connectivity');

    const response = await request.get('http://localhost:8000/');
    const status = response.status();
    const body = await response.json();

    console.log(`  Status: ${status}`);
    console.log(`  Response: ${JSON.stringify(body)}`);

    expect(status).toBe(200);
    expect(body.message).toContain('Auto Author');
  });
});
