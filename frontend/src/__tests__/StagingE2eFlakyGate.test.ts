import { readFileSync } from 'fs';
import path from 'path';

/**
 * Issue #551 (AC#4): the staging suite retries, so a canary that only passes on
 * retry used to report `1 flaky` and still exit `success`. `failOnFlakyTests`
 * turns that back into a red job. Retries stay on for the trace, but they can no
 * longer hide a regression.
 *
 * Guards the decision against a silent revert — a config flag has no runtime
 * behaviour to assert on locally.
 */
describe('staging E2E flaky gate', () => {
  const config = readFileSync(
    path.join(__dirname, '../../tests/e2e/staging/playwright.config.ts'),
    'utf8'
  );

  it('fails the run on flaky tests in CI', () => {
    expect(config).toMatch(/failOnFlakyTests:\s*!!process\.env\.CI/);
  });

  it('keeps retries so the retry trace is still captured', () => {
    // The count is free to change; retries existing at all in CI is the point.
    expect(config).toMatch(/retries:\s*process\.env\.CI\s*\?\s*[1-9]\d*\s*:\s*0/);
  });

  it('caps workers so the sign-in bootstrap cannot 429 itself', () => {
    // Each worker signs in once at startup; better-auth allows 3 per 10s per IP.
    expect(config).toMatch(/workers:\s*Math\.min\(3,/);
  });
});
