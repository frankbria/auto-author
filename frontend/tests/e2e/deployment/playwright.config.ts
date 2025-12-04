import { defineConfig, devices } from '@playwright/test';
import * as dotenv from 'dotenv';
import * as path from 'path';

// Load environment variables from .env.local (for test credentials)
dotenv.config({ path: path.resolve(__dirname, '../../../.env.local') });

// Determine if we're testing against a deployed environment or local
const isDeploymentTest = !!process.env.DEPLOYMENT_URL;
const baseURL = process.env.DEPLOYMENT_URL || 'http://localhost:3000';

/**
 * Playwright Configuration for E2E Testing
 *
 * Default: Spins up local frontend + backend for true E2E testing
 * With DEPLOYMENT_URL: Tests against deployed environment (smoke tests)
 */
export default defineConfig({
  testDir: '../deployment',

  // Global teardown for test data cleanup
  globalTeardown: '../global-teardown.ts',

  // Longer timeout for AI operations (TOC generation, draft generation)
  timeout: 120000, // 2 minutes

  // Sequential execution (simulates real user journey)
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
    baseURL,

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

  // Projects - Desktop Chrome only for E2E tests
  projects: [
    {
      name: 'deployment-chrome',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 },
      },
    },
  ],

  // Web server configuration - spins up both backend and frontend
  // Only used when not testing against a deployed environment
  webServer: isDeploymentTest ? undefined : [
    {
      // Backend API server
      command: 'cd ../../../../backend && uv run uvicorn app.main:app --port 8000 --host 0.0.0.0',
      url: 'http://localhost:8000/health',
      reuseExistingServer: !process.env.CI,
      timeout: 60000, // 60s to start backend
    },
    {
      // Frontend Next.js server
      command: 'cd ../../.. && NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 npm run dev',
      url: 'http://localhost:3000',
      reuseExistingServer: !process.env.CI,
      timeout: 60000, // 60s to start frontend
      env: {
        NEXT_PUBLIC_API_URL: 'http://localhost:8000/api/v1',
      },
    },
  ],
});
