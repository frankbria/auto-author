import { defineConfig, devices } from '@playwright/test';

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
    command: 'BYPASS_AUTH=true NEXT_PUBLIC_BYPASS_AUTH=true npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
    env: {
      BYPASS_AUTH: 'true',
      NEXT_PUBLIC_BYPASS_AUTH: 'true'
      // Keep NODE_ENV as development to load .env.local with Clerk keys
    }
  },

  expect: {
    timeout: 10000,
  },

  timeout: 30000,
});
