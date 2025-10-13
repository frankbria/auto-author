# Tasks 10-11 Quick Reference

**Source**: Component Test Review Report (Task 9)
**Target**: 80% frontend coverage (currently 65.28%)

---

## 🔴 CRITICAL: Fix First (Before Task 10)

### Dependency Import Errors - 68 Tests Failing

**Root Cause**: `web-vitals` and `date-fns` not mocked in test environment

**Fix** (add to `jest.setup.ts`):
```typescript
// Mock web-vitals
jest.mock('web-vitals', () => ({
  onCLS: jest.fn(),
  onFID: jest.fn(),
  onFCP: jest.fn(),
  onLCP: jest.fn(),
  onTTFB: jest.fn(),
}));

// Mock date-fns
jest.mock('date-fns', () => ({
  formatDistanceToNow: jest.fn(() => '5 minutes ago'),
  format: jest.fn((date) => new Date(date).toISOString()),
}));
```

**Verification**:
```bash
npm run test:coverage
# Should see 68 previously failing tests now pass
# ChapterEditor.saveStatus.test.tsx (19 tests)
# ChapterEditor.localStorage.test.tsx (30 tests)
# And others
```

**Impact**: +8-10% coverage gain
**Time**: 1-2 hours

---

## Task 10: BookCreationWizard Tests

**Status**: ZERO tests for 286-line core component
**Priority**: P1 (High) - Primary user entry point
**Estimated Effort**: 6-8 hours
**Coverage Gain**: +4-6%

### Component Overview
- **File**: `src/components/BookCreationWizard.tsx`
- **Lines**: 286
- **Complexity**: Medium-High
- **Dependencies**: react-hook-form, Zod validation, bookClient API
- **Form Fields**: 6 (title*, subtitle, description, cover_image_url, genre*, target_audience*)

### Required Tests (28 total)

#### 1. Rendering & Validation (8 tests)
```typescript
describe('Rendering & Validation', () => {
  it('renders all form fields correctly')
  it('shows validation errors for required fields (title, genre, target_audience)')
  it('validates title min/max length')
  it('validates URL format for cover_image_url')
  it('genre dropdown has 11 options')
  it('target_audience dropdown has 6 options')
  it('cancel button closes modal without submission')
  it('form resets on successful submission')
});
```

#### 2. Form Submission (6 tests)
```typescript
describe('Form Submission', () => {
  it('creates book with all fields filled')
  it('creates book with only required fields')
  it('navigates to book page on success')
  it('calls onSuccess callback if provided')
  it('shows success toast on creation')
  it('shows error toast on API failure')
});
```

#### 3. Loading States (4 tests)
```typescript
describe('Loading States', () => {
  it('disables all inputs during submission')
  it('shows loading spinner in submit button')
  it('prevents double submission')
  it('disables cancel button during submission')
});
```

#### 4. Edge Cases (7 tests)
```typescript
describe('Edge Cases', () => {
  it('handles empty optional fields gracefully')
  it('handles special characters in title')
  it('handles very long descriptions (>500 chars)')
  it('handles network timeout')
  it('handles network error recovery')
  it('handles invalid cover image URL')
  it('preserves form data on failed submission')
});
```

#### 5. Accessibility (3 tests)
```typescript
describe('Accessibility', () => {
  it('all form fields have proper labels')
  it('error messages announced to screen readers')
  it('keyboard navigation works for all controls')
});
```

### Test File Structure
```typescript
// src/components/__tests__/BookCreationWizard.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BookCreationWizard } from '../BookCreationWizard';
import bookClient from '@/lib/api/bookClient';
import { useRouter } from 'next/navigation';

jest.mock('@/lib/api/bookClient');
jest.mock('next/navigation');
jest.mock('sonner', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;
const mockRouter = {
  push: jest.fn(),
};

describe('BookCreationWizard', () => {
  const defaultProps = {
    isOpen: true,
    onOpenChange: jest.fn(),
    onSuccess: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
  });

  // Tests here...
});
```

### Mock Data Examples
```typescript
const validBookData = {
  title: 'My Test Book',
  subtitle: 'A subtitle',
  description: 'A description',
  genre: 'fiction',
  target_audience: 'adult',
  cover_image_url: 'https://example.com/cover.jpg',
};

const minimalBookData = {
  title: 'Minimal Book',
  genre: 'non-fiction',
  target_audience: 'general',
};
```

### Success Criteria
- ✅ 28 tests passing
- ✅ 80%+ coverage for BookCreationWizard.tsx
- ✅ No accessibility violations
- ✅ All edge cases handled

---

## Task 11: ChapterEditor + useChapterTabs Tests

**Status**: 68 tests blocked by dependency, useChapterTabs untested
**Priority**: P1 (High) - Core functionality
**Estimated Effort**: 10-14 hours (after dependency fix)
**Coverage Gain**: +8-12%

### Part A: Verify ChapterEditor Tests (Post-Fix)

**Files**:
- `ChapterEditor.saveStatus.test.tsx` (427 lines, 19 tests)
- `ChapterEditor.localStorage.test.tsx` (431 lines, 30 tests)

**Action**: Run tests after dependency fix
```bash
npm run test -- ChapterEditor.saveStatus.test.tsx
npm run test -- ChapterEditor.localStorage.test.tsx
```

**Expected**: All 68 tests should now pass
**If failures**: Investigate individual test failures (likely real bugs, not dependency issues)

---

### Part B: useChapterTabs Comprehensive Tests (NEW)

**File**: `src/hooks/useChapterTabs.ts`
**Lines**: 348
**Complexity**: Very High (TOC sync, localStorage, backend API, state management)
**Required Tests**: 27

#### 1. Initial Loading (6 tests)
```typescript
describe('Initial Loading', () => {
  it('loads chapters from TOC structure')
  it('falls back to chapter-tabs API if TOC fails')
  it('loads tab state from localStorage')
  it('loads tab state from backend')
  it('uses newer state when both exist (timestamp comparison)')
  it('handles load failures gracefully')
});
```

#### 2. State Management (8 tests)
```typescript
describe('State Management', () => {
  it('setActiveChapter opens tab if not already open')
  it('openTab delegates to setActiveChapter')
  it('closeTab removes from open tabs and updates active')
  it('closeTab switches to next tab when closing active')
  it('closeTab handles last tab closure')
  it('reorderTabs updates tab order correctly')
  it('updateChapterStatus optimistically updates UI')
  it('updateChapterStatus reverts on API error')
});
```

#### 3. Persistence (4 tests)
```typescript
describe('Persistence', () => {
  it('saveTabState saves to localStorage with timestamp')
  it('saveTabState saves to backend')
  it('auto-saves after 1-second debounce')
  it('handles save failures without user error')
});
```

#### 4. Refresh & Sync (5 tests)
```typescript
describe('Refresh & Sync', () => {
  it('refreshChapters reloads from TOC')
  it('refreshChapters falls back to API')
  it('refreshChapters removes deleted chapters from state')
  it('refreshChapters adds new chapters to tab order')
  it('refreshChapters preserves valid open tabs')
});
```

#### 5. Edge Cases (4 tests)
```typescript
describe('Edge Cases', () => {
  it('handles empty chapter list')
  it('handles missing active chapter')
  it('handles concurrent state updates')
  it('preserves state across re-renders')
});
```

### Test File Structure
```typescript
// src/hooks/__tests__/useChapterTabs.test.ts
import { renderHook, act, waitFor } from '@testing-library/react';
import { useChapterTabs } from '../useChapterTabs';
import bookClient from '@/lib/api/bookClient';
import { ChapterStatus } from '@/types/chapter-tabs';

jest.mock('@/lib/api/bookClient');

const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;

describe('useChapterTabs', () => {
  const mockBookId = 'book-123';

  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  // Tests here...
});
```

### Mock Data Examples
```typescript
const mockChapterTabs = [
  {
    id: 'ch1',
    title: 'Chapter 1',
    order_index: 0,
    parent_id: null,
    level: 1,
    status: ChapterStatus.DRAFT,
    has_content: false,
    word_count: 0,
    estimated_reading_time: 0,
    last_modified: '2025-10-13T00:00:00Z',
  },
  {
    id: 'ch2',
    title: 'Chapter 2',
    order_index: 1,
    parent_id: null,
    level: 1,
    status: ChapterStatus.IN_PROGRESS,
    has_content: true,
    word_count: 500,
    estimated_reading_time: 2,
    last_modified: '2025-10-13T01:00:00Z',
  },
];

const mockTocResponse = {
  toc: {
    chapters: mockChapterTabs,
  },
};

const mockTabState = {
  active_chapter_id: 'ch1',
  open_tab_ids: ['ch1', 'ch2'],
  tab_order: ['ch1', 'ch2'],
  last_updated: '2025-10-13T00:00:00Z',
};
```

### Success Criteria
- ✅ 68 ChapterEditor tests passing (unblocked)
- ✅ 27 useChapterTabs tests passing
- ✅ Hook coverage from 50% to 75%+
- ✅ Frontend overall coverage 77-83%

---

## Combined Impact

### Before Tasks 10-11
- **Tests**: 325 passing, 68 failing (393 total)
- **Pass Rate**: 82.7%
- **Coverage**: 65.28%

### After Tasks 10-11
- **Tests**: 420+ passing, 0 failing
- **Pass Rate**: 95%+
- **Coverage**: 77-83% ✅ **EXCEEDS 80% TARGET**

### Breakdown
- Dependency fix: 68 tests unblocked → +8-10%
- BookCreationWizard: 28 tests added → +4-6%
- useChapterTabs: 27 tests added → +3-4%
- **Total: +15-20% coverage**

---

## Testing Patterns to Follow

### 1. Use Testing Library Best Practices
```typescript
// ✅ Good - Query by accessible role/label
const button = screen.getByRole('button', { name: /submit/i });

// ❌ Bad - Query by implementation details
const button = container.querySelector('.submit-button');
```

### 2. Mock External Dependencies
```typescript
// Mock API clients
jest.mock('@/lib/api/bookClient');

// Mock routing
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

// Mock toast notifications
jest.mock('sonner', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));
```

### 3. Clean Up Between Tests
```typescript
beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
});

afterEach(() => {
  jest.runOnlyPendingTimers();
  jest.useRealTimers();
});
```

### 4. Use Descriptive Test Names
```typescript
// ✅ Good - Describes behavior
it('shows validation error when title is empty')

// ❌ Bad - Implementation-focused
it('calls setError on form submit')
```

### 5. Test User Behavior, Not Implementation
```typescript
// ✅ Good - User perspective
await user.type(titleInput, 'My Book');
await user.click(submitButton);
expect(mockBookClient.createBook).toHaveBeenCalledWith({
  title: 'My Book',
  ...
});

// ❌ Bad - Implementation details
expect(form.getValues().title).toBe('My Book');
```

---

## Time Estimates

| Task | Subtask | Hours | Total |
|------|---------|-------|-------|
| **Pre-Task** | Fix dependencies | 1-2 | 1-2 |
| **Task 10** | BookCreationWizard tests | 6-8 | 6-8 |
| **Task 11a** | Verify ChapterEditor | 0.5-1 | 0.5-1 |
| **Task 11b** | useChapterTabs tests | 10-12 | 10-12 |
| | **TOTAL** | | **18-23 hours** |

### Sprint Planning
- **Week 1**: Fix dependencies + BookCreationWizard (1-2 days)
- **Week 2**: useChapterTabs tests (2-3 days)
- **Buffer**: Edge case fixes, documentation (1 day)

---

## Definition of Done

### Task 10 Complete When:
- [ ] All 28 BookCreationWizard tests passing
- [ ] Coverage >80% for BookCreationWizard.tsx
- [ ] No accessibility violations
- [ ] All edge cases tested
- [ ] Test file documented with clear describe blocks

### Task 11 Complete When:
- [ ] Dependency fix deployed
- [ ] All 68 ChapterEditor tests passing
- [ ] All 27 useChapterTabs tests passing
- [ ] Frontend coverage 77-83%
- [ ] No test warnings or errors
- [ ] Git committed with conventional commit messages

### Overall Success:
- [ ] Frontend coverage ≥80%
- [ ] Test pass rate ≥95%
- [ ] All P0 and P1 gaps addressed
- [ ] Documentation updated (CLAUDE.md, baseline report)
- [ ] CI/CD pipeline green
