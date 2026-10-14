/**
 * Smoke Test - Verify basic app functionality
 * Simplified test to diagnose authentication and routing issues
 */

import { test, expect } from '@playwright/test';

test.describe('Smoke Test', () => {
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
