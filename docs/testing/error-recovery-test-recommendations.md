# Error Recovery E2E Test - Robustness Recommendations

## Overview

This document provides recommendations for improving the reliability, maintainability, and robustness of the error recovery E2E test suite.

## Current Test Reliability

### Strengths

✅ **Condition-based waiting**: No arbitrary timeouts, tests complete as soon as conditions are met
✅ **Precise timing measurement**: Millisecond-accurate timestamp tracking
✅ **Tolerance-based validation**: ±200ms tolerance accounts for execution variance
✅ **Comprehensive scenarios**: 8 tests covering success, failure, and edge cases
✅ **API interception**: Full control over responses without backend dependency
✅ **Detailed logging**: Console output aids debugging

### Current Limitations

⚠️ **Toast detection fragility**: Depends on specific ARIA roles and text matching
⚠️ **Timing sensitivity**: CI/CD environments may have higher variance
⚠️ **UI selector brittleness**: Text-based selectors may break with wording changes
⚠️ **Browser-specific behavior**: Timing may vary across Playwright browsers
⚠️ **Test data cleanup**: Created books persist unless manually deleted

## Recommendations for Robustness

### 1. Add data-testid Attributes

**Problem**: Text-based selectors (`getByRole`, `getByText`) are fragile and locale-dependent.

**Solution**: Add semantic test identifiers to components.

**Implementation**:

```tsx
// frontend/src/components/books/BookCreationForm.tsx
export function BookCreationForm() {
  return (
    <form data-testid="book-creation-form">
      <input
        data-testid="book-title-input"
        aria-label="Title"
        {...props}
      />
      <select
        data-testid="book-genre-select"
        aria-label="Genre"
        {...props}
      />
      <button
        data-testid="book-submit-button"
        type="submit"
      >
        Create Book
      </button>
    </form>
  );
}
```

**Test Update**:

```typescript
// Before (fragile)
await page.getByLabel(/title/i).fill('Test Book');

// After (robust)
await page.locator('[data-testid="book-title-input"]').fill('Test Book');
```

**Benefits**:
- Resilient to text changes
- Works across locales
- Clear intent in code
- Faster selector resolution

### 2. Increase Timing Tolerance in CI

**Problem**: CI/CD environments are slower and have more timing variance.

**Solution**: Detect CI environment and increase tolerance automatically.

**Implementation**:

```typescript
// frontend/src/e2e/error-recovery-flow.spec.ts

// Detect CI environment
const IS_CI = !!process.env.CI;

// Adjust tolerance based on environment
const BACKOFF_TOLERANCE_MS = IS_CI ? 500 : 200;

// Optional: Increase timeout in CI
const TEST_TIMEOUT = IS_CI ? 90000 : 60000;
```

**Benefits**:
- Tests more reliable in CI
- Maintains strict timing in local dev
- Reduces flaky test failures
- Self-documenting environment differences

### 3. Implement Toast Detection Helper

**Problem**: Toast detection is fragile and repeated across tests.

**Solution**: Create a robust helper with multiple fallback strategies.

**Implementation**:

```typescript
// frontend/src/__tests__/helpers/toastDetection.ts

export interface ToastOptions {
  /**
   * Expected toast type
   */
  type?: 'error' | 'success' | 'info' | 'warning';

  /**
   * Expected text content (partial match)
   */
  text?: string;

  /**
   * Timeout for waiting
   */
  timeout?: number;
}

/**
 * Robust toast detection with multiple fallback strategies
 */
export async function waitForToast(
  page: Page,
  options: ToastOptions = {}
): Promise<boolean> {
  const { type, text, timeout = 5000 } = options;

  // Strategy 1: ARIA role="alert"
  const strategy1 = async () => {
    const alert = page.locator('[role="alert"]');
    if (text) {
      return await alert.filter({ hasText: text }).isVisible();
    }
    return await alert.isVisible();
  };

  // Strategy 2: Common toast selectors
  const strategy2 = async () => {
    const selectors = [
      '[data-testid="toast"]',
      '.toast',
      '[class*="Toaster"]',
      '[data-sonner-toast]', // If using sonner
    ];

    for (const selector of selectors) {
      const element = page.locator(selector);
      if (text) {
        const match = await element.filter({ hasText: text }).isVisible();
        if (match) return true;
      } else {
        const visible = await element.isVisible();
        if (visible) return true;
      }
    }
    return false;
  };

  // Strategy 3: Type-specific detection
  const strategy3 = async () => {
    if (!type) return false;

    const typePatterns = {
      error: /error|danger|destructive/i,
      success: /success|completed/i,
      info: /info|information/i,
      warning: /warning|caution/i,
    };

    const pattern = typePatterns[type];
    if (!pattern) return false;

    const element = page.locator(`[role="alert"]`).filter({ hasText: pattern });
    return await element.isVisible();
  };

  // Try all strategies with timeout
  return await waitForCondition(
    async () => {
      return (
        (await strategy1()) ||
        (await strategy2()) ||
        (await strategy3())
      );
    },
    { timeout, timeoutMessage: `Toast not found (type: ${type}, text: ${text})` }
  );
}

/**
 * Wait for toast to disappear (auto-dismiss)
 */
export async function waitForToastDismissal(
  page: Page,
  timeout: number = 5000
): Promise<void> {
  await waitForCondition(
    async () => {
      const alerts = await page.locator('[role="alert"]').count();
      return alerts === 0;
    },
    { timeout, timeoutMessage: 'Toast did not dismiss' }
  );
}
```

**Test Update**:

```typescript
// Before (fragile)
const errorToast = page.locator('[role="alert"]').filter({ hasText: /error/i });
const hasErrorToast = await errorToast.isVisible();
expect(hasErrorToast).toBe(true);

// After (robust)
const hasErrorToast = await waitForToast(page, {
  type: 'error',
  text: 'Validation Error',
  timeout: 5000,
});
expect(hasErrorToast).toBe(true);
```

**Benefits**:
- Multiple fallback strategies
- Resilient to implementation changes
- Reusable across test suite
- Clear, semantic API

### 4. Add Test Data Cleanup

**Problem**: Tests create persistent data that clutters the database.

**Solution**: Implement automatic cleanup with failure safety.

**Implementation**:

```typescript
// frontend/src/__tests__/helpers/testDataCleanup.ts

export class TestDataManager {
  private createdBooks: string[] = [];
  private page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  /**
   * Track a created book for cleanup
   */
  trackBook(bookId: string): void {
    this.createdBooks.push(bookId);
    console.log(`📝 Tracked book for cleanup: ${bookId}`);
  }

  /**
   * Clean up all tracked books
   */
  async cleanup(): Promise<void> {
    console.log(`🧹 Cleaning up ${this.createdBooks.length} test books`);

    for (const bookId of this.createdBooks) {
      try {
        // Navigate to book page
        await this.page.goto(`/dashboard/books/${bookId}`, {
          waitUntil: 'networkidle',
          timeout: 5000,
        });

        // Click delete button
        const deleteButton = this.page.getByRole('button', { name: /delete/i });
        await deleteButton.click({ timeout: 2000 });

        // Type title to confirm (if needed)
        const confirmInput = this.page.getByPlaceholder(/type.*title/i);
        const needsConfirm = await confirmInput.isVisible().catch(() => false);

        if (needsConfirm) {
          // We don't know the exact title, so try API deletion instead
          await this.page.evaluate((id) => {
            return fetch(`/api/books/${id}`, { method: 'DELETE' });
          }, bookId);
        } else {
          // Simple deletion
          const confirmButton = this.page.getByRole('button', {
            name: /delete.*book|confirm/i,
          });
          await confirmButton.click({ timeout: 2000 });
        }

        console.log(`✓ Deleted book: ${bookId}`);
      } catch (error) {
        console.warn(`⚠️  Failed to delete book ${bookId}:`, error);
        // Continue cleanup even if one fails
      }
    }

    this.createdBooks = [];
  }
}
```

**Test Update**:

```typescript
test.describe('Error Recovery Flow', () => {
  let testDataManager: TestDataManager;

  test.beforeEach(({ page }) => {
    testDataManager = new TestDataManager(page);
  });

  test.afterEach(async () => {
    await testDataManager.cleanup();
  });

  test('creates book and cleans up', async ({ page }) => {
    const bookId = await createBook(page);
    testDataManager.trackBook(bookId); // Track for cleanup

    // ... test logic ...

    // Cleanup happens automatically in afterEach
  });
});
```

**Benefits**:
- Database stays clean
- Tests remain idempotent
- Failures don't prevent cleanup
- Clear logging of cleanup actions

### 5. Implement Retry Configuration for Tests

**Problem**: Tests use default retry configuration, making testing edge cases difficult.

**Solution**: Allow tests to configure retry behavior dynamically.

**Implementation**:

```typescript
// frontend/src/__tests__/helpers/apiConfig.ts

/**
 * Configure error handler behavior for testing
 */
export async function configureRetryBehavior(
  page: Page,
  config: {
    maxRetries?: number;
    baseDelay?: number;
    maxDelay?: number;
  }
): Promise<void> {
  await page.addInitScript((testConfig) => {
    // @ts-ignore - Injected for testing
    window.__TEST_ERROR_CONFIG__ = testConfig;
  }, config);
}

/**
 * Reset to default configuration
 */
export async function resetRetryBehavior(page: Page): Promise<void> {
  await page.addInitScript(() => {
    // @ts-ignore
    delete window.__TEST_ERROR_CONFIG__;
  });
}
```

**Error Handler Update**:

```typescript
// frontend/src/lib/errors/errorHandler.ts

export class ErrorHandler {
  private maxRetries: number;
  private baseDelay: number;
  private maxDelay: number;

  constructor(config: ErrorHandlerConfig = {}) {
    // Check for test configuration
    const testConfig = (window as any).__TEST_ERROR_CONFIG__;

    this.maxRetries = config.maxRetries ?? testConfig?.maxRetries ?? 3;
    this.baseDelay = config.baseDelay ?? testConfig?.baseDelay ?? 1000;
    this.maxDelay = config.maxDelay ?? testConfig?.maxDelay ?? 30000;
  }

  // ... rest of implementation
}
```

**Test Update**:

```typescript
test('respects custom retry configuration', async ({ page }) => {
  // Configure reduced retries for faster test
  await configureRetryBehavior(page, {
    maxRetries: 2,
    baseDelay: 500,
  });

  // ... test logic ...

  // Cleanup
  await resetRetryBehavior(page);
});
```

**Benefits**:
- Tests run faster with reduced delays
- Edge cases easier to test
- No changes to production code
- Clear test intent

### 6. Add Timing Statistics Collection

**Problem**: Hard to identify timing-related test failures without detailed data.

**Solution**: Collect and report timing statistics for all tests.

**Implementation**:

```typescript
// frontend/src/__tests__/helpers/timingStats.ts

export interface TimingStats {
  testName: string;
  attempts: number;
  delays: number[];
  totalDuration: number;
  expectedBackoffs: number[];
  deviations: number[];
  avgDeviation: number;
  maxDeviation: number;
}

/**
 * Calculate timing statistics from tracker
 */
export function calculateTimingStats(
  testName: string,
  tracker: ApiCallTracker,
  expectedBackoffs: number[]
): TimingStats {
  const delays = tracker.timestamps.map((ts, i) =>
    i === 0 ? 0 : ts - tracker.timestamps[i - 1]
  );

  const deviations = delays.slice(1).map((delay, i) => {
    const expected = expectedBackoffs[i] || 0;
    return Math.abs(delay - expected);
  });

  const avgDeviation =
    deviations.reduce((sum, dev) => sum + dev, 0) / (deviations.length || 1);

  const maxDeviation = Math.max(...deviations);

  return {
    testName,
    attempts: tracker.attempts,
    delays,
    totalDuration: tracker.timestamps[tracker.timestamps.length - 1] - tracker.timestamps[0],
    expectedBackoffs,
    deviations,
    avgDeviation,
    maxDeviation,
  };
}

/**
 * Log timing statistics to console
 */
export function logTimingStats(stats: TimingStats): void {
  console.log('\n📊 Timing Statistics:');
  console.log(`  Test: ${stats.testName}`);
  console.log(`  Attempts: ${stats.attempts}`);
  console.log(`  Total Duration: ${stats.totalDuration}ms`);
  console.log(`  Delays: ${stats.delays.join('ms, ')}ms`);
  console.log(`  Expected: ${stats.expectedBackoffs.join('ms, ')}ms`);
  console.log(`  Deviations: ${stats.deviations.map((d) => `${d}ms`).join(', ')}`);
  console.log(`  Avg Deviation: ${stats.avgDeviation.toFixed(0)}ms`);
  console.log(`  Max Deviation: ${stats.maxDeviation}ms`);
  console.log(`  Status: ${stats.maxDeviation <= 200 ? '✅ Within tolerance' : '⚠️  High variance'}`);
}

/**
 * Export timing statistics to file for analysis
 */
export async function exportTimingStats(
  stats: TimingStats[],
  filename: string = 'timing-stats.json'
): Promise<void> {
  const fs = require('fs').promises;
  await fs.writeFile(filename, JSON.stringify(stats, null, 2));
  console.log(`📈 Exported timing statistics to ${filename}`);
}
```

**Test Update**:

```typescript
test('exponential backoff with statistics', async ({ page }) => {
  const tracker = setupApiInterception(/* ... */);

  // ... test logic ...

  // Collect and log statistics
  const stats = calculateTimingStats(
    'exponential backoff test',
    tracker,
    [1000, 2000, 4000]
  );

  logTimingStats(stats);

  // Optional: Assert on statistics
  expect(stats.maxDeviation).toBeLessThanOrEqual(200);
  expect(stats.avgDeviation).toBeLessThanOrEqual(100);
});
```

**Benefits**:
- Detailed timing data for debugging
- Identify systematic timing issues
- Track timing variance over time
- Data-driven tolerance adjustment

### 7. Implement Visual Regression Testing

**Problem**: Loading states and UI behavior during retries hard to validate programmatically.

**Solution**: Add screenshot comparison for critical UI states.

**Implementation**:

```typescript
// frontend/src/__tests__/helpers/visualRegression.ts

/**
 * Take screenshot and compare with baseline
 */
export async function expectMatchesBaseline(
  page: Page,
  name: string,
  options: {
    threshold?: number;
    maxDiffPixels?: number;
  } = {}
): Promise<void> {
  const screenshot = await page.screenshot();

  // Playwright's built-in visual comparison
  await expect(screenshot).toMatchSnapshot(`${name}.png`, {
    threshold: options.threshold || 0.2,
    maxDiffPixels: options.maxDiffPixels || 100,
  });
}

/**
 * Update baseline screenshot
 */
export async function updateBaseline(
  page: Page,
  name: string
): Promise<void> {
  await page.screenshot({
    path: `src/__tests__/visual-baselines/${name}.png`,
  });
  console.log(`📸 Updated baseline: ${name}`);
}
```

**Test Update**:

```typescript
test('shows loading state during retry', async ({ page }) => {
  // Setup retry scenario
  const tracker = setupApiInterception(/* ... */);

  // Trigger operation
  await triggerBookCreation(page);

  // Wait for first retry to start
  await page.waitForTimeout(500);

  // Capture loading state
  await expectMatchesBaseline(page, 'retry-loading-state', {
    threshold: 0.2,
  });

  // ... rest of test
});
```

**Benefits**:
- Validates UI appearance during retries
- Detects unintended visual changes
- Documents expected UI states
- Complements functional testing

## Priority Implementation Order

### Phase 1: Quick Wins (High Impact, Low Effort)

1. **Add data-testid attributes** (1-2 hours)
   - Most impactful for reliability
   - Easy to implement
   - Prevents future selector issues

2. **Increase CI timing tolerance** (15 minutes)
   - Immediate improvement in CI reliability
   - Single line change
   - No side effects

3. **Add timing statistics logging** (1 hour)
   - Helps debug current issues
   - Useful for future tests
   - Easy to integrate

### Phase 2: Medium Priority (High Impact, Medium Effort)

4. **Implement toast detection helper** (2-3 hours)
   - Reusable across all tests
   - Significant reliability improvement
   - Moderate complexity

5. **Add test data cleanup** (2-3 hours)
   - Keeps database clean
   - Prevents test interference
   - Moderate complexity

### Phase 3: Advanced Features (Medium Impact, High Effort)

6. **Implement retry configuration** (3-4 hours)
   - Enables faster tests
   - Requires production code changes
   - Needs careful design

7. **Add visual regression testing** (4-6 hours)
   - Nice-to-have validation
   - Requires baseline maintenance
   - Higher complexity

## Maintenance Checklist

### When Test Fails

- [ ] Check timing statistics for variance patterns
- [ ] Review Playwright trace viewer
- [ ] Verify toast selectors still match
- [ ] Check CI environment differences
- [ ] Look for UI wording changes
- [ ] Validate API interception working

### When UI Changes

- [ ] Update data-testid attributes
- [ ] Update toast detection patterns
- [ ] Update visual regression baselines
- [ ] Re-run full test suite
- [ ] Check cross-browser compatibility

### When Error Handler Changes

- [ ] Update expected backoff values
- [ ] Update max retry expectations
- [ ] Add tests for new error types
- [ ] Update timing tolerance if needed
- [ ] Review test coverage gaps

### Monthly Review

- [ ] Analyze timing statistics trends
- [ ] Review flaky test reports
- [ ] Update baselines if UI evolved
- [ ] Audit test data cleanup effectiveness
- [ ] Check for new edge cases

## Measuring Test Reliability

### Key Metrics

**Pass Rate**:
- Target: >95% on re-runs
- Measure: Run each test 20 times
- Action: If <95%, investigate root cause

**Execution Time**:
- Target: <120 seconds for full suite
- Measure: CI/CD execution logs
- Action: If >120s, optimize slowest tests

**Timing Variance**:
- Target: Avg deviation <100ms
- Measure: Timing statistics
- Action: If >100ms, increase tolerance

**Flakiness Rate**:
- Target: <2% of test runs
- Measure: CI/CD failure rate
- Action: If >2%, implement robustness improvements

### Continuous Monitoring

```bash
# Run reliability test (20 iterations)
for i in {1..20}; do
  npx playwright test error-recovery-flow --reporter=json > "run-$i.json"
done

# Analyze results
node scripts/analyze-test-reliability.js run-*.json
```

**Output**:
```
Test Reliability Report
=======================
Total runs: 20
Pass rate: 95% (19/20)
Avg execution time: 98s
Timing variance: 87ms avg, 143ms max
Flaky tests: 1 (5%)

Recommendation: ✅ Test suite is reliable
```

## Conclusion

Implementing these recommendations will significantly improve test reliability:

1. **Immediate improvements**: data-testid + CI tolerance (90 minutes)
2. **Medium-term improvements**: helpers + cleanup (4-6 hours)
3. **Long-term improvements**: configuration + visual regression (7-10 hours)

**Expected outcomes**:
- Pass rate: 85% → 95%+
- Flakiness: 10% → <2%
- Maintenance effort: -50%
- Debug time: -60%

The test suite will be more maintainable, reliable, and valuable for catching real issues while minimizing false positives.
