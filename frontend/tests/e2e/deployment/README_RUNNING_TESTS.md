# Running E2E Deployment Tests

This directory contains comprehensive end-to-end tests that validate the complete user experience across the Auto-Author platform.

## Prerequisites

These tests require a **fully running environment** with real API access:

1. **✅ Backend API**: `python -m uvicorn app.main:app --reload`
   - Must be running on `http://localhost:8000`
   - MongoDB connection must be active
   - All environment variables configured (`.env`)

2. **✅ Frontend Dev Server**: `npm run dev`
   - Must be running on `http://localhost:3000`
   - Connected to backend API

3. **✅ MongoDB**: Running locally or MongoDB Atlas
   - Collections initialized
   - Test data can be created/destroyed

4. **✅ OpenAI API Access**: Valid API key in backend `.env`
   - Required for AI draft generation tests
   - Tests make real API calls (not mocked)

5. **✅ Clerk Authentication**: Configured for development
   - Test user created
   - Or use `BYPASS_AUTH=true` for testing

## Running Tests

### Run All Deployment Tests

```bash
# From frontend directory
npm run test:e2e:deployment

# Or using playwright directly
npx playwright test --config=tests/e2e/deployment/playwright.config.ts
```

### Run Specific Test Suite

```bash
# Run writing styles tests only (7 tests, ~6-8 minutes)
npx playwright test --config=tests/e2e/deployment/playwright.config.ts 06-draft-writing-styles

# Run custom questions tests only (4 tests, ~4-5 minutes)
npx playwright test --config=tests/e2e/deployment/playwright.config.ts 07-draft-custom-questions

# Run a specific test within a suite
npx playwright test --config=tests/e2e/deployment/playwright.config.ts 06-draft-writing-styles -g "Conversational"
```

### Run with UI Mode (Recommended for Development)

```bash
# See tests execute in real-time with browser automation
npx playwright test --config=tests/e2e/deployment/playwright.config.ts 06-draft-writing-styles --ui
```

### Run with Authentication Bypass

```bash
# For testing without real Clerk authentication
BYPASS_AUTH=true npx playwright test --config=tests/e2e/deployment/playwright.config.ts
```

## Test Suites

### 06-draft-writing-styles.spec.ts (7 tests)
**Issue**: auto-author-15k
**Duration**: ~6-8 minutes
**Tests**:
- 6 individual writing style validations (Conversational, Formal, Educational, Technical, Narrative, Inspirational)
- 1 comparison test across multiple styles

**Validates**:
- ✅ Each style produces appropriate tone and language
- ✅ Draft generation completes within 60-second budget
- ✅ Drafts are distinct across styles
- ✅ Word counts are consistent
- ✅ No console errors or 500 responses

### 07-draft-custom-questions.spec.ts (4 tests)
**Issue**: auto-author-bo7
**Duration**: ~4-5 minutes
**Tests**:
- Add custom questions and generate draft
- Remove default questions, use only custom
- Edit custom question text after adding
- Generate draft with mix of default and custom questions

**Validates**:
- ✅ Users can add custom questions
- ✅ Users can remove default questions
- ✅ Custom Q&A content appears in generated draft
- ✅ Draft generation works with customized questions
- ✅ No console errors or 500 responses

## Test Execution Notes

### Expected Test Duration
- **06-draft-writing-styles**: 6-8 minutes (7 drafts × 60s max each)
- **07-draft-custom-questions**: 4-5 minutes (4 drafts × 60s max each)
- **Both suites**: ~10-13 minutes total

### Performance Budgets
All tests validate against these budgets:
- **Draft Generation**: <60,000ms (60 seconds) per draft
- **TOC Generation**: <3,000ms (3 seconds)
- **Export PDF**: <5,000ms (5 seconds)
- **Export DOCX**: <5,000ms (5 seconds)
- **Auto-save**: <1,000ms (after 3s debounce)

### Test Data Cleanup
Tests create real books and chapters in the database. Each test suite uses unique book titles with timestamps to avoid conflicts.

**Cleanup Strategy**:
- Tests create: `"Test Book Name TIMESTAMP"`
- MongoDB can be cleared periodically with: `db.books.deleteMany({title: /Test/})`
- Or use a separate test database

## Debugging Failed Tests

### View Test Execution Traces
```bash
# Run tests with trace enabled
npx playwright test --config=tests/e2e/deployment/playwright.config.ts --trace on

# View trace after test
npx playwright show-report
```

### Run in Headed Mode (See Browser)
```bash
# Run with visible browser
npx playwright test --config=tests/e2e/deployment/playwright.config.ts --headed
```

### Increase Timeout for Debugging
```bash
# Increase timeout to 5 minutes per test
npx playwright test --config=tests/e2e/deployment/playwright.config.ts --timeout=300000
```

### Common Issues

**1. Test Hangs During Draft Generation**
- **Cause**: OpenAI API timeout or backend not responding
- **Fix**: Check backend logs, verify OpenAI API key is valid

**2. "Generate Draft" Button Not Found**
- **Cause**: Frontend UI may have changed
- **Fix**: Update test selectors to match current UI

**3. Authentication Failures**
- **Cause**: Clerk not configured or BYPASS_AUTH not set
- **Fix**: Set `BYPASS_AUTH=true` or configure Clerk test user

**4. Database Connection Errors**
- **Cause**: MongoDB not running
- **Fix**: Start MongoDB: `sudo systemctl start mongodb`

## CI/CD Integration

These tests should run:
1. **On Pull Requests** (targeting main/develop)
2. **Before Deployment** (as part of deployment checklist)
3. **On Schedule** (nightly regression suite)

**GitHub Actions Example**:
```yaml
- name: Run E2E Deployment Tests
  run: |
    cd frontend
    npm install
    npx playwright install --with-deps chromium
    npm run test:e2e:deployment
  env:
    BYPASS_AUTH: true
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

## Test Reporting

Results are output to:
- **Console**: Real-time test progress
- **HTML Report**: `playwright-report/index.html`
- **JSON Report**: `test-results/results.json`

View HTML report:
```bash
npx playwright show-report
```

## Contributing New E2E Tests

When adding new E2E tests to this suite:

1. **Follow naming convention**: `NN-feature-name.spec.ts`
2. **Include issue reference**: Add issue number in test header
3. **Estimate duration**: Document expected test duration
4. **Use fixtures**: Import from `fixtures/` directory
5. **Use page objects**: Import from `page-objects/` directory
6. **Validate performance**: Use `measureOperation()` for timed operations
7. **Check for errors**: Use `ConsoleMonitor` and `NetworkMonitor`
8. **Document test coverage**: List what the test validates

See existing tests (06, 07) for examples.

## Related Documentation

- **Gap Analysis**: `/docs/E2E_TEST_COVERAGE_GAP_ANALYSIS.md`
- **Test Infrastructure**: `/docs/references/testing-infrastructure.md`
- **Performance Monitoring**: `/docs/references/performance-monitoring.md`
- **Quality Standards**: `/docs/references/quality-standards.md`
