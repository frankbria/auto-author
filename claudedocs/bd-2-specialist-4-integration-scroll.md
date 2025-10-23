# Integration & Scroll Specialist - Task Brief

**Assigned Tests**: 4 failures
**Status**: Ready to start
**Priority**: P0

---

## Objective
Fix TabOverflowScroll tests (2) and ChapterQuestionsIntegration tests (2).

---

## Failing Tests

### TabOverflowScroll.test.tsx (2 failures)
1. "scrolls tab container when scroll buttons are clicked"
2. "automatically scrolls to make active tab visible"

### ChapterQuestionsIntegration.test.tsx (2 failures)
1. Full Integration Workflow › handles error states gracefully
2. Accessibility and Responsive Design › provides proper ARIA labels and roles

---

## Root Cause Analysis

### TabOverflowScroll Issues
**Hypothesis**: Scroll API mocking incomplete
- scrollLeft property not mocked properly
- scrollIntoView might not be triggering
- getBoundingClientRect returns 0s in jsdom (expected)
- Need to verify scroll behavior through other means

### ChapterQuestionsIntegration Issues
**Hypothesis**: Test isolation problems
- Tests might pass standalone but fail in full suite
- Mock conflicts between test files
- State leakage from previous tests
- Missing beforeEach cleanup

---

## Files to Investigate

### Test Files
- `frontend/src/__tests__/TabOverflowScroll.test.tsx`
- `frontend/src/__tests__/ChapterQuestionsIntegration.test.tsx`

### Component Files
- `frontend/src/components/chapters/ChapterTabs.tsx` (tab overflow logic)
- `frontend/src/components/chapters/questions/*` (integration components)

### Test Setup
- `frontend/src/jest.setup.ts` (scrollIntoView mock ~line 100)

---

## Investigation Steps

1. **Read Context**:
   - Read `claudedocs/bd-2-final-status.md` section on test isolation
   - Read existing scroll mocks in jest.setup.ts

2. **Run Tests Standalone**:
   ```bash
   cd frontend
   npm test TabOverflowScroll.test.tsx
   npm test ChapterQuestionsIntegration.test.tsx
   ```

3. **Run Tests in Suite**:
   ```bash
   npm test  # Full suite to check isolation issues
   ```

4. **Debug TabOverflowScroll**:
   - Check scrollIntoView mock implementation
   - Verify scrollLeft can be set and read
   - Check scroll button click handlers
   - Verify scroll behavior through DOM state (not visual)
   - Test with jest.spyOn(element, 'scrollIntoView')

5. **Debug ChapterQuestionsIntegration**:
   - Run test standalone vs in suite
   - Check beforeEach/afterEach cleanup
   - Verify mock scope isolation
   - Check for global state leakage
   - Identify which tests run before that affect these

6. **Apply Fixes**:
   - Enhance scroll API mocks
   - Add better test isolation (beforeEach cleanup)
   - Fix mock scope conflicts
   - Clear global state properly

7. **Verify**:
   ```bash
   npm test TabOverflowScroll.test.tsx
   npm test ChapterQuestionsIntegration.test.tsx
   npm test  # Full suite to confirm isolation
   ```

---

## Success Criteria

✅ All 4 tests passing
✅ Tests pass both standalone AND in full suite
✅ Scroll mocks work reliably
✅ Test isolation verified
✅ No regressions

---

## Patterns from bd-2-final-status.md

### Test Isolation Pattern
```typescript
beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  sessionStorage.clear();
  // Clear any global state specific to your tests
});

afterEach(() => {
  jest.restoreAllMocks();
});
```

### Scroll API Mocking Pattern
```typescript
// In jest.setup.ts or test file
Element.prototype.scrollIntoView = jest.fn();

// In test
const scrollSpy = jest.spyOn(element, 'scrollIntoView');
await user.click(scrollButton);
expect(scrollSpy).toHaveBeenCalled();
```

### scrollLeft Property
```typescript
// Mock scrollLeft as settable property
Object.defineProperty(HTMLElement.prototype, 'scrollLeft', {
  writable: true,
  value: 0,
});

// In test
const container = screen.getByRole('tablist');
container.scrollLeft = 100;
expect(container.scrollLeft).toBe(100);
```

### jsdom Scroll Limitations
```typescript
// ❌ Don't test visual scroll behavior
expect(element.getBoundingClientRect().left).toBe(100); // Always 0 in jsdom

// ✅ Test scroll API calls or DOM state
expect(scrollIntoView).toHaveBeenCalled();
expect(container.scrollLeft).toBe(100);
expect(container).toHaveAttribute('data-scrolled', 'true');
```

---

## Investigation Checklist

### For TabOverflowScroll
- [ ] Read test expectations (what should happen?)
- [ ] Check scrollIntoView mock in jest.setup.ts
- [ ] Verify scrollLeft property can be set/read
- [ ] Check scroll button click handlers in component
- [ ] Add spies to verify scroll methods are called
- [ ] Update test assertions if needed (verify behavior, not visuals)

### For ChapterQuestionsIntegration
- [ ] Run test standalone (does it pass?)
- [ ] Run test in full suite (does it fail?)
- [ ] Check which tests run before it
- [ ] Review beforeEach cleanup
- [ ] Check mock scope (jest.mock vs jest.fn)
- [ ] Look for global state mutations
- [ ] Add better cleanup if needed

---

## Common Isolation Issues

1. **Mock Leakage**:
   ```typescript
   // ❌ BAD: Mock persists across tests
   jest.mock('../api/bookClient');

   // ✅ GOOD: Clear in beforeEach
   beforeEach(() => {
     jest.clearAllMocks();
   });
   ```

2. **localStorage Pollution**:
   ```typescript
   beforeEach(() => {
     localStorage.clear();
     sessionStorage.clear();
   });
   ```

3. **Global State**:
   ```typescript
   // Check for module-level state
   let globalState = {};  // Can leak between tests

   beforeEach(() => {
     globalState = {};  // Reset
   });
   ```

---

## Deliverables

1. **Fixed scroll mocks** in jest.setup.ts or test file
2. **Fixed test isolation** in ChapterQuestionsIntegration
3. **Fixed test assertions** if needed
4. **Specialist report** documenting:
   - Root causes identified
   - Scroll mocking strategy
   - Isolation issues found
   - Fixes applied
   - Test results (standalone vs suite)

---

## Test Commands Reference

```bash
# Run specific tests
npm test TabOverflowScroll.test.tsx
npm test ChapterQuestionsIntegration.test.tsx

# Run with verbose output
npm test TabOverflowScroll.test.tsx -- --verbose

# Run individual test by name
npm test -t "scrolls tab container"

# Run standalone vs full suite
npm test TabOverflowScroll.test.tsx  # Standalone
npm test  # Full suite

# Check test order
npm test -- --listTests
```
