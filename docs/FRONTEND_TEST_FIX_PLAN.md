# Frontend Test Fix Plan - Path to 100% Pass Rate with 85%+ Coverage

**Date**: 2025-12-23
**Current Status**: 98.8% pass rate (802/812 tests passing)
**Target**: 100% pass rate with 85%+ code coverage

---

## Executive Summary

The frontend test suite is in excellent shape with only **2 failing tests** and **8 skipped tests**. This represents significant improvement from the previous state (75 failing tests). All failures are fixable with straightforward solutions.

### Current State
- **Test Suites**: 55 passing, 2 failing (57 total)
- **Tests**: 802 passing, 2 failing, 8 skipped (812 total)
- **Pass Rate**: 98.8%

---

## Failing Tests Analysis

### 1. ChapterQuestionsMobileAccessibility.test.tsx (1 failure)

**Test**: "provides appropriate touch targets for mobile"
**File**: `src/__tests__/ChapterQuestionsMobileAccessibility.test.tsx:314-329`

**Root Cause**: The test validates that all interactive buttons have minimum touch target size classes (`min-h-[44px]` or `min-w-[44px]`) for WCAG 2.1 mobile accessibility compliance.

**Bug Location**: `src/components/chapters/questions/QuestionDisplay.tsx:548-555`
```typescript
// Current (line 552):
<Button
  variant="outline"
  size="sm"
  onClick={lastAction === 'complete' ? handleMarkCompleted : handleSaveDraft}
  className="ml-2 h-8"  // Missing min-h-[44px] min-w-[44px]
>
  Retry
</Button>
```

**Category**: BUG IN MAIN CODE

**Fix Required**: Add accessibility touch target classes to the Retry button
```typescript
className="ml-2 h-8 min-h-[44px] min-w-[44px]"
```

**Effort**: 5 minutes
**Priority**: P1 - Accessibility compliance

---

### 2. ChapterQuestionsEndToEnd.test.tsx (1 failure)

**Test**: "triggers draft generation after question completion"
**File**: `src/__tests__/ChapterQuestionsEndToEnd.test.tsx:622-685`

**Root Cause**: Test mocks `draftClient.generateChapterDraft` but the component (`DraftGenerationButton.tsx:149`) uses `bookClient.generateChapterDraft` directly.

**Bug Location**: `src/__tests__/ChapterQuestionsEndToEnd.test.tsx:47-55`
```typescript
// Current (wrong mock):
jest.mock('../lib/api/draftClient', () => ({
  draftClient: {
    generateChapterDraft: jest.fn(),
    getDraftContent: jest.fn(),
    saveDraftContent: jest.fn(),
  }
}));
```

**Category**: BUG IN TEST CODE

**Fix Required**: Mock `bookClient.generateChapterDraft` instead of `draftClient`
```typescript
// In the existing bookClient mock (lines 22-44), add:
generateChapterDraft: jest.fn(),
getChapterQAResponses: jest.fn(),
```

And update the test assertion at line 668 to use `mockBookClient.generateChapterDraft` instead of `mockDraftClient.generateChapterDraft`.

**Effort**: 15 minutes
**Priority**: P1 - Test correctness

---

## Skipped Tests Analysis

### Category A: Error Handling Tests (3 tests)
**File**: `src/components/chapters/questions/__tests__/QuestionDisplay.enhanced.test.tsx`

| Test | Reason Skipped | Action |
|------|----------------|--------|
| should show network error message with actionable suggestion | Error handling UI not fully implemented | Unskip after error UI complete |
| should show server error message | Error handling UI not fully implemented | Unskip after error UI complete |
| should handle completion errors with retry | Error handling UI not fully implemented | Unskip after error UI complete |

**Category**: FUNCTIONALITY NOT YET BUILT
**Related to**: Error handling improvements planned in future sprints
**Effort to Fix**: 2-4 hours (implement error UI patterns)

### Category B: Auth State Handling (1 test)
**File**: `src/__tests__/ProtectedRoute.test.tsx`

| Test | Reason Skipped | Action |
|------|----------------|--------|
| handles auth state changes correctly | Better-auth migration edge cases | Update mock for better-auth patterns |

**Category**: BUG IN TEST CODE
**Related to**: Better-auth migration (completed 2025-12-17)
**Effort to Fix**: 30 minutes (update auth mocks)

### Category C: Accessibility Audits (3 tests)
**File**: `src/__tests__/accessibility/ComponentAccessibilityAudit.test.tsx`

| Test | Reason Skipped | Action |
|------|----------------|--------|
| should pass accessibility scan for primary navigation | Navigation component not fully accessible | Fix accessibility violations |
| should pass accessibility scan for TipTap Editor | TipTap needs aria-label improvements | Add ARIA attributes |
| should pass accessibility scan for generic modal pattern | Modal focus management incomplete | Implement focus trap |

**Category**: BUG IN MAIN CODE
**Related to**: WCAG 2.1 compliance efforts
**Effort to Fix**: 2-3 hours (accessibility improvements)

### Category D: Performance Testing (1 test)
**File**: `src/__tests__/ChapterQuestionsPerformance.test.tsx`

| Test | Reason Skipped | Action |
|------|----------------|--------|
| real-time auto-save performance | Flaky timing in test environment | Refactor with deterministic timing |

**Category**: BUG IN TEST CODE
**Related to**: Auto-save performance optimization
**Effort to Fix**: 1 hour (use fake timers)

---

## Implementation Plan

### Phase 1: Fix Failing Tests (Immediate - 20 mins)
**Goal**: 100% pass rate

| Task | Category | Time | Priority |
|------|----------|------|----------|
| Add touch target classes to Retry button | Main Code Bug | 5 min | P1 |
| Fix draft generation mock in E2E test | Test Code Bug | 15 min | P1 |

### Phase 2: Enable Auth Test (Quick Win - 30 mins)
**Goal**: 807/812 tests passing

| Task | Category | Time |
|------|----------|------|
| Update ProtectedRoute test for better-auth | Test Code Bug | 30 min |

### Phase 3: Fix Accessibility Scans (Medium Effort - 3 hours)
**Goal**: 810/812 tests passing

| Task | Category | Time |
|------|----------|------|
| Fix navigation accessibility violations | Main Code Bug | 1 hour |
| Add ARIA labels to TipTap Editor | Main Code Bug | 1 hour |
| Implement modal focus trap | Main Code Bug | 1 hour |

### Phase 4: Enable Error Handling Tests (Medium Effort - 4 hours)
**Goal**: 811/812 tests passing

| Task | Category | Time |
|------|----------|------|
| Implement error UI for network errors | Missing Functionality | 1.5 hours |
| Implement error UI for server errors | Missing Functionality | 1.5 hours |
| Implement retry flow for completions | Missing Functionality | 1 hour |

### Phase 5: Fix Performance Test (Quick - 1 hour)
**Goal**: 812/812 tests passing (100%)

| Task | Category | Time |
|------|----------|------|
| Refactor auto-save test with fake timers | Test Code Bug | 1 hour |

---

## Cross-Reference with Existing Issues

### Confirmed Overlaps
Based on CLAUDE.md documentation:
- Better-auth migration is **COMPLETE** (2025-12-17) - ProtectedRoute test skip may be outdated
- Accessibility testing infrastructure exists - tests may just need component updates
- Error handling with retry is documented as implemented - skipped tests may need updating

### Potential New Issues Required
The following should be tracked if not already in GitHub issues:
1. **Accessibility Compliance**: Add min touch target sizes to all interactive buttons
2. **Test Maintenance**: Update E2E test mocks post-architecture changes

---

## Coverage Analysis

### Current Coverage Concerns
While specific coverage percentages aren't available, the CLAUDE.md target is **85% minimum**.

### Key Files to Review for Coverage
1. `src/lib/api/bookClient.ts` - Core API client (critical)
2. `src/components/chapters/questions/QuestionContainer.tsx` - Question workflow
3. `src/components/chapters/questions/QuestionDisplay.tsx` - Response handling
4. `src/lib/errors/errorHandler.ts` - Error handling (has passing tests)

### Coverage Improvement Strategy
1. Run `npm test -- --coverage` to get current baseline
2. Focus on files with <70% coverage
3. Add tests for uncovered edge cases
4. Prioritize critical paths (auth, data persistence, API calls)

---

## Quick Reference: Fix Commands

### Fix Failing Tests
```bash
# 1. Fix QuestionDisplay.tsx Retry button
# Add min-h-[44px] min-w-[44px] to className at line 552

# 2. Fix ChapterQuestionsEndToEnd.test.tsx
# Update mock from draftClient to bookClient
# Update assertion from mockDraftClient to mockBookClient

# 3. Run tests to verify
cd frontend && npm test
```

### Run With Coverage
```bash
cd frontend && npm test -- --coverage --coverageThreshold='{"global":{"lines":85}}'
```

---

## Summary Table

| Category | Count | Effort | Priority |
|----------|-------|--------|----------|
| Bug in Main Code | 4 tests | 3.5 hours | P1-P2 |
| Bug in Test Code | 3 tests | 2 hours | P1-P2 |
| Missing Functionality | 3 tests | 4 hours | P3 |
| **Total** | **10 tests** | **9.5 hours** | - |

---

## Conclusion

The frontend test suite is in excellent condition at 98.8% pass rate. With approximately **9.5 hours of focused work**, all tests can be passing (100% pass rate). The two immediate failing tests can be fixed in under 30 minutes.

**Recommended Action**:
1. Fix the 2 failing tests immediately (Phase 1)
2. Address accessibility violations for WCAG compliance (Phase 3)
3. Enable skipped tests incrementally as related features stabilize

**Next Steps**:
1. Review this plan
2. Create GitHub issues for tracking if not already tracked
3. Implement Phase 1 fixes
4. Verify 100% pass rate
5. Address coverage gaps to reach 85% threshold
