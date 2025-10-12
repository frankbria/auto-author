# Keyboard Navigation - Action Plan

## Quick Summary

**Current Status**: 🟡 PARTIAL - Basic keyboard support exists but critical gaps remain

**Key Findings**:
- ✅ Chapter shortcuts (Ctrl+1-9) implemented and tested
- ✅ Modal escape key handling works correctly
- ✅ Form Enter key submission (native HTML)
- ❌ **CRITICAL**: Chapter tabs not keyboard accessible (WCAG violation)
- ❌ No keyboard shortcut documentation
- ⚠️ Incomplete focus indicator coverage

---

## Critical Issues (Fix Immediately)

### 1. Chapter Tabs Keyboard Accessibility ⚠️ WCAG VIOLATION
**Severity**: 🔴 CRITICAL
**WCAG**: 2.1.1 Keyboard (Level A)

**Problem**: Chapter tab elements use `<div onClick>` without keyboard handlers. Keyboard-only users cannot switch tabs except via Ctrl+1-9.

**File**: `/frontend/src/components/chapters/ChapterTab.tsx` (Lines 52-108)

**Fix**:
```typescript
// ADD to the div wrapper
<div
  role="button"
  tabIndex={0}
  aria-label={`Select ${chapter.title}`}
  aria-selected={isActive}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelect();
    }
  }}
  onClick={onSelect}
  // ... rest of props
>
```

**Estimated Time**: 1 hour
**Testing**: Verify Tab key navigation works, Enter/Space activate tabs

---

### 2. Visual Focus Indicators
**Severity**: 🔴 CRITICAL
**WCAG**: 2.4.7 Focus Visible (Level AA)

**Problem**: Custom styled elements may not show focus state clearly.

**Fix**: Add to global CSS or Tailwind config
```css
/* Ensure all focusable elements have visible focus */
*:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}
```

**Files to Review**:
- All interactive custom components
- Buttons with custom styling
- Tab elements
- Form controls

**Estimated Time**: 2 hours (1 hour implementation, 1 hour testing)
**Testing**: Tab through entire app, verify focus always visible

---

### 3. Delete Confirmation Enter Key
**Severity**: 🟡 IMPORTANT

**Problem**: DeleteBookModal confirmation input doesn't submit on Enter key.

**File**: `/frontend/src/components/books/DeleteBookModal.tsx` (Lines 140-162)

**Current Code**:
```typescript
<Input
  id="confirm-delete"
  value={confirmationText}
  onChange={(e) => setConfirmationText(e.target.value)}
/>
```

**Fixed Code**:
```typescript
<form onSubmit={(e) => {
  e.preventDefault();
  if (isConfirmed && !isDeleting) handleConfirm();
}}>
  <Input
    id="confirm-delete"
    value={confirmationText}
    onChange={(e) => setConfirmationText(e.target.value)}
  />
</form>
```

**Estimated Time**: 30 minutes
**Testing**: Type title, press Enter, verify deletion triggers

---

## Important Improvements (Next Sprint)

### 4. Document Keyboard Shortcuts
**Severity**: 🟡 IMPORTANT

**Action**: Create Help modal/page documenting all shortcuts

**Content**:
```
Keyboard Shortcuts

Chapter Navigation:
  Ctrl+1 through Ctrl+9    Switch to chapter tab 1-9

General:
  Escape                   Close modal or dialog
  Enter                    Submit form
  Tab                      Navigate forward
  Shift+Tab                Navigate backward

Coming Soon:
  Ctrl+S                   Manual save
  Ctrl+N                   New chapter
  Ctrl+W                   Close tab
```

**Files to Create**:
- `/frontend/src/app/dashboard/help/keyboard-shortcuts/page.tsx`
- Add "Keyboard Shortcuts" link to navigation

**Estimated Time**: 3 hours

---

### 5. Arrow Key Navigation for Tabs
**Severity**: 🟡 IMPORTANT

**Enhancement**: Add Left/Right arrow key navigation between chapter tabs (ARIA best practice)

**File**: `/frontend/src/components/chapters/ChapterTabs.tsx`

**Implementation**:
```typescript
// Enhance existing keyboard handler
const handleKeyDown = (event: KeyboardEvent) => {
  // Existing Ctrl+1-9 handling
  if (event.ctrlKey && event.key >= '1' && event.key <= '9') {
    // ... existing code
  }

  // NEW: Arrow key navigation
  if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
    const activeIndex = state.tab_order.indexOf(state.active_chapter_id);
    if (activeIndex === -1) return;

    let newIndex;
    if (event.key === 'ArrowRight') {
      newIndex = (activeIndex + 1) % state.tab_order.length;
    } else {
      newIndex = activeIndex === 0 ? state.tab_order.length - 1 : activeIndex - 1;
    }

    const newChapterId = state.tab_order[newIndex];
    if (newChapterId) {
      event.preventDefault();
      handleTabSelect(newChapterId);
    }
  }

  // Home/End keys
  if (event.key === 'Home') {
    event.preventDefault();
    handleTabSelect(state.tab_order[0]);
  }
  if (event.key === 'End') {
    event.preventDefault();
    handleTabSelect(state.tab_order[state.tab_order.length - 1]);
  }
};
```

**Estimated Time**: 2 hours (1 hour implementation, 1 hour testing)

---

### 6. Common Editor Shortcuts
**Severity**: 🟢 NICE TO HAVE

**Add these shortcuts**:
- `Ctrl+S` - Manual save (visual feedback)
- `Ctrl+N` - Create new chapter
- `Ctrl+W` - Close current tab
- `Ctrl+Tab` - Next tab
- `Ctrl+Shift+Tab` - Previous tab

**Implementation Location**: `/frontend/src/components/chapters/ChapterTabs.tsx`

**Estimated Time**: 4 hours

---

## Testing Plan

### Manual Testing Checklist

**Critical Path Testing** (30 minutes):
- [ ] Open app, press Tab repeatedly, verify logical order
- [ ] Navigate to chapter tabs, use Tab to select each tab
- [ ] Press Enter/Space on focused tab, verify it activates
- [ ] Press Escape on each modal, verify it closes
- [ ] Fill each form, press Enter, verify submission
- [ ] Verify focus visible on all interactive elements

**Comprehensive Testing** (2 hours):
- [ ] Test all pages using only keyboard (no mouse)
- [ ] Test Ctrl+1-9 shortcuts with 3, 5, 9, and 12 tabs
- [ ] Test arrow key navigation (after implementation)
- [ ] Test Home/End keys (after implementation)
- [ ] Verify no keyboard traps exist
- [ ] Test with screen reader (NVDA or VoiceOver)

### Automated Tests to Add

**File**: `/frontend/src/__tests__/KeyboardNavigation.test.tsx`

```typescript
// ADD these tests

describe('Chapter Tab Keyboard Navigation', () => {
  test('Tab key focuses chapter tabs', () => {
    // Render ChapterTabs
    // Press Tab
    // Verify first tab is focused
  });

  test('Enter key activates focused tab', () => {
    // Focus a tab
    // Press Enter
    // Verify tab becomes active
  });

  test('Arrow keys navigate between tabs', () => {
    // Focus first tab
    // Press ArrowRight
    // Verify next tab is focused
  });
});

describe('Form Keyboard Submission', () => {
  test('Enter key submits book creation form', () => {
    // Fill form
    // Focus any input
    // Press Enter
    // Verify onSubmit called
  });

  test('Enter key submits delete confirmation', () => {
    // Open DeleteBookModal
    // Type exact title
    // Press Enter
    // Verify deletion triggered
  });
});
```

**Estimated Time**: 2 hours to write tests

---

## Timeline

### Week 1: Critical Fixes
- **Day 1-2**: Fix chapter tab keyboard accessibility (#1)
- **Day 2-3**: Add focus visible indicators (#2)
- **Day 3**: Enable Enter key in delete modal (#3)
- **Day 4**: Write and run tests
- **Day 5**: Fix any issues found in testing

**Deliverable**: WCAG Level A compliant keyboard navigation

### Week 2: Important Improvements
- **Day 1**: Document keyboard shortcuts (#4)
- **Day 2-3**: Implement arrow key navigation (#5)
- **Day 4**: Add common editor shortcuts (#6)
- **Day 5**: Comprehensive testing and documentation

**Deliverable**: Enhanced keyboard navigation with documentation

### Week 3: Polish and Audit
- **Day 1-2**: Accessibility audit (automated and manual)
- **Day 3**: Fix any issues found
- **Day 4**: Screen reader testing
- **Day 5**: Final QA and documentation update

**Deliverable**: WCAG 2.1 AA compliant keyboard navigation

---

## Success Criteria

### Minimum (Week 1 Complete)
- ✅ All interactive elements keyboard accessible
- ✅ Focus visible on all focusable elements
- ✅ No WCAG Level A violations
- ✅ Manual testing checklist completed
- ✅ Test coverage for keyboard navigation

### Target (Week 2 Complete)
- ✅ Arrow key navigation in tabs
- ✅ Common keyboard shortcuts implemented
- ✅ Keyboard shortcuts documented
- ✅ Comprehensive test coverage
- ✅ WCAG 2.1 AA compliant

### Stretch (Week 3 Complete)
- ✅ Screen reader compatible
- ✅ Help system with keyboard tutorial
- ✅ Automated accessibility testing in CI/CD
- ✅ Accessibility statement published

---

## Resource Requirements

### Development
- **Engineer Time**: 80 hours (2 weeks)
- **QA Time**: 16 hours (testing)
- **Design Time**: 4 hours (focus indicator design)

### Tools Needed
- Browser DevTools (built-in)
- Screen reader (NVDA - free, or JAWS/VoiceOver)
- axe DevTools (free browser extension)
- Lighthouse (built into Chrome)

### Documentation
- Keyboard shortcuts reference
- Accessibility statement
- Updated user guide
- Developer guidelines for keyboard accessibility

---

## Maintenance

### Ongoing Requirements
- **Code Review**: Check keyboard accessibility in all new PRs
- **Testing**: Include keyboard navigation in QA checklists
- **Documentation**: Update shortcuts when adding new features
- **Monitoring**: Track accessibility complaints/issues

### Automated Checks
- Add axe-core to test suite
- Run Lighthouse accessibility audit in CI/CD
- Fail build on critical accessibility violations

---

## References

- Full analysis: `KEYBOARD_NAVIGATION_REPORT.md`
- WCAG 2.1 Guidelines: https://www.w3.org/WAI/WCAG21/quickref/
- ARIA Authoring Practices: https://www.w3.org/WAI/ARIA/apg/
- Keyboard Accessibility Testing: https://webaim.org/articles/keyboard/

---

**Document Created**: December 2024
**Priority**: HIGH
**Owner**: Engineering Team
**Estimated Completion**: 3 weeks
