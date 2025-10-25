import { defineConfig, devices } from '@playwright/test';
import * as dotenv from 'dotenv';
import * as path from 'path';

// Load .env.test file for E2E test environment
dotenv.config({ path: path.resolve(__dirname, '.env.test') });

/**
 * Cross-browser E2E testing configuration for Auto-Author
 * Covers interview-style prompts functionality across different browsers
 */
export default defineConfig({
  testDir: './src/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  globalSetup: require.resolve('./playwright.global-setup.ts'),
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/results.xml' }]
  ],

  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure'
  },

  projects: [
    // Desktop browsers
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    // Mobile devices
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },

    // Tablet devices
    {
      name: 'Mobile Safari iPad',
      use: { ...devices['iPad Pro'] },
    },

    // High-DPI displays
    {
      name: 'High DPI Chrome',
      use: {
        ...devices['Desktop Chrome HiDPI'],
      },
    },

    // Edge cases
    {
      name: 'Chrome with reduced motion',
      use: {
        ...devices['Desktop Chrome'],
        extraHTTPHeaders: {
          'prefers-reduced-motion': 'reduce'
        }
      },
    },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
    env: {
      // E2E test environment variables (loaded from .env.test)
      BYPASS_AUTH: process.env.BYPASS_AUTH || 'true',
      NEXT_PUBLIC_BYPASS_AUTH: process.env.NEXT_PUBLIC_BYPASS_AUTH || 'true',
      // Clerk configuration (with fallback defaults for E2E tests)
      NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || 'pk_test_ZGVsaWNhdGUtbGFkeWJpcmQtNDcuY2xlcmsuYWNjb3VudHMuZGV2JA',
      CLERK_SECRET_KEY: process.env.CLERK_SECRET_KEY || 'sk_test_yxycVoEwI4EzhsYAJ8g0Re8VBKClBrfoQC5OTnS6zE',
      // API configuration
      NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
      // Environment
      NEXT_PUBLIC_ENVIRONMENT: process.env.NEXT_PUBLIC_ENVIRONMENT || 'test',
      NODE_ENV: process.env.NODE_ENV || 'test'
    }
  },

  expect: {
    timeout: 10000,
  },

  timeout: 30000,
});
