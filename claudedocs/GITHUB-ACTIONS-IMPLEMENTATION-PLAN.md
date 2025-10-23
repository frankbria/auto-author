# GitHub Actions CI/CD Implementation Plan

## Executive Summary

This document provides a complete implementation plan for transitioning from manual SSH-based deployments to automated GitHub Actions workflows for both staging and production environments.

**Current State**: Manual SSH deployment to staging server (47.88.89.175) using PM2
**Target State**: Automated CI/CD with GitHub Actions triggered by git commits
**Timeline**: 3-5 hours implementation, 1-2 hours validation

---

## 1. Current Infrastructure Analysis

### Staging Server (dev.autoauthor.app)
- **Host**: 47.88.89.175 (ClawCloud)
- **User**: root
- **Frontend**: Next.js on port 3002 (PM2 process: auto-author-frontend)
- **Backend**: FastAPI on port 8000 (PM2 process: auto-author-backend)
- **Deployment**: `/opt/auto-author/current/`
- **Process Manager**: PM2
- **Reverse Proxy**: Nginx (configured for dev.autoauthor.app, api.dev.autoauthor.app)

### Repository Structure
- **Remote**: github.com/frankbria/auto-author
- **Branches**:
  - `main` - production-ready code
  - `develop` - staging branch (currently: fix/api-subdomain-csp)
  - Feature branches - individual features

### Existing Assets
- `.github/workflows/deploy-staging.tbd` - staging workflow template
- `.github/workflows/deploy-production.tbd` - production workflow template
- `.github/workflows/test-suite.tbd` - test workflow template
- `scripts/deploy-staging.sh` - manual deployment script (reference)

---

## 2. Deployment Architecture

### Branching Strategy

```
feature/* ──→ develop ──→ main ──→ tags (v*)
              │            │         │
              ↓            ↓         ↓
           Staging      (Manual)  Production
         (auto-deploy)  (merge)   (auto-deploy)
```

**Branch → Environment Mapping**:
- `develop` branch → **Staging** (dev.autoauthor.app) - Auto-deploy on push
- `main` branch → **Production** (autoauthor.app) - Manual merge, no auto-deploy
- `v*` tags → **Production** (autoauthor.app) - Auto-deploy on tag creation

### Deployment Triggers

#### Staging Deployment
**Trigger**: Push to `develop` branch OR successful test suite completion
**Conditions**:
- All tests must pass
- Type checking must pass
- Linting must pass

#### Production Deployment
**Trigger**: Git tag creation (e.g., `v1.0.0`, `v1.2.3-beta`) OR GitHub Release published
**Conditions**:
- Full test suite passes (unit, integration, E2E)
- Security audit passes
- Manual approval required (GitHub Environments feature)

---

## 3. Required GitHub Secrets

### Staging Secrets (Environment: `staging`)

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `STAGING_SSH_KEY` | Private SSH key for deployment user | Contents of `~/.ssh/id_ed25519` |
| `STAGING_HOST` | Staging server hostname/IP | `47.88.89.175` |
| `STAGING_USER` | SSH username | `root` |
| `STAGING_API_URL` | Backend API URL for frontend build | `https://api.dev.autoauthor.app/api/v1` |
| `STAGING_FRONTEND_URL` | Frontend URL | `https://dev.autoauthor.app` |
| `STAGING_CLERK_PUBLISHABLE_KEY` | Clerk auth public key | `pk_test_...` |
| `STAGING_CLERK_SECRET_KEY` | Clerk auth secret key | `sk_test_...` |
| `STAGING_MONGODB_URI` | MongoDB connection string | `mongodb://localhost:27017/autoauthor_staging` |

### Production Secrets (Environment: `production`)

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `PRODUCTION_SSH_KEY` | Private SSH key for deployment user | Contents of production SSH key |
| `PRODUCTION_HOST` | Production server hostname/IP | TBD (future production server) |
| `PRODUCTION_USER` | SSH username | TBD |
| `PRODUCTION_API_URL` | Backend API URL for frontend build | `https://api.autoauthor.app/api/v1` |
| `PRODUCTION_FRONTEND_URL` | Frontend URL | `https://autoauthor.app` |
| `PRODUCTION_CLERK_PUBLISHABLE_KEY` | Clerk auth public key (prod) | `pk_live_...` |
| `PRODUCTION_CLERK_SECRET_KEY` | Clerk auth secret key (prod) | `sk_live_...` |
| `PRODUCTION_MONGODB_URI` | MongoDB connection string | TBD |

### Repository Secrets (Global)

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `SLACK_WEBHOOK_URL` | Slack notifications webhook | `https://hooks.slack.com/...` |

---

## 4. Workflow Architecture

### Workflow 1: Test Suite (`test-suite.yml`)
**Trigger**: Push to any branch, Pull Requests
**Purpose**: Run comprehensive tests before allowing merge/deployment

```yaml
Jobs:
1. frontend-tests
   - Lint (ESLint)
   - Type check (TypeScript)
   - Unit tests (Jest)
   - Build validation

2. backend-tests
   - Lint (Ruff)
   - Type check (MyPy)
   - Unit tests (pytest)
   - API tests

3. e2e-tests
   - Playwright E2E suite
   - Only runs on develop/main branches
```

### Workflow 2: Deploy to Staging (`deploy-staging.yml`)
**Trigger**:
- Push to `develop` branch
- Successful completion of `test-suite` workflow on `develop`

```yaml
Jobs:
1. build
   - Build frontend with staging env vars
   - Run type checks
   - Create deployment artifacts

2. deploy
   - SSH to staging server
   - Upload deployment package
   - Extract to /opt/auto-author/releases/TIMESTAMP
   - Update /opt/auto-author/current symlink
   - Install dependencies
   - Update .env files
   - Restart PM2 services

3. verify
   - Health check endpoints
   - Smoke tests (API, frontend)
   - CORS verification
   - Database connectivity

4. notify
   - Slack notification with deployment status
   - Include commit SHA, branch, deployment URL
```

### Workflow 3: Deploy to Production (`deploy-production.yml`)
**Trigger**:
- Tag creation matching `v*` pattern
- GitHub Release published

```yaml
Jobs:
1. pre-flight
   - Security audit (npm audit, safety check)
   - Full test suite (unit, integration, E2E)
   - Performance benchmarks
   - Database migration dry-run

2. build
   - Build frontend with production env vars
   - Minification and optimization
   - Generate source maps (for debugging)

3. deploy
   - Manual approval required (GitHub Environment protection)
   - SSH to production server
   - Blue-green deployment strategy:
     * Deploy to new directory
     * Run migrations
     * Health checks on new deployment
     * Switch traffic (update symlink)
     * Keep old deployment for 24h (rollback)
   - Restart PM2 services

4. verify
   - Critical path tests
   - Performance validation
   - Security headers check
   - SSL certificate validation

5. notify
   - Slack notification with release notes
   - Include version, changelog, deployment status
```

---

## 5. Deployment Scripts

### Script 1: Remote Deployment Script (`scripts/deploy-remote.sh`)

This script runs ON THE SERVER via SSH from GitHub Actions.

```bash
#!/bin/bash
# Remote deployment script executed on staging/production server
# Usage: ./deploy-remote.sh <environment> <release-id> <api-url> <frontend-url>

set -euo pipefail

ENVIRONMENT=$1        # staging or production
RELEASE_ID=$2         # timestamp or tag (e.g., 20251021-143022 or v1.0.0)
API_URL=$3           # https://api.dev.autoauthor.app/api/v1
FRONTEND_URL=$4      # https://dev.autoauthor.app

DEPLOY_BASE="/opt/auto-author"
RELEASE_DIR="$DEPLOY_BASE/releases/$RELEASE_ID"
CURRENT_DIR="$DEPLOY_BASE/current"

echo "==> Deploying $ENVIRONMENT environment (Release: $RELEASE_ID)"

# Create release directory
mkdir -p "$RELEASE_DIR"

# Extract uploaded package
echo "==> Extracting deployment package..."
tar -xzf /tmp/deploy-package.tar.gz -C "$RELEASE_DIR"

# Setup backend environment
echo "==> Setting up backend..."
cd "$RELEASE_DIR/backend"

# Install Python dependencies
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Update .env file (merge with existing)
if [ -f "$CURRENT_DIR/backend/.env" ]; then
  cp "$CURRENT_DIR/backend/.env" .env
fi

# Setup frontend environment
echo "==> Setting up frontend..."
cd "$RELEASE_DIR/frontend"

# Install Node dependencies (production only)
npm ci --production

# Create/update .env.production
cat > .env.production <<EOF
NEXT_PUBLIC_API_URL=$API_URL
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$CLERK_PUBLISHABLE_KEY
CLERK_SECRET_KEY=$CLERK_SECRET_KEY
NEXT_PUBLIC_ENVIRONMENT=$ENVIRONMENT
PORT=3002
EOF

# Build frontend
echo "==> Building frontend..."
npm run build

# Update symlink atomically
echo "==> Switching to new release..."
ln -snf "$RELEASE_DIR" "$CURRENT_DIR.tmp"
mv -Tf "$CURRENT_DIR.tmp" "$CURRENT_DIR"

# Restart services
echo "==> Restarting services..."
pm2 restart auto-author-backend
pm2 restart auto-author-frontend

# Wait for services to start
sleep 5

# Health checks
echo "==> Running health checks..."
curl -f http://localhost:8000/api/v1/health || {
  echo "ERROR: Backend health check failed"
  exit 1
}

curl -f http://localhost:3002 || {
  echo "ERROR: Frontend health check failed"
  exit 1
}

echo "==> Deployment successful!"
echo "    Release: $RELEASE_ID"
echo "    Backend: http://localhost:8000"
echo "    Frontend: http://localhost:3002"

# Cleanup old releases (keep last 5)
cd "$DEPLOY_BASE/releases"
ls -t | tail -n +6 | xargs -r rm -rf

echo "==> Cleanup complete"
```

### Script 2: Rollback Script (`scripts/rollback.sh`)

```bash
#!/bin/bash
# Rollback to previous deployment
# Usage: ./rollback.sh <environment>

set -euo pipefail

ENVIRONMENT=$1
DEPLOY_BASE="/opt/auto-author"
CURRENT_DIR="$DEPLOY_BASE/current"

# Find previous release
PREVIOUS_RELEASE=$(ls -t "$DEPLOY_BASE/releases" | sed -n 2p)

if [ -z "$PREVIOUS_RELEASE" ]; then
  echo "ERROR: No previous release found"
  exit 1
fi

echo "==> Rolling back to: $PREVIOUS_RELEASE"

# Update symlink
ln -snf "$DEPLOY_BASE/releases/$PREVIOUS_RELEASE" "$CURRENT_DIR.tmp"
mv -Tf "$CURRENT_DIR.tmp" "$CURRENT_DIR"

# Restart services
pm2 restart auto-author-backend
pm2 restart auto-author-frontend

echo "==> Rollback complete!"
```

---

## 6. Phase-by-Phase Implementation

### Phase 1: Repository Setup (30 minutes)

**1.1 Configure GitHub Secrets**

```bash
# Navigate to: https://github.com/frankbria/auto-author/settings/secrets/actions

# Add repository secrets:
- SLACK_WEBHOOK_URL

# Create staging environment:
# Settings → Environments → New environment → "staging"
# Add staging secrets (see section 3)

# Create production environment (for future):
# Settings → Environments → New environment → "production"
# Enable required reviewers (yourself)
# Add production secrets (placeholder values for now)
```

**1.2 Generate and Add SSH Key**

```bash
# On your local machine:
ssh-keygen -t ed25519 -C "github-actions-staging" -f ~/.ssh/github_actions_staging

# Copy public key to staging server:
ssh-copy-id -i ~/.ssh/github_actions_staging.pub root@47.88.89.175

# Add private key to GitHub:
# Copy contents of ~/.ssh/github_actions_staging
cat ~/.ssh/github_actions_staging | pbcopy  # or xclip on Linux

# Add to GitHub as STAGING_SSH_KEY secret
```

**1.3 Verify SSH Access**

```bash
# Test SSH connection:
ssh -i ~/.ssh/github_actions_staging root@47.88.89.175 "echo 'SSH OK'"
```

### Phase 2: Workflow Files Setup (45 minutes)

**2.1 Activate Test Suite Workflow**

```bash
# Rename and customize test-suite workflow:
cd /home/frankbria/projects/auto-author
mv .github/workflows/test-suite.tbd .github/workflows/test-suite.yml

# Edit to match actual test commands
```

**2.2 Activate Staging Deployment Workflow**

```bash
# Rename staging workflow:
mv .github/workflows/deploy-staging.tbd .github/workflows/deploy-staging.yml

# Update with actual deployment commands (see section 7 for complete file)
```

**2.3 Create Deployment Scripts**

```bash
# Create scripts directory if not exists:
mkdir -p scripts

# Create deploy-remote.sh (see section 5)
# Create rollback.sh (see section 5)

# Make executable:
chmod +x scripts/deploy-remote.sh scripts/rollback.sh

# Commit deployment scripts:
git add scripts/deploy-remote.sh scripts/rollback.sh
git commit -m "ci: add automated deployment scripts"
```

### Phase 3: Server Preparation (30 minutes)

**3.1 Setup Release Directory Structure**

```bash
# SSH to staging server:
ssh root@47.88.89.175

# Create directory structure:
mkdir -p /opt/auto-author/releases
mkdir -p /opt/auto-author/shared/logs

# Move current deployment to releases:
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
mv /opt/auto-author/current "/opt/auto-author/releases/manual-$TIMESTAMP"

# Create symlink:
ln -s "/opt/auto-author/releases/manual-$TIMESTAMP" /opt/auto-author/current

# Verify PM2 processes still work:
pm2 status
pm2 restart all
```

**3.2 Upload Deployment Script to Server**

```bash
# On local machine:
scp scripts/deploy-remote.sh root@47.88.89.175:/opt/auto-author/
scp scripts/rollback.sh root@47.88.89.175:/opt/auto-author/

# Make executable on server:
ssh root@47.88.89.175 "chmod +x /opt/auto-author/*.sh"
```

### Phase 4: First Deployment Test (60 minutes)

**4.1 Create Test Feature Branch**

```bash
# On local machine:
git checkout -b test/github-actions-deploy

# Make a trivial change (to trigger deployment):
echo "# CI/CD Testing" >> README.md
git add README.md
git commit -m "test: trigger staging deployment"
git push origin test/github-actions-deploy
```

**4.2 Create PR to Develop**

```bash
# Create PR from test/github-actions-deploy → develop
# Watch GitHub Actions run tests

# Merge PR after tests pass
# Watch staging deployment workflow trigger
```

**4.3 Monitor Deployment**

```bash
# Watch GitHub Actions logs in real-time:
# https://github.com/frankbria/auto-author/actions

# SSH to server to check logs:
ssh root@47.88.89.175
pm2 logs auto-author-backend --lines 50
pm2 logs auto-author-frontend --lines 50
```

**4.4 Verify Deployment**

```bash
# Test staging endpoints:
curl https://api.dev.autoauthor.app/api/v1/health
curl -I https://dev.autoauthor.app

# Run deployment checklist:
# Follow claudedocs/DEPLOYMENT-TESTING-CHECKLIST.md

# Check CORS headers:
curl -I -X OPTIONS https://api.dev.autoauthor.app/api/v1/books \
  -H "Origin: https://dev.autoauthor.app" \
  -H "Access-Control-Request-Method: GET"
```

**4.5 Test Rollback (Optional)**

```bash
# SSH to server:
ssh root@47.88.89.175

# Execute rollback:
cd /opt/auto-author
./rollback.sh staging

# Verify services restarted correctly:
pm2 status
curl http://localhost:8000/api/v1/health
```

### Phase 5: Production Setup (Future - 30 minutes)

**5.1 Setup Production Server**

```bash
# When production server is provisioned:
# 1. Generate new SSH key for production
# 2. Add to GitHub secrets as PRODUCTION_SSH_KEY
# 3. Setup same directory structure as staging
# 4. Configure PM2 processes
# 5. Setup Nginx with production domains
```

**5.2 Activate Production Workflow**

```bash
# Rename production workflow:
mv .github/workflows/deploy-production.tbd .github/workflows/deploy-production.yml

# Update with production server details
# Test with first tag:
git tag v0.1.0-beta
git push origin v0.1.0-beta
```

---

## 7. Complete Workflow Files

### File: `.github/workflows/test-suite.yml`

```yaml
name: Test Suite

on:
  push:
    branches: ['**']
  pull_request:
    branches: [develop, main]

env:
  NODE_VERSION: '18'
  PYTHON_VERSION: '3.9'

jobs:
  frontend-tests:
    name: Frontend Tests
    runs-on: ubuntu-latest

    defaults:
      run:
        working-directory: ./frontend

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Run linting
        run: npm run lint

      - name: Run type checking
        run: npm run typecheck

      - name: Run unit tests
        run: npm test -- --passWithNoTests --ci --coverage

      - name: Build validation
        run: npm run build
        env:
          NEXT_PUBLIC_API_URL: https://api.dev.autoauthor.app/api/v1
          NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: ${{ secrets.STAGING_CLERK_PUBLISHABLE_KEY }}

  backend-tests:
    name: Backend Tests
    runs-on: ubuntu-latest

    defaults:
      run:
        working-directory: ./backend

    services:
      mongodb:
        image: mongo:6
        ports:
          - 27017:27017
        options: >-
          --health-cmd "mongosh --eval 'db.runCommand({ ping: 1 })'"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install uv
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.cargo/bin" >> $GITHUB_PATH

      - name: Create virtual environment
        run: uv venv

      - name: Install dependencies
        run: |
          source .venv/bin/activate
          uv pip install -r requirements.txt
          uv pip install pytest pytest-cov

      - name: Run tests
        run: |
          source .venv/bin/activate
          pytest tests/ --cov=app --cov-report=term-missing --cov-report=xml
        env:
          MONGODB_URI: mongodb://localhost:27017/autoauthor_test
          CLERK_JWT_PUBLIC_KEY: ${{ secrets.STAGING_CLERK_PUBLISHABLE_KEY }}
          ENVIRONMENT: test

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./backend/coverage.xml
          flags: backend

  e2e-tests:
    name: E2E Tests
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop' || github.ref == 'refs/heads/main'

    defaults:
      run:
        working-directory: ./frontend

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright browsers
        run: npx playwright install --with-deps chromium

      - name: Run E2E tests
        run: npx playwright test
        env:
          NEXT_PUBLIC_API_URL: https://api.dev.autoauthor.app/api/v1
          NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: ${{ secrets.STAGING_CLERK_PUBLISHABLE_KEY }}

      - name: Upload test results
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: frontend/playwright-report/
          retention-days: 7
```

### File: `.github/workflows/deploy-staging.yml`

```yaml
name: Deploy to Staging

on:
  push:
    branches: [develop]
  workflow_run:
    workflows: ["Test Suite"]
    types: [completed]
    branches: [develop]

env:
  NODE_VERSION: '18'
  PYTHON_VERSION: '3.9'

jobs:
  build-and-deploy:
    name: Build and Deploy to Staging
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' || github.event_name == 'push' }}

    environment:
      name: staging
      url: https://dev.autoauthor.app

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install uv
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.cargo/bin" >> $GITHUB_PATH

      - name: Build frontend
        working-directory: ./frontend
        env:
          NEXT_PUBLIC_API_URL: ${{ secrets.STAGING_API_URL }}
          NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: ${{ secrets.STAGING_CLERK_PUBLISHABLE_KEY }}
          NEXT_PUBLIC_ENVIRONMENT: staging
        run: |
          npm ci
          npm run build

      - name: Create deployment package
        run: |
          # Create temporary directory
          mkdir -p /tmp/deploy

          # Copy necessary files (exclude development artifacts)
          rsync -av --progress \
            --exclude='node_modules' \
            --exclude='.venv' \
            --exclude='.next' \
            --exclude='coverage' \
            --exclude='*.log' \
            --exclude='.env.local' \
            --exclude='.env' \
            --exclude='__pycache__' \
            --exclude='*.pyc' \
            --exclude='.pytest_cache' \
            --exclude='test-results' \
            --exclude='playwright-report' \
            --exclude='.git' \
            . /tmp/deploy/

          # Create tar archive
          cd /tmp/deploy
          tar -czf /tmp/deploy-package.tar.gz .

      - name: Setup SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.STAGING_SSH_KEY }}" > ~/.ssh/staging_key
          chmod 600 ~/.ssh/staging_key
          ssh-keyscan -H ${{ secrets.STAGING_HOST }} >> ~/.ssh/known_hosts

      - name: Upload package to server
        run: |
          scp -i ~/.ssh/staging_key /tmp/deploy-package.tar.gz \
            ${{ secrets.STAGING_USER }}@${{ secrets.STAGING_HOST }}:/tmp/

      - name: Deploy to staging
        run: |
          ssh -i ~/.ssh/staging_key \
            ${{ secrets.STAGING_USER }}@${{ secrets.STAGING_HOST }} \
            "bash -s" < scripts/deploy-remote.sh staging \
              $(date +%Y%m%d-%H%M%S) \
              ${{ secrets.STAGING_API_URL }} \
              ${{ secrets.STAGING_FRONTEND_URL }}
        env:
          CLERK_PUBLISHABLE_KEY: ${{ secrets.STAGING_CLERK_PUBLISHABLE_KEY }}
          CLERK_SECRET_KEY: ${{ secrets.STAGING_CLERK_SECRET_KEY }}

      - name: Health checks
        run: |
          # Wait for services to stabilize
          sleep 10

          # Backend health check
          echo "Checking backend health..."
          curl -f https://api.dev.autoauthor.app/api/v1/health || exit 1

          # Frontend health check
          echo "Checking frontend health..."
          curl -f https://dev.autoauthor.app || exit 1

          # CORS verification
          echo "Checking CORS headers..."
          curl -I -X OPTIONS https://api.dev.autoauthor.app/api/v1/books \
            -H "Origin: https://dev.autoauthor.app" \
            -H "Access-Control-Request-Method: GET" | grep -i "access-control-allow-origin" || exit 1

      - name: Smoke tests
        run: |
          # Test API docs endpoint
          curl -f https://api.dev.autoauthor.app/docs || exit 1

          echo "✅ All smoke tests passed"

      - name: Cleanup
        if: always()
        run: |
          rm -f ~/.ssh/staging_key
          rm -f /tmp/deploy-package.tar.gz

  notify:
    name: Notify Deployment Status
    runs-on: ubuntu-latest
    needs: [build-and-deploy]
    if: always()

    steps:
      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ needs.build-and-deploy.result }}
          text: |
            🚀 Staging Deployment ${{ needs.build-and-deploy.result }}

            Branch: ${{ github.ref_name }}
            Commit: ${{ github.sha }}
            Author: ${{ github.actor }}

            URL: https://dev.autoauthor.app
            API: https://api.dev.autoauthor.app
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### File: `.github/workflows/deploy-production.yml`

```yaml
name: Deploy to Production

on:
  push:
    tags:
      - 'v*'
  release:
    types: [published]

env:
  NODE_VERSION: '18'
  PYTHON_VERSION: '3.9'

jobs:
  pre-flight:
    name: Production Readiness Checks
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          cd frontend && npm ci
          cd ../backend && pip install -r requirements.txt

      - name: Run full test suite
        run: |
          cd frontend && npm test -- --ci --coverage
          cd ../backend && pytest --cov=app tests/

      - name: Security audit
        run: |
          cd frontend && npm audit --audit-level=moderate
          cd ../backend && pip install safety && safety check -r requirements.txt

      - name: Check for TODOs/FIXMEs
        run: |
          if grep -r "TODO\|FIXME" frontend/src backend/app --exclude-dir=node_modules --exclude-dir=.venv; then
            echo "⚠️  Found TODO/FIXME comments - review before production"
            exit 1
          fi

  build-and-deploy:
    name: Build and Deploy to Production
    runs-on: ubuntu-latest
    needs: [pre-flight]

    environment:
      name: production
      url: https://autoauthor.app

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Build frontend
        working-directory: ./frontend
        env:
          NEXT_PUBLIC_API_URL: ${{ secrets.PRODUCTION_API_URL }}
          NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: ${{ secrets.PRODUCTION_CLERK_PUBLISHABLE_KEY }}
          NEXT_PUBLIC_ENVIRONMENT: production
        run: |
          npm ci --production
          npm run build

      - name: Create deployment package
        run: |
          mkdir -p /tmp/deploy

          rsync -av --progress \
            --exclude='node_modules' \
            --exclude='.venv' \
            --exclude='.next' \
            --exclude='coverage' \
            --exclude='*.log' \
            --exclude='.env*' \
            --exclude='__pycache__' \
            --exclude='*.pyc' \
            --exclude='.pytest_cache' \
            --exclude='test-results' \
            --exclude='playwright-report' \
            --exclude='.git' \
            --exclude='tests' \
            --exclude='e2e' \
            . /tmp/deploy/

          cd /tmp/deploy
          tar -czf /tmp/deploy-package.tar.gz .

      - name: Setup SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.PRODUCTION_SSH_KEY }}" > ~/.ssh/production_key
          chmod 600 ~/.ssh/production_key
          ssh-keyscan -H ${{ secrets.PRODUCTION_HOST }} >> ~/.ssh/known_hosts

      - name: Upload package
        run: |
          scp -i ~/.ssh/production_key /tmp/deploy-package.tar.gz \
            ${{ secrets.PRODUCTION_USER }}@${{ secrets.PRODUCTION_HOST }}:/tmp/

      - name: Deploy to production
        run: |
          ssh -i ~/.ssh/production_key \
            ${{ secrets.PRODUCTION_USER }}@${{ secrets.PRODUCTION_HOST }} \
            "bash -s" < scripts/deploy-remote.sh production \
              ${{ github.ref_name }} \
              ${{ secrets.PRODUCTION_API_URL }} \
              ${{ secrets.PRODUCTION_FRONTEND_URL }}
        env:
          CLERK_PUBLISHABLE_KEY: ${{ secrets.PRODUCTION_CLERK_PUBLISHABLE_KEY }}
          CLERK_SECRET_KEY: ${{ secrets.PRODUCTION_CLERK_SECRET_KEY }}

      - name: Production verification
        run: |
          sleep 15

          # Backend health
          curl -f https://api.autoauthor.app/api/v1/health || exit 1

          # Frontend health
          curl -f https://autoauthor.app || exit 1

          # SSL certificate check
          echo | openssl s_client -connect autoauthor.app:443 2>/dev/null | \
            openssl x509 -noout -dates

          # Security headers
          curl -I https://autoauthor.app | grep -i "strict-transport-security" || exit 1

      - name: Cleanup
        if: always()
        run: |
          rm -f ~/.ssh/production_key
          rm -f /tmp/deploy-package.tar.gz

  notify:
    name: Notify Production Deployment
    runs-on: ubuntu-latest
    needs: [build-and-deploy]
    if: always()

    steps:
      - name: Notify team
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ needs.build-and-deploy.result }}
          text: |
            🚀 Production Deployment ${{ needs.build-and-deploy.result }}

            Version: ${{ github.ref_name }}
            Commit: ${{ github.sha }}
            Deployed by: ${{ github.actor }}

            🌐 https://autoauthor.app
            📡 https://api.autoauthor.app
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## 8. Rollback Procedures

### Automated Rollback (Staging)

```bash
# Trigger rollback workflow manually:
# GitHub → Actions → Deploy to Staging → Run workflow → Advanced options
# Select "rollback" option

# Or SSH to server:
ssh root@47.88.89.175
cd /opt/auto-author
./rollback.sh staging
```

### Manual Rollback (Production)

```bash
# List available releases:
ssh root@<production-host>
ls -lt /opt/auto-author/releases/

# Identify release to rollback to (e.g., previous version):
ROLLBACK_RELEASE="v1.0.0"

# Update symlink:
ln -snf "/opt/auto-author/releases/$ROLLBACK_RELEASE" /opt/auto-author/current.tmp
mv -Tf /opt/auto-author/current.tmp /opt/auto-author/current

# Restart services:
pm2 restart all

# Verify:
pm2 status
curl http://localhost:8000/api/v1/health
```

---

## 9. Monitoring and Alerting

### Health Check Endpoints

```
Staging:
- Backend: https://api.dev.autoauthor.app/api/v1/health
- Frontend: https://dev.autoauthor.app

Production:
- Backend: https://api.autoauthor.app/api/v1/health
- Frontend: https://autoauthor.app
```

### PM2 Monitoring

```bash
# View process status:
pm2 status

# View logs:
pm2 logs auto-author-backend --lines 100
pm2 logs auto-author-frontend --lines 100

# Monitor in real-time:
pm2 monit

# Setup PM2 startup script (survive server reboots):
pm2 startup
pm2 save
```

### Slack Notifications

Configured in workflows to notify on:
- ✅ Successful deployments
- ❌ Failed deployments
- ⚠️  Health check failures

---

## 10. Troubleshooting

### Issue: Deployment fails with "Permission denied"

**Solution**: Verify SSH key permissions and server access.

```bash
# Test SSH connection:
ssh -i ~/.ssh/github_actions_staging root@47.88.89.175 "echo 'SSH OK'"

# Check key permissions:
ls -l ~/.ssh/github_actions_staging  # Should be 600

# Verify key is added to server:
ssh root@47.88.89.175 "cat ~/.ssh/authorized_keys"
```

### Issue: Frontend build fails in CI

**Solution**: Check environment variables and build logs.

```bash
# Verify secrets are set in GitHub:
# Settings → Environments → staging → Environment secrets

# Test build locally with staging env:
cd frontend
NEXT_PUBLIC_API_URL=https://api.dev.autoauthor.app/api/v1 npm run build
```

### Issue: PM2 processes not restarting

**Solution**: Check PM2 configuration and logs.

```bash
ssh root@47.88.89.175

# Check PM2 status:
pm2 status

# Check process logs:
pm2 logs --lines 50

# Restart manually:
pm2 restart all

# Delete and recreate if needed:
pm2 delete all
cd /opt/auto-author/current/backend
pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8000" --name auto-author-backend

cd ../frontend
pm2 start "npm start" --name auto-author-frontend
pm2 save
```

### Issue: Health checks fail after deployment

**Solution**: Verify services are running and ports are correct.

```bash
ssh root@47.88.89.175

# Check if ports are listening:
netstat -tuln | grep -E '3002|8000'

# Test locally on server:
curl http://localhost:8000/api/v1/health
curl http://localhost:3002

# Check Nginx configuration:
nginx -t
systemctl status nginx

# Check logs:
tail -f /var/log/nginx/error.log
```

### Issue: CORS errors after deployment

**Solution**: Verify backend CORS configuration matches frontend URL.

```bash
# Check backend .env CORS settings:
ssh root@47.88.89.175
cat /opt/auto-author/current/backend/.env | grep CORS

# Should include:
# BACKEND_CORS_ORIGINS=["https://dev.autoauthor.app", "http://localhost:3000"]

# Test CORS headers:
curl -I -X OPTIONS https://api.dev.autoauthor.app/api/v1/books \
  -H "Origin: https://dev.autoauthor.app" \
  -H "Access-Control-Request-Method: GET"
```

---

## 11. Next Steps After Implementation

### Immediate (Post-Implementation)

1. ✅ Run deployment test following Phase 4
2. ✅ Verify staging deployment via DEPLOYMENT-TESTING-CHECKLIST.md
3. ✅ Document any issues encountered
4. ✅ Update runbook with actual server details

### Short-term (Within 1 week)

1. Monitor staging deployments for stability
2. Set up log aggregation (e.g., Papertrail, Loggly)
3. Configure uptime monitoring (e.g., UptimeRobot, Pingdom)
4. Create deployment dashboard (GitHub Actions badges)

### Medium-term (Within 1 month)

1. Provision production server
2. Set up production database (MongoDB Atlas or dedicated instance)
3. Configure production domain DNS
4. Activate production deployment workflow
5. Perform first production deployment with blue-green strategy

### Long-term (Ongoing)

1. Implement automated database backups
2. Set up infrastructure-as-code (Terraform/Ansible)
3. Add performance monitoring (New Relic, DataDog)
4. Create disaster recovery plan
5. Implement feature flags for gradual rollouts

---

## 12. Success Criteria

### Staging Deployment

- ✅ Push to `develop` branch triggers automatic deployment
- ✅ Deployment completes in <5 minutes
- ✅ Health checks pass automatically
- ✅ Slack notification received
- ✅ Application accessible at dev.autoauthor.app
- ✅ CORS working correctly
- ✅ Rollback works as expected

### Production Deployment

- ✅ Tag creation triggers deployment
- ✅ Manual approval required before deploy
- ✅ Full test suite passes
- ✅ Security audit passes
- ✅ Blue-green deployment with zero downtime
- ✅ Automatic rollback on health check failure
- ✅ Team notified of deployment status

---

## 13. Appendix

### A. Environment Variables Reference

**Frontend Environment Variables**:

```bash
# Staging (.env.production)
NEXT_PUBLIC_API_URL=https://api.dev.autoauthor.app/api/v1
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_ENVIRONMENT=staging
PORT=3002

# Production (.env.production)
NEXT_PUBLIC_API_URL=https://api.autoauthor.app/api/v1
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
CLERK_SECRET_KEY=sk_live_...
NEXT_PUBLIC_ENVIRONMENT=production
PORT=3002
```

**Backend Environment Variables**:

```bash
# Staging (.env)
ENVIRONMENT=staging
MONGODB_URI=mongodb://localhost:27017/autoauthor_staging
CLERK_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n"
CLERK_API_KEY=sk_test_...
BACKEND_CORS_ORIGINS=["https://dev.autoauthor.app","http://localhost:3000"]

# Production (.env)
ENVIRONMENT=production
MONGODB_URI=mongodb://...  # Use MongoDB Atlas or dedicated instance
CLERK_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n"
CLERK_API_KEY=sk_live_...
BACKEND_CORS_ORIGINS=["https://autoauthor.app"]
```

### B. Useful Commands

```bash
# GitHub CLI (gh)
gh workflow list                    # List all workflows
gh workflow run deploy-staging.yml  # Trigger workflow manually
gh run list --workflow=deploy-staging.yml  # View recent runs
gh run view <run-id>                # View run details
gh run watch                        # Watch current run

# Server Management
ssh root@47.88.89.175
pm2 status                          # Process status
pm2 logs --lines 100                # View logs
pm2 restart all                     # Restart all
pm2 monit                           # Real-time monitoring
pm2 save                            # Save process list
pm2 startup                         # Enable startup script

# Deployment Management
cd /opt/auto-author
ls -lt releases/                    # List releases
./rollback.sh staging               # Rollback
tail -f shared/logs/*.log           # View deployment logs

# Health Checks
curl https://api.dev.autoauthor.app/api/v1/health
curl https://dev.autoauthor.app
curl -I https://dev.autoauthor.app  # Check headers
```

### C. Resource Links

- **GitHub Actions Documentation**: https://docs.github.com/en/actions
- **PM2 Documentation**: https://pm2.keymetrics.io/docs/usage/quick-start/
- **Next.js Deployment**: https://nextjs.org/docs/deployment
- **FastAPI Deployment**: https://fastapi.tiangolo.com/deployment/
- **MongoDB Connection**: https://www.mongodb.com/docs/manual/reference/connection-string/

---

## Document Version

**Version**: 1.0
**Date**: 2025-10-21
**Author**: Claude Code
**Status**: Ready for Implementation

**Change Log**:
- v1.0 (2025-10-21): Initial implementation plan created
