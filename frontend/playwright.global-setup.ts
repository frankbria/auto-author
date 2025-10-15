import { chromium, FullConfig } from '@playwright/test';

/**
 * Playwright global setup - handles authentication bypass for E2E tests
 *
 * This setup runs once before all tests and configures the browser context
 * to bypass Clerk authentication using environment variables.
 */
async function globalSetup(config: FullConfig) {
  console.log('🔧 Global Setup: Configuring E2E test environment');

  // Verify BYPASS_AUTH is set
  if (process.env.BYPASS_AUTH !== 'true') {
    console.warn('⚠️  BYPASS_AUTH not set - tests may fail due to authentication');
  }

  // Verify NEXT_PUBLIC_BYPASS_AUTH is set for client-side detection
  if (process.env.NEXT_PUBLIC_BYPASS_AUTH !== 'true') {
    console.warn('⚠️  NEXT_PUBLIC_BYPASS_AUTH not set - dashboard may require auth');
  }

  console.log('✅ Global Setup: Environment configured');
  console.log(`   - BYPASS_AUTH: ${process.env.BYPASS_AUTH}`);
  console.log(`   - NEXT_PUBLIC_BYPASS_AUTH: ${process.env.NEXT_PUBLIC_BYPASS_AUTH}`);
  console.log(`   - NODE_ENV: ${process.env.NODE_ENV || 'development'}`);

  return;
}

export default globalSetup;
