import { expect, test } from '@playwright/test';
import { MongoClient } from 'mongodb';
import { DATABASE, MONGO, WEB } from '../../../playwright.real-auth.config';
import { TERMS_VERSION } from '../../lib/constants/legal';
import { signUpAndVerify } from './helpers';

/**
 * An existing account accepts a new Terms version once, at its next visit (#961).
 *
 * The database is touched only to make the account's record older than the
 * current Terms, the state a TERMS_VERSION bump leaves every existing account in.
 */

let mongo: MongoClient;
test.beforeAll(async () => {
  mongo = await new MongoClient(MONGO).connect();
});
test.afterAll(async () => {
  await mongo.close();
});
const users = () => mongo.db(DATABASE).collection('users');

for (const [label, staleRecord] of [
  ['an older version', { $set: { termsVersion: '2000-01-01', termsAcceptedAt: new Date(0) } }],
  ['no record (before #789)', { $unset: { termsVersion: '', termsAcceptedAt: '' } }],
] as const) {
  test(`an account with ${label} accepts the current Terms once`, async ({ page }) => {
    const email = `terms-${Date.now()}-${label.length}@example.com`;
    await signUpAndVerify(page, email);
    await expect(page.getByRole('heading', { name: /accept the terms/i })).toHaveCount(0);

    await users().updateOne({ email }, staleRecord);
    await page.reload();

    const accept = page.getByRole('button', { name: 'I accept the Terms of Service' });
    const heading = page.getByRole('heading', { level: 1, name: 'Please accept the Terms of Service' });
    await expect(heading).toBeVisible();
    await expect(page.getByRole('link', { name: /read the terms of service/i })).toHaveAttribute('href', '/terms');

    const before = Date.now();
    await accept.click();
    // The screen goes once the session reloads, after the server has recorded it.
    await expect(heading).toHaveCount(0);
    await expect(page).toHaveURL(/\/dashboard/);

    // Recorded server-side on the one users document the backend also reads
    // (#1263; backend test_terms_acceptance.py covers its user and retained record).
    const doc = await users().findOne({ email });
    expect(doc?.termsVersion).toBe(TERMS_VERSION);
    expect((doc?.termsAcceptedAt as Date).getTime()).toBeGreaterThanOrEqual(before - 1000);

    // Asked once: the next visit goes straight to the page.
    await page.reload();
    await expect(page.getByRole('heading', { level: 1, name: /accept the terms/i })).toHaveCount(0);
  });
}

test('the browser cannot choose the version it accepts, or accept for another site', async ({
  page,
}) => {
  const email = `terms-forged-${Date.now()}@example.com`;
  await signUpAndVerify(page, email);
  await users().updateOne({ email }, { $set: { termsVersion: '2000-01-01' } });
  const userId = String((await users().findOne({ email }))?._id);

  const crossSite = await page.request.post(`${WEB}/api/auth/terms/accept`, {
    headers: { Origin: 'https://evil.example' },
    data: { version: TERMS_VERSION, userId },
  });
  expect(crossSite.status()).toBe(403);
  expect((await users().findOne({ email }))?.termsVersion).toBe('2000-01-01');

  // A screen showing older Terms (left open across a deploy) is refused.
  const stale = await page.request.post(`${WEB}/api/auth/terms/accept`, {
    headers: { Origin: WEB },
    data: { version: '2000-01-01', userId },
  });
  expect(stale.status()).toBe(409);
  // So is a screen shown to another account, before this one signed in.
  const otherAccount = await page.request.post(`${WEB}/api/auth/terms/accept`, {
    headers: { Origin: WEB },
    data: { version: TERMS_VERSION, userId: 'someone-else' },
  });
  expect(otherAccount.status()).toBe(409);
  expect((await users().findOne({ email }))?.termsVersion).toBe('2000-01-01');

  const forged = await page.request.post(`${WEB}/api/auth/terms/accept`, {
    headers: { Origin: WEB },
    data: {
      version: TERMS_VERSION,
      userId,
      termsVersion: '2999-01-01',
      termsAcceptedAt: '1999-01-01T00:00:00Z',
    },
  });
  expect(forged.status()).toBe(200);
  const doc = await users().findOne({ email });
  expect(doc?.termsVersion).toBe(TERMS_VERSION);
  expect((doc?.termsAcceptedAt as Date).getFullYear()).toBeGreaterThan(2000);
});

test('a request without a session is refused', async ({ request }) => {
  const res = await request.post(`${WEB}/api/auth/terms/accept`, {
    headers: { Origin: WEB },
    data: { version: TERMS_VERSION, userId: 'anyone' },
  });
  expect(res.status()).toBe(401);
});

test('an account that does not accept can still reach billing and its data, but is asked on landing there', async ({
  page,
}) => {
  const email = `terms-exits-${Date.now()}@example.com`;
  await signUpAndVerify(page, email);
  await users().updateOne({ email }, { $set: { termsVersion: '2000-01-01' } });
  const heading = page.getByRole('heading', { level: 1, name: 'Please accept the Terms of Service' });

  // A sign-in that lands straight on Settings is still asked.
  await page.goto('/dashboard/settings');
  await expect(heading).toBeVisible();

  // The screen's own link opens Billing, where the subscription is cancelled.
  await page.getByRole('link', { name: 'cancel your subscription' }).click();
  await expect(page).toHaveURL(/\/dashboard\/settings\?tab=billing/);
  await expect(page.getByRole('tab', { name: 'Billing' })).toHaveAttribute('aria-selected', 'true');
  await expect(heading).toHaveCount(0);

  // Any other page asks again; nothing was recorded.
  await page.goto('/dashboard');
  await expect(heading).toBeVisible();
  await page.getByRole('link', { name: 'download your data or delete your account' }).click();
  await expect(page).toHaveURL(/\/profile$/);
  await expect(page.getByRole('button', { name: /download my data/i })).toBeVisible();
  expect((await users().findOne({ email }))?.termsVersion).toBe('2000-01-01');
});

// From the screen shown on /profile itself, the link points at the same URL.
test('the data and deletion link works from the screen shown on the profile itself', async ({
  page,
}) => {
  const email = `terms-exits-profile-${Date.now()}@example.com`;
  await signUpAndVerify(page, email);
  await users().updateOne({ email }, { $set: { termsVersion: '2000-01-01' } });

  await page.goto('/profile');
  const heading = page.getByRole('heading', { level: 1, name: 'Please accept the Terms of Service' });
  await expect(heading).toBeVisible();
  await page.getByRole('link', { name: 'download your data or delete your account' }).click();
  await expect(page.getByRole('button', { name: /download my data/i })).toBeVisible();
  await expect(heading).toHaveCount(0);
});
