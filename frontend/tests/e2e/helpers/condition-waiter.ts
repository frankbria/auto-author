/**
 * Condition-Based Waiting Utilities
 *
 * Replaces arbitrary timeouts with smart condition-based waiting.
 */

import { Page, Locator, expect } from '@playwright/test';

export interface WaitOptions {
  timeout?: number;
  interval?: number;
}

/**
 * Wait for a condition to become true with polling
 *
 * @param condition Function that returns a boolean or Promise<boolean>
 * @param options Wait options (timeout, interval)
 * @returns True if condition met, false if timeout
 */
export async function waitForCondition(
  condition: () => boolean | Promise<boolean>,
  options: WaitOptions = {}
): Promise<boolean> {
  const { timeout = 10000, interval = 100 } = options;
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    const result = await condition();
    if (result) {
      return true;
    }
    await new Promise(resolve => setTimeout(resolve, interval));
  }

  return false;
}

/**
 * Wait for an element's text content to match a condition
 */
export async function waitForTextContent(
  locator: Locator,
  expectedText: string | RegExp,
  options: WaitOptions = {}
): Promise<void> {
  const { timeout = 10000 } = options;

  await waitForCondition(async () => {
    try {
      const text = await locator.textContent({ timeout: 1000 });
      if (!text) return false;

      if (typeof expectedText === 'string') {
        return text.includes(expectedText);
      } else {
        return expectedText.test(text);
      }
    } catch {
      return false;
    }
  }, { timeout });
}

/**
 * Wait for auto-save to complete (3s debounce + save operation)
 *
 * Replaces: await page.waitForTimeout(3000)
 */
export async function waitForAutoSave(
  page: Page,
  options: WaitOptions = {}
): Promise<void> {
  const { timeout = 10000 } = options;

  // Wait for "Saving..." indicator to appear
  const savingIndicator = page.locator('[data-testid="auto-save-status"]:has-text("Saving")');

  try {
    await expect(savingIndicator).toBeVisible({ timeout: 5000 });
  } catch {
    // If "Saving" doesn't appear, it might have already saved
    const savedIndicator = page.locator('[data-testid="auto-save-status"]:has-text("Saved")');
    const isSaved = await savedIndicator.isVisible();
    if (isSaved) {
      console.log('✅ Content already saved');
      return;
    }
    throw new Error('Auto-save did not trigger');
  }

  // Wait for "Saved" indicator to appear
  const savedIndicator = page.locator('[data-testid="auto-save-status"]:has-text("Saved")');
  await expect(savedIndicator).toBeVisible({ timeout });

  console.log('✅ Auto-save complete');
}

/**
 * Wait for save operation to complete
 *
 * Replaces: await page.waitForTimeout(1000)
 */
export async function waitForSaveComplete(
  page: Page,
  options: WaitOptions = {}
): Promise<void> {
  const { timeout = 5000 } = options;

  // Wait for network idle or success indicator
  await Promise.race([
    page.waitForLoadState('networkidle', { timeout }),
    page.waitForResponse(
      resp => resp.url().includes('/api/v1/') && (resp.status() === 200 || resp.status() === 201),
      { timeout }
    )
  ]);

  console.log('✅ Save operation complete');
}

/**
 * Wait for CSP validation to complete
 *
 * Replaces: await page.waitForTimeout(1000)
 */
export async function waitForCSPValidation(
  page: Page,
  options: WaitOptions = {}
): Promise<string[]> {
  const { timeout = 2000 } = options;
  const cspErrors: string[] = [];

  const consoleHandler = (msg: any) => {
    const text = msg.text();
    if (text.toLowerCase().includes('csp') || text.toLowerCase().includes('content security policy')) {
      cspErrors.push(text);
    }
  };

  page.on('console', consoleHandler);

  // Wait for page to settle and capture any CSP errors
  await page.waitForLoadState('networkidle', { timeout });

  page.off('console', consoleHandler);

  return cspErrors;
}

/**
 * Wait for element to be stable (no more layout shifts)
 */
export async function waitForElementStable(
  locator: Locator,
  options: WaitOptions = {}
): Promise<void> {
  const { timeout = 5000, interval = 100 } = options;
  let lastBox = await locator.boundingBox();
  let stableCount = 0;
  const requiredStableChecks = 3;

  const isStable = await waitForCondition(async () => {
    await new Promise(resolve => setTimeout(resolve, interval));
    const currentBox = await locator.boundingBox();

    if (!lastBox || !currentBox) {
      stableCount = 0;
      lastBox = currentBox;
      return false;
    }

    const isSamePosition =
      currentBox.x === lastBox.x &&
      currentBox.y === lastBox.y &&
      currentBox.width === lastBox.width &&
      currentBox.height === lastBox.height;

    if (isSamePosition) {
      stableCount++;
      if (stableCount >= requiredStableChecks) {
        return true;
      }
    } else {
      stableCount = 0;
    }

    lastBox = currentBox;
    return false;
  }, { timeout });

  if (!isStable) {
    throw new Error('Element did not stabilize within timeout');
  }
}

/**
 * Wait for API response with specific criteria
 */
export async function waitForAPIResponse(
  page: Page,
  urlPattern: string | RegExp,
  expectedStatus: number = 200,
  options: WaitOptions = {}
): Promise<void> {
  const { timeout = 10000 } = options;

  await page.waitForResponse(
    resp => {
      const urlMatches = typeof urlPattern === 'string'
        ? resp.url().includes(urlPattern)
        : urlPattern.test(resp.url());

      return urlMatches && resp.status() === expectedStatus;
    },
    { timeout }
  );
}

/**
 * Wait for multiple conditions in parallel
 */
export async function waitForAll(
  conditions: Array<() => Promise<void>>,
  options: WaitOptions = {}
): Promise<void> {
  const { timeout = 10000 } = options;

  await Promise.all(
    conditions.map(condition =>
      Promise.race([
        condition(),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Condition timeout')), timeout)
        )
      ])
    )
  );
}
