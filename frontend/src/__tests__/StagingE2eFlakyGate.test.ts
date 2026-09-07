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

  // Anchored to a whole line so a commented-out setting, or a truthy value with
  // something appended (`!!process.env.CI && false`), does not satisfy the guard.
  it('fails the run on flaky tests in CI', () => {
    expect(config).toMatch(/^\s*failOnFlakyTests:\s*!!process\.env\.CI,\s*$/m);
  });

  it('keeps retries so the retry trace is still captured', () => {
    // The count is free to change; retries existing at all in CI is the point.
    expect(config).toMatch(/^\s*retries:\s*process\.env\.CI\s*\?\s*[1-9]\d*\s*:\s*0,\s*$/m);
  });

  // #599: a trace records request headers (session cookie) and action arguments
  // (the password passed to fill()), and `test-results/` is uploaded from a public
  // repo. This is a security setting, not a debugging preference.
  it('keeps traces off so artifacts cannot carry credentials', () => {
    expect(config).toMatch(/^\s*trace:\s*'off',\s*$/m);
  });

  it('clamps workers so the sign-in bootstrap cannot 429 itself', () => {
    // Each worker signs in once at startup and better-auth allows 3 per 10s per
    // IP, so the ceiling must stay at 2 — 3 leaves no room for a worker restart.
    expect(config).toMatch(/^\s*workers:\s*Math\.max\(1,\s*Math\.min\(2,/m);
  });
});
