# Performance Budgets - Environment-Aware Strategy

## Overview

This document explains the performance budget strategy for the auto-author application, including how budgets differ between production and staging environments.

## Why Environment-Specific Budgets?

**Problem:** Staging environment runs on shared VPS with different characteristics than production:
- Shared CPU/memory resources (resource contention)
- No CDN (slower static asset delivery)
- Higher network latency (remote server vs local)
- Cold starts for backend services
- Clerk authentication overhead (remote auth flow)

**Solution:** Separate budgets for staging vs production that:
- Still catch real performance regressions
- Account for infrastructure differences
- Prevent false failures due to environment overhead

## Budget Philosophy

### Production Budgets (Target Values)
These represent **optimal performance** on production infrastructure:
- CDN for static assets
- Dedicated resources
- Optimized routing
- Warm backend services

### Staging Budgets (Realistic Values)
These account for **staging environment overhead** (~2-3x more lenient):
- Shared VPS resources
- Network latency
- No CDN
- Cold starts

**Important:** Staging budgets still catch regressions. If staging performance degrades 50%+, it will fail even with lenient budgets.

## Performance Budgets by Category

### Core Web Vitals

| Metric | Production | Staging | Rationale |
|--------|-----------|---------|-----------|
| **LCP** (Largest Contentful Paint) | 2500ms | 3500ms | +1s for slower asset delivery (no CDN) |
| **CLS** (Cumulative Layout Shift) | 0.1 | 0.1 | Same - layout stability unaffected by environment |
| **FID** (First Input Delay) | 100ms | 200ms | +100ms for shared CPU resources |

### User Interface Operations

| Operation | Production | Staging | Rationale |
|-----------|-----------|---------|-----------|
| **Page Navigation** | 500ms | 1500ms | +1s for network latency, no CDN<br>*(Actual staging: 985-1090ms)* |
| **Clerk Modal Open** | 3000ms | 10000ms | +7s for remote auth flow<br>*(Actual staging: 6.6-6.8s)* |
| **Auto-save** | 1000ms | 2000ms | +1s for network round-trip |

### AI/Backend Operations

| Operation | Production | Staging | Rationale |
|-----------|-----------|---------|-----------|
| **TOC Generation** | 3000ms | 5000ms | +2s for network/compute overhead |
| **Draft Generation** | 60000ms | 90000ms | +30s for LLM API calls from remote server |
| **PDF Export** | 5000ms | 8000ms | +3s for file generation on shared resources |
| **DOCX Export** | 5000ms | 8000ms | +3s for file generation on shared resources |

## Automatic Environment Detection

The test suite **automatically detects** the environment and applies appropriate budgets:

```typescript
// In performance.fixture.ts
function isStagingEnvironment(): boolean {
  const deploymentUrl = process.env.DEPLOYMENT_URL || '';
  return deploymentUrl.includes('dev.autoauthor.app') || deploymentUrl.includes('staging');
}

export const PERFORMANCE_BUDGETS = isStagingEnvironment()
  ? STAGING_BUDGETS
  : PRODUCTION_BUDGETS;
```

**Detection Logic:**
- If `DEPLOYMENT_URL` contains `dev.autoauthor.app` or `staging` → use staging budgets
- Otherwise → use production budgets

**Running Tests:**
```bash
# Staging (auto-detected)
DEPLOYMENT_URL=https://dev.autoauthor.app npx playwright test

# Production (auto-detected)
DEPLOYMENT_URL=https://autoauthor.app npx playwright test

# Local (uses production budgets as baseline)
npx playwright test
```

## Important Distinctions

### FID vs Clerk Modal Opening

**Before Fix:** The FID test was incorrectly measuring Clerk modal opening time (6-8s), not true First Input Delay.

**After Fix:**
1. **FID Test** - Measures browser responsiveness (should be <200ms staging, <100ms production)
2. **Clerk Modal Test** - Separate test for full authentication modal flow (6-8s staging, 3s production)

**Why This Matters:**
- FID is a Core Web Vital measuring user experience
- Modal opening time is an operational metric
- Conflating them creates false failures and misunderstanding

## Monitoring Strategy

### When Tests Fail

**If staging test fails:**
1. Check actual timing vs budget
2. If within 20% of budget → environment variance (acceptable)
3. If exceeds budget by 50%+ → real regression (investigate)

**If production test fails:**
1. Immediate investigation required
2. Production budgets are tight - failures indicate real issues

### Regression Detection

**Example - Page Navigation:**
- Production budget: 500ms
- Staging budget: 1500ms
- Actual staging: 985-1090ms ✅

**If staging jumps to 2000ms:**
- Still faster than old FID confusion (6-8s)
- But **exceeds staging budget** → regression detected ✅
- Alert triggered even with lenient staging budget

## Future Optimization Path

### Phase 1: Staging (Current)
- Budgets: Lenient for shared VPS
- Goal: Catch major regressions
- Status: ✅ Implemented

### Phase 2: Production Deployment
- Budgets: Tight for optimized infrastructure
- Goal: Meet Core Web Vitals "Good" ratings
- Status: 🚧 Pending production infrastructure

### Phase 3: Continuous Monitoring
- Real User Monitoring (RUM)
- Performance trends over time
- Automatic alerts on degradation
- Status: 📋 Planned

## Configuration Files

**Budget Definitions:**
- `frontend/tests/e2e/fixtures/performance.fixture.ts`

**Usage in Tests:**
- `frontend/tests/e2e/deployment/04-security-performance.spec.ts`
- `frontend/tests/e2e/deployment/02-user-journey.spec.ts`
- `frontend/tests/e2e/deployment/03-advanced-features.spec.ts`

## References

- [Web Vitals](https://web.dev/vitals/)
- [FID - First Input Delay](https://web.dev/fid/)
- [LCP - Largest Contentful Paint](https://web.dev/lcp/)
- [CLS - Cumulative Layout Shift](https://web.dev/cls/)
- [Performance Budgets](https://web.dev/performance-budgets-101/)

---

**Last Updated:** December 4, 2025
**Status:** ✅ Environment-aware budgets implemented and tested
