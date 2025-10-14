# E2E Test: Editing & Auto-save Flow

## Overview

This E2E test suite validates the chapter editor's auto-save functionality, including localStorage backup on network failure and save status indicators. It addresses a critical gap identified in the E2E assessment report.

## Test Location

**File**: `frontend/src/e2e/editing-autosave-flow.spec.ts`

## Test Coverage

### 1. Normal Auto-save Flow (Test 1)
- ✅ User types content in TipTap editor
- ✅ Auto-save triggers after 3-second debounce
- ✅ Save status updates: "Not saved yet" → "Saving..." → "Saved ✓ [timestamp]"
- ✅ Content persists on page refresh
- ✅ No localStorage backup created on successful save

### 2. localStorage Backup on Network Failure (Test 2)
- ✅ Network failure simulated via `page.route()` interception
- ✅ Content automatically backed up to localStorage
- ✅ Error message indicates local backup was created
- ✅ Backup persists across page refreshes
- ✅ Backup structure: `{ content, timestamp, error }`

### 3. Content Recovery from Backup (Test 3)
- ✅ Recovery notification appears when backup exists
- ✅ "Restore Backup" and "Dismiss" buttons present
- ✅ Clicking "Restore Backup" loads content into editor
- ✅ Notification dismisses after restoration
- ✅ Backup cleared from localStorage after recovery
- ✅ Restored content auto-saves successfully

### 4. Backup Dismissal (Test 4)
- ✅ User can dismiss backup without restoring
- ✅ Notification disappears after dismissal
- ✅ Backup removed from localStorage
- ✅ Editor content remains unchanged

### 5. Save Status Indicators (Test 5)
- ✅ Initial state: "Not saved yet"
- ✅ During save: "Saving..." with spinner icon
- ✅ After success: "Saved ✓ [timestamp]" with checkmark
- ✅ Status cycle repeats on subsequent edits

### 6. Debounce Behavior (Test 6)
- ✅ Save does NOT trigger before 3-second delay
- ✅ Save correctly triggers after full 3-second debounce
- ✅ Rapid typing does not create multiple save requests

### 7. Network Recovery (Test 7)
- ✅ Initial save fails and creates backup
- ✅ Network restored mid-session
- ✅ Subsequent edits save successfully
- ✅ Backup cleared after successful save post-recovery

## Test Strategy

### Optimization: Condition-Based Waiting
All async operations use `waitForCondition` helper instead of fixed timeouts:

```typescript
import { waitForCondition } from '../__tests__/helpers/conditionWaiting';

await waitForCondition(
  async () => await page.locator('text=/saved.*✓/i').isVisible(),
  {
    timeout: 10000,
    timeoutMessage: 'Save completion indicator did not appear',
  }
);
```

**Benefits**:
- Tests complete as fast as possible (no arbitrary waits)
- More reliable (no race conditions from timing variations)
- Clear error messages when conditions fail
- Consistent with optimization strategy from Task 2

### Network Failure Simulation

Uses Playwright's `page.route()` to intercept and fail API calls:

```typescript
await page.route('**/api/books/*/chapters/*/content', (route) => {
  if (route.request().method() === 'PUT' || route.request().method() === 'POST') {
    // Simulate network failure
    route.abort('failed');
  } else {
    // Allow GET requests through
    route.continue();
  }
});
```

This approach:
- Tests real network failure scenarios
- Can be toggled mid-test for recovery testing
- Doesn't require backend changes or special test modes

### localStorage Access

Uses `page.evaluate()` to access browser storage from test context:

```typescript
// Get backup
const backup = await page.evaluate(([bid, cid]) => {
  const backupKey = `chapter-backup-${bid}-${cid}`;
  const backup = localStorage.getItem(backupKey);
  return backup ? JSON.parse(backup) : null;
}, [bookId, chapterId]);

// Set backup
await page.evaluate(([bid, cid, content, error]) => {
  const backupKey = `chapter-backup-${bid}-${cid}`;
  const backup = { content, timestamp: Date.now(), error };
  localStorage.setItem(backupKey, JSON.stringify(backup));
}, [bookId, chapterId, content, error]);
```

**Benefits**:
- Direct access to browser storage
- Enables setup and verification of backup scenarios
- No need to trigger UI actions to create backups

## Running the Tests

### Prerequisites
```bash
# Install Playwright browsers if not already installed
npx playwright install

# Ensure backend server is running
cd backend && uv run uvicorn app.main:app --reload

# Ensure frontend dev server is running (in another terminal)
cd frontend && npm run dev
```

### Run Commands

```bash
# Run all editing & auto-save tests
npx playwright test editing-autosave-flow

# Run specific test by name
npx playwright test editing-autosave-flow -g "auto-saves content"

# Run with UI mode (interactive debugging)
npx playwright test editing-autosave-flow --ui

# Run headed (see browser actions)
npx playwright test editing-autosave-flow --headed

# Run with debug mode (step through)
npx playwright test editing-autosave-flow --debug

# Run on specific browser only
npx playwright test editing-autosave-flow --project=chromium
```

### Viewing Test Results

```bash
# Generate HTML report
npx playwright show-report

# View test traces (after failure)
npx playwright show-trace trace.zip
```

## Test Configuration

### Timeouts
- **Test Timeout**: 60 seconds (full test suite)
- **Auto-save Debounce**: 3 seconds (matches implementation)
- **API Timeout**: 5 seconds (max wait for API responses)
- **Condition Timeout**: 5-10 seconds (waitForCondition default)

### Test Data
```typescript
const TEST_BOOK_ID = 'test-book-123';
const TEST_CHAPTER_ID = 'test-chapter-456';
const TEST_CONTENT = {
  initial: '<p>Initial chapter content that should be saved.</p>',
  modified: '<p>Modified content after user edits.</p>',
  backup: '<p>Content that will be backed up to localStorage on network failure.</p>',
  recovery: '<p>Recovered content from localStorage backup.</p>',
};
```

## Key Implementation Details

### Auto-save Mechanism
1. **Debounce Period**: 3 seconds from last keystroke
2. **Trigger**: Content change in TipTap editor
3. **API Endpoint**: `PUT /api/books/{bookId}/chapters/{chapterId}/content`
4. **On Success**: Clear any existing localStorage backup
5. **On Failure**: Create localStorage backup with error details

### localStorage Backup Structure
```typescript
interface ChapterBackup {
  content: string;        // HTML content from TipTap editor
  timestamp: number;      // Date.now() when backup created
  error: string;          // Error message from failed save
}

// Storage key format
const backupKey = `chapter-backup-${bookId}-${chapterId}`;
```

### Save Status Indicator States
1. **Not saved yet**: Initial state, no recent save
2. **Saving...**: Save in progress (with spinner icon)
3. **Saved ✓ [timestamp]**: Save completed successfully
4. **Error message**: Displayed in red banner on failure

## Assumptions & Limitations

### Assumptions
1. **Authentication**: Tests assume Clerk dev mode auto-authentication
2. **API Availability**: Backend server must be running at `http://localhost:3000`
3. **Editor Initialization**: TipTap editor loads with `.tiptap-editor` class
4. **localStorage Support**: Browser has localStorage enabled and functional

### Limitations
1. **No Real Network Testing**: Uses route interception, not actual network conditions
2. **Single Browser Context**: Doesn't test cross-tab synchronization
3. **Timing Dependencies**: Some tests use `page.waitForTimeout()` for debounce verification
4. **Mock-Free**: Requires real backend and database (not fully isolated)

## Troubleshooting

### Test Failures

#### "Chapter editor did not load"
**Cause**: Editor initialization timeout
**Fix**:
- Verify frontend dev server is running
- Check for JavaScript errors in browser console
- Increase timeout in `navigateToChapterEditor` helper

#### "Save completion indicator did not appear"
**Cause**: API save request failed or timeout
**Fix**:
- Verify backend server is running
- Check API endpoint is accessible
- Review network tab for failed requests
- Check Clerk authentication is working

#### "Backup recovery notification did not appear"
**Cause**: localStorage backup not detected on mount
**Fix**:
- Verify `setLocalStorageBackup` helper is called correctly
- Check localStorage is enabled in browser
- Ensure backup key format matches: `chapter-backup-${bookId}-${chapterId}`

### Common Issues

#### Tests Pass Locally, Fail in CI
**Possible Causes**:
1. Different timing behavior in CI environment
2. Authentication not configured for CI
3. localStorage not available in headless browser
4. Backend not running or accessible in CI

**Solutions**:
- Increase timeouts in `playwright.config.ts` for CI
- Mock authentication or configure test account
- Check headless browser localStorage support
- Ensure backend service is available in CI pipeline

#### Flaky Tests
**Possible Causes**:
1. Race conditions from timing assumptions
2. Network latency variations
3. Resource constraints in test environment

**Solutions**:
- Replace `page.waitForTimeout()` with `waitForCondition()`
- Increase condition timeouts for slow environments
- Add retry logic in `playwright.config.ts`
- Use `test.beforeEach()` to ensure clean state

## Recommendations

### Selector Improvements
Add `data-testid` attributes to components for more reliable selectors:

#### ChapterEditor.tsx
```tsx
<div data-testid="chapter-editor" className="h-full flex flex-col">
  {hasBackup && (
    <div data-testid="backup-recovery-banner" className="bg-yellow-500/10...">
      <span>A local backup of your content is available...</span>
      <div className="flex gap-2">
        <Button data-testid="restore-backup-button" onClick={handleRecoverBackup}>
          Restore Backup
        </Button>
        <Button data-testid="dismiss-backup-button" onClick={handleDismissBackup}>
          Dismiss
        </Button>
      </div>
    </div>
  )}

  <EditorContent
    data-testid="editor-content"
    editor={editor}
    className="w-full h-full..."
  />

  <div data-testid="save-status-indicator" data-save-status={saveStatus}>
    {isSaving && <span>Saving...</span>}
    {!isSaving && lastSaved && <span>Saved ✓ {lastSaved.toLocaleTimeString()}</span>}
    {!isSaving && !lastSaved && <span>Not saved yet</span>}
  </div>
</div>
```

#### Benefits
- Selectors independent of UI text changes
- More explicit test intent
- Faster selector execution
- Easier to maintain when UI refactored

### Additional Test Coverage

#### Priority: High
1. **Concurrent Tab Testing**: Verify backup doesn't conflict across browser tabs
2. **Quota Exceeded**: Test when localStorage quota is full
3. **Corrupted Backup**: Verify graceful handling of invalid JSON in localStorage
4. **Mobile Testing**: Run tests on mobile viewports and devices

#### Priority: Medium
1. **Network Speed**: Test with simulated slow network (slow 3G)
2. **Large Content**: Verify backup with very large chapter content
3. **Rapid Network Toggle**: Test rapid network failure/recovery cycles
4. **Browser Refresh During Save**: Test page refresh while save is in progress

#### Priority: Low
1. **Visual Regression**: Screenshot comparisons of save status indicators
2. **Accessibility**: Verify screen reader announcements for save status
3. **Internationalization**: Test with different language settings
4. **Performance**: Measure auto-save impact on editor performance

### CI/CD Integration

#### GitHub Actions Workflow
```yaml
name: E2E Tests - Editing & Auto-save

on: [push, pull_request]

jobs:
  e2e-editing-autosave:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci
        working-directory: frontend

      - name: Install Playwright browsers
        run: npx playwright install --with-deps
        working-directory: frontend

      - name: Start backend server
        run: |
          cd backend
          uv run uvicorn app.main:app &
          sleep 5

      - name: Run E2E tests
        run: npx playwright test editing-autosave-flow
        working-directory: frontend
        env:
          BASE_URL: http://localhost:3000

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-results
          path: frontend/test-results/

      - name: Upload Playwright report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: frontend/playwright-report/
```

## Metrics & Success Criteria

### Test Execution Metrics
- **Total Tests**: 7 test scenarios
- **Expected Duration**: 90-120 seconds (full suite)
- **Pass Rate Target**: 100%
- **Flakiness Tolerance**: < 5% (1 flake per 20 runs)

### Coverage Metrics
- **Component Coverage**: ChapterEditor.tsx (auto-save logic)
- **API Coverage**: Chapter content save endpoint
- **Storage Coverage**: localStorage backup/recovery
- **UI Coverage**: Save status indicators, backup notifications

### Quality Metrics
- **Reliability**: 95%+ pass rate in CI
- **Maintainability**: < 5 minutes to update tests for UI changes
- **Execution Speed**: < 2 minutes for full suite
- **Debuggability**: Clear error messages for all failure modes

## Related Documentation

- **Implementation**: `frontend/src/components/chapters/ChapterEditor.tsx`
- **Unit Tests**: `frontend/src/components/chapters/__tests__/ChapterEditor.localStorage.test.tsx`
- **Optimization Helper**: `frontend/src/__tests__/helpers/conditionWaiting.ts`
- **E2E Assessment**: `docs/plans/e2e-assessment.md`
- **Playwright Config**: `frontend/playwright.config.ts`

## Changelog

### 2025-10-13 - Initial Implementation
- Created comprehensive E2E test suite for editing & auto-save flow
- Implemented 7 test scenarios covering critical user workflows
- Used condition-based waiting optimization pattern
- Added network failure simulation and localStorage validation
- Documented test coverage, limitations, and recommendations
