# Dialog & Modal Specialist - Task Brief

**Assigned Tests**: 7 failures
**Status**: Ready to start
**Priority**: P0

---

## Objective
Fix all BookCard deletion tests (6) and TocGenerationWizard loading state test (1).

---

## Failing Tests

### BookCard.test.tsx (6 failures)
All under "Delete functionality" describe block:
1. should show confirmation dialog when delete button is clicked
2. should close dialog when cancel is clicked
3. should call onDelete when delete is confirmed
4. should show loading state during deletion
5. should handle deletion errors gracefully
6. should prevent card navigation when delete button is clicked

### TocGenerationWizard.test.tsx (1 failure)
- "shows loading state in TocGenerating"

---

## Root Cause Analysis

### BookCard Issues
**Hypothesis**: DeleteBookModal integration with Radix UI Dialog
- Dialog Portal mock exists in jest.setup.ts (lines 150-170)
- DeleteBookModal might not be rendering children properly
- Type-to-confirm logic might be blocking test interactions
- Missing mocks for confirmation flow

### TocWizard Issues
**Hypothesis**: Loading state not rendering or wrong query selector
- Check if loading spinner has correct test ID
- Verify component conditional rendering logic

---

## Files to Investigate

### Test Files
- `frontend/src/__tests__/components/BookCard.test.tsx`
- `frontend/src/__tests__/TocGenerationWizard.test.tsx`

### Component Files
- `frontend/src/components/BookCard.tsx`
- `frontend/src/components/DeleteBookModal.tsx`
- `frontend/src/components/toc/TocGenerationWizard.tsx`
- `frontend/src/components/toc/TocGenerating.tsx`

### Test Setup
- `frontend/src/jest.setup.ts` (Dialog Portal mock ~line 150)

---

## Investigation Steps

1. **Read Context**:
   - Read `claudedocs/bd-2-final-status.md` for Portal mock details
   - Read failing test files to understand expectations

2. **Run Tests**:
   ```bash
   cd frontend
   npm test BookCard.test.tsx
   npm test TocGenerationWizard.test.tsx
   ```

3. **Debug BookCard**:
   - Check if DeleteBookModal renders dialog content
   - Verify type-to-confirm input is accessible
   - Check button enable/disable logic
   - Ensure onDelete callback is properly mocked

4. **Debug TocWizard**:
   - Check loading state conditional rendering
   - Verify spinner/loading element query selector
   - Check if component is wrapped in proper provider

5. **Apply Fixes**:
   - Update test mocks if needed
   - Fix component rendering issues
   - Add missing test setup

6. **Verify**:
   ```bash
   npm test BookCard.test.tsx
   npm test TocGenerationWizard.test.tsx
   npm test  # Full suite to check for regressions
   ```

---

## Success Criteria

✅ All 7 tests passing
✅ No regressions in full test suite
✅ Fixes documented in specialist report

---

## Common Patterns from bd-2-final-status.md

### Dialog Portal Mock (jest.setup.ts)
```typescript
const Portal = ({ children }: { children: React.ReactNode }) => {
  return <div data-radix-portal>{children}</div>;
};
```

### Type-to-Confirm Pattern (DeleteBookModal)
- User must type book title exactly to enable delete button
- Check if test provides correct typing interaction
- Verify button enable state after typing

### Test Isolation
```typescript
beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
});
```

---

## Deliverables

1. **Fixed test files** (if test issues found)
2. **Fixed component files** (if component issues found)
3. **Updated mocks** (if mock issues found)
4. **Specialist report** documenting:
   - Root causes identified
   - Fixes applied
   - Test results (before/after)
   - Any patterns discovered

---

## Test Commands Reference

```bash
# Run specific tests
npm test BookCard.test.tsx
npm test TocGenerationWizard.test.tsx

# Run with verbose output
npm test BookCard.test.tsx -- --verbose

# Run full suite
npm test
```
