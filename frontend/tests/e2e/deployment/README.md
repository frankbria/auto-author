# Deployment Testing Infrastructure

## Overview

This directory contains automated deployment validation tests for Auto-Author. These tests verify the complete user journey from authentication through book export, ensuring all critical features work correctly in production.

**Status**: Phase 1 Complete ✅

**Coverage**: Foundation infrastructure (config, fixtures, helpers, page objects)

## What Was Built (Phase 1)

### Directory Structure

```
tests/e2e/
├── deployment/
│   ├── playwright.config.ts      # Deployment-specific Playwright config
│   └── README.md                 # This file
├── fixtures/
│   ├── auth.fixture.ts           # Clerk authentication helpers
│   ├── test-data.fixture.ts      # Static test data (book, summary, TOC)
│   └── performance.fixture.ts    # Performance budgets & measurement
├── helpers/
│   ├── console-monitor.ts        # Browser console error detection
│   ├── network-monitor.ts        # API call tracking & validation
│   └── csp-validator.ts          # CSP header validation
├── page-objects/
│   ├── auth.page.ts              # Homepage & authentication
│   ├── dashboard.page.ts         # Dashboard & book list
│   └── book-form.page.ts         # Create/edit book forms
└── artifacts/                    # Test outputs (screenshots, videos, reports)
```

### Key Features

#### 1. Playwright Configuration
- **Sequential execution** for realistic user journey simulation
- **120-second timeout** for AI operations (TOC, draft generation)
- **Retry logic** (2 retries) for reliability
- **Rich reporting** (HTML, JSON, console output)
- **Failure artifacts** (screenshots, videos, traces)

#### 2. Test Data Fixtures
All test data sourced from `DEPLOYMENT-TESTING-CHECKLIST.md`:
- Book metadata (title, description, genre, target audience)
- Book summary (558 characters)
- TOC wizard Q&A responses
- Chapter Q&A for draft generation
- Field validation constraints

#### 3. Authentication
- Clerk authentication flow automation
- Environment-based credentials
- Sign-in and sign-out helpers
- Auth token verification

#### 4. Performance Monitoring
- **Performance budgets**:
  - TOC Generation: <3000ms
  - Export (PDF/DOCX): <5000ms
  - Auto-save: <1000ms
  - Page Navigation: <500ms
- **Core Web Vitals**:
  - LCP (Largest Contentful Paint): <2.5s
  - CLS (Cumulative Layout Shift): <0.1
- Performance measurement utilities

#### 5. Test Helpers
- **Console Monitor**: Detects console errors, CORS errors, CSP violations
- **Network Monitor**: Tracks API calls, validates responses, checks auth headers
- **CSP Validator**: Validates Content Security Policy headers

#### 6. Page Objects
Clean abstraction layer for UI interactions:
- **AuthPage**: Homepage, Clerk authentication
- **DashboardPage**: Book list, navigation
- **BookFormPage**: Create/edit books, form validation

## Setup

### 1. Environment Configuration

Copy the example environment file:

```bash
cp tests/e2e/.env.deployment.example tests/e2e/.env.deployment
```

Edit `.env.deployment` with your test credentials:

```env
DEPLOYMENT_URL=https://dev.autoauthor.app
TEST_USER_EMAIL=your-test-user@autoauthor.app
TEST_USER_PASSWORD=your-secure-password
```

### 2. Test Account Setup

Create a dedicated test account in Clerk:
1. Sign up at your deployment URL
2. Use a dedicated email (e.g., `test-deploy@autoauthor.app`)
3. Save credentials in `.env.deployment`

## Running Tests

### Local Development

```bash
# Run all deployment tests
npm test -- tests/e2e/deployment/

# Run with UI mode (debugging)
npx playwright test tests/e2e/deployment/ --ui

# Run specific test file
npx playwright test tests/e2e/deployment/01-preflight.spec.ts

# View test report
npx playwright show-report tests/e2e/artifacts/reports/
```

### CI/CD

Tests will run automatically via GitHub Actions (Phase 3).

## Next Steps (Phase 2 & 3)

### Phase 2: Core Test Suites (In Progress)
- [ ] Create `01-preflight.spec.ts` (API health checks)
- [ ] Create `02-user-journey.spec.ts` (book creation → export)
- [ ] Create `03-advanced-features.spec.ts` (auto-save, delete, voice)
- [ ] Create `04-security-performance.spec.ts` (CSP, Core Web Vitals)
- [ ] Create `05-regression.spec.ts` (critical flows)
- [ ] Create `06-export-validation.spec.ts` (PDF/DOCX validation)

### Phase 3: Integration & CI/CD
- [ ] Create GitHub Actions workflow
- [ ] Add export file validation (PDF/DOCX parsing)
- [ ] Create test reporting dashboard
- [ ] Add Lighthouse integration
- [ ] Set up artifact storage (S3)

## Architecture Decisions

### Why Sequential Execution?
Deployment tests simulate real user journeys. Running tests in parallel would:
1. Create race conditions with shared test data
2. Make debugging harder (interleaved logs)
3. Not reflect real user behavior

### Why 120s Timeout?
AI operations (TOC generation, draft generation) can take 15-60 seconds. The 120s timeout provides headroom for:
- Network latency
- Server load variations
- AI processing time

### Why Page Objects?
Page Objects provide:
1. **Reusability**: Shared UI interactions across tests
2. **Maintainability**: UI changes update in one place
3. **Readability**: Tests read like user actions

## Troubleshooting

### Authentication Fails
- **Verify credentials**: Check `.env.deployment` has correct values
- **Check Clerk config**: Ensure test account exists
- **Review console**: Check for CSP/CORS errors

### Network Errors
- **CORS**: Verify backend CORS configuration
- **CSP**: Check Content Security Policy headers
- **Auth headers**: Ensure Bearer tokens are included

### Performance Budget Failures
- **Network throttling**: Disable for accurate measurements
- **Server load**: Run during low-traffic periods
- **Increase budgets**: Adjust in `performance.fixture.ts` if needed

## Related Documentation

- **Implementation Plan**: `/claudedocs/DEPLOYMENT_AUTOMATION_PLAN.md`
- **Test Checklist**: `/claudedocs/DEPLOYMENT-TESTING-CHECKLIST.md`
- **Main Playwright Config**: `/frontend/playwright.config.ts`

## Contact

For questions or issues with deployment testing:
1. Check implementation plan: `claudedocs/DEPLOYMENT_AUTOMATION_PLAN.md`
2. Review test checklist: `claudedocs/DEPLOYMENT-TESTING-CHECKLIST.md`
3. Create a GitHub issue with `[deployment-tests]` tag

---

**Phase 1 Status**: ✅ Complete
**Next Milestone**: Phase 2 - Core Test Suites
**Est. Completion**: Phase 2 (24 hours), Phase 3 (16 hours)
