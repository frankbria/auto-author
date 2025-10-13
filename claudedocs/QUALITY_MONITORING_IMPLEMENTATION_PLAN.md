# Quality Monitoring Implementation Plan

**Generated**: 2025-10-12
**Source**: Consolidated from UI Improvements checklist (Sprint 3-4 quality requirements)
**Status**: Ready for Implementation
**See Also**: `/IMPLEMENTATION_PLAN.md` Sprint 3-4 section for overall context
**Owner**: Development Team
**Timeline**: 3 weeks (15-20 development hours)

---

## Executive Summary

This plan coordinates the implementation of systematic quality monitoring for the Auto-Author application, addressing performance tracking, loading state management, data preservation, and responsive design validation. The implementation follows a phased approach prioritizing foundation → validation → integration.

### Key Objectives
1. **Performance Monitoring**: Track and optimize Core Web Vitals and operation timings
2. **Loading State Management**: Provide clear user feedback for all async operations
3. **Data Preservation**: Validate and enhance data safety mechanisms
4. **Responsive Design**: Ensure consistent mobile experience across devices
5. **Quality Dashboard**: Centralize quality metrics and monitoring
6. **CI/CD Integration**: Automate quality gates and prevent regressions

---

## Current Status

### ✅ Completed Quality Work
- **Auto-save Optimization** (2h): localStorage backup, save status indicators
- **Keyboard Navigation Audit** (3h): WCAG 2.1 compliance, comprehensive reports
- **Loading State Audit** (3h): Gap analysis completed, 5 high-priority issues identified

### 🚧 Pending High-Priority Items
- **Performance Monitoring Setup** (4h): NOT STARTED
- **Loading State Implementation** (3h): Audit complete, implementation pending
- **Responsive Design Validation** (2h): NOT STARTED
- **Data Preservation Verification** (2h): NOT STARTED

### Total Remaining Effort
- **High Priority**: 11 hours
- **Dashboard/Integration**: 4-6 hours
- **Total**: 15-17 hours over 3 weeks

---

## Architecture Overview

### Quality Monitoring Stack
```
┌─────────────────────────────────────────────────┐
│         Quality Monitoring Dashboard            │
│   (Centralized metrics and visualization)       │
└─────────────────────────────────────────────────┘
                      ↑
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
    ↓                 ↓                 ↓
┌─────────┐    ┌──────────┐    ┌───────────┐
│ Perf    │    │ Loading  │    │ Data      │
│ Monitor │    │ State    │    │ Preserve  │
└─────────┘    └──────────┘    └───────────┘
    ↓                 ↓                 ↓
┌─────────────────────────────────────────────────┐
│              CI/CD Quality Gates                 │
│   (Automated validation and regression tests)   │
└─────────────────────────────────────────────────┘
```

### Technology Stack
- **Performance**: `web-vitals` (Google's official library)
- **Loading States**: React Context + Custom hooks
- **Data Storage**: localStorage wrapper with TTL and validation
- **Responsive Testing**: Playwright with custom viewport helpers
- **Monitoring**: Custom dashboard + optional third-party integration

---

## Phase 1: Foundation (Week 1)

### 1.1 Performance Monitoring Setup (4 hours)

**Objective**: Establish baseline performance tracking and optimization infrastructure

#### Implementation Tasks

**1.1.1 Install Dependencies (30 min)**
```bash
cd frontend
npm install web-vitals
npm install --save-dev @types/web-vitals
```

**1.1.2 Create Performance Utilities (1.5h)**

File: `frontend/src/lib/performance/metrics.ts`
```typescript
import { onCLS, onFID, onFCP, onLCP, onTTFB, onINP } from 'web-vitals';

export interface PerformanceMetric {
  name: string;
  value: number;
  rating: 'good' | 'needs-improvement' | 'poor';
  timestamp: number;
}

export interface CustomMetric {
  operation: string;
  duration: number;
  metadata?: Record<string, unknown>;
}

// Core Web Vitals tracking
export function initializeWebVitals() {
  onCLS(sendToAnalytics);
  onFID(sendToAnalytics);
  onFCP(sendToAnalytics);
  onLCP(sendToAnalytics);
  onTTFB(sendToAnalytics);
  onINP(sendToAnalytics);
}

// Custom operation tracking
export class PerformanceTracker {
  private marks: Map<string, number> = new Map();

  startOperation(operationId: string): void {
    performance.mark(`${operationId}-start`);
    this.marks.set(operationId, performance.now());
  }

  endOperation(operationId: string, metadata?: Record<string, unknown>): CustomMetric {
    performance.mark(`${operationId}-end`);
    const measure = performance.measure(
      operationId,
      `${operationId}-start`,
      `${operationId}-end`
    );

    return {
      operation: operationId,
      duration: measure.duration,
      metadata
    };
  }
}

function sendToAnalytics(metric: PerformanceMetric) {
  // Send to backend analytics endpoint or store locally
  if (process.env.NODE_ENV === 'production') {
    // POST to analytics endpoint
  } else {
    console.log('[Performance]', metric);
  }
}
```

File: `frontend/src/lib/performance/budgets.ts`
```typescript
export const PERFORMANCE_BUDGETS = {
  // Core Web Vitals thresholds
  LCP: { good: 2500, needsImprovement: 4000 },
  FID: { good: 100, needsImprovement: 300 },
  CLS: { good: 0.1, needsImprovement: 0.25 },
  TTFB: { good: 800, needsImprovement: 1800 },
  INP: { good: 200, needsImprovement: 500 },

  // Custom operation budgets (milliseconds)
  operations: {
    'toc-generation': { good: 5000, needsImprovement: 10000 },
    'export-pdf': { good: 10000, needsImprovement: 30000 },
    'export-docx': { good: 10000, needsImprovement: 30000 },
    'draft-generation': { good: 8000, needsImprovement: 15000 },
    'auto-save': { good: 1000, needsImprovement: 5000 },
    'page-load': { good: 3000, needsImprovement: 5000 }
  }
} as const;

export function checkBudget(metric: string, value: number): 'good' | 'needs-improvement' | 'poor' {
  const budget = PERFORMANCE_BUDGETS.operations[metric as keyof typeof PERFORMANCE_BUDGETS.operations];
  if (!budget) return 'good';

  if (value <= budget.good) return 'good';
  if (value <= budget.needsImprovement) return 'needs-improvement';
  return 'poor';
}
```

**1.1.3 Create Performance Hook (1h)**

File: `frontend/src/hooks/usePerformanceTracking.ts`
```typescript
import { useEffect, useRef } from 'react';
import { PerformanceTracker } from '@/lib/performance/metrics';

export function usePerformanceTracking(operationName: string) {
  const tracker = useRef(new PerformanceTracker());

  const startTracking = () => {
    tracker.current.startOperation(operationName);
  };

  const endTracking = (metadata?: Record<string, unknown>) => {
    const metric = tracker.current.endOperation(operationName, metadata);
    // Optionally send to analytics
    return metric;
  };

  return { startTracking, endTracking };
}
```

**1.1.4 Integrate with Existing Operations (1h)**

Update key operations:
- `frontend/src/components/toc/TocGenerationWizard.tsx`
- `frontend/src/components/chapters/DraftGenerator.tsx`
- `frontend/src/app/dashboard/books/[bookId]/export/page.tsx`
- `frontend/src/components/chapters/ChapterEditor.tsx` (auto-save)

**1.1.5 Testing (30 min)**

File: `frontend/src/lib/performance/__tests__/metrics.test.ts`
```typescript
describe('PerformanceTracker', () => {
  it('should track operation duration', () => {
    const tracker = new PerformanceTracker();
    tracker.startOperation('test-op');
    // Simulate work
    const metric = tracker.endOperation('test-op');
    expect(metric.duration).toBeGreaterThan(0);
  });

  it('should include metadata in metrics', () => {
    const tracker = new PerformanceTracker();
    tracker.startOperation('test-op');
    const metric = tracker.endOperation('test-op', { bookId: '123' });
    expect(metric.metadata).toEqual({ bookId: '123' });
  });
});
```

#### Acceptance Criteria
- ✅ Core Web Vitals tracked on all pages
- ✅ Custom operations (TOC, export, draft, auto-save) tracked
- ✅ Performance budgets defined and validated
- ✅ Metrics logged in dev, sent to analytics in prod
- ✅ Test coverage ≥85%

---

### 1.2 Loading State Improvements (3 hours)

**Objective**: Implement missing loading indicators for 5 high-priority operations identified in audit

#### Gap Analysis from Audit Report
High-priority operations missing loading states:
1. TOC generation (critical)
2. Export operations (critical)
3. Draft generation (critical)
4. Chapter creation (medium)
5. Book metadata save (medium)

#### Implementation Tasks

**1.2.1 Create Loading State Manager (1h)**

File: `frontend/src/lib/loading/LoadingStateManager.ts`
```typescript
export interface LoadingState {
  isLoading: boolean;
  progress?: number;
  status?: string;
  startTime?: number;
  estimatedTimeRemaining?: number;
}

export class LoadingStateManager {
  private states: Map<string, LoadingState> = new Map();
  private listeners: Map<string, Set<(state: LoadingState) => void>> = new Map();

  startLoading(operationId: string, status?: string): void {
    const state: LoadingState = {
      isLoading: true,
      progress: 0,
      status,
      startTime: Date.now()
    };
    this.states.set(operationId, state);
    this.notifyListeners(operationId, state);
  }

  updateProgress(operationId: string, progress: number, status?: string): void {
    const state = this.states.get(operationId);
    if (!state) return;

    const elapsed = Date.now() - (state.startTime || 0);
    const estimatedTotal = progress > 0 ? (elapsed / progress) * 100 : 0;
    const estimatedTimeRemaining = estimatedTotal - elapsed;

    const updatedState = {
      ...state,
      progress,
      status: status || state.status,
      estimatedTimeRemaining
    };

    this.states.set(operationId, updatedState);
    this.notifyListeners(operationId, updatedState);
  }

  completeLoading(operationId: string): void {
    this.states.delete(operationId);
    this.notifyListeners(operationId, { isLoading: false });
  }

  subscribe(operationId: string, listener: (state: LoadingState) => void): () => void {
    if (!this.listeners.has(operationId)) {
      this.listeners.set(operationId, new Set());
    }
    this.listeners.get(operationId)!.add(listener);

    // Return unsubscribe function
    return () => {
      this.listeners.get(operationId)?.delete(listener);
    };
  }

  private notifyListeners(operationId: string, state: LoadingState): void {
    this.listeners.get(operationId)?.forEach(listener => listener(state));
  }
}

export const globalLoadingManager = new LoadingStateManager();
```

**1.2.2 Create React Hook (30 min)**

File: `frontend/src/hooks/useLoadingState.ts`
```typescript
import { useState, useEffect } from 'react';
import { globalLoadingManager, LoadingState } from '@/lib/loading/LoadingStateManager';

export function useLoadingState(operationId: string) {
  const [state, setState] = useState<LoadingState>({ isLoading: false });

  useEffect(() => {
    const unsubscribe = globalLoadingManager.subscribe(operationId, setState);
    return unsubscribe;
  }, [operationId]);

  const startLoading = (status?: string) => {
    globalLoadingManager.startLoading(operationId, status);
  };

  const updateProgress = (progress: number, status?: string) => {
    globalLoadingManager.updateProgress(operationId, progress, status);
  };

  const completeLoading = () => {
    globalLoadingManager.completeLoading(operationId);
  };

  return {
    ...state,
    startLoading,
    updateProgress,
    completeLoading
  };
}
```

**1.2.3 Create Progress Components (1h)**

File: `frontend/src/components/loading/ProgressIndicator.tsx`
```typescript
import { Progress } from '@/components/ui/progress';
import { Loader2 } from 'lucide-react';

interface ProgressIndicatorProps {
  progress?: number;
  status?: string;
  estimatedTimeRemaining?: number;
  isIndeterminate?: boolean;
}

export function ProgressIndicator({
  progress,
  status,
  estimatedTimeRemaining,
  isIndeterminate = false
}: ProgressIndicatorProps) {
  const formatTime = (ms: number) => {
    const seconds = Math.ceil(ms / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  return (
    <div className="space-y-2" role="status" aria-live="polite">
      {isIndeterminate ? (
        <div className="flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-sm text-muted-foreground">{status || 'Loading...'}</span>
        </div>
      ) : (
        <>
          <Progress value={progress} className="h-2" />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{status || 'Processing...'}</span>
            {progress !== undefined && (
              <span>{Math.round(progress)}%</span>
            )}
          </div>
          {estimatedTimeRemaining !== undefined && estimatedTimeRemaining > 1000 && (
            <p className="text-xs text-muted-foreground">
              Estimated time remaining: {formatTime(estimatedTimeRemaining)}
            </p>
          )}
        </>
      )}
    </div>
  );
}
```

**1.2.4 Integrate with High-Priority Operations (30 min)**

Update components:
1. `TocGenerationWizard.tsx` - Add progress tracking
2. `ExportProgressModal.tsx` - Enhance with time estimates
3. `DraftGenerator.tsx` - Add progress indicator
4. `ChapterEditor.tsx` - Visual feedback for auto-save
5. `BookPage.tsx` - Loading state for metadata updates

#### Acceptance Criteria
- ✅ All 5 high-priority operations have loading indicators
- ✅ Progress bars show completion percentage
- ✅ Estimated time remaining displayed for operations >5 seconds
- ✅ All loading states have ARIA labels
- ✅ Test coverage ≥85%

---

## Phase 2: Validation (Week 2)

### 2.1 Data Preservation Verification (2 hours)

**Objective**: Validate and enhance data safety mechanisms

#### Implementation Tasks

**2.1.1 Create SafeStorage Wrapper (1h)**

File: `frontend/src/lib/storage/SafeStorage.ts`
```typescript
export interface StorageItem<T> {
  data: T;
  timestamp: number;
  version: string;
  expiresAt?: number;
}

export class SafeStorage {
  private prefix = 'auto-author';
  private version = '1.0';

  set<T>(key: string, data: T, ttlHours = 24): boolean {
    try {
      const item: StorageItem<T> = {
        data,
        timestamp: Date.now(),
        version: this.version,
        expiresAt: Date.now() + (ttlHours * 60 * 60 * 1000)
      };
      localStorage.setItem(`${this.prefix}:${key}`, JSON.stringify(item));
      return true;
    } catch (error) {
      console.error('[SafeStorage] Failed to save:', error);
      return false;
    }
  }

  get<T>(key: string): T | null {
    try {
      const raw = localStorage.getItem(`${this.prefix}:${key}`);
      if (!raw) return null;

      const item: StorageItem<T> = JSON.parse(raw);

      // Check expiration
      if (item.expiresAt && Date.now() > item.expiresAt) {
        this.remove(key);
        return null;
      }

      // Check version compatibility
      if (item.version !== this.version) {
        console.warn('[SafeStorage] Version mismatch, data may be outdated');
      }

      return item.data;
    } catch (error) {
      console.error('[SafeStorage] Failed to retrieve:', error);
      return null;
    }
  }

  remove(key: string): void {
    localStorage.removeItem(`${this.prefix}:${key}`);
  }

  clear(): void {
    Object.keys(localStorage)
      .filter(key => key.startsWith(this.prefix))
      .forEach(key => localStorage.removeItem(key));
  }

  getAll(): Record<string, unknown> {
    const items: Record<string, unknown> = {};
    Object.keys(localStorage)
      .filter(key => key.startsWith(this.prefix))
      .forEach(key => {
        const shortKey = key.replace(`${this.prefix}:`, '');
        items[shortKey] = this.get(shortKey);
      });
    return items;
  }
}

export const storage = new SafeStorage();
```

**2.1.2 Create Navigation Guard (30 min)**

File: `frontend/src/hooks/useUnsavedChangesWarning.ts`
```typescript
import { useEffect } from 'react';

export function useUnsavedChangesWarning(hasUnsavedChanges: boolean) {
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
        return e.returnValue;
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [hasUnsavedChanges]);
}
```

**2.1.3 Testing Suite (30 min)**

Comprehensive tests for:
- localStorage persistence beyond 24 hours
- Unsaved changes warning before navigation
- Multi-tab conflict detection
- Form input preservation during errors
- Auto-save failure recovery

#### Acceptance Criteria
- ✅ localStorage validated for 24+ hour persistence
- ✅ Navigation warning prevents accidental data loss
- ✅ Multi-tab conflicts detected and handled
- ✅ Form inputs preserved during network errors
- ✅ Test coverage ≥85%

---

### 2.2 Responsive Design Validation (2 hours)

**Objective**: Ensure consistent mobile experience across all devices

#### Implementation Tasks

**2.2.1 Create Playwright Test Suite (1h)**

File: `e2e/responsive/viewport-testing.spec.ts`
```typescript
import { test, expect } from '@playwright/test';

const VIEWPORTS = [
  { name: 'Mobile Small', width: 320, height: 568 },
  { name: 'Mobile Medium', width: 375, height: 667 },
  { name: 'Mobile Large', width: 414, height: 896 },
  { name: 'Tablet', width: 768, height: 1024 },
  { name: 'Desktop', width: 1440, height: 900 }
];

for (const viewport of VIEWPORTS) {
  test.describe(`Responsive: ${viewport.name}`, () => {
    test.use({ viewport });

    test('dashboard renders correctly', async ({ page }) => {
      await page.goto('/dashboard');
      await expect(page).toHaveScreenshot(`dashboard-${viewport.name}.png`);
    });

    test('book page renders correctly', async ({ page }) => {
      // Test book page rendering
    });

    test('chapter editor renders correctly', async ({ page }) => {
      // Test editor rendering
    });
  });
}
```

**2.2.2 Touch Target Validation (30 min)**

File: `e2e/responsive/touch-targets.spec.ts`
```typescript
import { test, expect } from '@playwright/test';

async function validateTouchTargets(page: Page) {
  const interactiveElements = await page.locator('button, a, input, [role="button"]').all();

  for (const element of interactiveElements) {
    const box = await element.boundingBox();
    if (box) {
      expect(box.width).toBeGreaterThanOrEqual(44);
      expect(box.height).toBeGreaterThanOrEqual(44);
    }
  }
}

test('all interactive elements meet minimum touch target size', async ({ page }) => {
  await page.goto('/dashboard');
  await validateTouchTargets(page);
});
```

**2.2.3 Mobile Interaction Testing (30 min)**

Test scenarios:
- Text readability without zooming
- Navigation usability on small screens
- Form input accessibility
- Landscape and portrait orientations
- Touch gesture support

#### Acceptance Criteria
- ✅ Application works on screens ≥320px
- ✅ All touch targets ≥44x44 pixels
- ✅ Text readable without zooming
- ✅ Navigation usable on mobile
- ✅ Automated visual regression tests

---

## Phase 3: Integration (Week 3)

### 3.1 Quality Monitoring Dashboard (2-3 hours)

**Objective**: Centralize quality metrics and provide visibility

#### Implementation Tasks

**3.1.1 Create Dashboard Page (1.5h)**

File: `frontend/src/app/quality/page.tsx`
```typescript
export default function QualityDashboardPage() {
  return (
    <div className="container py-6">
      <h1>Quality Monitoring Dashboard</h1>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <WebVitalsCard />
        <OperationPerformanceCard />
        <LoadingStateMetricsCard />
        <DataPreservationCard />
        <ResponsiveTestResultsCard />
        <TestCoverageCard />
      </div>
    </div>
  );
}
```

**3.1.2 Create Metric Cards (1h)**

Individual cards for:
- Core Web Vitals summary
- Operation performance trends
- Loading state coverage
- Data preservation stats
- Responsive test results
- Test coverage metrics

**3.1.3 Real-time Updates (30 min)**

Implement WebSocket or polling for live metrics updates

#### Acceptance Criteria
- ✅ Dashboard displays all quality metrics
- ✅ Real-time updates for performance data
- ✅ Historical trends visualized
- ✅ Export capability for reports
- ✅ Mobile-responsive dashboard

---

### 3.2 CI/CD Integration (2-3 hours)

**Objective**: Automate quality gates and prevent regressions

#### Implementation Tasks

**3.2.1 GitHub Actions Workflow (1h)**

File: `.github/workflows/quality-gates.yml`
```yaml
name: Quality Gates

on:
  pull_request:
  push:
    branches: [main]

jobs:
  performance-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npm run build
      - run: npm run lighthouse-ci

  responsive-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npx playwright install
      - run: npm run test:responsive

  loading-state-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm run validate:loading-states
```

**3.2.2 Performance Budget Enforcement (1h)**

Configure Lighthouse CI with performance budgets

**3.2.3 Documentation (30 min)**

Update CLAUDE.md and create quality gate documentation

#### Acceptance Criteria
- ✅ Performance budgets enforced in CI/CD
- ✅ Responsive tests run automatically
- ✅ Loading state validation automated
- ✅ Failed builds prevent merges
- ✅ Clear error messages for failures

---

## Testing Strategy

### Unit Tests
- Performance tracking utilities
- Loading state manager
- SafeStorage wrapper
- Touch target validators

### Integration Tests
- Performance tracking with React components
- Loading state integration with operations
- Data preservation workflows
- Navigation guards

### E2E Tests (Playwright)
- Responsive design across viewports
- Touch target validation
- Mobile interaction scenarios
- Performance budget validation

### Coverage Requirements
- Minimum: 85% code coverage
- Target: 90% code coverage
- All tests must pass (100% pass rate)

---

## Documentation Updates

### Files to Update
1. **CLAUDE.md** - Add quality monitoring section
2. **IMPLEMENTATION_PLAN.md** - Mark quality tasks complete when done
3. **CURRENT_SPRINT.md** - Update sprint progress
4. **README.md** - Add quality standards section
5. **Package.json** - Add quality-related scripts

### New Documentation
1. **QUALITY_STANDARDS.md** - Define quality metrics and budgets
2. **PERFORMANCE_GUIDE.md** - Best practices for performance
3. **TESTING_GUIDE.md** - Quality testing procedures

---

## Risk Management

### Identified Risks

**Performance Overhead**
- **Risk**: Tracking adds latency to operations
- **Mitigation**: Use async tracking, batch analytics calls
- **Monitoring**: Measure tracking overhead in tests

**Browser Compatibility**
- **Risk**: Some APIs not available in all browsers
- **Mitigation**: Feature detection, graceful degradation
- **Testing**: Test on major browsers (Chrome, Firefox, Safari, Edge)

**Storage Limitations**
- **Risk**: localStorage quota exceeded
- **Mitigation**: TTL-based cleanup, monitor storage usage
- **Fallback**: Server-side backup for critical data

**CI/CD Performance**
- **Risk**: Quality checks slow down CI/CD pipeline
- **Mitigation**: Parallel job execution, cache dependencies
- **Optimization**: Run full suite only on main branch

---

## Success Metrics

### Quantitative Metrics
- Core Web Vitals: LCP <2.5s, FID <100ms, CLS <0.1
- Operation Performance: 90% within budget
- Loading State Coverage: 100% of async operations
- Test Coverage: ≥85%
- Responsive Tests: Pass on all viewports

### Qualitative Metrics
- User feedback on loading experience
- Developer satisfaction with monitoring tools
- Reduced bug reports for data loss
- Improved mobile usability ratings

---

## Timeline and Milestones

### Week 1 Milestones
- ✅ Performance monitoring infrastructure
- ✅ Loading state improvements deployed
- ✅ Initial metrics collection

### Week 2 Milestones
- ✅ Data preservation validated
- ✅ Responsive design verified
- ✅ Automated test suite complete

### Week 3 Milestones
- ✅ Quality dashboard deployed
- ✅ CI/CD integration complete
- ✅ Documentation finalized

---

## Appendix A: Performance Budgets Reference

### Core Web Vitals
| Metric | Good | Needs Improvement | Poor |
|--------|------|-------------------|------|
| LCP | ≤2.5s | ≤4s | >4s |
| FID | ≤100ms | ≤300ms | >300ms |
| CLS | ≤0.1 | ≤0.25 | >0.25 |
| TTFB | ≤800ms | ≤1.8s | >1.8s |
| INP | ≤200ms | ≤500ms | >500ms |

### Custom Operations
| Operation | Good | Needs Improvement | Poor |
|-----------|------|-------------------|------|
| TOC Generation | ≤5s | ≤10s | >10s |
| PDF Export | ≤10s | ≤30s | >30s |
| DOCX Export | ≤10s | ≤30s | >30s |
| Draft Generation | ≤8s | ≤15s | >15s |
| Auto-save | ≤1s | ≤5s | >5s |

---

## Appendix B: Responsive Breakpoints

### Standard Breakpoints
- **Mobile Small**: 320px - 374px
- **Mobile Medium**: 375px - 413px
- **Mobile Large**: 414px - 767px
- **Tablet**: 768px - 1023px
- **Desktop Small**: 1024px - 1439px
- **Desktop Large**: ≥1440px

### Touch Target Standards
- **Minimum Size**: 44x44 pixels (WCAG 2.1 Level AAA)
- **Recommended**: 48x48 pixels (Material Design)
- **Spacing**: ≥8px between targets

---

## Appendix C: Git Workflow

### Branch Naming
- `feat/quality-performance-monitoring`
- `feat/quality-loading-states`
- `feat/quality-data-preservation`
- `feat/quality-responsive-validation`
- `feat/quality-dashboard`
- `feat/quality-ci-integration`

### Commit Message Format
```
feat(quality): add performance monitoring infrastructure

- Implement web-vitals tracking
- Create PerformanceTracker utility
- Add performance budgets
- Integrate with TOC and export operations

Closes #123
```

---

**Last Updated**: 2025-10-12
**Version**: 1.0
**Status**: Ready for Implementation
