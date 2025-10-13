# Error Recovery Flow E2E Test Documentation

## Overview

This document describes the comprehensive End-to-End (E2E) test suite for validating automatic error recovery with exponential backoff in the Auto-Author application.

## Test Location

**File**: `frontend/src/e2e/error-recovery-flow.spec.ts`

**Framework**: Playwright E2E Testing

**Test Count**: 8 comprehensive scenarios

## Related Implementation

**Error Handler**: `frontend/src/lib/errors/errorHandler.ts`

**Unit Tests**: `frontend/src/lib/errors/errorHandler.test.ts` (29 tests, 100% pass rate)

**Task Reference**: Agile Testing Strategy - Task 8

## Test Scenarios

### Test 1: Successful Recovery on Transient Error

**Purpose**: Validates automatic retry succeeds after initial failure

**Scenario**:
- First API call returns 503 Service Unavailable
- Error handler automatically retries after 1 second
- Second attempt succeeds with 201 Created
- User sees success without manual intervention

**Validations**:
- ✅ Exactly 2 API attempts made
- ✅ First attempt failed with 503
- ✅ Second attempt succeeded with 201
- ✅ Retry delay ~1000ms (±200ms tolerance)
- ✅ No error toast displayed (transparent recovery)
- ✅ User redirected to book page

**Expected Behavior**:
```
Attempt 1: 503 Service Unavailable
  ↓ Wait 1s (exponential backoff)
Attempt 2: 201 Success
  ↓ Success! No error shown
User sees book created
```

### Test 2: Exponential Backoff Timing Validation

**Purpose**: Validates retry delays follow exponential backoff formula

**Scenario**:
- First API call fails with 503
- Second API call fails with 503
- Third API call succeeds with 201
- Timing measured between attempts

**Validations**:
- ✅ Exactly 3 API attempts made
- ✅ First retry delay ~1000ms (1s)
- ✅ Second retry delay ~2000ms (2s)
- ✅ Third retry delay would be ~4000ms (4s) if needed
- ✅ Second delay approximately 2x the first delay
- ✅ Formula: `baseDelay * 2^attempt` verified

**Expected Behavior**:
```
Attempt 1: 503 Service Unavailable
  ↓ Wait 1s (1000 * 2^0)
Attempt 2: 503 Service Unavailable
  ↓ Wait 2s (1000 * 2^1)
Attempt 3: 201 Success
  ↓ Success!
User sees book created
```

**Timing Validation**:
- Measured with millisecond precision
- ±200ms tolerance accounts for execution overhead
- Validates exponential growth pattern (doubling)

### Test 3: Non-Retryable Errors Fail Immediately

**Purpose**: Validates validation errors don't trigger retry logic

**Scenario**:
- API call returns 400 Bad Request (validation error)
- Error handler should NOT retry
- Error immediately shown to user

**Validations**:
- ✅ Exactly 1 API attempt made (no retry)
- ✅ Response status 400
- ✅ Error toast appears immediately
- ✅ Toast shows "Validation Error" title
- ✅ User remains on form page
- ✅ Form data preserved

**Expected Behavior**:
```
Attempt 1: 400 Validation Error
  ↓ Immediate failure (no retry)
Toast: "Validation Error: Title is required"
User stays on form to fix error
```

**Error Classification**:
- 400 Bad Request → Validation Error → No Retry
- 401 Unauthorized → Auth Error → No Retry
- 403 Forbidden → Auth Error → No Retry
- 404 Not Found → Unknown Error → No Retry

### Test 4: Max Retry Limit Respected

**Purpose**: Validates retry logic stops after 3 attempts

**Scenario**:
- All API calls fail with 503
- Error handler retries up to max limit (3 total attempts)
- Final error shown to user after retries exhausted

**Validations**:
- ✅ Exactly 3 API attempts made
- ✅ All attempts failed with 503
- ✅ First retry delay ~1000ms
- ✅ Second retry delay ~2000ms
- ✅ Error toast appears after final attempt
- ✅ Toast shows "Server Error" title
- ✅ User remains on form page

**Expected Behavior**:
```
Attempt 1: 503 Service Unavailable
  ↓ Wait 1s
Attempt 2: 503 Service Unavailable
  ↓ Wait 2s
Attempt 3: 503 Service Unavailable
  ↓ Max retries reached
Toast: "Server Error: Service temporarily unavailable"
User sees final error
```

**Max Retry Configuration**:
- Default: 3 attempts (initial + 2 retries)
- Configurable via `ErrorHandler({ maxRetries: n })`
- After max attempts, error propagates to user

### Test 5: Network Errors Retry Automatically

**Purpose**: Validates network failures trigger retry logic

**Scenario**:
- First API call aborts (network failure)
- Second API call succeeds

**Validations**:
- ✅ Exactly 2 API attempts made
- ✅ First attempt aborted (network error)
- ✅ Second attempt succeeded
- ✅ No error toast (transparent recovery)

**Expected Behavior**:
```
Attempt 1: Network error (fetch failed)
  ↓ Wait 1s
Attempt 2: 201 Success
  ↓ Success! No error shown
User sees book created
```

**Network Error Types**:
- `TypeError: Failed to fetch`
- `NetworkError: Connection failed`
- Route abort in Playwright (`route.abort('failed')`)

### Test 6: Rate Limiting Triggers Retry

**Purpose**: Validates 429 rate limit errors are retryable

**Scenario**:
- First API call returns 429 Too Many Requests
- Second API call succeeds after backoff

**Validations**:
- ✅ Exactly 2 API attempts made
- ✅ First attempt 429 (rate limited)
- ✅ Second attempt 201 (success)
- ✅ Retry delay ~1000ms
- ✅ No error toast (transparent recovery)

**Expected Behavior**:
```
Attempt 1: 429 Too Many Requests
  ↓ Wait 1s (give server time to recover)
Attempt 2: 201 Success
  ↓ Success! No error shown
User sees book created
```

**Rate Limiting Strategy**:
- Treat 429 as retryable (server error category)
- Exponential backoff helps prevent thundering herd
- Max 3 attempts prevents infinite retry loop

### Test 7: Auth Errors Do NOT Retry

**Purpose**: Validates authentication errors fail immediately

**Scenario**:
- API call returns 401 Unauthorized
- Error handler should NOT retry
- Auth error shown to user

**Validations**:
- ✅ Exactly 1 API attempt made (no retry)
- ✅ Response status 401
- ✅ Error toast appears immediately
- ✅ Toast shows "Authentication Error" title
- ✅ User remains on form page

**Expected Behavior**:
```
Attempt 1: 401 Unauthorized
  ↓ Immediate failure (no retry)
Toast: "Authentication Error: Authentication required"
User needs to re-authenticate
```

**Auth Error Handling**:
- 401/403 errors likely require user action (login)
- Retrying won't fix authentication issues
- Fail fast to prompt user to authenticate

### Test 8: User Experience During Retries

**Purpose**: Validates UI behavior during retry operations

**Scenario**:
- API call fails then succeeds
- UI should show loading state during retries
- Operation appears transparent to user

**Validations**:
- ✅ Submit button disabled during retry
- ✅ Loading indicator shown (best-effort)
- ✅ Form remains interactive
- ✅ Retry happens automatically
- ✅ Success without user intervention

**Expected Behavior**:
```
User clicks "Create Book"
  ↓ Button shows loading state
Attempt 1: 503 Service Unavailable
  ↓ Still loading (retry in progress)
  ↓ Wait 1s
Attempt 2: 201 Success
  ↓ Loading complete
User redirected to book page
```

**UX Considerations**:
- Loading state persists across retries
- User doesn't know retry happened (seamless)
- No progress bar (fixed timeout approach)
- Cancel not available during retry

## Test Implementation Details

### API Interception Strategy

```typescript
// Setup route interception with tracking
const tracker = setupApiInterception(page, '**/api/books**', async (route, tracker) => {
  tracker.attempts++;
  tracker.timestamps.push(Date.now());

  if (tracker.attempts === 1) {
    // First attempt fails
    await route.fulfill({ status: 503 });
  } else {
    // Second attempt succeeds
    await route.fulfill({ status: 201, body: successData });
  }
});
```

**Benefits**:
- Precise control over API responses
- Timestamp tracking for timing validation
- Simulates real network conditions
- No backend mocking required

### Timing Validation Approach

```typescript
// Calculate delay between attempts
const delay = timestamps[1] - timestamps[0];

// Validate with tolerance
expectDelayInRange(delay, 1000, 200);
// Expects: 800ms ≤ delay ≤ 1200ms
```

**Tolerance Rationale**:
- ±200ms accounts for JavaScript execution overhead
- Browser timing not perfectly precise
- CI/CD systems may have more variance
- Still validates exponential pattern

### Condition-Based Waiting

```typescript
// Wait for success condition instead of fixed timeout
await waitForCondition(
  async () => {
    const url = page.url();
    return url.includes('/books/');
  },
  { timeout: 10000, timeoutMessage: 'Book creation did not complete' }
);
```

**Benefits**:
- Tests complete as soon as condition met
- No arbitrary delays
- More reliable than `page.waitForTimeout()`
- Clear error messages on failure

## Running the Tests

### Local Development

```bash
# Run all error recovery tests
npx playwright test error-recovery-flow

# Run specific test by name
npx playwright test error-recovery-flow -g "successful recovery"

# Run with UI mode for debugging
npx playwright test error-recovery-flow --ui

# Run with headed browser (see what's happening)
npx playwright test error-recovery-flow --headed

# Run with trace for debugging
npx playwright test error-recovery-flow --trace on
```

### CI/CD Integration

```bash
# Run with CI configuration (2 retries on failure)
CI=true npx playwright test error-recovery-flow

# Generate report
npx playwright test error-recovery-flow --reporter=html

# Generate test results for CI
npx playwright test error-recovery-flow --reporter=json,junit
```

### View Test Results

```bash
# Open HTML report
npx playwright show-report

# View trace for failed test
npx playwright show-trace test-results/error-recovery-flow/trace.zip
```

## Test Configuration

### Timeouts

```typescript
const TEST_TIMEOUT = 60000; // 1 minute per test
const BACKOFF_TOLERANCE_MS = 200; // ±200ms timing tolerance
```

**Rationale**:
- 60 second test timeout allows for 3 retries + overhead
- Each retry: 1s + 2s + 4s = 7s total backoff
- Plus API call time, assertions, and navigation
- 200ms tolerance for timing validation

### Expected Backoff Delays

```typescript
const EXPECTED_BACKOFFS = {
  attempt0: 1000, // baseDelay * 2^0 = 1s
  attempt1: 2000, // baseDelay * 2^1 = 2s
  attempt2: 4000, // baseDelay * 2^2 = 4s
};
```

**Formula**: `baseDelay * 2^attempt`

**Max Delay**: 30 seconds (configured in errorHandler.ts)

## Debugging Tips

### Test Failures

**Symptom**: Test times out waiting for success

**Possible Causes**:
1. API interception not working (check route pattern)
2. Success condition not matching actual UI
3. Error handler not imported/used correctly

**Debug Steps**:
```bash
# Run with trace to see network calls
npx playwright test error-recovery-flow --trace on

# Run headed to see browser
npx playwright test error-recovery-flow --headed

# Add --debug to pause execution
npx playwright test error-recovery-flow --debug
```

### Timing Validation Failures

**Symptom**: "Expected delay to be between X and Y"

**Possible Causes**:
1. System under heavy load (increase tolerance)
2. Browser execution slow (run fewer parallel tests)
3. Timing measurement off by constant offset

**Solutions**:
- Increase `BACKOFF_TOLERANCE_MS` to 500 for slow systems
- Run tests serially in CI: `workers: 1`
- Check timestamps are measured correctly

### Toast Detection Failures

**Symptom**: "Error toast did not appear"

**Possible Causes**:
1. Toast uses different ARIA role
2. Toast appears/disappears too quickly
3. Toast text doesn't match filter

**Debug Steps**:
```typescript
// Add screenshot before assertion
await page.screenshot({ path: 'toast-debug.png' });

// Try different selectors
const toast1 = page.locator('[role="alert"]');
const toast2 = page.locator('[data-testid="toast"]');
const toast3 = page.locator('.toast-container');
```

## Best Practices for Maintenance

### When Adding New Tests

1. **Follow naming convention**: "should [do something] when [condition]"
2. **Use setupApiInterception helper**: Consistent tracking
3. **Validate timing with tolerance**: Don't expect exact milliseconds
4. **Check both success and error paths**: Test should cover both outcomes
5. **Add console logging**: Help future debugging

### When Updating Error Handler

1. **Update expected backoffs**: If formula changes
2. **Update max retries**: If default changes
3. **Add new error types**: Add corresponding E2E test
4. **Verify timing tolerance**: May need adjustment

### When UI Changes

1. **Update selectors**: Use data-testid where possible
2. **Update toast detection**: Match new ARIA patterns
3. **Update loading states**: Match new loading indicators
4. **Test with new UI**: Ensure tests still pass

## Performance Considerations

### Test Execution Time

**Average per test**: 5-15 seconds
**Full suite**: 60-120 seconds (8 tests)

**Optimization strategies**:
- Use `test.describe.parallel()` for independent tests
- Reduce backoff delays in test environment (config option)
- Cache browser contexts between tests
- Run only changed tests in CI (`--only-changed`)

### Resource Usage

**Per test**:
- 1 browser context
- 1 page instance
- ~3 API interceptions
- ~100 MB memory

**Full suite**:
- 8 browser contexts (if parallel)
- ~800 MB memory
- Minimal CPU (waiting for timers)

## Coverage Gap Analysis

### What This E2E Test Covers

✅ **Retry logic**: Automatic retry for transient errors
✅ **Timing**: Exponential backoff validation
✅ **Error classification**: Retryable vs non-retryable
✅ **Max attempts**: Retry limit enforcement
✅ **User experience**: Loading states and error messages
✅ **Multiple error types**: 503, 429, 400, 401, network
✅ **Success scenarios**: Recovery after retry
✅ **Failure scenarios**: Error shown after max retries

### What This Test Does NOT Cover

❌ **Multiple simultaneous operations**: Concurrent API calls with retries
❌ **Network bandwidth throttling**: Slow connections
❌ **Browser back/forward during retry**: Navigation edge cases
❌ **Tab suspension during retry**: Background tab behavior
❌ **Custom retry configuration**: Non-default maxRetries/baseDelay
❌ **Retry cancellation**: User cancels operation during retry
❌ **Server-side retry logic**: Backend retry behavior
❌ **WebSocket failures**: Real-time connection errors

### Recommendations for Additional Tests

1. **Multi-operation test**: Multiple books created simultaneously
2. **Network throttling test**: Slow connection simulation
3. **Navigation test**: User navigates away during retry
4. **Configuration test**: Custom retry settings
5. **Mobile test**: Touch interactions during retry
6. **Accessibility test**: Screen reader announces retry status

## Related Documentation

- **Error Handler Implementation**: `frontend/src/lib/errors/README.md`
- **Unit Tests**: `frontend/src/lib/errors/errorHandler.test.ts`
- **E2E Test Helpers**: `frontend/src/__tests__/helpers/conditionWaiting.ts`
- **Complete Journey Test**: `frontend/src/e2e/complete-authoring-journey.spec.ts`
- **Agile Testing Strategy**: `docs/plans/agile-testing-strategy.md`

## Success Criteria

### Test Pass Criteria

All 8 tests must pass with:
- ✅ Correct retry count for each scenario
- ✅ Timing within tolerance (±200ms)
- ✅ Appropriate error messages shown
- ✅ User experience validated

### Quality Metrics

- **Test reliability**: >95% pass rate on re-runs
- **Execution time**: <120 seconds for full suite
- **Coverage**: Validates all error types in errorHandler.ts
- **Documentation**: Clear explanations for each test

## Conclusion

This E2E test suite provides comprehensive validation of the error recovery flow, ensuring:

1. **Automatic retry works**: Transient errors recover transparently
2. **Timing is correct**: Exponential backoff follows expected pattern
3. **Classification works**: Retryable vs non-retryable errors
4. **Limits respected**: Max retry attempts enforced
5. **UX is smooth**: Loading states and error messages appropriate

The tests complement the unit test suite (100% pass rate, 29 tests) by validating the entire error recovery flow in a real browser environment with actual network interception and timing measurements.
