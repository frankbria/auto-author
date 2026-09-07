import { defineConfig, devices } from '@playwright/test';
import * as dotenv from 'dotenv';
import * as path from 'path';

// Load test environment variables from the staging directory
dotenv.config({ path: path.join(__dirname, '.env.test') });

/**
 * Playwright configuration for staging E2E tests
 *
 * Tests run against https://dev.autoauthor.app with real Better-auth authentication
 *
 * Required environment variables:
 * - STAGING_TEST_EMAIL: Test user email for staging
 * - STAGING_TEST_PASSWORD: Test user password for staging
 */
export default defineConfig({
  testDir: '.',

  // Maximum time one test can run
  timeout: 180 * 1000, // 3 minutes per test

  // Run tests in files in parallel
  fullyParallel: false, // Sequential for staging to avoid conflicts

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 2 : 0,

  // #551: retries stay on so a genuinely transient failure still yields a trace,
  // but a test that only passes on retry now fails the job instead of reporting
  // `1 flaky` and exiting success. The #83 session canary is the spec most likely
  // to catch an auth-path break; it must not be able to be green-on-retry.
  failOnFlakyTests: !!process.env.CI,

  // Opt out of parallel tests on CI. Single worker by default to avoid session
  // conflicts; clamped to 1..2 because each worker signs in once at startup and
  // better-auth allows only 3 `/sign-in*` requests per 10s per IP (#551). Three
  // would fit but leave zero headroom: if Playwright replaces a crashed worker
  // mid-run, its bootstrap is a 4th sign-in inside the same window and 429s.
  // The clamp also absorbs a mistyped dispatch input (`0`, `-2`, `2.5`, `abc`).
  workers: Math.max(1, Math.min(2, Math.round(Number(process.env.STAGING_E2E_WORKERS) || 1))),

  // Reporter to use
  reporter: [
    ['html', { outputFolder: 'playwright-report-staging' }],
    ['list'],
    ['json', { outputFile: 'test-results/staging-results.json' }],
    ...(process.env.CI ? [['github' as const]] : []),
  ],

  // Shared settings for all the projects below
  use: {
    // Base URL for staging environment
    baseURL: 'https://dev.autoauthor.app',

    // #599: traces are OFF for staging, and this is a security setting, not a
    // preference. A trace records request headers, so every authenticated call
    // in it carries `Cookie: __Secure-better-auth.session_token=...`, and it
    // records action arguments, so `fill()` on the password field stores the
    // credential in plaintext. `test-results/` is uploaded as a CI artifact from
    // a public repo, which published both on every failure.
    //
    // Screenshot and video are kept: a password input renders masked, so neither
    // carries the credential. Reproduce a staging failure with a manual
    // `workflow_dispatch` rather than by turning this back on.
    trace: 'off',

    // Screenshot on failure
    screenshot: 'only-on-failure',

    // Video on failure
    video: 'retain-on-failure',

    // Viewport size
    viewport: { width: 1920, height: 1080 },

    // Browser context options
    ignoreHTTPSErrors: false,

    // Action timeout
    actionTimeout: 30 * 1000, // 30 seconds

    // Navigation timeout
    navigationTimeout: 30 * 1000, // 30 seconds
  },

  // Configure projects for major browsers
  projects: [
    {
      name: 'staging-chrome',
      use: {
        ...devices['Desktop Chrome'],
        // Better-auth uses httpOnly cookies - ensure they work
        contextOptions: {
          acceptDownloads: true,
        },
      },
    },

    // Uncomment to test on additional browsers
    // {
    //   name: 'staging-firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'staging-webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],

  // Run your local dev server before starting the tests
  // webServer: {
  //   command: 'npm run dev',
  //   url: 'http://localhost:3000',
  //   reuseExistingServer: !process.env.CI,
  // },
});
