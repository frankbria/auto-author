/**
 * Pre-Flight Health Checks
 *
 * Validates that the deployment environment is healthy before running full test suite.
 * Tests API endpoints, CORS configuration, and basic connectivity.
 *
 * Based on DEPLOYMENT-TESTING-CHECKLIST.md Pre-Flight Checks section.
 */

import { test, expect } from '@playwright/test';

const API_BASE_URL = process.env.DEPLOYMENT_URL?.replace('https://', 'https://api.') || 'http://localhost:8000';
const FRONTEND_URL = process.env.DEPLOYMENT_URL || 'http://localhost:3000';

test.describe('Pre-Flight Health Checks', () => {
  test('Backend API Health', async ({ request }) => {
    console.log(`\n🏥 Testing backend health: ${API_BASE_URL}`);

    const response = await request.get(`${API_BASE_URL}/`);

    // Verify 200 OK status
    expect(response.status(), 'Backend should return 200 OK').toBe(200);

    // Verify response body
    const body = await response.json();
    expect(body.message).toContain('Welcome to the Auto Author API');

    console.log('✅ Backend API is healthy');
  });

  test('CORS Configuration - Frontend to API', async ({ request }) => {
    console.log(`\n🔒 Testing CORS: ${FRONTEND_URL} → ${API_BASE_URL}`);

    // Send OPTIONS preflight request
    const response = await request.fetch(`${API_BASE_URL}/api/v1/books/`, {
      method: 'OPTIONS',
      headers: {
        'Origin': FRONTEND_URL,
        'Access-Control-Request-Method': 'GET',
      }
    });

    const headers = response.headers();

    // Verify CORS headers
    expect(
      headers['access-control-allow-origin'],
      'CORS should allow frontend origin'
    ).toBe(FRONTEND_URL);

    expect(
      headers['access-control-allow-credentials'],
      'CORS should allow credentials'
    ).toBe('true');

    console.log('✅ CORS configuration is correct');
    console.log(`   Allow-Origin: ${headers['access-control-allow-origin']}`);
    console.log(`   Allow-Credentials: ${headers['access-control-allow-credentials']}`);
  });

  test('API Books Endpoint - Reachable', async ({ request }) => {
    console.log(`\n📚 Testing books API: ${API_BASE_URL}/api/v1/books/`);

    // This should return 401 Unauthorized (no auth token), not 500 or network error
    const response = await request.get(`${API_BASE_URL}/api/v1/books/`);

    // Accept 200 (if auth not required), 401 (auth required), or 403 (forbidden)
    const validStatuses = [200, 401, 403];
    expect(
      validStatuses.includes(response.status()),
      `Books API should return 200, 401, or 403, not ${response.status()}`
    ).toBeTruthy();

    // Should NOT be 500 Internal Server Error
    expect(response.status()).not.toBe(500);

    console.log(`✅ Books API is reachable (status: ${response.status()})`);
  });

  test('Frontend - Loads Without Errors', async ({ page }) => {
    console.log(`\n🌐 Testing frontend: ${FRONTEND_URL}`);

    const consoleErrors: string[] = [];

    // Monitor console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Navigate to frontend
    await page.goto(FRONTEND_URL);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Verify no console errors
    expect(
      consoleErrors,
      `Expected no console errors, but found: ${consoleErrors.join(', ')}`
    ).toHaveLength(0);

    // Verify page loaded (should have Sign In button)
    await expect(page.locator('text=Sign In')).toBeVisible({ timeout: 5000 });

    console.log('✅ Frontend loads without errors');
  });

  test('CSP Headers - Frontend', async ({ request }) => {
    console.log(`\n🛡️ Testing CSP headers: ${FRONTEND_URL}`);

    const response = await request.get(FRONTEND_URL);
    const headers = response.headers();
    const csp = headers['content-security-policy'];

    // Verify CSP header exists
    expect(csp, 'Content-Security-Policy header should exist').toBeTruthy();

    // Verify key directives
    expect(csp).toContain('connect-src');
    expect(csp).toContain('api.dev.autoauthor.app');
    expect(csp).toContain('script-src');
    expect(csp).toContain('clerk.accounts.dev');

    console.log('✅ Frontend CSP headers are configured');
  });

  test('CSP Headers - Backend API Docs', async ({ request }) => {
    console.log(`\n🛡️ Testing API docs CSP: ${API_BASE_URL}/docs`);

    const response = await request.get(`${API_BASE_URL}/docs`);
    const headers = response.headers();
    const csp = headers['content-security-policy'];

    // Verify CSP header exists
    expect(csp, 'Content-Security-Policy header should exist').toBeTruthy();

    // Verify key directives for Swagger UI
    expect(csp).toContain('script-src');
    expect(csp).toContain('cdn.jsdelivr.net');
    expect(csp).toContain('style-src');
    expect(csp).toContain('img-src');

    console.log('✅ Backend API docs CSP headers are configured');
  });

  test('Swagger UI - Loads Without Errors', async ({ page }) => {
    console.log(`\n📖 Testing Swagger UI: ${API_BASE_URL}/docs`);

    const cspViolations: string[] = [];

    // Monitor for CSP violations
    page.on('console', msg => {
      const text = msg.text();
      if (text.toLowerCase().includes('refused to') || text.toLowerCase().includes('csp')) {
        cspViolations.push(text);
      }
    });

    // Navigate to Swagger UI
    await page.goto(`${API_BASE_URL}/docs`);

    // Wait for Swagger UI to load
    await page.waitForSelector('.swagger-ui', { timeout: 15000 });

    // Verify no CSP violations
    expect(
      cspViolations,
      `Expected no CSP violations, but found: ${cspViolations.join(', ')}`
    ).toHaveLength(0);

    // Verify Swagger UI is visible (not blank/white page)
    const swaggerUI = page.locator('.swagger-ui');
    await expect(swaggerUI).toBeVisible();

    // Verify can expand/collapse endpoints
    const firstEndpoint = page.locator('.opblock').first();
    await expect(firstEndpoint).toBeVisible();

    console.log('✅ Swagger UI loads without CSP errors');
  });
});

/**
 * Pre-Flight Summary
 *
 * This test suite validates:
 * ✅ Backend API is healthy and accessible
 * ✅ CORS configuration allows frontend → backend communication
 * ✅ API endpoints are reachable (not returning 500 errors)
 * ✅ Frontend loads without console errors
 * ✅ CSP headers are properly configured (frontend & backend)
 * ✅ Swagger UI documentation is accessible
 *
 * If all pre-flight checks pass, the deployment is healthy and ready for full testing.
 */
