# E2E Test Failure Analysis - December 4, 2025

## Executive Summary

After removing the `BYPASS_AUTH` security vulnerability, E2E tests were run against the staging environment (`https://dev.autoauthor.app`) using real Clerk authentication. **Authentication works correctly** (users can log in via Clerk), but **API calls fail with 401 errors** because the JWT token is not being passed to the backend API.

### Test Results Summary

| Category | Passing | Failing | Skipped |
|----------|---------|---------|---------|
| Pre-flight Health Checks | 7 | 0 | 0 |
| User Journey | 0 | 8 | 0 |
| Advanced Features | 1 | 7 | 0 |
| Security & Performance | 4 | 8 | 0 |
| Regression | 0 | 31+ | 0 |
| **TOTAL** | **12** | **54+** | **0** |

**Pass Rate: ~18%** (12/66 tests)

---

## Passing Tests (12)

### Pre-Flight Health Checks (7/7) ✅
1. Backend API Health - 303ms
2. CORS Configuration - Frontend to API - 47ms
3. API Books Endpoint - Reachable - 43ms
4. Frontend - Loads Without Errors - 1.5s
5. CSP Headers - Frontend - 125ms
6. CSP Headers - Backend API Docs - 44ms
7. Swagger UI - Loads Without Errors - 1.2s

### Advanced Features (1/8) ✅
- Voice input: Browser Speech API availability - 5.5s

### Security & Performance (4/12) ✅
- CSP Headers: Frontend (Next.js) - 455ms
- CSP Headers: Backend API Docs (Swagger UI) - 1.2s
- LCP (Largest Contentful Paint) < 2.5s - **772ms** ✅
- CLS (Cumulative Layout Shift) < 0.1 - **0.000** ✅

---

## Failing Tests - Root Cause Analysis

### Category 1: JWT Token Not Passed to API (BLOCKER)

**Affected Tests:** ~45 tests (all tests requiring book creation/manipulation)

**Symptoms:**
- Clerk authentication succeeds (user logs in, redirects to dashboard)
- API calls to `https://api.dev.autoauthor.app/api/v1/books/` fail with 401
- Error message: `{"detail":"Missing authentication credentials"}`

**Example Error:**
```
✅ User authenticated successfully
✅ Book form filled with test data
⚠️ Failed Request: 401  - https://api.dev.autoauthor.app/api/v1/books/
❌ Browser Error: Error creating book: Error: Failed to create book: 401 {"detail":"Missing authentication credentials"}
    at s.createBook (https://dev.autoauthor.app/_next/static/chunks/391-b9ed32c012233eb1.js:1:1200)
```

**Root Cause:**
The frontend's `bookClient` is not receiving or passing the JWT token from Clerk to API requests. The token provider pattern (`bookClient.setTokenProvider(getToken)`) may not be:
1. Initialized correctly on page load
2. Waiting for Clerk to provide the token
3. Including the token in API request headers

**Affected Test Files:**
- `02-user-journey.spec.ts` (8 tests)
- `03-advanced-features.spec.ts` (6 tests)
- `04-security-performance.spec.ts` (6 tests)
- `05-regression.spec.ts` (25+ tests)

**Fix Required:**
1. Investigate `frontend/src/lib/bookClient.ts` - token provider setup
2. Check if `getToken()` is returning undefined
3. Verify Authorization header is being set on API requests
4. May need to add await/initialization for Clerk session

---

### Category 2: Playwright Fixture Error

**Affected Tests:** 3 tests (Auto-save functionality)

**Symptoms:**
```
Internal error: step id not found: fixture@42
Internal error: step id not found: fixture@50
```

**Tests Affected:**
- Auto-save: Normal Operation (3s debounce)
- Auto-save: Network Failure with localStorage Backup
- Auto-save: Rapid Typing (debounce resets)

**Root Cause:**
Playwright internal fixture reference error. This appears to be a test infrastructure issue, not application code.

**Fix Required:**
- Review `03-advanced-features.spec.ts` fixture setup
- May need to update Playwright version or refactor fixtures

---

### Category 3: Performance Budget Failures

**Affected Tests:** 2 tests

#### FID (First Input Delay) Simulation
- **Result:** 6.6-6.8s
- **Budget:** Not specified, but test failing
- **Location:** `04-security-performance.spec.ts:146`

#### Page Navigation
- **Result:** 985-1090ms
- **Budget:** 500ms
- **Location:** `04-security-performance.spec.ts:168`

**Root Cause:**
Performance issues on staging environment, possibly due to:
1. Network latency
2. Initial Clerk authentication overhead
3. Server cold starts

**Note:** These failures are secondary to the JWT issue. Once API calls work, actual page content loads may be faster.

---

## Fix Priority

### P0 - Critical (Blocks all other tests)
1. **JWT Token Passing Issue**
   - Investigate token provider pattern in bookClient
   - Ensure Clerk `getToken()` returns valid JWT
   - Verify Authorization header is set on API requests

### P1 - High Priority
2. **Playwright Fixture Error**
   - Review fixture setup in auto-save tests
   - Update test infrastructure if needed

### P2 - Medium Priority
3. **Performance Budget**
   - Adjust budgets for staging environment
   - Or optimize initial load/navigation

---

## Recommended Next Steps

### Immediate (for next session):

1. **Debug Token Flow:**
   ```typescript
   // Add logging to see what's happening
   const token = await getToken();
   console.log('Token present:', !!token);
   console.log('Token preview:', token?.substring(0, 20) + '...');
   ```

2. **Check Network Tab:**
   - Manually test in browser with DevTools open
   - Verify Authorization header is present on API requests
   - Compare with successful local requests

3. **Review BookClient Initialization:**
   - Check `frontend/src/lib/bookClient.ts`
   - Ensure token provider is set BEFORE any API calls
   - May need to await Clerk session initialization

4. **Verify Staging Deployment:**
   - Confirm latest frontend code is deployed
   - Check if any auth-related code was missed in deployment

### Files to Review:
- `frontend/src/lib/bookClient.ts` - Token provider setup
- `frontend/src/app/dashboard/new-book/page.tsx` - Where createBook is called
- `frontend/src/hooks/useClerkToken.ts` - If exists, token retrieval hook
- `frontend/src/app/layout.tsx` - Clerk provider setup

---

## Environment Details

- **Test Target:** https://dev.autoauthor.app (staging)
- **API:** https://api.dev.autoauthor.app
- **Test Date:** December 4, 2025
- **Playwright Version:** See `frontend/package.json`
- **Branch:** `feature/p0-blockers-quick-wins`
- **Commit:** `78fba2d` (BYPASS_AUTH removal)

---

## Appendix: Full Test List

### Pre-Flight (7 tests) - 7 passing
| # | Test | Status | Time |
|---|------|--------|------|
| 1 | Backend API Health | ✅ | 303ms |
| 2 | CORS Configuration | ✅ | 47ms |
| 3 | API Books Endpoint | ✅ | 43ms |
| 4 | Frontend Loads | ✅ | 1.5s |
| 5 | CSP Headers Frontend | ✅ | 125ms |
| 6 | CSP Headers API | ✅ | 44ms |
| 7 | Swagger UI | ✅ | 1.2s |

### User Journey (8 tests) - 0 passing
| # | Test | Status | Reason |
|---|------|--------|--------|
| 8-10 | Create Book with Metadata | ❌ | 401 JWT |
| 11 | Add Book Summary | ❌ | Skipped (depends on 8) |
| 12 | Generate TOC | ❌ | Skipped |
| 13 | View Book with TOC | ❌ | Skipped |
| 14 | Chapter Editor | ❌ | Skipped |
| 15 | AI Draft Generation | ❌ | Skipped |
| 16 | Chapter Tabs | ❌ | Skipped |
| 17 | Export Book | ❌ | Skipped |

### Advanced Features (8 tests) - 1 passing
| # | Test | Status | Reason |
|---|------|--------|--------|
| 18-26 | Auto-save tests | ❌ | Fixture error |
| 27-35 | Delete Book tests | ❌ | 401 JWT |
| 36-38 | Voice Input UI | ❌ | 401 JWT |
| 39 | Speech API availability | ✅ | Works |

### Security & Performance (12 tests) - 4 passing
| # | Test | Status | Reason |
|---|------|--------|--------|
| 40 | CSP Frontend | ✅ | |
| 41 | CSP Swagger | ✅ | |
| 42-44 | CSP Monitor Journey | ❌ | 401 JWT |
| 45 | LCP | ✅ | 772ms |
| 46 | CLS | ✅ | 0.000 |
| 47-49 | FID | ❌ | Performance |
| 50-52 | Page Navigation | ❌ | 985-1090ms |
| 53-64 | Performance Budgets | ❌ | 401 JWT |

### Regression (31+ tests) - 0 passing
All require book creation, blocked by JWT issue.
