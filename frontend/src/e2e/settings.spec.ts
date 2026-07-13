/**
 * Account settings E2E (issue #64)
 *
 * Covers the tabbed settings workflow end to end with a mocked backend
 * (deterministic, no real auth/DB): load stored preferences → edit writing/
 * export/notification options → Save (asserts the merged PATCH payload) →
 * success toast; plus the Security tab's password change against the
 * better-auth endpoint and the active-session list. Runs with BYPASS_AUTH=true.
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
  bio: 'Bio',
  preferences: {
    theme: 'dark',
    email_notifications: true,
    marketing_emails: false,
    default_writing_style: 'academic',
    auto_save_interval: 10,
    default_export_format: 'epub',
    default_page_size: 'A4',
    include_empty_chapters: true,
    writing_reminders: false,
    progress_updates: true,
    backup_notifications: true,
  },
};

const SESSION = {
  user: { id: 'u1', email: 'ada@example.com', name: 'Ada L.', twoFactorEnabled: false },
  session: { id: 's1', token: 'current-token', expiresAt: '2027-01-01T00:00:00Z' },
};

async function mockUsersMe(
  page: import('@playwright/test').Page,
  onPatch?: (body: Record<string, unknown>) => void
) {
  await page.route('**/users/me', (route) => {
    if (route.request().method() === 'PATCH') {
      const body = route.request().postDataJSON();
      onPatch?.(body);
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ...PROFILE,
          preferences: { ...PROFILE.preferences, ...(body.preferences as object) },
        }),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(PROFILE),
    });
  });
}

async function mockAuthSession(page: import('@playwright/test').Page) {
  await page.route('**/api/auth/get-session', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(SESSION),
    })
  );
}

test.describe('Account settings (issue #64)', () => {
  test('loads stored preferences, edits them, and saves the merged payload', async ({ page }) => {
    let patched: Record<string, unknown> | null = null;
    await mockAuthSession(page);
    await mockUsersMe(page, (body) => {
      patched = body;
    });

    await page.goto('/dashboard/settings');

    // Writing tab hydrates from the stored preferences
    const styleSelect = page.locator('#default-writing-style');
    await expect(styleSelect).toHaveValue('academic');
    await expect(page.locator('#auto-save-interval')).toHaveValue('10');
    await expect(page.locator('#editor-theme')).toHaveValue('dark');

    await styleSelect.selectOption('technical');
    await page.locator('#auto-save-interval').fill('15');

    // Notifications tab is gated "coming soon" — no delivery infra exists (#195)
    await page.getByRole('tab', { name: /notifications/i }).click();
    await expect(page.getByText('Coming soon')).toBeVisible();
    await expect(page.locator('#notification-writing_reminders')).toBeDisabled();
    await expect(page.locator('#notification-email_notifications')).toBeDisabled();

    await page.getByRole('button', { name: /save settings/i }).click();

    await expect.poll(() => patched).not.toBeNull();
    const prefs = (patched! as { preferences: Record<string, unknown> }).preferences;
    expect(prefs.default_writing_style).toBe('technical');
    expect(prefs.auto_save_interval).toBe(15);
    // Untouched stored values survive the merge — incl. the gated notification flags
    expect(prefs.writing_reminders).toBe(false);
    expect(prefs.default_export_format).toBe('epub');
    expect(prefs.marketing_emails).toBe(false);
    await expect(page.getByText('Settings saved')).toBeVisible();
  });

  test('export tab reflects stored defaults and hides page size for non-PDF', async ({ page }) => {
    await mockAuthSession(page);
    await mockUsersMe(page);

    await page.goto('/dashboard/settings');
    await expect(page.locator('#default-writing-style')).toHaveValue('academic');

    await page.getByRole('tab', { name: /export/i }).click();
    await expect(page.getByRole('radio', { name: 'EPUB' })).toBeChecked();
    await expect(page.locator('#include-empty-chapters')).toHaveAttribute('data-state', 'checked');
    // Page size applies to PDF only
    await expect(page.getByRole('radio', { name: 'Letter' })).toHaveCount(0);

    await page.getByRole('radio', { name: 'PDF' }).click();
    await expect(page.getByRole('radio', { name: 'A4' })).toBeChecked();
  });

  test('shows a destructive toast and keeps edits when the save fails', async ({ page }) => {
    await mockAuthSession(page);
    await page.route('**/users/me', (route) => {
      if (route.request().method() === 'PATCH') {
        return route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'boom' }),
        });
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(PROFILE),
      });
    });

    await page.goto('/dashboard/settings');
    await expect(page.locator('#default-writing-style')).toHaveValue('academic');
    await page.locator('#default-writing-style').selectOption('creative');
    await page.getByRole('button', { name: /save settings/i }).click();

    await expect(page.getByText('Save failed')).toBeVisible();
    // The edit is not lost on failure
    await expect(page.locator('#default-writing-style')).toHaveValue('creative');
  });

  test('security tab revokes another device session', async ({ page }) => {
    let revokedToken: string | null = null;
    await mockAuthSession(page);
    await mockUsersMe(page);
    await page.route('**/api/auth/list-sessions', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { token: 'current-token', userAgent: 'Chrome', updatedAt: '2026-07-01T00:00:00Z' },
          { token: 'other', userAgent: 'iPhone Mobile Safari', updatedAt: '2026-06-30T00:00:00Z' },
        ]),
      })
    );
    await page.route('**/api/auth/revoke-session', (route) => {
      revokedToken = (route.request().postDataJSON() as { token: string }).token;
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: true }),
      });
    });

    await page.goto('/dashboard/settings');
    await expect(page.locator('#default-writing-style')).toHaveValue('academic');
    await page.getByRole('tab', { name: /security/i }).click();

    await expect(page.getByText('Mobile device')).toBeVisible();
    await page.getByRole('button', { name: /^revoke$/i }).click();

    await expect.poll(() => revokedToken).toBe('other');
    await expect(page.getByText('Mobile device')).toHaveCount(0);
  });

  test('security tab changes the password through better-auth', async ({ page }) => {
    let changeBody: Record<string, unknown> | null = null;
    await mockAuthSession(page);
    await mockUsersMe(page);
    await page.route('**/api/auth/change-password', (route) => {
      changeBody = route.request().postDataJSON();
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: true }),
      });
    });
    await page.route('**/api/auth/list-sessions', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { token: 'current-token', userAgent: 'Chrome', updatedAt: '2026-07-01T00:00:00Z' },
          { token: 'other', userAgent: 'iPhone Mobile Safari', updatedAt: '2026-06-30T00:00:00Z' },
        ]),
      })
    );

    await page.goto('/dashboard/settings');
    await expect(page.locator('#default-writing-style')).toHaveValue('academic');
    await page.getByRole('tab', { name: /security/i }).click();

    // Active sessions render with the current device marked
    await expect(page.getByText('This device')).toBeVisible();
    await expect(page.getByText('Mobile device')).toBeVisible();

    // Change password
    await page.locator('#current-password').fill('old-password-1');
    await page.locator('#new-password').fill('brand-new-password');
    await page.locator('#confirm-password').fill('brand-new-password');
    await page.getByRole('button', { name: /change password/i }).click();

    await expect.poll(() => changeBody).not.toBeNull();
    expect(changeBody!.currentPassword).toBe('old-password-1');
    expect(changeBody!.newPassword).toBe('brand-new-password');
    expect(changeBody!.revokeOtherSessions).toBe(true);
    await expect(page.getByText('Password changed')).toBeVisible();
  });
});
