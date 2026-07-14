/**
 * Profile Editing E2E (issue #63)
 *
 * Covers the profile page end to end with mocked backend (deterministic, no
 * real auth/DB): load profile → edit fields → Save (asserts PATCH payload) →
 * success toast; and avatar upload (asserts POST /users/me/avatar + image
 * updates). `/profile` is not behind middleware, so no auth bypass is needed.
 */

import { test, expect } from '@playwright/test';

const PROFILE = {
  id: 'u1',
  auth_id: 'u1',
  email: 'ada@example.com',
  first_name: 'Ada',
  last_name: 'Lovelace',
  display_name: 'Ada L.',
  avatar_url: null,
  bio: 'Original bio',
  preferences: { theme: 'dark', email_notifications: true, marketing_emails: false },
};

test.describe('Profile editing (issue #63)', () => {
  test('loads, edits, and saves the profile', async ({ page }) => {
    let patchedBody: Record<string, unknown> | null = null;

    await page.route('**/users/me', (route) => {
      const method = route.request().method();
      if (method === 'PATCH') {
        patchedBody = route.request().postDataJSON();
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ...PROFILE, ...(patchedBody as object) }),
        });
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(PROFILE),
      });
    });

    await page.goto('/profile');

    // Form hydrates from the mocked GET /users/me.
    const firstName = page.locator('#firstName');
    await expect(firstName).toHaveValue('Ada');
    await expect(page.locator('#bio')).toHaveValue('Original bio');
    await expect(page.locator('#displayName')).toHaveValue('Ada L.');

    // Edit and save.
    await firstName.fill('Grace');
    await page.locator('#displayName').fill('Grace H.');
    await page.locator('#bio').fill('New bio about writing');
    await page.getByRole('button', { name: /save changes/i }).click();

    await expect.poll(() => patchedBody?.first_name).toBe('Grace');
    expect(patchedBody?.display_name).toBe('Grace H.');
    expect(patchedBody?.bio).toBe('New bio about writing');
    await expect(page.getByText('Profile updated')).toBeVisible();
  });

  test('seeds display name from full name when unset (no truncation on save)', async ({ page }) => {
    await page.route('**/users/me', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...PROFILE, display_name: null }),
      })
    );

    await page.goto('/profile');
    // Must seed "Ada Lovelace", not "Ada" — a save persists this value and
    // exports prefer display_name over the first/last fallback.
    await expect(page.locator('#displayName')).toHaveValue('Ada Lovelace');
  });

  test('uploads a profile picture', async ({ page }) => {
    let avatarPosted = false;

    await page.route('**/users/me', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(PROFILE),
      })
    );
    await page.route('**/users/me/avatar', (route) => {
      avatarPosted = true;
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Profile picture updated', avatar_url: 'https://cdn/new-avatar.png' }),
      });
    });

    await page.goto('/profile');
    await expect(page.locator('#firstName')).toHaveValue('Ada');

    await page.setInputFiles('[data-testid="avatar-input"]', {
      name: 'avatar.png',
      mimeType: 'image/png',
      buffer: Buffer.from('89504e470d0a1a0a', 'hex'),
    });

    await expect.poll(() => avatarPosted).toBe(true);
    await expect(page.getByAltText('Profile picture')).toHaveAttribute(
      'src',
      /new-avatar\.png/
    );
  });

  test('account deletion requires typing the account email (#216)', async ({ page }) => {
    let deleteRequested = false;

    await page.route('**/users/me', (route) => {
      if (route.request().method() === 'DELETE') {
        deleteRequested = true;
        return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(PROFILE),
      });
    });

    await page.goto('/profile');
    await expect(page.locator('#firstName')).toHaveValue('Ada');

    await page.getByRole('button', { name: /^delete account$/i }).click();

    const confirmButton = page.getByRole('button', { name: /delete account permanently/i });
    const confirmInput = page.locator('#confirm-delete-account');

    // Disabled with no input, and stays disabled on a wrong phrase.
    await expect(confirmButton).toBeDisabled();
    await confirmInput.fill('wrong@example.com');
    await expect(confirmButton).toBeDisabled();
    await expect(page.getByText(/must match exactly/i)).toBeVisible();
    expect(deleteRequested).toBe(false);

    // Exact account email enables deletion; confirming issues the DELETE.
    await confirmInput.fill(PROFILE.email);
    await expect(confirmButton).toBeEnabled();
    await confirmButton.click();
    await expect.poll(() => deleteRequested).toBe(true);
  });
});
