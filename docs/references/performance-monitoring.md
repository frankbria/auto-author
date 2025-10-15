# Performance Monitoring

## Overview
Comprehensive performance tracking system with Core Web Vitals and custom operation monitoring.

**Location**: `frontend/src/lib/performance/`, `frontend/src/hooks/usePerformanceTracking.ts`

## Core Components

1. **Metrics System** (`frontend/src/lib/performance/metrics.ts`):
   - Core Web Vitals tracking (LCP, FID, INP, CLS, TTFB, FCP)
   - PerformanceTracker class for custom operations
   - Rating system (good/needs-improvement/poor)
   - localStorage caching for offline scenarios
   - Development console logging and production analytics integration

2. **Performance Budgets** (`frontend/src/lib/performance/budgets.ts`):
   - 25+ operation budgets defined
   - Critical operations: TOC generation (3000ms), Export (5000ms), Draft generation (4000ms)
   - Auto-save budget: 1000ms
   - Budget validation and warning system
   - Priority-based categorization (1=critical, 3=low)

3. **React Hook** (`frontend/src/hooks/usePerformanceTracking.ts`):
   - Async operation tracking: `trackOperation(name, operation, metadata)`
   - Automatic cleanup on unmount
   - Budget validation with warnings
   - Error handling with performance context
   - Manual tracker creation for complex scenarios

4. **Web Vitals Initialization** (`frontend/src/components/performance/WebVitalsInit.tsx`):
   - Automatic Core Web Vitals tracking on app load
   - Client-side only (no SSR)
   - Integrated into app layout

## Usage

**Basic Operation Tracking**:
```typescript
import { usePerformanceTracking } from '@/hooks/usePerformanceTracking';

const { trackOperation } = usePerformanceTracking();

const handleExport = async () => {
  const result = await trackOperation('export-pdf', async () => {
    return await bookClient.exportPDF(bookId);
  }, { bookId, format: 'pdf' });

  if (result.metric.exceeded_budget) {
    console.warn(`Export took ${result.metric.duration}ms`);
  }
};
```

**Manual Tracker for Complex Scenarios**:
```typescript
const { createTracker } = usePerformanceTracking();

const tracker = createTracker('complex-operation', { phase: 'init' });
// ... do work across multiple functions ...
const metric = tracker.end({ result: 'success' });
```

## Integrated Operations

Performance tracking is active in:
- **TOC Generation**: toc-generation, toc-questions, toc-readiness, analyze-summary
- **Export**: export-pdf, export-docx, export-stats
- **Draft Generation**: generate-draft
- **Auto-save**: auto-save, manual-save
- **Chapter Operations**: chapter-load, chapter-list

## Performance Budgets

| Operation | Budget | Priority | Description |
|-----------|--------|----------|-------------|
| toc-generation | 3000ms | 1 | AI-powered TOC generation |
| export-pdf | 5000ms | 1 | PDF export |
| export-docx | 5000ms | 1 | DOCX export |
| generate-draft | 4000ms | 1 | AI draft from Q&A |
| auto-save | 1000ms | 1 | Auto-save (3s debounce) |
| chapter-load | 500ms | 1 | Load chapter content |
| book-list | 1200ms | 2 | Load user books |
| toc-questions | 2000ms | 2 | Generate clarifying questions |

## Development Mode

In development, performance metrics are logged to console with color-coded output:
- ✅ Green: Within budget (good)
- ⚠️ Yellow: Near budget (needs-improvement)
- ❌ Red: Exceeded budget (poor)

## Production Mode

In production, metrics are cached in localStorage for offline scenarios and should be sent to analytics endpoints:
```typescript
// TODO: Replace with actual analytics implementation
// window.gtag?.('event', event.event_name, event);
// window.analytics?.track(event.event_name, event);
```

## Testing

Test suite: `frontend/src/lib/performance/__tests__/metrics.test.ts`
- 20/20 tests passing (100% pass rate)
- Coverage: Basic tracking, budget validation, localStorage caching, error handling
- Development mode logging verification

## Future Enhancements

1. **Analytics Integration**: Connect to Google Analytics, Mixpanel, or custom endpoint
2. **Performance Dashboards**: Visualize metrics over time
3. **Alerting**: Automatic alerts when operations consistently exceed budgets
4. **Historical Analysis**: Track performance trends and regressions
5. **User Segmentation**: Performance metrics by user type or device
