/**
 * Authentication Page Object
 *
 * Handles homepage and better-auth authentication interactions.
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
   * Navigate to sign-in page
   */
  async gotoSignIn(): Promise<void> {
    await this.page.goto('/auth/sign-in');
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Click the Sign In button on homepage
   */
  async clickSignIn(): Promise<void> {
    await this.page.click('text=Sign In');

    // Wait for sign-in page to load
    await this.page.waitForURL('**/auth/sign-in', { timeout: 10000 });
  }

  /**
   * Fill in better-auth authentication form
   */
  async fillCredentials(email: string, password: string): Promise<void> {
    // Wait for form to be visible
    await this.page.waitForSelector('form', { timeout: 5000 });

    // Fill email field
    await this.page.fill('input[type="email"]', email);

    // Fill password field
    await this.page.fill('input[type="password"]', password);
  }

  /**
   * Click the sign in button on the sign-in form
   */
  async submitSignIn(): Promise<void> {
    await this.page.click('button[type="submit"]');
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
    const cspErrors: string[] = [];

    this.page.on('console', msg => {
      const text = msg.text();
      if (text.toLowerCase().includes('csp') || text.toLowerCase().includes('content security policy')) {
        cspErrors.push(text);
      }
    });

    await this.page.waitForTimeout(1000);

    expect(cspErrors, `Expected no CSP errors, but found: ${cspErrors.join(', ')}`).toHaveLength(0);
  }

  /**
   * Verify Sign In button is visible on homepage
   */
  async verifySignInButtonVisible(): Promise<void> {
    await expect(this.page.locator('text=Sign In')).toBeVisible();
  }

  /**
   * Full authentication flow (from homepage)
   */
  async authenticate(email: string, password: string): Promise<void> {
    await this.clickSignIn();
    await this.fillCredentials(email, password);
    await this.submitSignIn();
    await this.waitForAuthComplete();

    console.log('✅ Authentication successful');
  }

  /**
   * Direct authentication flow (go straight to sign-in page)
   */
  async authenticateDirect(email: string, password: string): Promise<void> {
    await this.gotoSignIn();
    await this.fillCredentials(email, password);
    await this.submitSignIn();
    await this.waitForAuthComplete();

    console.log('✅ Authentication successful');
  }

  /**
   * Sign out
   */
  async signOut(): Promise<void> {
    // Click user menu button (avatar button)
    await this.page.click('button[class*="rounded-full"]');

    // Click sign out option
    await this.page.click('text=Sign out');

    // Wait for redirect to homepage
    await this.page.waitForURL('/', { timeout: 10000 });

    console.log('✅ Sign out successful');
  }

  /**
   * Verify authentication session exists
   */
  async verifyAuthSession(): Promise<void> {
    const hasSession = await this.page.evaluate(async () => {
      return document.cookie.includes('better-auth');
    });

    expect(hasSession, 'Expected authentication session to exist').toBeTruthy();
  }

  /**
   * Verify better-auth session is cleared
   */
  async verifySessionCleared(): Promise<void> {
    const hasSession = await this.page.evaluate(async () => {
      return document.cookie.includes('better-auth');
    });

    expect(hasSession, 'Expected authentication session to be cleared').toBeFalsy();
  }
}
