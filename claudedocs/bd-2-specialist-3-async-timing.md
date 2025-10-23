# Async Timing Specialist - Task Brief

**Assigned Tests**: 8 failures
**Status**: Ready to start
**Priority**: P0

---

## Objective
Fix errorHandler timing tests (5), VoiceTextInputIntegration test (1), and ChapterQuestionsEndToEnd tests (2).

---

## Failing Tests

### errorHandler.test.ts (5 failures)
1. ErrorHandler Class › should stop retrying after max attempts
2. ErrorHandler Class › should apply exponential backoff between retries
3. ErrorHandler Class › should allow custom max retries configuration
4. handleApiError - High-Level API › should show toast notification on network error after retries exhausted
5. handleApiError - High-Level API › should support custom error messages in toast

### VoiceTextInputIntegration.test.tsx (1 failure)
- "triggers auto-save when typing"

### ChapterQuestionsEndToEnd.test.tsx (2 failures)
1. Complete Question Answering Workflow › completes full question answering session
2. Integration with Chapter Workflow › triggers draft generation after question completion

---

## Root Cause Analysis

### errorHandler Issues
**Hypothesis**: Complex fake timer interactions with exponential backoff
- jest.useFakeTimers() conflicting with retry logic
- Need proper act() wrapping for timer advances
- Toast notifications might not be triggering
- Error instantiation pattern issues (TypeError triggers real fetch)

### VoiceTextInput Issues
**Hypothesis**: Debounce timing with fake timers
- 3-second auto-save debounce needs fake timer advancement
- act() + Promise.resolve() pattern required
- userEvent.setup({ delay: null }) needed with fake timers

### EndToEnd Issues
**Hypothesis**: React Query incompatibility with fake timers
- React Query's internal timers conflict with jest.useFakeTimers()
- Extended timeouts needed (15000-30000ms)
- Complex async workflows need real timers

---

## Files to Investigate

### Test Files
- `frontend/src/lib/errors/errorHandler.test.ts`
- `frontend/src/__tests__/VoiceTextInputIntegration.test.tsx`
- `frontend/src/__tests__/ChapterQuestionsEndToEnd.test.tsx`

### Implementation Files
- `frontend/src/lib/errors/errorHandler.ts`
- `frontend/src/components/chapters/VoiceTextInput.tsx`

### Test Setup
- `frontend/src/jest.setup.ts`

---

## Investigation Steps

1. **Read Context**:
   - Read `claudedocs/bd-2-final-status.md` section on async timing issues
   - Read errorHandler implementation to understand retry logic

2. **Run Tests**:
   ```bash
   cd frontend
   npm test errorHandler.test.ts
   npm test VoiceTextInputIntegration.test.tsx
   npm test ChapterQuestionsEndToEnd.test.tsx
   ```

3. **Debug errorHandler**:
   - Check fake timer setup (useFakeTimers/useRealTimers)
   - Verify exponential backoff calculation (2^attempt * baseDelay)
   - Check act() wrapping for timer advances
   - Verify toast mock is called correctly
   - Check error instantiation pattern (avoid TypeError)

4. **Debug VoiceTextInput**:
   - Verify debounce delay (should be 3000ms)
   - Check userEvent.setup({ delay: null })
   - Apply act() + jest.advanceTimersByTime(3000)
   - Ensure auto-save callback triggers

5. **Debug EndToEnd**:
   - Check if fake timers are disabled (should use real timers)
   - Verify timeouts are extended (15000-30000ms)
   - Check React Query mock setup
   - Ensure complex workflows have enough time

6. **Apply Fixes**:
   - Implement consistent fake timer pattern
   - Fix error instantiation
   - Add proper act() wrapping
   - Adjust timeouts for complex workflows

7. **Verify**:
   ```bash
   npm test errorHandler.test.ts
   npm test VoiceTextInputIntegration.test.tsx
   npm test ChapterQuestionsEndToEnd.test.tsx
   npm test  # Full suite
   ```

---

## Success Criteria

✅ All 8 tests passing
✅ Fake timers work correctly with retry logic
✅ Debounce timing reliable and fast
✅ EndToEnd tests complete without timeouts
✅ No regressions in timing-sensitive tests

---

## Patterns from bd-2-final-status.md

### Fake Timer Pattern (for debounce)
```typescript
jest.useFakeTimers();
const user = userEvent.setup({ delay: null });

await user.type(input, 'text');

await act(async () => {
  jest.advanceTimersByTime(3000);
  await Promise.resolve();
});

jest.useRealTimers();
```

### Exponential Backoff Pattern
```typescript
// Advance timers for each retry
for (let i = 0; i < maxRetries; i++) {
  const delay = Math.pow(2, i) * 1000; // 2^i seconds

  await act(async () => {
    jest.advanceTimersByTime(delay);
    await Promise.resolve();
  });
}
```

### Error Instantiation Pattern (from bd-2-final-status.md)
```typescript
// ❌ BAD: Triggers real fetch in jsdom
new TypeError('Failed to fetch')

// ✅ GOOD: Safe error creation
const err = new Error('Failed to fetch');
err.name = 'NetworkError';
```

### React Query + Real Timers Pattern
```typescript
// Don't use fake timers with React Query
test('complex workflow', async () => {
  // Use real timers (default)

  await waitFor(() => {
    expect(result).toBeTruthy();
  }, { timeout: 15000 }); // Extended timeout
}, 30000); // Test timeout
```

---

## Known Issues from bd-2-final-status.md

1. **React Query Incompatibility**:
   - React Query's internal timers conflict with jest.useFakeTimers()
   - Solution: Use real timers + extended timeouts

2. **TypeError Fetch Issue**:
   - Creating `new TypeError('Failed to fetch')` triggers actual fetch
   - Solution: Use Error with name property

3. **Toast Mock**:
   - sonner toast needs proper mock in jest.setup.ts
   - Check if mock is being called correctly

---

## Deliverables

1. **Fixed test files** with proper timing patterns
2. **Updated errorHandler tests** with correct fake timer usage
3. **Fixed VoiceTextInput test** with debounce timing
4. **Fixed EndToEnd tests** with appropriate timeouts
5. **Specialist report** documenting:
   - Root causes identified
   - Timing patterns applied
   - Test results (before/after)
   - Best practices for async testing

---

## Test Commands Reference

```bash
# Run specific tests
npm test errorHandler.test.ts
npm test VoiceTextInputIntegration.test.tsx
npm test ChapterQuestionsEndToEnd.test.tsx

# Run with verbose output
npm test errorHandler.test.ts -- --verbose

# Run individual test by name
npm test -t "should stop retrying after max attempts"

# Run full suite
npm test
```
