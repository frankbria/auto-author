# CI/CD Recovery Plan - Auto-Author Project

**Date:** 2025-10-24
**Status:** CRITICAL - Staging Deployments Blocked
**Author:** CI/CD Pipeline Engineer

---

## Executive Summary

The `develop` branch currently contains premature CI/CD workflow integrations that are causing deployment failures and blocking staging releases. This document provides a comprehensive analysis and step-by-step recovery plan to restore stable staging deployments while isolating failing CI/CD workflows.

### Current State
- ✅ Local tests passing (frontend Jest tests: PASS)
- ✅ Backend tests functional (194 tests collected)
- ✅ CORS issues resolved (deploy.sh script restored)
- ❌ GitHub Actions workflows failing
- ❌ Staging deployments blocked by failed CI/CD
- ⚠️ 29 commits on `develop` ahead of `main`

---

## 1. Workflow Analysis

### 1.1 Current Workflows on `develop` Branch

#### A. `test-suite.yml` (5,353 bytes)
**Purpose:** Run frontend/backend unit tests on PR and push events
**Status:** ⚠️ PARTIALLY FAILING
**Issues Identified:**
- Frontend tests: PASSING locally, may fail in CI due to environment
- Backend tests: Complex Docker/MongoDB setup required
- E2E tests embedded: 10+ minute runtime, currently failing
- Missing CI secret: `CLERK_PUBLISHABLE_KEY_CI_TEST`

**Key Problems:**
```yaml
# Line 59: Uses undefined CI secret
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: ${{ secrets.CLERK_PUBLISHABLE_KEY_CI_TEST }}

# Lines 123-162: E2E tests run AFTER unit tests on develop/main push
# This creates 10+ minute bottleneck in test suite
e2e-tests:
  name: E2E (staging)
  needs: [frontend-tests, backend-tests]
  if: github.event_name == 'push' && (github.ref == 'refs/heads/develop' || github.ref == 'refs/heads/main')
```

#### B. `deploy-staging.yml` (2,535 bytes)
**Purpose:** Deploy to staging server after successful tests
**Status:** ⚠️ DEPENDENT ON FAILING TESTS
**Trigger:** `workflow_run` after `test-suite.yml` completion

**Key Configuration:**
```yaml
on:
  workflow_run:
    workflows: ["Test Suite"]
    types: [completed]
    branches: [develop]
```

**Issues:**
- Blocks on failed `test-suite.yml`
- Requires SSH secrets: `SSH_KEY`, `HOST`, `USER`
- Multiple environment secrets needed
- No manual deployment fallback documented

#### C. `e2e-staging.yml` (4,461 bytes)
**Purpose:** Run comprehensive E2E tests against staging environment
**Status:** ❌ FAILING (10+ minute runtime)
**Trigger:** After successful `deploy-staging.yml` OR manual `workflow_dispatch`

**Issues Identified:**
1. **Playwright E2E Tests:**
   - 10+ minute execution time
   - Running against live staging environment
   - Missing test user credentials: `TEST_USER_EMAIL`, `TEST_USER_PASSWORD`
   - Requires staging environment to be healthy

2. **Backend E2E Tests:**
   - Lines 85-104: Complex backend E2E test suite
   - Tests that bypass mocks (real API calls)
   - Includes OpenAI integration tests (expensive)
   - Local MongoDB required (`mongodb://localhost:27017`)

3. **Cost and Time Implications:**
   - OpenAI API calls in tests: $$$ per run
   - 10+ minutes added to deployment pipeline
   - Blocks rapid iteration on staging

#### D. `deploy-production.yml.disabled` (7,247 bytes)
**Status:** ✅ CORRECTLY DISABLED
**Note:** Production deployment workflow is properly deactivated until staging is stable.

### 1.2 Workflows on `main` Branch (Baseline)

```bash
# On main branch, workflows are in .tbd (to-be-determined) state
deploy-production.tbd
deploy-staging.tbd
test-suite.tbd
```

**Interpretation:** The `main` branch has placeholder workflow files, indicating CI/CD was never activated there. The activation happened directly on `develop` via PR #8 (commit `71f504f`).

---

## 2. Root Cause Analysis

### 2.1 Integration Timeline

```
1. Commit 71f504f (Oct 23): "feat: activate GitHub Actions CI/CD pipeline" (PR #8)
   - Added 3 workflows: test-suite.yml, deploy-staging.yml, e2e-staging.yml
   - Added deploy-production.yml (later disabled in 40a4978)

2. Commits 8066927 - c6aee7f (Oct 23-24): Multiple fixes
   - YAML syntax errors
   - Missing secrets
   - SSH key format issues
   - Environment declarations
   - Clerk configuration problems

3. Commits 68066f9 - bc4adab (Oct 24): CORS and deployment fixes
   - Restored deploy.sh script
   - Fixed backend .env generation
   - Resolved Next.js 15 compatibility issues
```

### 2.2 Why CI/CD is Failing

#### Critical Issues:
1. **Missing GitHub Secrets:**
   - `CLERK_PUBLISHABLE_KEY_CI_TEST` (test-suite.yml:59)
   - `TEST_USER_EMAIL` (e2e-staging.yml:80)
   - `TEST_USER_PASSWORD` (e2e-staging.yml:81)
   - Various deployment secrets may be misconfigured

2. **Economic Inefficiency:**
   - E2E tests with real OpenAI API calls
   - 10+ minute test runtime blocks deployments
   - Should be run separately, not in critical path

3. **Architectural Problems:**
   - E2E tests embedded in test-suite.yml (lines 123-162)
   - Also duplicated in e2e-staging.yml (lines 74-104)
   - No separation between fast unit tests and slow integration tests

4. **Environment Dependencies:**
   - E2E tests require healthy staging environment
   - Circular dependency: deployment blocked by E2E, E2E needs deployment
   - No local E2E validation before pushing

### 2.3 Impact on Staging Deployments

```
Current Flow (BROKEN):
┌─────────────────┐
│  Push to develop│
└────────┬────────┘
         │
         ▼
┌──────────────────────────────┐
│  test-suite.yml              │
│  - Frontend tests: ~2 min    │──❌ FAILS (missing secrets)
│  - Backend tests: ~3 min     │
│  - E2E tests: ~10 min        │
└──────────────┬───────────────┘
               │
               ▼
      ❌ DEPLOYMENT BLOCKED
         (workflow_run failed)
```

---

## 3. Recovery Strategy

### 3.1 Objectives

1. ✅ **Restore Stable Staging Deployments**
   - Remove blocking CI/CD workflows from critical path
   - Enable manual deployments via `deploy.sh`
   - Preserve working code (CORS fixes, etc.)

2. ✅ **Isolate CI/CD Work**
   - Move experimental workflows to dedicated branch
   - Allow iterative fixes without blocking staging
   - Maintain git history for debugging

3. ✅ **Define E2E Test Strategy**
   - Separate fast unit tests from slow E2E tests
   - Run E2E tests locally or post-deployment
   - Avoid expensive OpenAI calls in CI/CD

4. ✅ **Document Manual Deployment Process**
   - Provide clear steps for deploying to staging
   - List required secrets and environment variables
   - Create backup deployment documentation

### 3.2 Recommended Approach

#### Option A: Revert CI/CD Integration (RECOMMENDED)
**Pros:**
- Fast recovery to known stable state
- Preserves CORS fixes and working code
- Clean history with explanatory commit
- Can re-integrate CI/CD properly later

**Cons:**
- Loses CI/CD work temporarily (but preserved in branch)

#### Option B: Fix Workflows in Place
**Pros:**
- Keeps CI/CD active
- Learns from failures

**Cons:**
- Multiple failures to debug simultaneously
- Blocks staging deployments during fixes
- Risk of cascading failures

**Decision:** Choose **Option A** for immediate recovery, then work on CI/CD in isolation.

---

## 4. Step-by-Step Recovery Plan

### Phase 1: Backup Current State (5 minutes)

```bash
# 1. Create backup branch with current develop state
git checkout develop
git branch backup/develop-with-cicd-2025-10-24
git push origin backup/develop-with-cicd-2025-10-24

# 2. Verify backup
git log backup/develop-with-cicd-2025-10-24 --oneline -5

# Expected output:
# cb594cc docs: add comprehensive deployment architecture...
# bc4adab docs: add detailed analysis of CORS error fix
# f11798a fix: restore missing deploy.sh script...
```

### Phase 2: Create CI/CD Isolation Branch (5 minutes)

```bash
# 1. Create dedicated branch for CI/CD work
git checkout -b feature/github-actions-cicd develop
git push -u origin feature/github-actions-cicd

# 2. This branch will contain all CI/CD workflows for iterative fixes
# Can continue working on CI/CD without blocking staging
```

### Phase 3: Revert CI/CD from Develop (10 minutes)

```bash
# 1. Checkout develop
git checkout develop

# 2. Identify commit BEFORE CI/CD activation
# PR #8 was commit 71f504f, so revert to parent commit
git log --oneline -30 | grep -B1 "71f504f"
# Expected: 0433f49 fix: use generic secret names scoped by environment

# 3. Create revert strategy
# We want to keep commits AFTER 71f504f but remove workflow files
# Strategy: Remove workflow .yml files, keep .tbd placeholders

# 4. Remove active workflow files
git rm .github/workflows/test-suite.yml
git rm .github/workflows/deploy-staging.yml
git rm .github/workflows/e2e-staging.yml

# 5. Verify .tbd files still exist
ls -la .github/workflows/*.tbd

# Expected output:
# deploy-production.tbd
# deploy-staging.tbd
# test-suite.tbd

# 6. Commit the removal
git commit -m "revert: remove active CI/CD workflows to restore stable staging deployments

The CI/CD workflows introduced in PR #8 (71f504f) are causing deployment
failures due to missing secrets, long E2E test runtimes, and architectural
issues. This commit removes the active workflows (.yml files) while
preserving:

- All CORS fixes (f11798a, 700cc96)
- deploy.sh script restoration
- Backend .env generation fixes
- Next.js 15 compatibility fixes
- All documentation improvements

CI/CD work is preserved in:
- Branch: feature/github-actions-cicd
- Backup: backup/develop-with-cicd-2025-10-24

This allows staging deployments to proceed via manual deploy.sh execution
while CI/CD workflows are fixed in isolation.

Refs: #8
See: docs/CI_CD_RECOVERY_PLAN.md"

# 7. Push to remote
git push origin develop
```

### Phase 4: Verify Stable State (5 minutes)

```bash
# 1. Check develop branch state
git status
# Expected: On branch develop, nothing to commit

# 2. Verify workflows removed
ls -la .github/workflows/
# Expected: Only .tbd files and .disabled files

# 3. Verify deploy.sh exists
ls -la scripts/deploy.sh
# Expected: -rwxr-xr-x ... scripts/deploy.sh

# 4. Verify local tests still pass
cd frontend && npm test
# Expected: PASS src/__tests__/...

cd ../backend && uv run pytest tests/ --co -q
# Expected: collected 194 items / 5 skipped
```

### Phase 5: Document Manual Deployment (10 minutes)

Create/update deployment documentation with manual process:

```bash
# 1. Create manual deployment guide
# See Section 5 below for content
```

---

## 5. Manual Staging Deployment Process

### 5.1 Prerequisites

**Required Secrets (stored in GitHub Secrets or local .env):**
```bash
# Server Access
HOST=your-staging-server.com
USER=root
SSH_KEY=<private_key_content>

# Application URLs
API_URL=https://api.dev.autoauthor.app
FRONTEND_URL=https://dev.autoauthor.app

# Clerk Authentication
CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
CLERK_WEBHOOK_SECRET=whsec_...

# Database
DATABASE_URI=mongodb://localhost:27017
DATABASE_NAME=auto_author_staging

# OpenAI
OPENAI_API_KEY=sk-...
```

### 5.2 Manual Deployment Steps

```bash
# 1. Ensure you're on develop branch with latest changes
git checkout develop
git pull origin develop

# 2. SSH into staging server
ssh root@your-staging-server.com

# 3. On staging server, pull latest code
cd /opt/auto-author/current
git pull origin develop

# 4. Set environment variables (one-time setup)
# Create a .env.deploy file with all secrets:
cat > /opt/auto-author/.env.deploy << 'EOF'
export API_URL=https://api.dev.autoauthor.app
export FRONTEND_URL=https://dev.autoauthor.app
export CLERK_PUBLISHABLE_KEY=pk_test_...
export CLERK_SECRET_KEY=sk_test_...
export DATABASE_URI=mongodb://localhost:27017
export DATABASE_NAME=auto_author_staging
export OPENAI_API_KEY=sk-...
export CLERK_WEBHOOK_SECRET=whsec_...
EOF

# 5. Source environment variables
source /opt/auto-author/.env.deploy

# 6. Create release directory
RELEASE_ID=$(date +%Y%m%d-%H%M%S)
mkdir -p /opt/auto-author/releases/$RELEASE_ID
rsync -av --exclude='.git' --exclude='node_modules' --exclude='.venv' \
  /opt/auto-author/current/ /opt/auto-author/releases/$RELEASE_ID/

# 7. Run deployment script
cd /opt/auto-author/releases/$RELEASE_ID
bash scripts/deploy.sh /opt/auto-author/releases/$RELEASE_ID

# 8. Verify deployment
curl -f http://localhost:8000/api/v1/health
curl -f http://localhost:3002

# 9. Check external endpoints
curl -f https://api.dev.autoauthor.app/api/v1/health
curl -f https://dev.autoauthor.app
```

### 5.3 Deployment Script Analysis

The `scripts/deploy.sh` script (restored in commit f11798a) performs:

1. **Backend Setup:**
   - Installs Python dependencies via `uv`
   - Creates `.env` file with all required variables
   - Sets up CORS origins correctly

2. **Frontend Setup:**
   - Installs Node.js dependencies (production only)
   - Creates `.env.production` with public variables
   - Builds Next.js application

3. **Service Management:**
   - Updates `/opt/auto-author/current` symlink atomically
   - Restarts PM2 services (backend and frontend)
   - Performs health checks

4. **Cleanup:**
   - Removes old releases (keeps last 5)

**Critical Fix in deploy.sh (line 45-59):**
```bash
# This was the CORS fix from commit 700cc96
echo "==> Creating backend .env file..."
{
    echo "ENVIRONMENT=staging"
    echo "DATABASE_URI=$DATABASE_URI"
    echo "DATABASE_NAME=$DATABASE_NAME"
    echo "OPENAI_AUTOAUTHOR_API_KEY=$OPENAI_API_KEY"
    echo "CLERK_API_KEY=$CLERK_SECRET_KEY"
    echo "CLERK_JWT_PUBLIC_KEY=$CLERK_PUBLISHABLE_KEY"
    echo "CLERK_SECRET_KEY=$CLERK_SECRET_KEY"
    echo "CLERK_FRONTEND_API=https://delicate-ladybird-47.clerk.accounts.dev"
    echo "CLERK_BACKEND_API=https://api.clerk.dev"
    echo "CLERK_JWT_ALGORITHM=RS256"
    echo "CLERK_WEBHOOK_SECRET=${CLERK_WEBHOOK_SECRET:-}"
    echo 'BACKEND_CORS_ORIGINS=["'"$FRONTEND_URL"'","https://dev.autoauthor.app","http://localhost:3000"]'
} > .env
```

**Why This Matters:**
- CORS errors were caused by missing backend `.env` file
- The deploy.sh script now generates this file correctly
- This fix MUST be preserved when re-integrating CI/CD

---

## 6. E2E Test Execution Strategy

### 6.1 Problem Statement

**Current E2E Test Suite:**
- **Runtime:** 10+ minutes
- **Cost:** Uses real OpenAI API ($$$ per run)
- **Location:** Embedded in test-suite.yml (lines 123-162) AND e2e-staging.yml
- **Frequency:** Runs on every push to develop/main

**Economic Analysis:**
```
Current Cost per Deploy:
- E2E test runtime: 10 minutes @ GitHub Actions compute
- OpenAI API calls: ~10 calls @ $0.03 each = $0.30
- MongoDB instance runtime: 5 minutes
- Total time added to deployment: 10+ minutes

If deploying 5x per day:
- Lost developer time: 50 minutes/day
- OpenAI costs: $1.50/day = $45/month
- CI/CD compute: ~$20/month (estimate)
```

### 6.2 Recommended Strategy

#### Tier 1: Fast Unit Tests (CI/CD Critical Path)
**Runtime:** < 5 minutes
**Frequency:** Every PR and push
**Location:** `test-suite.yml` (simplified)

```yaml
name: Fast Tests

on:
  pull_request:
    branches: [develop, main]
  push:
    branches: [develop, main]

jobs:
  frontend-tests:
    # Lint, type check, unit tests, build
    # NO E2E tests here

  backend-tests:
    # Unit tests only
    # Mock all external services
    # NO OpenAI calls
    # NO real database integration tests
```

**What to Include:**
- Linting and type checking
- Unit tests with mocked dependencies
- Build verification (no real secrets needed)
- Fast integration tests (< 30 seconds)

**What to Exclude:**
- E2E tests with Playwright
- Tests requiring real OpenAI API
- Tests requiring real database
- Tests requiring staging environment

#### Tier 2: Integration Tests (Pre-Deployment)
**Runtime:** 5-10 minutes
**Frequency:** Before merging to develop, optional in CI
**Location:** Run locally or in separate workflow

```bash
# Run locally before pushing:
cd frontend
npx playwright test --grep @integration

cd ../backend
uv run pytest tests/integration/ -v
```

**What to Include:**
- Database integration tests (local MongoDB)
- API contract tests
- Component integration tests
- Performance regression tests

#### Tier 3: Full E2E Tests (Post-Deployment)
**Runtime:** 10-20 minutes
**Frequency:** After successful staging deployment
**Location:** Separate workflow with manual trigger

```yaml
name: Post-Deployment E2E

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to test'
        required: true
        default: 'staging'
  schedule:
    # Run nightly at 2 AM
    - cron: '0 2 * * *'

jobs:
  e2e-tests:
    # Run comprehensive E2E suite
    # Test against live staging environment
    # Include OpenAI integration tests
```

**What to Include:**
- Full Playwright E2E test suite
- Backend E2E tests with real APIs
- User workflow tests (authentication, book creation, TOC generation, export)
- Performance monitoring tests

**Trigger Conditions:**
1. **Manual:** After manual staging deployment
2. **Scheduled:** Nightly smoke tests
3. **Optional:** After CI/CD deployment (non-blocking)

### 6.3 Economic Benefits

```
New Strategy:
- Fast tests on every push: 3-5 minutes (NO OpenAI costs)
- Deployment unblocked: proceed to staging immediately
- E2E tests run post-deployment: non-blocking, can fail without blocking
- OpenAI costs: Only on manual trigger or nightly = ~$1-2/month

Time savings: 10 min/deploy × 5 deploys/day = 50 min/day = 4 hours/week
Cost savings: ~$43/month in OpenAI + faster iteration cycles
```

### 6.4 Implementation Plan for E2E Strategy

**Phase 1: Separate Workflows (when re-enabling CI/CD)**
```bash
# In feature/github-actions-cicd branch:
1. Simplify test-suite.yml - remove E2E tests (lines 123-162)
2. Keep e2e-staging.yml but change trigger to workflow_dispatch + schedule
3. Add test tagging: @unit, @integration, @e2e
```

**Phase 2: Tag Existing Tests**
```bash
# Frontend E2E tests
cd frontend/tests/e2e
# Add @e2e tag to test.describe() calls

# Backend tests
cd backend/tests
# Mark expensive tests with @pytest.mark.e2e
# Mark OpenAI tests with @pytest.mark.openai
```

**Phase 3: Update Documentation**
```bash
# Create docs/TESTING_STRATEGY.md
# Document test tiers and when to run each
```

---

## 7. CI/CD Re-Integration Plan (Future Work)

Once staging is stable, re-enable CI/CD in isolated branch:

### 7.1 Prerequisites
1. ✅ Staging deployments working via manual process
2. ✅ All GitHub Secrets configured:
   - `CLERK_PUBLISHABLE_KEY_CI_TEST` (for test builds)
   - `TEST_USER_EMAIL` and `TEST_USER_PASSWORD` (for E2E)
   - All deployment secrets verified
3. ✅ E2E tests tagged and separated (@unit vs @e2e)
4. ✅ Local E2E test validation working

### 7.2 Simplified Workflow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Push to develop                                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
          ┌───────────────────────┐
          │  test-suite.yml       │
          │  (FAST TESTS ONLY)    │
          │  - Frontend: 2 min    │
          │  - Backend: 3 min     │
          │  Total: ~5 minutes    │
          └───────────┬───────────┘
                      │
                      ▼
                 ✅ SUCCESS
                      │
                      ▼
          ┌───────────────────────┐
          │  deploy-staging.yml   │
          │  - Rsync code         │
          │  - Run deploy.sh      │
          │  - Health checks      │
          │  Total: ~5 minutes    │
          └───────────┬───────────┘
                      │
                      ▼
              ✅ DEPLOYMENT DONE
                      │
                      ▼
          ┌───────────────────────┐
          │  e2e-post-deploy.yml  │
          │  (NON-BLOCKING)       │
          │  - Run in background  │
          │  - Report failures    │
          │  - Don't block next   │
          │  Total: 10-15 minutes │
          └───────────────────────┘
```

### 7.3 Incremental Activation Steps

```bash
# Work in feature/github-actions-cicd branch

# Step 1: Fix test-suite.yml
# - Remove E2E tests (lines 123-162)
# - Fix secret names
# - Test on feature branch first

# Step 2: Test staging deployment workflow
# - Ensure deploy.sh is called correctly
# - Verify all secrets are available
# - Test manual trigger first

# Step 3: Add post-deployment E2E (optional)
# - Create e2e-post-deploy.yml
# - Manual trigger only initially
# - Monitor for false positives

# Step 4: Merge to develop
# - Only after all workflows tested on feature branch
# - Staged rollout: test-suite first, then deploy, then E2E

# Step 5: Monitor and iterate
# - Watch GitHub Actions logs
# - Fix issues in feature branch
# - Cherry-pick fixes to develop as needed
```

### 7.4 Workflow File Templates (Future)

#### Simplified test-suite.yml
```yaml
name: Fast Tests

on:
  pull_request:
    branches: [develop, main]
  push:
    branches: [develop, main]

env:
  NODE_VERSION: '20'
  PYTHON_VERSION: '3.11'

jobs:
  frontend-tests:
    name: Frontend (lint/type/unit/build)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Skip if frontend untouched
        id: changes
        uses: dorny/paths-filter@v3
        with:
          filters: |
            frontend:
              - 'frontend/**'

      - name: Setup Node
        if: steps.changes.outputs.frontend == 'true'
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install deps
        if: steps.changes.outputs.frontend == 'true'
        working-directory: frontend
        run: npm ci

      - name: Lint
        if: steps.changes.outputs.frontend == 'true'
        working-directory: frontend
        run: npm run lint

      - name: Typecheck
        if: steps.changes.outputs.frontend == 'true'
        working-directory: frontend
        run: npm run typecheck

      - name: Unit tests
        if: steps.changes.outputs.frontend == 'true'
        working-directory: frontend
        run: npm test -- --coverage

      - name: Build
        if: steps.changes.outputs.frontend == 'true'
        working-directory: frontend
        env:
          NEXT_PUBLIC_API_URL: http://localhost:9999
          NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: pk_test_placeholder
          CLERK_SECRET_KEY: sk_test_placeholder
        run: npm run build

  backend-tests:
    name: Backend (unit + coverage)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Skip if backend untouched
        id: changes
        uses: dorny/paths-filter@v3
        with:
          filters: |
            backend:
              - 'backend/**'

      - name: Setup Python
        if: steps.changes.outputs.backend == 'true'
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install uv
        if: steps.changes.outputs.backend == 'true'
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Test
        if: steps.changes.outputs.backend == 'true'
        working-directory: backend
        env:
          DATABASE_URI: mongodb://localhost:27017
          DATABASE_NAME: autoauthor_test
          OPENAI_AUTOAUTHOR_API_KEY: test-key-mock
          CLERK_API_KEY: test-key-mock
          CLERK_JWT_PUBLIC_KEY: test-mock
          CLERK_FRONTEND_API: https://example.dev
          CLERK_BACKEND_API: https://api.clerk.dev
          ENVIRONMENT: test
        run: |
          $HOME/.cargo/bin/uv run pip install -r requirements.txt
          $HOME/.cargo/bin/uv run pip install pytest pytest-cov

          # Start MongoDB
          docker run -d --name mongo -p 27017:27017 \
            --health-cmd="mongosh --eval 'db.runCommand({ping:1})'" \
            --health-interval=10s --health-timeout=5s --health-retries=5 \
            mongo:6

          # Wait for healthy
          for i in {1..20}; do
            docker inspect --format='{{json .State.Health.Status}}' mongo | grep -q healthy && break || sleep 2
          done

          # Run unit tests only (no E2E, no OpenAI)
          $HOME/.cargo/bin/uv run pytest tests/ \
            --cov=app --cov-report=term-missing --cov-report=xml:coverage.xml \
            -m "not e2e and not openai" \
            --ignore=tests/test_debug_chapter_questions.py \
            --ignore=tests/test_debug_questions.py \
            --ignore=tests/test_e2e_no_mocks.py \
            -v

      - name: Upload coverage
        if: steps.changes.outputs.backend == 'true'
        uses: codecov/codecov-action@v4
        with:
          files: backend/coverage.xml
          flags: backend
```

#### Deployment workflow (deploy-staging.yml)
```yaml
name: Deploy to Staging

on:
  workflow_run:
    workflows: ["Fast Tests"]
    types: [completed]
    branches: [develop]
  workflow_dispatch:

jobs:
  deploy:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' || github.event_name == 'workflow_dispatch' }}

    environment:
      name: staging
      url: https://dev.autoauthor.app

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.SSH_KEY }}" > ~/.ssh/staging_key
          chmod 600 ~/.ssh/staging_key
          ssh-keyscan -H "${{ secrets.HOST }}" >> ~/.ssh/known_hosts

      - name: Create Remote Release Directory
        run: |
          RELEASE_ID=$(date +%Y%m%d-%H%M%S)
          echo "RELEASE_ID=$RELEASE_ID" >> $GITHUB_ENV
          ssh -i ~/.ssh/staging_key ${{ secrets.USER }}@${{ secrets.HOST }} \
            "mkdir -p /opt/auto-author/releases/$RELEASE_ID"

      - name: Rsync source
        run: |
          rsync -az --delete -e "ssh -i ~/.ssh/staging_key" \
            --exclude '.git' \
            --exclude 'node_modules' \
            --exclude '.venv' \
            --exclude '__pycache__' \
            --exclude '*.log' \
            --exclude '.next' \
            ./ ${{ secrets.USER }}@${{ secrets.HOST }}:/opt/auto-author/releases/${{ env.RELEASE_ID }}/

      - name: Run deploy.sh on server
        run: |
          ssh -i ~/.ssh/staging_key ${{ secrets.USER }}@${{ secrets.HOST }} \
            "export API_URL='${{ secrets.API_URL }}' && \
             export FRONTEND_URL='${{ secrets.FRONTEND_URL }}' && \
             export CLERK_PUBLISHABLE_KEY='${{ secrets.CLERK_PUBLISHABLE_KEY }}' && \
             export CLERK_SECRET_KEY='${{ secrets.CLERK_SECRET_KEY }}' && \
             export DATABASE_URI='${{ secrets.DATABASE_URI }}' && \
             export DATABASE_NAME='${{ secrets.DATABASE_NAME }}' && \
             export OPENAI_API_KEY='${{ secrets.OPENAI_API_KEY }}' && \
             export CLERK_WEBHOOK_SECRET='${{ secrets.CLERK_WEBHOOK_SECRET }}' && \
             bash /opt/auto-author/releases/${{ env.RELEASE_ID }}/scripts/deploy.sh \
               /opt/auto-author/releases/${{ env.RELEASE_ID }}"

      - name: Health checks
        run: |
          for i in {1..10}; do
            curl -f https://api.dev.autoauthor.app/api/v1/health && break || sleep 5
          done
          for i in {1..10}; do
            curl -f https://dev.autoauthor.app && break || sleep 5
          done

      - name: Cleanup
        if: always()
        run: rm -f ~/.ssh/staging_key
```

#### Post-deployment E2E (e2e-post-deploy.yml)
```yaml
name: Post-Deployment E2E Tests

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to test'
        required: true
        default: 'staging'
  schedule:
    # Nightly at 2 AM UTC
    - cron: '0 2 * * *'

env:
  STAGING_URL: https://dev.autoauthor.app
  STAGING_API_URL: https://api.dev.autoauthor.app

jobs:
  e2e-tests:
    name: E2E Tests (Non-Blocking)
    runs-on: ubuntu-latest

    environment:
      name: ${{ github.event.inputs.environment || 'staging' }}

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install frontend deps
        working-directory: frontend
        run: npm ci

      - name: Install Playwright
        working-directory: frontend
        run: npx playwright install --with-deps chromium

      - name: Wait for staging
        run: |
          max_attempts=30
          attempt=0
          while [ $attempt -lt $max_attempts ]; do
            if curl -f -s ${{ env.STAGING_API_URL }}/api/v1/health > /dev/null; then
              echo "✅ Staging ready"
              break
            fi
            echo "⏳ Waiting... ($((attempt + 1))/$max_attempts)"
            sleep 10
            attempt=$((attempt + 1))
          done

          if [ $attempt -eq $max_attempts ]; then
            echo "❌ Staging not ready"
            exit 1
          fi

      - name: Run Playwright E2E
        working-directory: frontend
        run: npx playwright test tests/e2e/deployment --config=tests/e2e/deployment/playwright.config.ts
        env:
          DEPLOYMENT_URL: ${{ env.STAGING_URL }}
          BASE_URL: ${{ env.STAGING_URL }}
          TEST_USER_EMAIL: ${{ secrets.TEST_USER_EMAIL }}
          TEST_USER_PASSWORD: ${{ secrets.TEST_USER_PASSWORD }}
          NEXT_PUBLIC_API_URL: ${{ env.STAGING_API_URL }}/api/v1
          NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: ${{ secrets.CLERK_PUBLISHABLE_KEY }}

      - name: Upload Playwright report
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-e2e-report
          path: frontend/playwright-report/
          retention-days: 7

      # Backend E2E tests (optional, expensive)
      - name: Setup Python
        if: github.event.inputs.run_backend_e2e == 'true'
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Backend E2E (OpenAI tests)
        if: github.event.inputs.run_backend_e2e == 'true'
        working-directory: backend
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          export PATH="$HOME/.cargo/bin:$PATH"
          uv venv
          source .venv/bin/activate
          uv pip install -r requirements.txt
          uv pip install pytest pytest-asyncio

          pytest tests/ -m "e2e or openai" -v --tb=short
        env:
          DATABASE_URI: mongodb://localhost:27017
          DATABASE_NAME: autoauthor_e2e_test
          OPENAI_AUTOAUTHOR_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          CLERK_API_KEY: ${{ secrets.CLERK_SECRET_KEY }}
          CLERK_JWT_PUBLIC_KEY: ${{ secrets.CLERK_PUBLISHABLE_KEY }}
          BASE_URL: ${{ env.STAGING_API_URL }}
          ENVIRONMENT: staging
```

---

## 8. Risk Assessment

### 8.1 Risks of Current State (No Action)
- **Severity: CRITICAL**
- Staging deployments remain blocked indefinitely
- Cannot test new features on staging
- CORS fixes and critical bugfixes stuck in develop
- Manual workarounds become permanent
- Team velocity decreases due to deployment friction

### 8.2 Risks of Recovery Plan
- **Severity: LOW**
- Temporarily lose CI/CD automation (acceptable tradeoff)
- Must remember to manually deploy (mitigated by documentation)
- Risk of human error in manual deployments (mitigated by deploy.sh script)
- CI/CD work preserved in branches, can re-enable later

### 8.3 Mitigation Strategies
1. **Backup branches created** before any destructive operations
2. **All CI/CD work preserved** in `feature/github-actions-cicd` branch
3. **Deploy.sh script tested** and working (commit f11798a)
4. **Documentation comprehensive** for manual process
5. **Rollback plan available** (restore from backup branch)

---

## 9. Success Criteria

### 9.1 Phase 1 Success (Recovery)
- ✅ Develop branch has no active CI/CD workflows (.yml files removed)
- ✅ Local tests still passing (frontend and backend)
- ✅ deploy.sh script executable and tested
- ✅ Manual staging deployment documented
- ✅ All CORS fixes preserved

### 9.2 Phase 2 Success (Manual Deployment)
- ✅ Successful manual deployment to staging
- ✅ Frontend accessible at https://dev.autoauthor.app
- ✅ Backend API accessible at https://api.dev.autoauthor.app
- ✅ No CORS errors in browser console
- ✅ User authentication working

### 9.3 Phase 3 Success (CI/CD Re-Integration, Future)
- ✅ Fast tests (< 5 min) running on every push
- ✅ Automated deployments to staging after test success
- ✅ E2E tests separated and non-blocking
- ✅ All GitHub Secrets configured correctly
- ✅ No deployment failures for 1 week

---

## 10. Next Steps

### Immediate Actions (Today)
1. ✅ Review this recovery plan with team
2. ✅ Execute Phase 1-3 of recovery plan (backup, isolate, revert)
3. ✅ Test manual staging deployment
4. ✅ Document any issues encountered
5. ✅ Update team on new deployment process

### Short-Term (This Week)
1. Create deployment runbook with manual steps
2. Train team members on manual deployment
3. Monitor staging stability for 2-3 days
4. Begin fixing CI/CD workflows in `feature/github-actions-cicd` branch
5. Set up GitHub Secrets correctly

### Medium-Term (Next 2 Weeks)
1. Implement E2E test tagging strategy
2. Simplify test-suite.yml (remove E2E)
3. Test CI/CD workflows on feature branch
4. Gradual re-integration: tests → deployment → E2E
5. Monitor and iterate

### Long-Term (Next Month)
1. Establish E2E test schedule (nightly)
2. Set up monitoring and alerting for CI/CD
3. Document lessons learned
4. Consider CI/CD best practices training
5. Evaluate production deployment automation

---

## 11. Lessons Learned

### What Went Wrong
1. **Big Bang Integration:** All CI/CD workflows activated at once without staged rollout
2. **Missing Prerequisites:** Secrets not configured before activation
3. **No Local Testing:** E2E workflows not tested locally before push
4. **Tight Coupling:** E2E tests embedded in critical path (test-suite)
5. **Economic Inefficiency:** Expensive OpenAI tests running on every push

### What Went Right
1. **CORS Fixes Preserved:** deploy.sh script properly restored (f11798a)
2. **Git History Clean:** Can easily identify problematic commits
3. **Backup Strategy:** Multiple branches preserve work
4. **Documentation:** Comprehensive commit messages aid debugging
5. **Rollback Possible:** Changes are reversible

### Best Practices for Future CI/CD Work
1. **Staged Rollout:** Enable workflows one at a time
2. **Secret Verification:** Check all secrets before activating workflows
3. **Local Testing:** Test workflow logic locally using `act` or similar tools
4. **Fast Tests First:** Keep critical path under 5 minutes
5. **Economic Analysis:** Separate expensive tests from cheap tests
6. **Manual Triggers:** Start with `workflow_dispatch` before automatic triggers
7. **Monitoring:** Set up alerts for workflow failures
8. **Documentation:** Update runbooks before enabling automation

---

## 12. Appendix

### A. Related Documentation
- `/home/frankbria/projects/auto-author/scripts/deploy.sh` - Deployment script
- `/home/frankbria/projects/auto-author/.github/workflows/*.tbd` - Workflow templates
- `/home/frankbria/projects/auto-author/docs/references/testing-infrastructure.md` - Testing docs

### B. Key Commits
- `71f504f` - Initial CI/CD activation (PR #8)
- `f11798a` - CORS fix (deploy.sh restoration)
- `700cc96` - Backend .env generation fix
- `40a4978` - Production workflow disabled

### C. Branch Strategy
```
main (stable production)
  └── develop (stable staging) ← YOU ARE HERE
       ├── feature/github-actions-cicd (CI/CD fixes)
       └── backup/develop-with-cicd-2025-10-24 (backup)
```

### D. GitHub Secrets Checklist
- [ ] `SSH_KEY` - SSH private key for staging server
- [ ] `HOST` - Staging server hostname
- [ ] `USER` - SSH username (typically "root")
- [ ] `API_URL` - https://api.dev.autoauthor.app
- [ ] `FRONTEND_URL` - https://dev.autoauthor.app
- [ ] `CLERK_PUBLISHABLE_KEY` - pk_test_...
- [ ] `CLERK_SECRET_KEY` - sk_test_...
- [ ] `CLERK_WEBHOOK_SECRET` - whsec_...
- [ ] `DATABASE_URI` - MongoDB connection string
- [ ] `DATABASE_NAME` - auto_author_staging
- [ ] `OPENAI_API_KEY` - sk-...
- [ ] `TEST_USER_EMAIL` - Test user for E2E
- [ ] `TEST_USER_PASSWORD` - Test user password
- [ ] `CLERK_PUBLISHABLE_KEY_CI_TEST` - Public key for test builds

### E. Contact Information
- **CI/CD Pipeline Engineer:** (This role)
- **Repository:** https://github.com/frankbria/auto-author
- **Staging Server:** https://dev.autoauthor.app
- **Staging API:** https://api.dev.autoauthor.app

---

## 13. Decision Log

| Date | Decision | Rationale | Outcome |
|------|----------|-----------|---------|
| 2025-10-24 | Remove CI/CD workflows from develop | Staging deployments blocked, manual deployment proven stable | Pending |
| 2025-10-24 | Separate E2E tests from unit tests | 10+ min runtime, expensive OpenAI calls | Pending |
| 2025-10-24 | Use deploy.sh for manual deployments | Script tested and working (CORS fixes) | Pending |

---

**END OF RECOVERY PLAN**

*Generated: 2025-10-24*
*Version: 1.0*
*Status: Ready for Review*
