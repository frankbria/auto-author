/**
 * Network Monitor Helper
 *
 * Monitors network requests and responses, useful for API call validation.
 */

import { Page, Request, Response, Route } from '@playwright/test';
import { expect } from '@playwright/test';

export interface NetworkRequest {
  url: string;
  method: string;
  status?: number;
  statusText?: string;
  headers: Record<string, string>;
  timestamp: number;
}

export class NetworkMonitor {
  private requests: NetworkRequest[] = [];
  private responses: Map<string, Response> = new Map();
  private failedRequests: NetworkRequest[] = [];

  constructor(private page: Page) {
    // Monitor all requests
    page.on('request', (request: Request) => {
      const networkRequest: NetworkRequest = {
        url: request.url(),
        method: request.method(),
        headers: request.headers(),
        timestamp: Date.now()
      };

      this.requests.push(networkRequest);
    });

    // Monitor all responses
    page.on('response', (response: Response) => {
      const url = response.url();
      this.responses.set(url, response);

      // Track failed requests (4xx, 5xx)
      const status = response.status();
      if (status >= 400) {
        const existingRequest = this.requests.find(r => r.url === url);
        if (existingRequest) {
          existingRequest.status = status;
          existingRequest.statusText = response.statusText();
          this.failedRequests.push(existingRequest);

          console.warn(`⚠️ Failed Request: ${status} ${response.statusText()} - ${url}`);
        }
      }
    });

    // Monitor request failures
    page.on('requestfailed', (request: Request) => {
      console.error(`❌ Request Failed: ${request.url()}`);
    });
  }

  /**
   * Get all network requests
   */
  getRequests(): NetworkRequest[] {
    return this.requests;
  }

  /**
   * Get requests matching a URL pattern
   */
  getRequestsMatching(pattern: string | RegExp): NetworkRequest[] {
    const regex = typeof pattern === 'string' ? new RegExp(pattern) : pattern;
    return this.requests.filter(r => regex.test(r.url));
  }

  /**
   * Get failed requests (4xx, 5xx status codes)
   */
  getFailedRequests(): NetworkRequest[] {
    return this.failedRequests;
  }

  /**
   * Get response for a specific URL
   */
  getResponse(url: string): Response | undefined {
    return this.responses.get(url);
  }

  /**
   * Wait for a specific API request to complete
   */
  async waitForRequest(urlPattern: string | RegExp, options?: { timeout?: number }): Promise<Response> {
    const response = await this.page.waitForResponse(
      resp => {
        const regex = typeof urlPattern === 'string' ? new RegExp(urlPattern) : urlPattern;
        return regex.test(resp.url());
      },
      { timeout: options?.timeout || 30000 }
    );

    return response;
  }

  /**
   * Assert no 500 errors occurred
   */
  assertNo500Errors(): void {
    const serverErrors = this.failedRequests.filter(r => r.status && r.status >= 500);

    if (serverErrors.length > 0) {
      const errorMessages = serverErrors.map(r => `${r.status} ${r.statusText} - ${r.url}`).join('\n');
      expect(serverErrors, `Expected no 500 errors, but found:\n${errorMessages}`).toHaveLength(0);
    }
  }

  /**
   * Assert no CORS errors
   */
  assertNoCORSErrors(): void {
    // CORS errors typically show as failed requests
    const corsErrors = this.failedRequests.filter(r =>
      r.url.includes('api') && (!r.status || r.status === 0)
    );

    if (corsErrors.length > 0) {
      const errorMessages = corsErrors.map(r => r.url).join('\n');
      expect(corsErrors, `Possible CORS errors detected:\n${errorMessages}`).toHaveLength(0);
    }
  }

  /**
   * Verify API request includes Authorization header
   */
  async verifyAuthHeader(urlPattern: string | RegExp): Promise<void> {
    const requests = this.getRequestsMatching(urlPattern);

    expect(requests.length, `Expected at least one request matching ${urlPattern}`).toBeGreaterThan(0);

    const authRequest = requests.find(r => r.headers['authorization']);
    expect(authRequest, `Expected request to ${urlPattern} to include Authorization header`).toBeTruthy();
    expect(authRequest!.headers['authorization']).toContain('Bearer');
  }

  /**
   * Check response headers for CORS configuration
   */
  async checkCORSHeaders(url: string): Promise<void> {
    const response = this.responses.get(url);

    if (!response) {
      throw new Error(`No response found for URL: ${url}`);
    }

    const headers = response.headers();

    // Check for CORS headers
    const allowOrigin = headers['access-control-allow-origin'];
    const allowCredentials = headers['access-control-allow-credentials'];

    expect(allowOrigin, `Expected access-control-allow-origin header on ${url}`).toBeTruthy();
    expect(allowCredentials, `Expected access-control-allow-credentials header on ${url}`).toBeTruthy();

    console.log(`✅ CORS headers verified for ${url}`);
  }

  /**
   * Reset collected requests
   */
  reset(): void {
    this.requests = [];
    this.responses.clear();
    this.failedRequests = [];
  }

  /**
   * Get summary of network activity
   */
  getSummary(): { total: number; failed: number; successful: number } {
    return {
      total: this.requests.length,
      failed: this.failedRequests.length,
      successful: this.requests.length - this.failedRequests.length
    };
  }

  /**
   * Print summary to console
   */
  printSummary(): void {
    const summary = this.getSummary();
    console.log('\n📊 Network Monitor Summary:');
    console.log(`   Total Requests: ${summary.total}`);
    console.log(`   Successful: ${summary.successful}`);
    console.log(`   Failed: ${summary.failed}`);
  }
}
