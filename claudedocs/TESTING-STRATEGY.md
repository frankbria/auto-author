# Testing Strategy - Multi-Layer Approach

**Purpose**: Ensure quality at every stage from development to production

---

## Testing Layers

### Layer 1: CI Unit & Integration Tests (GitHub Actions)
**Triggers**: Every commit, every PR
**Duration**: ~3-5 minutes
**Coverage**: 183 tests

**What's Tested**:
- ✅ Frontend: Lint, typecheck, unit tests, build validation
- ✅ Backend: Unit tests, integration tests (with MongoDB)
- ✅ No external API dependencies (OpenAI, real Clerk auth)

**Location**: `.github/workflows/test-suite.yml`

**Run Locally**:
```bash
# Frontend
cd frontend
npm run lint
npm run typecheck
npm test

# Backend
cd backend
uv run pytest tests/ \
  --ignore=tests/test_debug_chapter_questions.py \
  --ignore=tests/test_debug_questions.py \
  --ignore=tests/test_e2e_no_mocks.py \
  -k "not test_generate_toc_endpoint and not test_toc_generation_workflow_e2e"
```

---

### Layer 2: Staging Deployment (Automated)
**Triggers**: Merge to `main` branch
**Duration**: ~5-8 minutes
**Environment**: dev.autoauthor.app

**What Happens**:
1. CI tests pass
2. Build frontend with staging env vars
3. Deploy to staging server (47.88.89.175)
4. Health checks (backend, frontend, CORS)
5. Smoke tests (API docs endpoint)

**Location**: `.github/workflows/deploy-staging.yml`

**Health Check**:
```bash
curl https://api.dev.autoauthor.app/api/v1/health
curl https://dev.autoauthor.app
```

---

### Layer 3: E2E Tests on Staging (Automated After Deployment)
**Triggers**: After successful staging deployment OR manual trigger
**Duration**: ~10-15 minutes
**Coverage**: Full user journeys + OpenAI integration

**What's Tested**:
- ✅ **Playwright E2E suite**: Complete user workflows
  - Authentication flow
  - Book creation
  - Summary → TOC wizard → Chapters → Export
- ✅ **Backend E2E tests with real OpenAI API**:
  - `test_e2e_no_mocks.py` - Complete system workflow
  - `test_debug_chapter_questions.py` - Chapter question generation
  - `test_debug_questions.py` - TOC question generation
  - `test_generate_toc_endpoint` - TOC generation with OpenAI
  - `test_toc_generation_workflow_e2e` - Full TOC workflow

**Location**: `.github/workflows/e2e-staging.yml`

**Run Manually**:
```bash
# Trigger via GitHub UI:
Actions → E2E Tests on Staging → Run workflow

# Or via GitHub CLI:
gh workflow run e2e-staging.yml
```

**Required Secrets** (add to staging environment):
- `OPENAI_API_KEY` - Your OpenAI API key

---

### Layer 4: Manual Validation on Staging (Human Testing)
**Triggers**: After E2E tests pass
**Duration**: 20-30 minutes
**Coverage**: Full feature set + edge cases

**What to Test**:
Follow: `claudedocs/DEPLOYMENT-TESTING-CHECKLIST.md`

**Key Workflows**:
1. Authentication (Clerk sign-up/sign-in)
2. Book CRUD operations
3. Summary creation with validation
4. TOC wizard (readiness → Q&A → generation)
5. Chapter editing with AI drafts
6. Voice input integration
7. Export to PDF/DOCX
8. Delete book with type-to-confirm
9. Auto-save with offline resilience

**Performance Budgets**:
- TOC Generation: <3s
- Export: <5s
- Auto-save: <1s
- Navigation: <500ms

---

### Layer 5: Production Deployment (Tag-Triggered)
**Triggers**: Git tag creation (`v*`) OR GitHub Release
**Duration**: ~10-15 minutes
**Environment**: autoauthor.app (TBD)

**Pre-Flight Checks**:
1. Full test suite (183 tests)
2. Security audit (npm audit, safety check)
3. Check for TODO/FIXME comments
4. Manual approval required

**Location**: `.github/workflows/deploy-production.yml`

**Create Release**:
```bash
# After staging validation passes:
git tag v1.0.0
git push origin v1.0.0

# Or create GitHub Release via UI
```

---

## Test Categorization

### ✅ Fast Tests (CI - Every Commit)
**Duration**: 3-5 minutes
**No external APIs**

```python
# Backend example:
@pytest.mark.unit
def test_book_creation_logic():
    # Pure logic, no external calls
    ...

@pytest.mark.integration
def test_book_api_with_mock_db():
    # Uses test MongoDB, no OpenAI
    ...
```

```typescript
// Frontend example:
describe('BookForm', () => {
  it('validates input fields', () => {
    // Pure UI logic, no API calls
  });
});
```

---

### 🐌 Slow Tests (Staging E2E - After Deployment)
**Duration**: 10-15 minutes
**Uses real external APIs**

```python
# Backend example:
@pytest.mark.e2e
@pytest.mark.slow
def test_toc_generation_with_openai():
    # Calls real OpenAI API
    response = client.post("/api/v1/books/{id}/generate-toc")
    assert response.status_code == 200
```

```typescript
// Frontend example (Playwright):
test('complete authoring journey', async ({ page }) => {
  // Full user flow with real backend
  await page.goto('https://dev.autoauthor.app');
  // ... complete workflow
});
```

---

## Running Tests Locally

### All Fast Tests (Pre-Commit)
```bash
# Frontend
cd frontend
npm run lint
npm run typecheck
npm test

# Backend
cd backend
uv run pytest tests/ \
  --ignore=tests/test_debug_chapter_questions.py \
  --ignore=tests/test_debug_questions.py \
  --ignore=tests/test_e2e_no_mocks.py \
  -k "not test_generate_toc_endpoint and not test_toc_generation_workflow_e2e"
```

### Specific E2E Tests (Requires OpenAI API Key)
```bash
# Backend E2E with OpenAI
cd backend
export OPENAI_AUTOAUTHOR_API_KEY=your-key-here
uv run pytest tests/test_e2e_no_mocks.py -v

# Frontend E2E with Playwright
cd frontend
npx playwright test --ui
```

### All Tests (Including Slow)
```bash
# Backend (all tests)
cd backend
export OPENAI_AUTOAUTHOR_API_KEY=your-key-here
uv run pytest tests/ -v

# Frontend E2E
cd frontend
npx playwright test
```

---

## Adding New Tests

### When to Add CI Tests (Fast)
- New business logic functions
- New API endpoints (with mocked external calls)
- New UI components
- Data validation logic
- Error handling

### When to Add E2E Tests (Slow)
- New user-facing workflows
- Integration with external APIs (OpenAI, Clerk)
- Multi-step processes (TOC wizard, export)
- Critical user journeys

---

## Test Metrics

### Current Coverage

| Layer | Tests | Duration | Frequency |
|-------|-------|----------|-----------|
| CI Fast Tests | 183 | 3-5 min | Every commit |
| Staging Deploy | Health checks | 5-8 min | Every merge to main |
| E2E Staging | ~20 tests | 10-15 min | After staging deploy |
| Manual Validation | Full checklist | 20-30 min | Before production |
| Production Deploy | Same as staging | 10-15 min | On tag creation |

### Coverage Goals
- Unit/Integration: **85%** (current target)
- E2E Critical Paths: **100%** (main user journeys)
- Manual Validation: **100%** (before production release)

---

## Continuous Improvement

### Adding OpenAI API Key to Staging E2E

To enable automated E2E tests with OpenAI:

1. **Get OpenAI API Key**:
   - Go to: https://platform.openai.com/api-keys
   - Create new key for staging testing

2. **Add to GitHub Secrets**:
   ```
   Settings → Environments → staging → Environment secrets
   Name: OPENAI_API_KEY
   Value: sk-proj-...
   ```

3. **Enable Workflow**:
   ```bash
   # The e2e-staging.yml workflow will automatically run
   # after successful staging deployments
   ```

### Monitoring Test Health

**GitHub Actions**:
- https://github.com/frankbria/auto-author/actions
- Monitor test success rates
- Watch for flaky tests

**Local Development**:
```bash
# Run tests with coverage
cd backend
uv run pytest --cov=app --cov-report=html

# Open coverage report
open htmlcov/index.html
```

---

## Quick Reference

### Test Commands

```bash
# Fast CI tests (run before commit)
npm test                    # Frontend
pytest tests/ -m "not slow" # Backend

# Slow E2E tests (run before production)
npx playwright test         # Frontend E2E
pytest tests/test_e2e*.py   # Backend E2E with OpenAI

# All tests
npm run test:ci             # Frontend all
pytest tests/               # Backend all
```

### Workflow URLs

- **CI Tests**: https://github.com/frankbria/auto-author/actions/workflows/test-suite.yml
- **Staging Deploy**: https://github.com/frankbria/auto-author/actions/workflows/deploy-staging.yml
- **E2E Staging**: https://github.com/frankbria/auto-author/actions/workflows/e2e-staging.yml
- **Production Deploy**: https://github.com/frankbria/auto-author/actions/workflows/deploy-production.yml

---

## Summary

**3-Layer Testing Approach**:
1. **Fast CI** (3-5 min) → Every commit → 183 tests, no external APIs
2. **Staging E2E** (10-15 min) → After deployment → Real APIs, full workflows
3. **Manual Validation** (20-30 min) → Before production → Human verification

**Result**: High confidence in code quality at every stage, from development to production deployment. 🚀
