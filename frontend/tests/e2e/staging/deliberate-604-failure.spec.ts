import { test, expect } from './fixtures/auth.fixture';

/**
 * #604 item 1: a deliberately failing authenticated staging test, on a throwaway
 * branch that is never merged. It signs in through the real auth fixture, opens
 * the dashboard, and asserts text that does not exist, so Playwright writes its
 * failure outputs (screenshot, video, error-context.md). The published artifact
 * is then inspected for the excluded files and any readable credential.
 */
test('deliberate #604 failure after sign-in', async ({ authenticatedPage: page }) => {
  await page.goto('/dashboard');
  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.getByText('deliberate-604-failure-marker')).toBeVisible({ timeout: 3000 });
});
