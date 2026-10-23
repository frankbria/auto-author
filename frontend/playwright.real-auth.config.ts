import { defineConfig, devices } from '@playwright/test';
import * as path from 'path';

/**
 * Real authentication, no bypass (#843).
 *
 * The main E2E suite runs with BYPASS_AUTH, so nothing required ever exercised
 * the chain a real user depends on: better-auth signs a cookie, the backend
 * verifies it, finds the session, and scopes data to that user. This config
 * starts its own backend and frontend with the bypass off, on their own ports
 * and their own database, and the spec signs up through the page.
 *
 * Run: npx playwright test --config=playwright.real-auth.config.ts
 * Needs MongoDB on localhost:27017 and `uv` for the backend.
 */

export const WEB = 'http://localhost:3001';
export const API = 'http://localhost:8001/api/v1';
// The frontend's output. With no email provider the development server prints
// each email there, which is how the spec gets the verification link.
export const FRONTEND_LOG = path.resolve(__dirname, 'test-results/real-auth-frontend.log');
const BACKEND_LOG = path.resolve(__dirname, 'test-results/real-auth-backend.log');
// Lines the frontend's MongoDB driver turns into failures (#972); see src/e2e/real-auth/mongo-faults.cjs.
export const MONGO_FAULTS = path.resolve(__dirname, 'test-results/real-auth-mongo-faults');

export const MONGO = process.env.E2E_MONGODB_URI || 'mongodb://localhost:27017';
export const DATABASE = 'auto_author_e2e_real_auth';
const SECRET =
  process.env.BETTER_AUTH_SECRET || 'test-secret-for-ci-minimum-32-characters-long-safe-for-testing';

// Stated explicitly so a bypass set in the calling shell cannot leak in.
const NO_BYPASS = {
  BYPASS_AUTH: 'false',
  NEXT_PUBLIC_BYPASS_AUTH: 'false',
  E2E_ALLOW_BYPASS: '0',
};

export default defineConfig({
  testDir: './src/e2e/real-auth',
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list']],
  outputDir: 'test-results/real-auth',
  // `next dev` compiles each page on first request.
  timeout: 240_000,
  expect: { timeout: 60_000 },
  use: {
    baseURL: WEB,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `mkdir -p "${path.dirname(BACKEND_LOG)}" && uv run uvicorn app.main:app --host 127.0.0.1 --port 8001 > "${BACKEND_LOG}" 2>&1`,
      cwd: path.resolve(__dirname, '../backend'),
      url: `${API}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ...NO_BYPASS,
        ENVIRONMENT: 'test',
        MONGODB_URI: MONGO,
        DATABASE_NAME: DATABASE,
        BETTER_AUTH_SECRET: SECRET,
        BETTER_AUTH_URL: WEB,
        BACKEND_CORS_ORIGINS: WEB,
      },
    },
    {
      // `next dev`, not a build: NEXT_PUBLIC_* values are read at start, so this
      // frontend can point at its own backend without a second build.
      command: `mkdir -p "${path.dirname(FRONTEND_LOG)}" && npx next dev --webpack --port 3001 > "${FRONTEND_LOG}" 2>&1`,
      url: `${WEB}/api/health`,
      reuseExistingServer: false,
      timeout: 240_000,
      env: {
        ...NO_BYPASS,
        DATABASE_URL: MONGO,
        DATABASE_NAME: DATABASE,
        BETTER_AUTH_SECRET: SECRET,
        BETTER_AUTH_URL: WEB,
        NEXT_PUBLIC_BETTER_AUTH_URL: WEB,
        NEXT_PUBLIC_API_URL: API,
        NEXT_PUBLIC_ENVIRONMENT: 'test',
        // Unset on purpose: with no provider, development prints emails.
        EMAIL_SERVICE_PROVIDER: '',
        NODE_OPTIONS: `--require ${path.resolve(__dirname, 'src/e2e/real-auth/mongo-faults.cjs')}`,
        E2E_MONGO_FAULTS: MONGO_FAULTS,
      },
    },
  ],
});
