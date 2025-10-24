/**
 * CSP (Content Security Policy) Validator
 *
 * Validates CSP headers and ensures no violations occur.
 */

import { Page, Response } from '@playwright/test';
import { expect } from '@playwright/test';

export interface CSPConfig {
  directives: string[];
  allowedSources: {
    [directive: string]: string[];
  };
}

export class CSPValidator {
  /**
   * Validate CSP headers on a response
   */
  static async validateCSPHeaders(
    response: Response,
    expectedDirectives: string[]
  ): Promise<void> {
    const headers = response.headers();
    const csp = headers['content-security-policy'];

    expect(csp, 'Expected Content-Security-Policy header to be present').toBeTruthy();

    // Check for each expected directive
    for (const directive of expectedDirectives) {
      expect(
        csp,
        `Expected CSP to include directive: ${directive}`
      ).toContain(directive);
    }

    console.log(`✅ CSP headers validated for ${response.url()}`);
  }

  /**
   * Validate frontend CSP headers
   */
  static async validateFrontendCSP(response: Response): Promise<void> {
    const expectedDirectives = [
      'connect-src',
      'api.dev.autoauthor.app',
      'script-src',
      'clerk.accounts.dev'
    ];

    await this.validateCSPHeaders(response, expectedDirectives);
  }

  /**
   * Validate backend API CSP headers
   */
  static async validateBackendCSP(response: Response): Promise<void> {
    const expectedDirectives = [
      'script-src',
      'cdn.jsdelivr.net',
      'style-src',
      'cdn.jsdelivr.net',
      'img-src',
      'fastapi.tiangolo.com'
    ];

    await this.validateCSPHeaders(response, expectedDirectives);
  }

  /**
   * Check page for CSP violations
   */
  static async checkForCSPViolations(page: Page): Promise<void> {
    // CSP violations appear as console errors
    const cspViolations: string[] = [];

    page.on('console', msg => {
      const text = msg.text();
      if (
        text.toLowerCase().includes('csp') ||
        text.toLowerCase().includes('content security policy') ||
        text.toLowerCase().includes('refused to load') ||
        text.toLowerCase().includes('refused to execute')
      ) {
        cspViolations.push(text);
        console.error(`❌ CSP Violation: ${text}`);
      }
    });

    // Wait a bit for any violations to appear
    await page.waitForTimeout(1000);

    if (cspViolations.length > 0) {
      const violations = cspViolations.join('\n');
      expect(cspViolations, `CSP violations detected:\n${violations}`).toHaveLength(0);
    }

    console.log('✅ No CSP violations detected');
  }

  /**
   * Parse CSP header into structured format
   */
  static parseCSP(cspHeader: string): CSPConfig {
    const directives: string[] = [];
    const allowedSources: { [directive: string]: string[] } = {};

    // Split by semicolon to get each directive
    const directiveParts = cspHeader.split(';').map(d => d.trim());

    for (const part of directiveParts) {
      if (!part) continue;

      const [directive, ...sources] = part.split(/\s+/);
      directives.push(directive);
      allowedSources[directive] = sources;
    }

    return { directives, allowedSources };
  }

  /**
   * Check if a source is allowed for a directive
   */
  static isSourceAllowed(
    cspConfig: CSPConfig,
    directive: string,
    source: string
  ): boolean {
    const allowedSources = cspConfig.allowedSources[directive] || [];
    return allowedSources.some(allowed =>
      allowed === source ||
      allowed === '*' ||
      (allowed.startsWith('*.') && source.endsWith(allowed.substring(1)))
    );
  }

  /**
   * Verify Swagger UI can load without CSP errors
   */
  static async validateSwaggerUICSP(page: Page, apiDocsUrl: string): Promise<void> {
    const cspViolations: string[] = [];

    // Monitor for CSP violations
    page.on('console', msg => {
      const text = msg.text();
      if (text.toLowerCase().includes('refused to')) {
        cspViolations.push(text);
      }
    });

    // Navigate to Swagger UI
    await page.goto(apiDocsUrl);

    // Wait for Swagger UI to load
    await page.waitForSelector('.swagger-ui', { timeout: 10000 });

    // Check for violations
    if (cspViolations.length > 0) {
      const violations = cspViolations.join('\n');
      throw new Error(`Swagger UI CSP violations:\n${violations}`);
    }

    console.log('✅ Swagger UI loaded without CSP violations');
  }
}
