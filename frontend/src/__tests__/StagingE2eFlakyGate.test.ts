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

  it('keeps retries so a transient failure is still absorbed', () => {
    // The count is free to change; retries existing at all in CI is the point.
    // They no longer buy a trace under CI — see the trace guard above (#599).
    expect(config).toMatch(/^\s*retries:\s*process\.env\.CI\s*\?\s*[1-9]\d*\s*:\s*0,\s*$/m);
  });

  // #599: a trace records request headers (session cookie) and action arguments
  // (the password passed to fill()), and `test-results/` is uploaded from a public
  // repo. This is a security setting, not a debugging preference. Off under CI
  // only — locally nothing is published, so traces stay available for debugging.
  it('keeps traces off under CI so artifacts cannot carry credentials', () => {
    expect(config).toMatch(/^\s*trace:\s*process\.env\.CI\s*\?\s*'off'\s*:/m);
  });

  // A `--trace` flag on the command line overrides the config outright, so the
  // setting above is only a control if nothing re-enables it at the call site.
  it('does not re-enable tracing from the npm script', () => {
    const pkg = readFileSync(path.join(__dirname, '../../package.json'), 'utf8');
    const script = JSON.parse(pkg).scripts['test:e2e:staging'] as string;
    expect(script).toContain('tests/e2e/staging/playwright.config.ts');
    expect(script).not.toMatch(/--trace/);
  });

  it('clamps workers so the sign-in bootstrap cannot 429 itself', () => {
    // Each worker signs in once at startup and better-auth allows 3 per 10s per
    // IP, so the ceiling must stay at 2 — 3 leaves no room for a worker restart.
    expect(config).toMatch(/^\s*workers:\s*Math\.max\(1,\s*Math\.min\(2,/m);
  });
});
