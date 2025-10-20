# TipTap Editor Specialist - Task Brief

**Assigned Tests**: 14 failures
**Status**: Ready to start
**Priority**: P0

---

## Objective
Fix all ChapterEditor.saveStatus tests (10) and ChapterEditor.localStorage tests (4).

---

## Failing Tests

### ChapterEditor.saveStatus.test.tsx (10 failures)
1. Initial state › shows "Not saved yet" when no save has occurred
2. Saving state › shows loading spinner during auto-save
3. Saving state › shows loading spinner during manual save
4. Saved state › shows green checkmark and timestamp after successful auto-save
5. Error state › clears error message on subsequent successful save
6. Character count › displays character count alongside save status
7. Character count › updates character count as user types
8. Visual consistency › maintains status indicator position in footer
9. Visual consistency › shows only one status indicator at a time
10. Accessibility › provides accessible status updates for screen readers

### ChapterEditor.localStorage.test.tsx (4 failures)
1. Backup on save failure › backs up content when manual save fails
2. Backup on save failure › handles localStorage quota exceeded error gracefully
3. Backup recovery › handles corrupted backup data gracefully
4. Edge cases › handles multiple rapid save failures correctly

---

## Root Cause Analysis

**Primary Issue**: TipTap editor mock doesn't fully replicate real editor behavior
- Mock exists in jest.setup.ts (lines 257-469, 200+ lines)
- State management for save operations incomplete
- Callback handling (onChange, onUpdate) might not trigger properly
- Character count not updating from mock

**Secondary Issues**:
- localStorage backup logic not triggered by mocked save failures
- Editor state persistence not working in mock

---

## Files to Investigate

### Test Files
- `frontend/src/components/chapters/__tests__/ChapterEditor.saveStatus.test.tsx`
- `frontend/src/components/chapters/__tests__/ChapterEditor.localStorage.test.tsx`

### Component Files
- `frontend/src/components/chapters/ChapterEditor.tsx`
- `frontend/src/components/chapters/EditorContent.tsx` (if exists)

### Test Setup
- `frontend/src/jest.setup.ts` (TipTap mock lines 257-469)

---

## Investigation Steps

1. **Read Context**:
   - Read `claudedocs/bd-2-final-status.md` section on TipTap issues
   - Read TipTap mock in jest.setup.ts to understand current implementation

2. **Run Tests**:
   ```bash
   cd frontend
   npm test ChapterEditor.saveStatus.test.tsx
   npm test ChapterEditor.localStorage.test.tsx
   ```

3. **Debug Save Status**:
   - Check if editor.getHTML() returns expected content
   - Verify onChange callbacks trigger on editor updates
   - Check character count calculation (editor.storage.characterCount)
   - Ensure save status indicators render with correct text/icons

4. **Debug localStorage Backup**:
   - Check if save failure triggers localStorage.setItem()
   - Verify backup key format matches test expectations
   - Ensure corrupted JSON handling works
   - Check quota exceeded error simulation

5. **Enhance TipTap Mock**:
   - Add better state management for content updates
   - Implement proper callback triggering (onChange, onUpdate)
   - Add character count tracking
   - Support localStorage interactions

6. **Verify**:
   ```bash
   npm test ChapterEditor.saveStatus.test.tsx
   npm test ChapterEditor.localStorage.test.tsx
   npm test ChapterEditor  # All ChapterEditor tests
   npm test  # Full suite
   ```

---

## Success Criteria

✅ All 14 tests passing
✅ TipTap mock properly simulates editor state
✅ Save status indicators render correctly
✅ localStorage backup works as expected
✅ No regressions in other ChapterEditor tests

---

## TipTap Mock Analysis (from bd-2-final-status.md)

### Current Mock Structure (jest.setup.ts lines 257-469)
```typescript
class MockEditor {
  content: string;
  listeners: Map<string, Function[]>;

  getHTML() { return this.content; }
  on(event, callback) { /* listener management */ }
  commands: { /* command implementations */ }
  storage: { characterCount: { characters: () => 0 } }
}
```

### Known Issues
- Callbacks don't trigger on content updates
- Character count always returns 0
- State changes don't propagate to component
- localStorage interactions not simulated

### Required Enhancements
1. **Stateful Content Management**:
   ```typescript
   setContent(html: string) {
     this.content = html;
     this.trigger('update', { editor: this });
   }
   ```

2. **Character Count**:
   ```typescript
   storage: {
     characterCount: {
       characters: () => this.content.replace(/<[^>]*>/g, '').length
     }
   }
   ```

3. **Event Triggering**:
   ```typescript
   trigger(event: string, data: any) {
     const handlers = this.listeners.get(event) || [];
     handlers.forEach(handler => handler(data));
   }
   ```

---

## Common Patterns

### Save Status Test Pattern
```typescript
// User types in editor
await user.type(screen.getByRole('textbox'), 'content');

// Wait for auto-save debounce
await act(async () => {
  jest.advanceTimersByTime(3000);
  await Promise.resolve();
});

// Verify save status
expect(screen.getByText(/saved/i)).toBeInTheDocument();
```

### localStorage Backup Pattern
```typescript
// Simulate save failure
mockUpdateChapter.mockRejectedValueOnce(new Error('Network error'));

// Trigger save
await user.click(screen.getByText(/save/i));

// Verify backup
const backup = localStorage.getItem('chapter-backup-123');
expect(backup).toBeTruthy();
```

---

## Deliverables

1. **Enhanced TipTap mock** in jest.setup.ts
2. **Fixed test files** (if test issues found)
3. **Fixed component files** (if component issues found)
4. **Specialist report** documenting:
   - TipTap mock enhancements made
   - Root causes identified
   - Fixes applied
   - Test results (before/after)
   - Patterns for future TipTap testing

---

## Test Commands Reference

```bash
# Run specific tests
npm test ChapterEditor.saveStatus.test.tsx
npm test ChapterEditor.localStorage.test.tsx

# Run all ChapterEditor tests
npm test ChapterEditor

# Run with coverage
npm test ChapterEditor -- --coverage

# Run full suite
npm test
```
