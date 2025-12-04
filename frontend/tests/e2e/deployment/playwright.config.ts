import { defineConfig, devices } from '@playwright/test';
import * as dotenv from 'dotenv';
import * as path from 'path';

// Load environment variables from .env.local (for test credentials)
dotenv.config({ path: path.resolve(__dirname, '../../../.env.local') });

/**
 * Playwright Configuration for Deployment Testing
 *
 * This config is specifically for automated deployment validation tests.
 * It runs sequentially (not parallel) to simulate real user flows and
 * supports longer timeouts for AI operations (TOC generation, draft generation).
 */
export default defineConfig({
  testDir: '../deployment',

  // Global teardown for test data cleanup
  globalTeardown: '../global-teardown.ts',

  // Longer timeout for AI operations (TOC generation, draft generation)
  timeout: 120000, // 2 minutes

  // Sequential execution for deployment tests (simulates real user journey)
  fullyParallel: false,

  // Retry failed tests for reliability
  retries: 2,

  // Single worker for sequential execution
  workers: 1,

  // Reporters for CI/CD and local development
  reporter: [
    ['html', { outputFolder: '../artifacts/reports', open: 'never' }],
    ['json', { outputFile: '../artifacts/results.json' }],
    ['list'] // Console output
  ],

  use: {
    // Base URL from environment or default to dev
    baseURL: process.env.DEPLOYMENT_URL || 'https://dev.autoauthor.app',

    // Trace on failure for debugging
    trace: 'retain-on-failure',

    // Screenshot on failure
    screenshot: 'only-on-failure',

    // Video on failure
    video: 'retain-on-failure',

    // Navigation timeout
    navigationTimeout: 30000,

    // Action timeout
    actionTimeout: 10000,
  },

  // Test match pattern
  testMatch: /.*\.spec\.ts/,

  // Projects - Desktop Chrome only for deployment tests
  projects: [
    {
      name: 'deployment-chrome',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 },
      },
    },
  ],

  // Web server configuration (if needed for local testing)
  // webServer: {
  //   command: 'npm run dev',
  //   url: 'http://localhost:3000',
  //   reuseExistingServer: !process.env.CI,
  // },
});
