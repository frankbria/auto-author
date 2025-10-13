/**
 * Responsive Design E2E Tests
 *
 * Tests responsive behavior and WCAG 2.1 touch target compliance
 * across multiple viewports and devices.
 *
 * Test Coverage:
 * - Mobile viewports (320px - 414px)
 * - Tablet viewports (768px - 1024px)
 * - Desktop viewports (1440px+)
 * - Touch target validation (44x44px minimum)
 * - Layout adaptivity
 * - Component visibility at breakpoints
 */

import { test, expect, type Page } from '@playwright/test';

// Viewport presets matching responsiveHelpers.ts
const VIEWPORTS = {
  mobileSmall: { width: 320, height: 568, name: 'iPhone SE (smallest)' },
  mobile: { width: 375, height: 667, name: 'iPhone 12 Mini' },
  mobileMedium: { width: 390, height: 844, name: 'iPhone 12/13' },
  mobileLarge: { width: 414, height: 896, name: 'iPhone Plus' },
  tablet: { width: 768, height: 1024, name: 'iPad Mini' },
  tabletLarge: { width: 1024, height: 1366, name: 'iPad Pro' },
  desktop: { width: 1440, height: 900, name: 'Desktop' },
};

// WCAG 2.1 requirements
const TOUCH_TARGET_MIN_SIZE = 44; // Level AAA
const TOUCH_TARGET_MIN_SPACING = 8;

/**
 * Helper: Get bounding box of element
 */
async function getElementSize(page: Page, selector: string) {
  const element = page.locator(selector).first();
  const box = await element.boundingBox();
  return box;
}

/**
 * Helper: Check if element meets touch target requirements
 */
async function validateTouchTarget(page: Page, selector: string, name: string) {
  const box = await getElementSize(page, selector);

  if (!box) {
    throw new Error(`Element not found or not visible: ${selector}`);
  }

  expect(box.width, `${name} width should be at least ${TOUCH_TARGET_MIN_SIZE}px`).toBeGreaterThanOrEqual(
    TOUCH_TARGET_MIN_SIZE
  );

  expect(box.height, `${name} height should be at least ${TOUCH_TARGET_MIN_SIZE}px`).toBeGreaterThanOrEqual(
    TOUCH_TARGET_MIN_SIZE
  );

  return box;
}

/**
 * Helper: Navigate to test page and wait for load
 */
async function navigateToPage(page: Page, path: string) {
  await page.goto(path);
  await page.waitForLoadState('networkidle');
}

test.describe('Responsive Design - Touch Targets', () => {
  test.beforeEach(async ({ page }) => {
    // Set up authentication if needed
    // await setupAuth(page);
  });

  test.describe('Button Component Touch Targets', () => {
    test('should have minimum 44x44px touch targets for icon buttons', async ({ page }) => {
      await page.setViewportSize(VIEWPORTS.mobile);
      await navigateToPage(page, '/dashboard');

      // Test all button sizes
      const iconButtons = page.locator('button[data-size="icon"]');
      const count = await iconButtons.count();

      if (count > 0) {
        for (let i = 0; i < count; i++) {
          const button = iconButtons.nth(i);
          const box = await button.boundingBox();

          if (box) {
            expect(box.width, `Icon button ${i + 1} width`).toBeGreaterThanOrEqual(TOUCH_TARGET_MIN_SIZE);
            expect(box.height, `Icon button ${i + 1} height`).toBeGreaterThanOrEqual(TOUCH_TARGET_MIN_SIZE);
          }
        }
      }
    });

    test('should have adequate touch targets for all buttons', async ({ page }) => {
      await page.setViewportSize(VIEWPORTS.mobile);
      await navigateToPage(page, '/dashboard');

      const buttons = page.locator('button:visible');
      const count = await buttons.count();

      expect(count, 'Should have interactive buttons on page').toBeGreaterThan(0);

      let violations = 0;
      const violationDetails: Array<{ index: number; width: number; height: number }> = [];

      for (let i = 0; i < count; i++) {
        const button = buttons.nth(i);
        const box = await button.boundingBox();

        if (box) {
          if (box.width < TOUCH_TARGET_MIN_SIZE || box.height < TOUCH_TARGET_MIN_SIZE) {
            violations++;
            violationDetails.push({ index: i, width: box.width, height: box.height });
          }
        }
      }

      if (violations > 0) {
        console.log(`Found ${violations} touch target violations:`);
        violationDetails.forEach((v) => {
          console.log(`  Button ${v.index + 1}: ${v.width}x${v.height}px`);
        });
      }

      expect(violations, 'Should have no touch target violations').toBe(0);
    });
  });

  test.describe('Chapter Tab Touch Targets', () => {
    test.skip('should have adequate close button size on desktop', async ({ page }) => {
      // Skip if chapter page requires specific book/chapter setup
      await page.setViewportSize(VIEWPORTS.desktop);
      await navigateToPage(page, '/dashboard/books/test-book/chapters/test-chapter');

      const closeButton = page.locator('[aria-label="Close chapter"]').or(page.locator('[aria-label="Close"]'));

      if ((await closeButton.count()) > 0) {
        await validateTouchTarget(
          page,
          '[aria-label="Close chapter"]',
          'Chapter tab close button'
        );
      }
    });
  });

  test.describe('Modal Touch Targets', () => {
    test.skip('should have adequate close button size in dialogs', async ({ page }) => {
      // Skip if modal requires specific trigger
      await page.setViewportSize(VIEWPORTS.mobile);
      await navigateToPage(page, '/dashboard');

      // Trigger a modal (example: delete book modal)
      // const deleteButton = page.locator('[aria-label="Delete book"]').first();
      // if (await deleteButton.isVisible()) {
      //   await deleteButton.click();
      //   await page.waitForSelector('[role="dialog"]');

      //   const dialogCloseButton = page.locator('[role="dialog"] button[aria-label*="Close"]');
      //   await validateTouchTarget(page, dialogCloseButton, 'Dialog close button');
      // }
    });
  });

  test.describe('Editor Toolbar Touch Targets', () => {
    test.skip('should have adequate button sizes in editor toolbar', async ({ page }) => {
      // Skip if editor requires specific chapter setup
      await page.setViewportSize(VIEWPORTS.mobile);
      await navigateToPage(page, '/dashboard/books/test-book/chapters/test-chapter');

      // Wait for editor to load
      await page.waitForSelector('.ProseMirror', { timeout: 5000 });

      const toolbarButtons = page.locator('[data-testid="editor-toolbar"] button');
      const count = await toolbarButtons.count();

      expect(count, 'Editor toolbar should have buttons').toBeGreaterThan(0);

      for (let i = 0; i < count; i++) {
        const button = toolbarButtons.nth(i);
        const box = await button.boundingBox();

        if (box) {
          expect(box.width, `Toolbar button ${i + 1} width`).toBeGreaterThanOrEqual(TOUCH_TARGET_MIN_SIZE);
          expect(box.height, `Toolbar button ${i + 1} height`).toBeGreaterThanOrEqual(TOUCH_TARGET_MIN_SIZE);
        }
      }
    });
  });
});

test.describe('Responsive Design - Layout Adaptation', () => {
  for (const [key, viewport] of Object.entries(VIEWPORTS)) {
    test.describe(`${viewport.name} (${viewport.width}px)`, () => {
      test.beforeEach(async ({ page }) => {
        await page.setViewportSize(viewport);
      });

      test('should not have horizontal scroll', async ({ page }) => {
        await navigateToPage(page, '/dashboard');

        const bodyScrollWidth = await page.evaluate(() => document.body.scrollWidth);
        const windowInnerWidth = await page.evaluate(() => window.innerWidth);

        expect(bodyScrollWidth, 'Should not have horizontal overflow').toBeLessThanOrEqual(windowInnerWidth + 1); // +1px tolerance
      });

      test('should have readable text', async ({ page }) => {
        await navigateToPage(page, '/dashboard');

        // Check font sizes are not too small
        const bodyFontSize = await page.evaluate(() => {
          return window.getComputedStyle(document.body).fontSize;
        });

        const fontSize = parseFloat(bodyFontSize);
        expect(fontSize, 'Body font size should be at least 14px').toBeGreaterThanOrEqual(14);
      });

      test('should have all critical UI elements visible', async ({ page }) => {
        await navigateToPage(page, '/dashboard');

        // Check for critical elements
        const criticalElements = [
          'main', // Main content area
          'button', // At least one button
        ];

        for (const selector of criticalElements) {
          const element = page.locator(selector).first();
          await expect(element, `${selector} should be visible`).toBeVisible();
        }
      });

      test('should adapt book card layout', async ({ page }) => {
        await navigateToPage(page, '/dashboard');

        const bookCards = page.locator('[data-testid="book-card"]').or(page.locator('article').or(page.locator('.book-card')));

        if ((await bookCards.count()) > 0) {
          const card = bookCards.first();
          const box = await card.boundingBox();

          if (box) {
            // Card should not exceed viewport width
            expect(box.width, 'Book card width should fit viewport').toBeLessThanOrEqual(viewport.width);

            // Card should have adequate height
            expect(box.height, 'Book card should have minimum height').toBeGreaterThan(100);
          }
        }
      });
    });
  }
});

test.describe('Responsive Design - Mobile Specific', () => {
  test('should show mobile chapter navigation on small viewports', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    // Test would require navigating to a chapter page
    // Skipped for now - implement when chapter pages are set up
    test.skip();
  });

  test('should hide desktop chapter tabs on mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    // Test would require navigating to a chapter page
    test.skip();
  });

  test('should show desktop chapter tabs on large viewports', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    // Test would require navigating to a chapter page
    test.skip();
  });
});

test.describe('Responsive Design - Breakpoint Transitions', () => {
  test('should transition smoothly between mobile and desktop', async ({ page }) => {
    await navigateToPage(page, '/dashboard');

    // Start at mobile
    await page.setViewportSize(VIEWPORTS.mobile);
    await page.waitForTimeout(500); // Allow transition

    // Verify mobile layout
    const isMobileBefore = await page.evaluate(() => window.innerWidth < 768);
    expect(isMobileBefore).toBe(true);

    // Transition to desktop
    await page.setViewportSize(VIEWPORTS.desktop);
    await page.waitForTimeout(500); // Allow transition

    // Verify desktop layout
    const isDesktopAfter = await page.evaluate(() => window.innerWidth >= 1024);
    expect(isDesktopAfter).toBe(true);

    // Verify no layout errors
    const hasOverflow = await page.evaluate(() => {
      return document.body.scrollWidth > window.innerWidth;
    });

    expect(hasOverflow).toBe(false);
  });

  test('should handle tablet breakpoint correctly', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.tablet);
    await navigateToPage(page, '/dashboard');

    const isTablet = await page.evaluate(() => {
      const width = window.innerWidth;
      return width >= 768 && width < 1024;
    });

    expect(isTablet).toBe(true);

    // Verify no horizontal scroll
    const bodyScrollWidth = await page.evaluate(() => document.body.scrollWidth);
    const windowInnerWidth = await page.evaluate(() => window.innerWidth);

    expect(bodyScrollWidth).toBeLessThanOrEqual(windowInnerWidth + 1);
  });
});

test.describe('Responsive Design - Touch Target Spacing', () => {
  test('should have adequate spacing between adjacent buttons', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await navigateToPage(page, '/dashboard');

    // Find groups of adjacent buttons (e.g., modal footers, toolbars)
    const buttonGroups = page.locator('[role="group"] button, .flex button, .gap-2 button');
    const count = await buttonGroups.count();

    if (count >= 2) {
      // Check first two adjacent buttons
      const button1Box = await buttonGroups.nth(0).boundingBox();
      const button2Box = await buttonGroups.nth(1).boundingBox();

      if (button1Box && button2Box) {
        // Calculate horizontal distance
        const horizontalDistance = Math.max(
          0,
          button2Box.x - (button1Box.x + button1Box.width),
          button1Box.x - (button2Box.x + button2Box.width)
        );

        // Calculate vertical distance
        const verticalDistance = Math.max(
          0,
          button2Box.y - (button1Box.y + button1Box.height),
          button1Box.y - (button2Box.y + button2Box.height)
        );

        const distance = Math.min(horizontalDistance, verticalDistance);

        if (distance > 0) {
          expect(distance, 'Button spacing should be at least 8px').toBeGreaterThanOrEqual(
            TOUCH_TARGET_MIN_SPACING
          );
        }
      }
    }
  });
});

test.describe('Responsive Design - Performance', () => {
  test('should not cause layout shift when resizing', async ({ page }) => {
    await navigateToPage(page, '/dashboard');

    // Measure CLS (Cumulative Layout Shift)
    await page.setViewportSize(VIEWPORTS.mobile);
    await page.waitForTimeout(1000);

    await page.setViewportSize(VIEWPORTS.desktop);
    await page.waitForTimeout(1000);

    // Get layout shift score
    const cls = await page.evaluate(() => {
      return new Promise<number>((resolve) => {
        let clsScore = 0;

        const observer = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.entryType === 'layout-shift' && !(entry as any).hadRecentInput) {
              clsScore += (entry as any).value;
            }
          }
        });

        observer.observe({ entryTypes: ['layout-shift'] });

        // Wait 2 seconds then resolve
        setTimeout(() => {
          observer.disconnect();
          resolve(clsScore);
        }, 2000);
      });
    });

    // CLS should be low (< 0.1 is good, < 0.25 is acceptable)
    expect(cls, 'Cumulative Layout Shift should be minimal').toBeLessThan(0.25);
  });
});

test.describe('Responsive Design - Accessibility Integration', () => {
  test('should maintain keyboard navigation at all viewports', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await navigateToPage(page, '/dashboard');

    // Tab through interactive elements
    await page.keyboard.press('Tab');
    await page.waitForTimeout(100);

    const firstFocused = await page.evaluate(() => {
      return document.activeElement?.tagName;
    });

    expect(['BUTTON', 'A', 'INPUT']).toContain(firstFocused);

    // Tab again
    await page.keyboard.press('Tab');
    await page.waitForTimeout(100);

    const secondFocused = await page.evaluate(() => {
      return document.activeElement?.tagName;
    });

    expect(['BUTTON', 'A', 'INPUT']).toContain(secondFocused);
  });

  test('should have visible focus indicators on mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await navigateToPage(page, '/dashboard');

    // Focus first button
    const button = page.locator('button').first();
    await button.focus();

    // Check for focus indicator
    const hasFocusStyle = await button.evaluate((el) => {
      const styles = window.getComputedStyle(el);
      // Check for ring, outline, or border change
      return (
        styles.outline !== 'none' ||
        styles.outlineWidth !== '0px' ||
        (styles.boxShadow && styles.boxShadow !== 'none')
      );
    });

    expect(hasFocusStyle, 'Button should have visible focus indicator').toBe(true);
  });
});
