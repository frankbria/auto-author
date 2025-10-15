# Agile Testing Strategy Implementation Plan

> **For Claude:** Use `${SUPERPOWERS_SKILLS_ROOT}/skills/collaboration/executing-plans/SKILL.md` to implement this plan task-by-task.

**Goal:** Implement comprehensive testing coverage using agile iteration: assess/optimize existing E2E tests, TDD Phase 1 features, build critical user journey E2E tests, and expand component test coverage.

**Architecture:** Three-iteration approach with decision gates. Iteration 1 establishes baseline and fixes issues. Iteration 2 focuses on end-to-end user flows. Iteration 3 covers component-level testing. Each iteration measures progress and adapts priorities.

**Tech Stack:** Jest (unit/integration), Playwright (E2E), React Testing Library, pytest (backend), coverage.js, condition-based waiting patterns

---

## Iteration 1: Foundation + Assessment (Sprint 1-2)

### Task 1: Assess Existing E2E Test Coverage

**Goal:** Understand what E2E tests exist, what they cover, and identify gaps.

**Files:**
- Read: `frontend/src/__tests__/e2e/SystemE2E.test.tsx`
- Read: `frontend/src/__tests__/SystemIntegration.test.tsx`
- Read: `frontend/playwright.config.ts`
- Create: `docs/testing/e2e-assessment-report.md`

**Step 1: Run existing E2E tests and capture performance metrics**

```bash
cd frontend
npm run test:e2e -- --reporter=html
```

Expected: Test report generated in `test-results/index.html`

**Step 2: Document test execution times**

Open `test-results/index.html` in browser, note:
- Total execution time
- Individual test durations
- Any failed tests
- Any flaky tests (intermittent failures)

**Step 3: Analyze test coverage**

Read both E2E test files and create a coverage matrix:

```markdown
## E2E Coverage Matrix

| User Flow | Covered? | Test File | Issues |
|-----------|----------|-----------|--------|
| Sign up → Create book → Draft | ✅ / ❌ | SystemE2E.test.tsx | None / Slow / Flaky |
| Edit existing book | ✅ / ❌ | - | Not covered |
| Delete book | ✅ / ❌ | - | Not covered |
| Export PDF/DOCX | ✅ / ❌ | - | Not covered |
| Error recovery | ✅ / ❌ | - | Not covered |
```

**Step 4: Create assessment report**

Create `docs/testing/e2e-assessment-report.md`:

```markdown
# E2E Test Assessment Report

**Date:** 2025-10-13

## Current State
- Total E2E tests: [number]
- Total execution time: [X] minutes
- Pass rate: [X]%
- Flaky tests: [list]

## Coverage Gaps
[List uncovered user flows]

## Performance Issues
[List slow tests with reasons]

## Recommendations
1. [Fix/optimize/rewrite/delete specific tests]
2. [Add missing coverage for X flow]
3. [Performance improvements]
```

**Step 5: Commit assessment report**

```bash
git add docs/testing/e2e-assessment-report.md
git commit -m "docs(testing): add E2E test assessment report"
```

---

### Task 2: Optimize Slow E2E Tests

**Goal:** Reduce E2E test execution time to <5 minutes for critical paths.

**Files:**
- Modify: `frontend/src/__tests__/e2e/SystemE2E.test.tsx`
- Create: `frontend/src/__tests__/helpers/conditionWaiting.ts`

**Step 1: Write condition-based waiting helper (TDD)**

Create failing test:

```typescript
// frontend/src/__tests__/helpers/conditionWaiting.test.ts
import { waitForCondition } from './conditionWaiting';

describe('waitForCondition', () => {
  it('should resolve when condition becomes true', async () => {
    let value = false;
    setTimeout(() => { value = true; }, 100);

    await waitForCondition(() => value, { timeout: 1000, interval: 50 });
    expect(value).toBe(true);
  });

  it('should timeout if condition never true', async () => {
    await expect(
      waitForCondition(() => false, { timeout: 100, interval: 20 })
    ).rejects.toThrow('Condition timeout');
  });
});
```

**Step 2: Run test to verify it fails**

```bash
npm test -- conditionWaiting.test
```

Expected: FAIL - "Cannot find module './conditionWaiting'"

**Step 3: Implement condition-based waiting utility**

Create `frontend/src/__tests__/helpers/conditionWaiting.ts`:

```typescript
export interface WaitOptions {
  timeout?: number;
  interval?: number;
  timeoutMessage?: string;
}

export async function waitForCondition(
  condition: () => boolean | Promise<boolean>,
  options: WaitOptions = {}
): Promise<void> {
  const {
    timeout = 5000,
    interval = 100,
    timeoutMessage = 'Condition timeout'
  } = options;

  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    const result = await condition();
    if (result) return;
    await new Promise(resolve => setTimeout(resolve, interval));
  }

  throw new Error(timeoutMessage);
}
```

**Step 4: Run test to verify it passes**

```bash
npm test -- conditionWaiting.test
```

Expected: PASS - 2 tests passed

**Step 5: Replace arbitrary waits in E2E tests**

Modify `frontend/src/__tests__/e2e/SystemE2E.test.tsx`:

Find patterns like:
```typescript
// BAD: Arbitrary wait
await page.waitForTimeout(3000);
```

Replace with:
```typescript
// GOOD: Condition-based wait
await waitForCondition(
  async () => {
    const button = await page.$('[data-testid="submit-button"]');
    return button !== null && await button.isEnabled();
  },
  { timeout: 5000 }
);
```

**Step 6: Use API setup for test data**

Add test data setup helper:

```typescript
// frontend/src/__tests__/helpers/testDataSetup.ts
import { bookClient } from '@/lib/api/bookClient';

export async function createTestBook(token: string) {
  return await bookClient.createBook({
    title: 'Test Book',
    genre: 'non-fiction',
    summary: 'Test summary'
  }, token);
}
```

Replace UI-based book creation in tests with API calls.

**Step 7: Run optimized E2E suite and measure improvement**

```bash
npm run test:e2e -- --reporter=html
```

Compare execution time with baseline from Task 1.
Target: 30-50% reduction in execution time.

**Step 8: Commit optimizations**

```bash
git add frontend/src/__tests__/helpers/ frontend/src/__tests__/e2e/
git commit -m "test(e2e): optimize test execution with condition-based waiting"
```

---

### Task 3: TDD Export Options Modal Component

**Goal:** Create ExportOptionsModal component with comprehensive tests.

**Files:**
- Create: `frontend/src/components/export/ExportOptionsModal.test.tsx`
- Create: `frontend/src/components/export/ExportOptionsModal.tsx`
- Create: `frontend/src/components/export/types.ts`

**Step 1: Write failing test for format selection**

```typescript
// frontend/src/components/export/ExportOptionsModal.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { ExportOptionsModal } from './ExportOptionsModal';

describe('ExportOptionsModal', () => {
  const mockOnExport = jest.fn();
  const mockOnCancel = jest.fn();

  it('should render format selection options', () => {
    render(
      <ExportOptionsModal
        isOpen={true}
        onExport={mockOnExport}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByLabelText('PDF')).toBeInTheDocument();
    expect(screen.getByLabelText('DOCX')).toBeInTheDocument();
  });

  it('should call onExport with selected format', () => {
    render(
      <ExportOptionsModal
        isOpen={true}
        onExport={mockOnExport}
        onCancel={mockOnCancel}
      />
    );

    fireEvent.click(screen.getByLabelText('PDF'));
    fireEvent.click(screen.getByRole('button', { name: /export/i }));

    expect(mockOnExport).toHaveBeenCalledWith({
      format: 'pdf',
      includeEmptyChapters: true,
      pageSize: 'letter'
    });
  });
});
```

**Step 2: Run test to verify it fails**

```bash
npm test -- ExportOptionsModal.test
```

Expected: FAIL - "Cannot find module './ExportOptionsModal'"

**Step 3: Create type definitions**

```typescript
// frontend/src/components/export/types.ts
export type ExportFormat = 'pdf' | 'docx';
export type PageSize = 'letter' | 'a4';

export interface ExportOptions {
  format: ExportFormat;
  includeEmptyChapters: boolean;
  pageSize?: PageSize; // Only for PDF
}
```

**Step 4: Implement minimal ExportOptionsModal component**

```typescript
// frontend/src/components/export/ExportOptionsModal.tsx
import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { ExportOptions, ExportFormat, PageSize } from './types';

interface ExportOptionsModalProps {
  isOpen: boolean;
  onExport: (options: ExportOptions) => void;
  onCancel: () => void;
}

export function ExportOptionsModal({ isOpen, onExport, onCancel }: ExportOptionsModalProps) {
  const [format, setFormat] = useState<ExportFormat>('pdf');
  const [pageSize, setPageSize] = useState<PageSize>('letter');
  const [includeEmptyChapters, setIncludeEmptyChapters] = useState(true);

  const handleExport = () => {
    onExport({
      format,
      includeEmptyChapters,
      ...(format === 'pdf' && { pageSize })
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={onCancel}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Export Options</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <RadioGroup value={format} onValueChange={(v) => setFormat(v as ExportFormat)}>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="pdf" id="pdf" />
              <Label htmlFor="pdf">PDF</Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="docx" id="docx" />
              <Label htmlFor="docx">DOCX</Label>
            </div>
          </RadioGroup>

          {format === 'pdf' && (
            <RadioGroup value={pageSize} onValueChange={(v) => setPageSize(v as PageSize)}>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="letter" id="letter" />
                <Label htmlFor="letter">Letter (8.5" x 11")</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="a4" id="a4" />
                <Label htmlFor="a4">A4</Label>
              </div>
            </RadioGroup>
          )}

          <div className="flex justify-end space-x-2">
            <Button variant="outline" onClick={onCancel}>Cancel</Button>
            <Button onClick={handleExport}>Export</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

**Step 5: Run test to verify it passes**

```bash
npm test -- ExportOptionsModal.test
```

Expected: PASS - 2 tests passed

**Step 6: Add tests for page size selection**

Add to test file:

```typescript
it('should show page size options only for PDF', () => {
  const { rerender } = render(
    <ExportOptionsModal isOpen={true} onExport={mockOnExport} onCancel={mockOnCancel} />
  );

  fireEvent.click(screen.getByLabelText('PDF'));
  expect(screen.getByLabelText('Letter (8.5" x 11")')).toBeInTheDocument();

  fireEvent.click(screen.getByLabelText('DOCX'));
  expect(screen.queryByLabelText('Letter (8.5" x 11")')).not.toBeInTheDocument();
});
```

**Step 7: Run all tests**

```bash
npm test -- ExportOptionsModal.test
```

Expected: PASS - 3 tests passed

**Step 8: Commit**

```bash
git add frontend/src/components/export/
git commit -m "feat(export): add ExportOptionsModal component with TDD"
```

---

### Task 4: TDD Error Handler Utility

**Goal:** Create unified error handler with retry logic and classification.

**Files:**
- Create: `frontend/src/lib/api/errorHandler.test.ts`
- Create: `frontend/src/lib/api/errorHandler.ts`
- Create: `frontend/src/lib/api/errorTypes.ts`

**Step 1: Define error types**

```typescript
// frontend/src/lib/api/errorTypes.ts
export enum ErrorType {
  NETWORK = 'network',
  TIMEOUT = 'timeout',
  VALIDATION = 'validation',
  AUTHENTICATION = 'authentication',
  AUTHORIZATION = 'authorization',
  NOT_FOUND = 'not_found',
  SERVER_ERROR = 'server_error',
  UNKNOWN = 'unknown'
}

export interface ApiError {
  type: ErrorType;
  message: string;
  statusCode?: number;
  retryable: boolean;
  correlationId: string;
  details?: Record<string, any>;
}

export interface RetryConfig {
  maxAttempts: number;
  backoffMs: number;
  backoffMultiplier: number;
}
```

**Step 2: Write failing tests for error classification**

```typescript
// frontend/src/lib/api/errorHandler.test.ts
import { classifyError, ErrorType } from './errorTypes';

describe('classifyError', () => {
  it('should classify network errors', () => {
    const error = new Error('Network request failed');
    const classified = classifyError(error);

    expect(classified.type).toBe(ErrorType.NETWORK);
    expect(classified.retryable).toBe(true);
  });

  it('should classify 401 as authentication error', () => {
    const error = { response: { status: 401 } };
    const classified = classifyError(error);

    expect(classified.type).toBe(ErrorType.AUTHENTICATION);
    expect(classified.retryable).toBe(false);
  });

  it('should classify 500 as server error', () => {
    const error = { response: { status: 500 } };
    const classified = classifyError(error);

    expect(classified.type).toBe(ErrorType.SERVER_ERROR);
    expect(classified.retryable).toBe(true);
  });
});
```

**Step 3: Run test to verify it fails**

```bash
npm test -- errorHandler.test
```

Expected: FAIL - "classifyError is not a function"

**Step 4: Implement error classification**

```typescript
// frontend/src/lib/api/errorHandler.ts
import { v4 as uuidv4 } from 'uuid';
import { ApiError, ErrorType, RetryConfig } from './errorTypes';

export function classifyError(error: any): ApiError {
  const correlationId = uuidv4();

  // Network errors
  if (error.message?.includes('Network') || error.message?.includes('fetch')) {
    return {
      type: ErrorType.NETWORK,
      message: 'Network connection failed. Please check your internet connection.',
      retryable: true,
      correlationId
    };
  }

  // HTTP status code errors
  if (error.response?.status) {
    const status = error.response.status;

    if (status === 401) {
      return {
        type: ErrorType.AUTHENTICATION,
        message: 'Authentication failed. Please log in again.',
        statusCode: status,
        retryable: false,
        correlationId
      };
    }

    if (status === 403) {
      return {
        type: ErrorType.AUTHORIZATION,
        message: 'You do not have permission to perform this action.',
        statusCode: status,
        retryable: false,
        correlationId
      };
    }

    if (status === 404) {
      return {
        type: ErrorType.NOT_FOUND,
        message: 'The requested resource was not found.',
        statusCode: status,
        retryable: false,
        correlationId
      };
    }

    if (status === 422) {
      return {
        type: ErrorType.VALIDATION,
        message: error.response.data?.message || 'Validation failed.',
        statusCode: status,
        retryable: false,
        correlationId,
        details: error.response.data?.errors
      };
    }

    if (status >= 500) {
      return {
        type: ErrorType.SERVER_ERROR,
        message: 'Server error occurred. Please try again.',
        statusCode: status,
        retryable: true,
        correlationId
      };
    }
  }

  // Unknown errors
  return {
    type: ErrorType.UNKNOWN,
    message: error.message || 'An unexpected error occurred.',
    retryable: false,
    correlationId
  };
}
```

**Step 5: Run test to verify it passes**

```bash
npm test -- errorHandler.test
```

Expected: PASS - 3 tests passed

**Step 6: Write failing tests for retry logic**

```typescript
describe('handleApiCall', () => {
  it('should retry transient errors up to 3 times', async () => {
    let attempts = 0;
    const apiCall = jest.fn(async () => {
      attempts++;
      if (attempts < 3) throw new Error('Network request failed');
      return { success: true };
    });

    const result = await handleApiCall(apiCall);

    expect(attempts).toBe(3);
    expect(result).toEqual({ success: true });
  });

  it('should not retry non-retryable errors', async () => {
    const apiCall = jest.fn(async () => {
      throw { response: { status: 401 } };
    });

    await expect(handleApiCall(apiCall)).rejects.toThrow();
    expect(apiCall).toHaveBeenCalledTimes(1);
  });

  it('should use exponential backoff', async () => {
    const delays: number[] = [];
    let attempts = 0;

    jest.spyOn(global, 'setTimeout').mockImplementation((cb: any, delay: number) => {
      delays.push(delay);
      cb();
      return 0 as any;
    });

    const apiCall = jest.fn(async () => {
      attempts++;
      if (attempts < 4) throw new Error('Network request failed');
      return { success: true };
    });

    await handleApiCall(apiCall);

    expect(delays).toEqual([1000, 2000, 4000]); // Exponential backoff
  });
});
```

**Step 7: Implement retry logic with exponential backoff**

```typescript
const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxAttempts: 3,
  backoffMs: 1000,
  backoffMultiplier: 2
};

async function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export async function handleApiCall<T>(
  apiCall: () => Promise<T>,
  config: Partial<RetryConfig> = {}
): Promise<T> {
  const retryConfig = { ...DEFAULT_RETRY_CONFIG, ...config };
  let lastError: ApiError | null = null;

  for (let attempt = 0; attempt < retryConfig.maxAttempts; attempt++) {
    try {
      return await apiCall();
    } catch (error) {
      lastError = classifyError(error);

      // Don't retry non-retryable errors
      if (!lastError.retryable) {
        throw lastError;
      }

      // Don't retry on last attempt
      if (attempt === retryConfig.maxAttempts - 1) {
        throw lastError;
      }

      // Exponential backoff
      const backoffDelay = retryConfig.backoffMs * Math.pow(retryConfig.backoffMultiplier, attempt);
      await delay(backoffDelay);
    }
  }

  throw lastError;
}
```

**Step 8: Run all tests**

```bash
npm test -- errorHandler.test
```

Expected: PASS - 6 tests passed

**Step 9: Commit**

```bash
git add frontend/src/lib/api/errorHandler.ts frontend/src/lib/api/errorTypes.ts
git commit -m "feat(api): add error classification and retry logic with TDD"
```

---

### Task 5: Establish Baseline Coverage Metrics

**Goal:** Generate coverage reports for backend and frontend to establish baseline.

**Files:**
- Create: `docs/testing/coverage-baseline.md`

**Step 1: Generate backend coverage report**

```bash
cd backend
uv run pytest --cov=app --cov-report=html --cov-report=json --cov-report=term
```

Expected: Coverage report generated in `htmlcov/` and `coverage.json`

**Step 2: Capture backend coverage metrics**

```bash
# Extract coverage percentage
cat coverage.json | jq '.totals.percent_covered'
```

Note the percentage (e.g., 80.5%)

**Step 3: Generate frontend coverage report**

```bash
cd frontend
npm run test:coverage
```

Expected: Coverage report in `coverage/` directory

**Step 4: Create baseline document**

Create `docs/testing/coverage-baseline.md`:

```markdown
# Test Coverage Baseline

**Date:** 2025-10-13

## Backend Coverage
- **Overall:** 80.5%
- **Lines:** 1234/1543
- **Branches:** 456/567
- **Functions:** 234/289

### By Module
| Module | Coverage |
|--------|----------|
| app/services/ai_service.py | 90% |
| app/services/transcription_service.py | 85% |
| app/api/endpoints/books.py | 75% |

## Frontend Coverage
- **Overall:** XX%
- **Statements:** XXX/XXX
- **Branches:** XXX/XXX
- **Functions:** XXX/XXX
- **Lines:** XXX/XXX

### By Component Type
| Type | Coverage |
|------|----------|
| Components | XX% |
| Pages | XX% |
| Utilities | XX% |
| API Client | XX% |

## Test Execution Metrics

### Backend
- Total tests: 59
- Execution time: X.X seconds
- Pass rate: 80% (47 passing)

### Frontend
- Total tests: XX
- Execution time: XX seconds
- Pass rate: XX%

### E2E Tests
- Total tests: X
- Execution time: X minutes
- Pass rate: XX%

## Goals for Next Iteration
- Backend: Maintain 80%+
- Frontend: Achieve 80%+
- E2E: Add 3 critical path tests
- Reduce E2E execution time to <5 minutes
```

**Step 5: Commit baseline document**

```bash
git add docs/testing/coverage-baseline.md
git commit -m "docs(testing): establish coverage baseline metrics"
```

---

## Iteration 2: Critical User Journeys E2E (Sprint 3-4)

### Task 6: E2E Test - Complete Authoring Journey

**Goal:** Create comprehensive E2E test for full book authoring workflow.

**Files:**
- Create: `frontend/src/e2e/complete-authoring-journey.spec.ts`
- Create: `frontend/src/e2e/fixtures/mockAiResponses.ts`

**Step 1: Create mock AI responses fixture**

```typescript
// frontend/src/e2e/fixtures/mockAiResponses.ts
export const mockBookQuestions = [
  {
    id: 'q1',
    question: 'What is the main theme of your book?',
    category: 'concept'
  },
  {
    id: 'q2',
    question: 'Who is your target audience?',
    category: 'audience'
  }
];

export const mockTOC = [
  { id: '1', title: 'Introduction', order: 1 },
  { id: '2', title: 'Chapter 1: Getting Started', order: 2 },
  { id: '3', title: 'Chapter 2: Advanced Topics', order: 3 }
];

export const mockChapterQuestions = [
  {
    id: 'cq1',
    question: 'What are the key points for this chapter?',
    category: 'content'
  }
];

export const mockDraft = {
  content: '<h1>Chapter 1: Getting Started</h1><p>This is the beginning of your journey...</p>',
  word_count: 500,
  reading_time: 2
};
```

**Step 2: Write E2E test structure**

```typescript
// frontend/src/e2e/complete-authoring-journey.spec.ts
import { test, expect } from '@playwright/test';
import { mockBookQuestions, mockTOC, mockChapterQuestions, mockDraft } from './fixtures/mockAiResponses';

test.describe('Complete Authoring Journey', () => {
  test.beforeEach(async ({ page }) => {
    // Mock AI API endpoints
    await page.route('**/api/ai/generate-questions', async (route) => {
      await route.fulfill({
        status: 200,
        body: JSON.stringify(mockBookQuestions)
      });
    });

    await page.route('**/api/ai/generate-toc', async (route) => {
      await route.fulfill({
        status: 200,
        body: JSON.stringify(mockTOC)
      });
    });

    await page.route('**/api/ai/generate-chapter-questions', async (route) => {
      await route.fulfill({
        status: 200,
        body: JSON.stringify(mockChapterQuestions)
      });
    });

    await page.route('**/api/ai/generate-draft', async (route) => {
      await route.fulfill({
        status: 200,
        body: JSON.stringify(mockDraft)
      });
    });
  });

  test('user can create book and generate complete draft', async ({ page }) => {
    // 1. Navigate to dashboard
    await page.goto('/dashboard');

    // 2. Click create book
    await page.click('[data-testid="create-book-button"]');

    // 3. Fill book details
    await page.fill('[name="title"]', 'My Test Book');
    await page.selectOption('[name="genre"]', 'non-fiction');
    await page.fill('[name="summary"]', 'This is a test book summary');
    await page.click('[data-testid="next-button"]');

    // 4. Wait for questions to be generated
    await page.waitForSelector('[data-testid="question-0"]');
    expect(await page.textContent('[data-testid="question-0"]')).toContain('main theme');

    // 5. Answer questions
    await page.fill('[data-testid="answer-0"]', 'The main theme is productivity');
    await page.fill('[data-testid="answer-1"]', 'Business professionals');
    await page.click('[data-testid="submit-answers"]');

    // 6. Wait for TOC generation
    await page.waitForSelector('[data-testid="toc-chapter-1"]');
    expect(await page.textContent('[data-testid="toc-chapter-1"]')).toContain('Introduction');

    // 7. Confirm TOC
    await page.click('[data-testid="confirm-toc"]');

    // 8. Navigate to first chapter
    await page.click('[data-testid="chapter-tab-0"]');

    // 9. Generate chapter questions
    await page.click('[data-testid="generate-chapter-questions"]');
    await page.waitForSelector('[data-testid="chapter-question-0"]');

    // 10. Answer chapter questions
    await page.fill('[data-testid="chapter-answer-0"]', 'Key points include...');
    await page.click('[data-testid="submit-chapter-answers"]');

    // 11. Generate draft
    await page.click('[data-testid="generate-draft"]');

    // 12. Wait for draft to appear
    await page.waitForSelector('.chapter-content');
    const content = await page.textContent('.chapter-content');
    expect(content).toContain('Chapter 1: Getting Started');
    expect(content).toContain('beginning of your journey');

    // 13. Verify word count displayed
    const wordCount = await page.textContent('[data-testid="word-count"]');
    expect(wordCount).toContain('500');
  });
});
```

**Step 3: Run test to see current failures**

```bash
npm run test:e2e -- complete-authoring-journey.spec.ts
```

Expected: May fail on various points - note which steps fail

**Step 4: Add data-testid attributes to components**

Based on test failures, add missing test IDs to components:

```typescript
// Example in BookCreationWizard
<Button data-testid="create-book-button" onClick={handleCreate}>
  Create Book
</Button>
```

**Step 5: Run test again**

```bash
npm run test:e2e -- complete-authoring-journey.spec.ts
```

Expected: PASS - Complete journey from book creation to draft

**Step 6: Add performance assertion**

```typescript
test('authoring journey completes in under 60 seconds', async ({ page }) => {
  const startTime = Date.now();

  // ... complete journey steps ...

  const duration = Date.now() - startTime;
  expect(duration).toBeLessThan(60000); // 60 seconds
});
```

**Step 7: Run final test**

```bash
npm run test:e2e -- complete-authoring-journey.spec.ts
```

Expected: PASS - Both tests pass

**Step 8: Commit**

```bash
git add frontend/src/e2e/
git commit -m "test(e2e): add complete authoring journey test"
```

---

### Task 7: E2E Test - Editing & Auto-save Flow

**Goal:** Test editing workflow with auto-save and localStorage backup.

**Files:**
- Create: `frontend/src/e2e/editing-autosave-flow.spec.ts`

**Step 1: Write test for successful auto-save**

```typescript
// frontend/src/e2e/editing-autosave-flow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Editing & Auto-save Flow', () => {
  test('should auto-save chapter edits', async ({ page }) => {
    // 1. Login and navigate to existing book
    await page.goto('/dashboard');
    await page.click('[data-testid="book-card-0"]');

    // 2. Open chapter editor
    await page.click('[data-testid="chapter-tab-0"]');

    // 3. Type content
    const editor = page.locator('.ProseMirror');
    await editor.fill('This is new content for the chapter.');

    // 4. Wait for "Saving..." indicator
    await page.waitForSelector('[data-testid="save-status"]');
    const saveStatus = await page.textContent('[data-testid="save-status"]');
    expect(saveStatus).toContain('Saving');

    // 5. Wait for "Saved ✓" indicator
    await page.waitForSelector('[data-testid="save-status"]:has-text("Saved")');
    const savedStatus = await page.textContent('[data-testid="save-status"]');
    expect(savedStatus).toMatch(/Saved ✓ \d{1,2}:\d{2}/);

    // 6. Refresh page
    await page.reload();

    // 7. Verify content persisted
    const persistedContent = await editor.textContent();
    expect(persistedContent).toContain('This is new content');
  });
});
```

**Step 2: Run test**

```bash
npm run test:e2e -- editing-autosave-flow.spec.ts
```

Expected: PASS

**Step 3: Write test for localStorage backup on network failure**

```typescript
test('should backup to localStorage when network fails', async ({ page, context }) => {
  // 1. Navigate to chapter editor
  await page.goto('/dashboard');
  await page.click('[data-testid="book-card-0"]');
  await page.click('[data-testid="chapter-tab-0"]');

  // 2. Simulate network offline
  await context.setOffline(true);

  // 3. Type content
  const editor = page.locator('.ProseMirror');
  await editor.fill('Content saved to localStorage');

  // 4. Wait for error indicator
  await page.waitForSelector('[data-testid="save-status"]:has-text("Error")');

  // 5. Check localStorage has backup
  const localStorageData = await page.evaluate(() => {
    return localStorage.getItem('chapter-backup-draft');
  });

  expect(localStorageData).toContain('Content saved to localStorage');

  // 6. Restore network
  await context.setOffline(false);

  // 7. Trigger manual save
  await page.click('[data-testid="retry-save"]');

  // 8. Wait for success
  await page.waitForSelector('[data-testid="save-status"]:has-text("Saved")');

  // 9. Verify localStorage backup cleared
  const clearedBackup = await page.evaluate(() => {
    return localStorage.getItem('chapter-backup-draft');
  });

  expect(clearedBackup).toBeNull();
});
```

**Step 4: Run test**

```bash
npm run test:e2e -- editing-autosave-flow.spec.ts
```

Expected: PASS - 2 tests passed

**Step 5: Commit**

```bash
git add frontend/src/e2e/editing-autosave-flow.spec.ts
git commit -m "test(e2e): add editing and auto-save flow tests"
```

---

### Task 8: E2E Test - Error Recovery Flow

**Goal:** Test error handling with retry logic.

**Files:**
- Create: `frontend/src/e2e/error-recovery-flow.spec.ts`

**Step 1: Write test for automatic retry**

```typescript
// frontend/src/e2e/error-recovery-flow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Error Recovery Flow', () => {
  test('should automatically retry transient errors', async ({ page }) => {
    let requestCount = 0;

    // Mock API to fail twice, then succeed
    await page.route('**/api/books', async (route) => {
      requestCount++;

      if (requestCount < 3) {
        await route.fulfill({
          status: 500,
          body: JSON.stringify({ message: 'Server error' })
        });
      } else {
        await route.fulfill({
          status: 201,
          body: JSON.stringify({ id: '123', title: 'Test Book' })
        });
      }
    });

    // 1. Try to create book
    await page.goto('/dashboard');
    await page.click('[data-testid="create-book-button"]');
    await page.fill('[name="title"]', 'Test Book');
    await page.click('[data-testid="submit"]');

    // 2. Verify retry indicators appear
    await page.waitForSelector('[data-testid="retry-indicator"]');
    const retryText = await page.textContent('[data-testid="retry-indicator"]');
    expect(retryText).toContain('Retrying');

    // 3. Verify eventual success
    await page.waitForSelector('[data-testid="success-notification"]');
    expect(requestCount).toBe(3);
  });

  test('should preserve user input during retry', async ({ page }) => {
    let requestCount = 0;

    await page.route('**/api/books', async (route) => {
      requestCount++;

      if (requestCount === 1) {
        await route.abort('failed');
      } else {
        const postData = route.request().postDataJSON();
        await route.fulfill({
          status: 201,
          body: JSON.stringify({ id: '123', ...postData })
        });
      }
    });

    // 1. Fill form with data
    await page.goto('/dashboard');
    await page.click('[data-testid="create-book-button"]');
    await page.fill('[name="title"]', 'My Important Book');
    await page.fill('[name="summary"]', 'This summary must be preserved');

    // 2. Submit (will fail and retry)
    await page.click('[data-testid="submit"]');

    // 3. Verify success with correct data
    await page.waitForSelector('[data-testid="success-notification"]');

    // 4. Navigate to book
    await page.click('[data-testid="book-card-0"]');

    // 5. Verify data preserved
    expect(await page.textContent('h1')).toContain('My Important Book');
    expect(await page.textContent('[data-testid="summary"]')).toContain('This summary must be preserved');
  });

  test('should show manual retry for non-transient errors', async ({ page }) => {
    await page.route('**/api/books', async (route) => {
      await route.fulfill({
        status: 422,
        body: JSON.stringify({
          message: 'Validation failed',
          errors: { title: 'Title is required' }
        })
      });
    });

    // 1. Submit invalid form
    await page.goto('/dashboard');
    await page.click('[data-testid="create-book-button"]');
    await page.click('[data-testid="submit"]');

    // 2. Verify validation error shown (no auto-retry)
    await page.waitForSelector('[data-testid="error-notification"]');
    const errorText = await page.textContent('[data-testid="error-notification"]');
    expect(errorText).toContain('Title is required');

    // 3. Verify no automatic retry occurred
    expect(await page.locator('[data-testid="retry-indicator"]').count()).toBe(0);
  });
});
```

**Step 2: Run tests**

```bash
npm run test:e2e -- error-recovery-flow.spec.ts
```

Expected: PASS - 3 tests passed

**Step 3: Commit**

```bash
git add frontend/src/e2e/error-recovery-flow.spec.ts
git commit -m "test(e2e): add error recovery flow tests"
```

---

## Iteration 3: Component Deep Dive (Sprint 5-6)

### Task 9: Review Existing Component Tests

**Goal:** Assess comprehensiveness of existing component tests and identify gaps.

**Files:**
- Read: All existing test files in `frontend/src/__tests__/`
- Create: `docs/testing/component-test-gaps.md`

**Step 1: List all existing component tests**

```bash
cd frontend
npm test -- --listTests | grep -E "test.tsx$" > /tmp/test-list.txt
wc -l /tmp/test-list.txt
```

Note: X test files found

**Step 2: Create test coverage matrix**

For each major component category, check test existence:

```markdown
## Component Test Coverage Matrix

| Component | Test Exists | Comprehensive? | Gaps |
|-----------|-------------|----------------|------|
| DeleteBookModal | ✅ | ✅ | None |
| BookCard | ✅ | ✅ | None |
| ChapterEditor | ✅ | ⚠️ | Missing error state tests |
| VoiceTextInput | ✅ | ✅ | None |
| BookCreationWizard | ❌ | - | No tests |
| TOCGenerationWizard | ✅ | ⚠️ | Missing cancel flow |
| ExportOptionsModal | ✅ | ✅ | Created in Task 3 |
| ErrorNotification | ✅ | ✅ | Created in Task 4 |
```

**Step 3: Identify priority gaps**

List components needing tests:
1. BookCreationWizard - HIGH (complex form, multiple steps)
2. ChapterEditor error states - MEDIUM (error handling important)
3. TOCGenerationWizard cancel flow - LOW (edge case)

**Step 4: Create gap analysis document**

Create `docs/testing/component-test-gaps.md`:

```markdown
# Component Test Gap Analysis

**Date:** 2025-10-13

## High Priority Gaps

### BookCreationWizard
**Current:** No tests
**Needed:**
- Multi-step form navigation
- Field validation
- Error handling
- Success flow
- Cancel/back navigation

**Estimated effort:** 8 hours

## Medium Priority Gaps

### ChapterEditor Error States
**Current:** Has basic tests, missing error scenarios
**Needed:**
- Network error during save
- LocalStorage backup
- Recovery from error

**Estimated effort:** 4 hours

## Low Priority Gaps

### TOCGenerationWizard Cancel Flow
**Current:** Has main flow tests
**Needed:**
- Cancel during generation
- Discard changes confirmation

**Estimated effort:** 2 hours

## Total Effort: 14 hours
```

**Step 5: Commit gap analysis**

```bash
git add docs/testing/component-test-gaps.md
git commit -m "docs(testing): component test gap analysis"
```

---

### Task 10: TDD BookCreationWizard Component Tests

**Goal:** Create comprehensive tests for BookCreationWizard.

**Files:**
- Create: `frontend/src/components/__tests__/BookCreationWizard.test.tsx`
- Modify: `frontend/src/components/BookCreationWizard.tsx` (if needed)

**Step 1: Write test for multi-step navigation**

```typescript
// frontend/src/components/__tests__/BookCreationWizard.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BookCreationWizard } from '../BookCreationWizard';

describe('BookCreationWizard', () => {
  const mockOnCreate = jest.fn();
  const mockOnCancel = jest.fn();

  it('should navigate through wizard steps', async () => {
    render(
      <BookCreationWizard
        isOpen={true}
        onClose={mockOnCancel}
        onCreate={mockOnCreate}
      />
    );

    // Step 1: Book details
    expect(screen.getByLabelText('Title')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Test Book' } });
    fireEvent.change(screen.getByLabelText('Genre'), { target: { value: 'non-fiction' } });
    fireEvent.click(screen.getByText('Next'));

    // Step 2: Summary
    await waitFor(() => {
      expect(screen.getByLabelText('Summary')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText('Summary'), { target: { value: 'Test summary' } });
    fireEvent.click(screen.getByText('Next'));

    // Step 3: Confirm
    await waitFor(() => {
      expect(screen.getByText('Review your book')).toBeInTheDocument();
    });

    expect(screen.getByText('Test Book')).toBeInTheDocument();
    expect(screen.getByText('Test summary')).toBeInTheDocument();
  });
});
```

**Step 2: Run test to check current state**

```bash
npm test -- BookCreationWizard.test
```

Expected: May pass or fail depending on current implementation

**Step 3: Add validation tests**

```typescript
it('should validate required fields', async () => {
  render(<BookCreationWizard isOpen={true} onClose={mockOnCancel} onCreate={mockOnCreate} />);

  // Try to proceed without filling fields
  fireEvent.click(screen.getByText('Next'));

  // Should show validation errors
  await waitFor(() => {
    expect(screen.getByText('Title is required')).toBeInTheDocument();
  });

  // Form should not advance
  expect(screen.getByLabelText('Title')).toBeInTheDocument(); // Still on step 1
});

it('should validate title length', async () => {
  render(<BookCreationWizard isOpen={true} onClose={mockOnCancel} onCreate={mockOnCreate} />);

  fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'ab' } });
  fireEvent.click(screen.getByText('Next'));

  await waitFor(() => {
    expect(screen.getByText('Title must be at least 3 characters')).toBeInTheDocument();
  });
});
```

**Step 4: Add error handling test**

```typescript
it('should handle API errors gracefully', async () => {
  mockOnCreate.mockRejectedValue(new Error('Network error'));

  render(<BookCreationWizard isOpen={true} onClose={mockOnCancel} onCreate={mockOnCreate} />);

  // Fill and submit form
  fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Test Book' } });
  fireEvent.change(screen.getByLabelText('Genre'), { target: { value: 'non-fiction' } });
  fireEvent.click(screen.getByText('Next'));

  await waitFor(() => {
    fireEvent.change(screen.getByLabelText('Summary'), { target: { value: 'Test' } });
  });

  fireEvent.click(screen.getByText('Create Book'));

  // Should show error
  await waitFor(() => {
    expect(screen.getByText(/error/i)).toBeInTheDocument();
  });

  // Should stay in wizard (not close)
  expect(screen.getByLabelText('Summary')).toBeInTheDocument();
});
```

**Step 5: Run all tests**

```bash
npm test -- BookCreationWizard.test
```

Expected: PASS - All wizard tests pass

**Step 6: Commit**

```bash
git add frontend/src/components/__tests__/BookCreationWizard.test.tsx
git commit -m "test(components): add comprehensive BookCreationWizard tests"
```

---

### Task 11: Expand ChapterEditor Error State Tests

**Goal:** Add missing error scenario tests to ChapterEditor.

**Files:**
- Modify: `frontend/src/components/chapters/__tests__/ChapterEditor.saveStatus.test.tsx`

**Step 1: Add network error test**

```typescript
// Add to existing test file
describe('ChapterEditor Error States', () => {
  it('should handle network error during save', async () => {
    // Mock save to fail
    jest.spyOn(bookClient, 'updateChapter').mockRejectedValue(new Error('Network error'));

    const { container } = render(
      <ChapterEditor
        chapterId="123"
        initialContent="Test content"
        onSave={mockOnSave}
      />
    );

    // Type content
    const editor = container.querySelector('.ProseMirror');
    fireEvent.input(editor, { target: { innerHTML: 'New content' } });

    // Wait for auto-save attempt
    await waitFor(() => {
      expect(screen.getByText(/saving/i)).toBeInTheDocument();
    });

    // Should show error
    await waitFor(() => {
      expect(screen.getByText(/error saving/i)).toBeInTheDocument();
    });

    // Should show retry button
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  it('should backup to localStorage on save failure', async () => {
    jest.spyOn(bookClient, 'updateChapter').mockRejectedValue(new Error('Network error'));
    const setItemSpy = jest.spyOn(Storage.prototype, 'setItem');

    const { container } = render(
      <ChapterEditor chapterId="123" initialContent="Test" onSave={mockOnSave} />
    );

    const editor = container.querySelector('.ProseMirror');
    fireEvent.input(editor, { target: { innerHTML: 'New content for backup' } });

    // Wait for save error
    await waitFor(() => {
      expect(screen.getByText(/error saving/i)).toBeInTheDocument();
    });

    // Verify localStorage backup
    expect(setItemSpy).toHaveBeenCalledWith(
      expect.stringContaining('chapter-backup'),
      expect.stringContaining('New content for backup')
    );
  });

  it('should recover from localStorage after successful retry', async () => {
    const updateMock = jest.spyOn(bookClient, 'updateChapter')
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce({ success: true });

    const removeItemSpy = jest.spyOn(Storage.prototype, 'removeItem');

    const { container } = render(
      <ChapterEditor chapterId="123" initialContent="Test" onSave={mockOnSave} />
    );

    // Trigger save error
    const editor = container.querySelector('.ProseMirror');
    fireEvent.input(editor, { target: { innerHTML: 'Content' } });

    await waitFor(() => {
      expect(screen.getByText(/error saving/i)).toBeInTheDocument();
    });

    // Click retry
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));

    // Wait for success
    await waitFor(() => {
      expect(screen.getByText(/saved/i)).toBeInTheDocument();
    });

    // Verify localStorage cleared
    expect(removeItemSpy).toHaveBeenCalledWith(expect.stringContaining('chapter-backup'));
  });
});
```

**Step 2: Run tests**

```bash
npm test -- ChapterEditor.saveStatus.test
```

Expected: PASS - All tests including new error states

**Step 3: Commit**

```bash
git add frontend/src/components/chapters/__tests__/ChapterEditor.saveStatus.test.tsx
git commit -m "test(components): expand ChapterEditor error state tests"
```

---

### Task 12: Generate Updated Coverage Report

**Goal:** Compare coverage after Iteration 3 to baseline.

**Files:**
- Create: `docs/testing/coverage-iteration-3.md`

**Step 1: Run all tests with coverage**

```bash
# Backend
cd backend
uv run pytest --cov=app --cov-report=json

# Frontend
cd frontend
npm run test:coverage
```

**Step 2: Extract metrics**

```bash
# Backend coverage
cd backend
cat coverage.json | jq '.totals.percent_covered'

# Frontend coverage
cd frontend
cat coverage/coverage-summary.json | jq '.total.lines.pct'
```

**Step 3: Create comparison report**

```markdown
# Coverage Report - Post Iteration 3

**Date:** 2025-10-XX

## Backend Coverage
- **Previous:** 80.5%
- **Current:** 80.8%
- **Change:** +0.3%

✅ **Goal Met:** Maintained 80%+

## Frontend Coverage
- **Previous:** XX%
- **Current:** 82.5%
- **Change:** +X%

✅ **Goal Met:** Achieved 80%+

## E2E Coverage
- **Tests Added:** 3 (authoring journey, editing, error recovery)
- **Total E2E Tests:** X
- **Execution Time:** 4 minutes (Previous: 8 minutes)

✅ **Goal Met:** <5 minutes, 3 critical paths covered

## New Test Files Created
1. `ExportOptionsModal.test.tsx` (Task 3)
2. `errorHandler.test.ts` (Task 4)
3. `complete-authoring-journey.spec.ts` (Task 6)
4. `editing-autosave-flow.spec.ts` (Task 7)
5. `error-recovery-flow.spec.ts` (Task 8)
6. `BookCreationWizard.test.tsx` (Task 10)

## Tests Expanded
1. `ChapterEditor.saveStatus.test.tsx` (+3 error state tests)

## Next Iteration Priorities
- [ ] Visual regression tests (if needed)
- [ ] Performance tests for large books
- [ ] Accessibility audit tests
- [ ] Component tests for remaining gaps
```

**Step 4: Commit**

```bash
git add docs/testing/coverage-iteration-3.md
git commit -m "docs(testing): post-iteration 3 coverage report"
```

---

## Decision Gate: Next Steps

After completing Iteration 3, review:

1. **Coverage Metrics**
   - Backend: XX% (goal: 80%+)
   - Frontend: XX% (goal: 80%+)
   - Critical paths covered by E2E

2. **Test Quality**
   - Flaky test count: X
   - E2E execution time: X minutes
   - Test maintenance burden

3. **Remaining Gaps**
   - Low-priority component tests
   - Visual regression tests
   - Performance tests

**Decision Options:**

**A) Continue to Iteration 4** - Fill remaining gaps identified in gap analysis

**B) Focus on Quality** - Fix flaky tests, optimize slow tests, improve test maintainability

**C) Maintenance Mode** - Switch to TDD for new features only, maintain current coverage

**D) Visual Regression** - Add Playwright screenshot testing for UI components

---

## Testing Patterns & Utilities

### Condition-Based Waiting Pattern

```typescript
// Use for reliable E2E tests instead of arbitrary timeouts
await waitForCondition(
  async () => {
    const element = await page.$(selector);
    return element !== null && await element.isEnabled();
  },
  { timeout: 5000, interval: 100 }
);
```

### Mock API Setup Pattern

```typescript
// Centralize mock responses for consistency
export async function setupMockAI(page: Page) {
  await page.route('**/api/ai/**', async (route) => {
    const url = route.request().url();

    if (url.includes('generate-questions')) {
      await route.fulfill({ status: 200, body: JSON.stringify(mockQuestions) });
    } else if (url.includes('generate-toc')) {
      await route.fulfill({ status: 200, body: JSON.stringify(mockTOC) });
    }
    // ... other routes
  });
}
```

### Test Data Factory Pattern

```typescript
// Create reusable test data builders
export const testDataFactory = {
  book: (overrides = {}) => ({
    id: '123',
    title: 'Test Book',
    genre: 'non-fiction',
    summary: 'Test summary',
    ...overrides
  }),

  chapter: (overrides = {}) => ({
    id: '1',
    title: 'Chapter 1',
    content: 'Test content',
    word_count: 100,
    ...overrides
  })
};
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install uv
          uv sync
      - name: Run tests with coverage
        run: |
          cd backend
          uv run pytest --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Run tests with coverage
        run: |
          cd frontend
          npm run test:coverage
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node
        uses: actions/setup-node@v3
      - name: Install Playwright
        run: |
          cd frontend
          npm ci
          npx playwright install --with-deps
      - name: Run E2E tests
        run: |
          cd frontend
          npm run test:e2e
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: frontend/test-results/
```

---

## Success Criteria

### Iteration 1 Complete When:
- ✅ E2E assessment report created
- ✅ E2E tests optimized (<5 min runtime)
- ✅ Phase 1 features have TDD tests
- ✅ Coverage baseline established

### Iteration 2 Complete When:
- ✅ 3 critical E2E tests created and passing
- ✅ E2E tests use mocked AI responses
- ✅ All E2E tests run in <5 minutes

### Iteration 3 Complete When:
- ✅ Component test gaps filled
- ✅ Frontend coverage ≥80%
- ✅ Backend coverage maintained ≥80%
- ✅ Coverage comparison report created

### Overall Success:
- ✅ All critical user journeys covered by E2E tests
- ✅ All interactive components have comprehensive tests
- ✅ Error handling tested thoroughly
- ✅ Auto-save and recovery tested
- ✅ Test suite runs fast (<10 min total)
- ✅ CI/CD integration working
- ✅ TDD workflow established for future features

---

## Maintenance Guidelines

### Adding New Tests
1. Follow TDD: Write test first, watch it fail, implement, pass
2. Use test data factories for consistency
3. Mock external dependencies (AI APIs, auth)
4. Add data-testid attributes to new components
5. Keep tests focused (one behavior per test)

### Updating Tests
1. When bugs found, write failing test first
2. Update tests when API contracts change
3. Remove obsolete tests when features removed
4. Keep test names descriptive

### Performance
1. Run fast unit tests in watch mode during development
2. Run E2E tests before commits
3. Run full suite in CI/CD
4. Optimize slow tests immediately

---

**Plan complete!**

This plan provides detailed, step-by-step instructions for implementing comprehensive testing coverage in three agile iterations with built-in decision gates and measurement points.
