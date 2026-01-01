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

  // Opt out of parallel tests on CI
  workers: 1, // Single worker to avoid session conflicts

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

    // Collect trace when retrying the failed test
    trace: 'on-first-retry',

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
