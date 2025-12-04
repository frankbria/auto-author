/**
 * Global Teardown for E2E Tests
 *
 * Cleans up test data after all tests complete.
 */

import { cleanupTestBooks, cleanupTestChapters } from './fixtures/test-data.fixture';

/**
 * Global teardown function
 */
export default async function globalTeardown() {
  console.log('\n🧹 Running global teardown...\n');

  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Note: If using real authentication, you'd need to get a valid token here
  // For BYPASS_AUTH mode, token is not required
  const authToken = process.env.TEST_AUTH_TOKEN;

  try {
    // Clean up test books
    await cleanupTestBooks(baseUrl, authToken);

    // Clean up test chapters
    await cleanupTestChapters(baseUrl, authToken);

    console.log('\n✅ Global teardown complete\n');
  } catch (error) {
    console.error('\n❌ Error during global teardown:', error);
    // Don't throw - teardown errors shouldn't fail the test suite
  }
}
