/**
 * Console Monitor Helper
 *
 * Monitors browser console for errors, warnings, and CSP violations.
 */

import { Page, ConsoleMessage } from '@playwright/test';
import { expect } from '@playwright/test';

export class ConsoleMonitor {
  private errors: ConsoleMessage[] = [];
  private warnings: ConsoleMessage[] = [];
  private logs: ConsoleMessage[] = [];

  constructor(private page: Page) {
    // Attach console listener
    page.on('console', msg => {
      const type = msg.type();

      if (type === 'error') {
        this.errors.push(msg);
        console.error(`❌ Browser Error: ${msg.text()}`);
      } else if (type === 'warning') {
        this.warnings.push(msg);
        console.warn(`⚠️ Browser Warning: ${msg.text()}`);
      } else {
        this.logs.push(msg);
      }
    });

    // Also monitor page errors
    page.on('pageerror', error => {
      console.error(`❌ Page Error: ${error.message}`);
    });
  }

  /**
   * Get all console errors
   */
  getErrors(): ConsoleMessage[] {
    return this.errors;
  }

  /**
   * Get all console warnings
   */
  getWarnings(): ConsoleMessage[] {
    return this.warnings;
  }

  /**
   * Get all console logs
   */
  getLogs(): ConsoleMessage[] {
    return this.logs;
  }

  /**
   * Assert that there are no console errors
   */
  assertNoErrors(): void {
    if (this.errors.length > 0) {
      const errorMessages = this.errors.map(e => e.text()).join('\n');
      expect(this.errors, `Expected no console errors, but found:\n${errorMessages}`).toHaveLength(0);
    }
  }

  /**
   * Assert that there are no CORS errors
   */
  assertNoCORSErrors(): void {
    const corsErrors = this.errors.filter(e =>
      e.text().toLowerCase().includes('cors') ||
      e.text().toLowerCase().includes('cross-origin')
    );

    if (corsErrors.length > 0) {
      const errorMessages = corsErrors.map(e => e.text()).join('\n');
      expect(corsErrors, `Expected no CORS errors, but found:\n${errorMessages}`).toHaveLength(0);
    }
  }

  /**
   * Assert that there are no CSP (Content Security Policy) errors
   */
  assertNoCSPErrors(): void {
    const cspErrors = this.errors.filter(e =>
      e.text().toLowerCase().includes('csp') ||
      e.text().toLowerCase().includes('content security policy') ||
      e.text().toLowerCase().includes('refused to')
    );

    if (cspErrors.length > 0) {
      const errorMessages = cspErrors.map(e => e.text()).join('\n');
      expect(cspErrors, `Expected no CSP errors, but found:\n${errorMessages}`).toHaveLength(0);
    }
  }

  /**
   * Check for specific error patterns
   */
  hasErrorMatching(pattern: string | RegExp): boolean {
    const regex = typeof pattern === 'string' ? new RegExp(pattern, 'i') : pattern;
    return this.errors.some(e => regex.test(e.text()));
  }

  /**
   * Reset collected messages
   */
  reset(): void {
    this.errors = [];
    this.warnings = [];
    this.logs = [];
  }

  /**
   * Get summary of console activity
   */
  getSummary(): { errors: number; warnings: number; logs: number } {
    return {
      errors: this.errors.length,
      warnings: this.warnings.length,
      logs: this.logs.length
    };
  }

  /**
   * Print summary to console
   */
  printSummary(): void {
    const summary = this.getSummary();
    console.log('\n📊 Console Monitor Summary:');
    console.log(`   Errors: ${summary.errors}`);
    console.log(`   Warnings: ${summary.warnings}`);
    console.log(`   Logs: ${summary.logs}`);
  }
}
