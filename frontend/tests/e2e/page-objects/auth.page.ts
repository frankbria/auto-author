/**
 * Authentication Page Object
 *
 * Handles homepage and Clerk authentication interactions.
 */

import { Page, expect } from '@playwright/test';

export class AuthPage {
  constructor(private page: Page) {}

  /**
   * Navigate to homepage
   */
  async goto(): Promise<void> {
    await this.page.goto('/');
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Click the Sign In button
   */
  async clickSignIn(): Promise<void> {
    await this.page.click('text=Sign In');

    // Wait for Clerk modal to appear
    await this.page.waitForSelector('[data-clerk-modal]', { timeout: 10000 });
  }

  /**
   * Fill in Clerk authentication form
   */
  async fillCredentials(email: string, password: string): Promise<void> {
    // Fill email/identifier
    await this.page.fill('input[name="identifier"]', email);
    await this.page.click('button:has-text("Continue")');

    // Wait for password field
    await this.page.waitForSelector('input[name="password"]', { timeout: 5000 });

    // Fill password
    await this.page.fill('input[name="password"]', password);
  }

  /**
   * Click the sign in button in Clerk modal
   */
  async submitSignIn(): Promise<void> {
    await this.page.click('button:has-text("Sign in")');
  }

  /**
   * Wait for authentication to complete and redirect to dashboard
   */
  async waitForAuthComplete(): Promise<void> {
    await this.page.waitForURL('**/dashboard', { timeout: 15000 });
  }

  /**
   * Verify no CSP errors appear during authentication
   */
  async verifyNoCSPErrors(): Promise<void> {
    const { waitForCSPValidation } = await import('../helpers/condition-waiter');

    const cspErrors = await waitForCSPValidation(this.page, { timeout: 2000 });

    expect(cspErrors, `Expected no CSP errors, but found: ${cspErrors.join(', ')}`).toHaveLength(0);
  }

  /**
   * Verify Clerk button is visible
   */
  async verifySignInButtonVisible(): Promise<void> {
    await expect(this.page.locator('text=Sign In')).toBeVisible();
  }

  /**
   * Full authentication flow
   */
  async authenticate(email: string, password: string): Promise<void> {
    await this.clickSignIn();
    await this.fillCredentials(email, password);
    await this.submitSignIn();
    await this.waitForAuthComplete();

    console.log('✅ Authentication successful');
  }

  /**
   * Sign out
   */
  async signOut(): Promise<void> {
    // Click user menu
    await this.page.click('[data-testid="user-menu"]');

    // Click sign out
    await this.page.click('text=Sign Out');

    // Wait for redirect to homepage
    await this.page.waitForURL('/', { timeout: 10000 });

    console.log('✅ Sign out successful');
  }

  /**
   * Verify authentication token exists
   */
  async verifyAuthToken(): Promise<void> {
    const authToken = await this.page.evaluate(() =>
      localStorage.getItem('clerk-token') || sessionStorage.getItem('clerk-token')
    );

    expect(authToken, 'Expected authentication token to exist').toBeTruthy();
  }

  /**
   * Verify Clerk session is cleared
   */
  async verifySessionCleared(): Promise<void> {
    const authToken = await this.page.evaluate(() =>
      localStorage.getItem('clerk-token') || sessionStorage.getItem('clerk-token')
    );

    expect(authToken, 'Expected authentication token to be cleared').toBeNull();
  }
}
