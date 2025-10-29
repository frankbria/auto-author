# Deployment Pipeline Architecture
## Auto-Author Next.js + FastAPI Project

**Status**: Architectural Design
**Date**: 2025-10-24
**Author**: DevOps Architect

---

## Executive Summary

This document defines an optimized deployment pipeline architecture that separates **fast feedback** (unit/integration tests) from **slow validation** (E2E tests), enabling rapid staging deployments while maintaining quality gates for production.

**Key Principles**:
- **Speed**: Fast feedback loop for developers (< 5 minutes)
- **Quality**: Comprehensive testing without blocking deployments
- **Cost**: Optimize GitHub Actions minutes usage
- **Flexibility**: Support for experimental CI/CD changes

---

## 1. Branch Strategy

### 1.1 Branch Structure

```
main (production)
├── develop (staging)
│   ├── feature/* (feature development)
│   └── hotfix/* (urgent fixes)
└── ci-experimental/* (CI/CD experiments)
```

### 1.2 Branch Definitions

| Branch | Purpose | Auto-Deploy | Test Requirements | Protection Rules |
|--------|---------|-------------|-------------------|------------------|
| `main` | Production-ready code | Manual approval | All tests pass + manual QA | Required reviews, status checks |
| `develop` | Staging environment | Automatic | Fast tests only | Fast tests must pass |
| `feature/*` | Feature development | No | Fast tests on PR | PR review required |
| `hotfix/*` | Emergency production fixes | Manual | All tests + expedited review | Emergency approval process |
| `ci-experimental/*` | CI/CD workflow testing | No | None | No protection |

### 1.3 Branch Flow

```
feature/new-component
    ↓ (PR with fast tests)
develop (automatic staging deploy)
    ↓ (manual promotion after E2E validation)
main (manual production deploy)
```

**CI/CD Experimental Flow**:
```
ci-experimental/new-workflow
    ↓ (test workflow changes in isolation)
develop (merge after validation)
```

---

## 2. Pipeline Architecture

### 2.1 Three-Tier Test Strategy

```
┌─────────────────────────────────────────────────────────┐
│ TIER 1: Fast Feedback (< 5 min) - BLOCKS DEPLOYMENT    │
├─────────────────────────────────────────────────────────┤
│ • Frontend: lint, typecheck, unit, build               │
│ • Backend: unit tests, coverage (85%+)                 │
│ • Triggers: All PRs, all pushes to develop/main        │
│ • Cost: ~2-3 minutes, runs frequently                  │
└─────────────────────────────────────────────────────────┘
                        ↓ PASS
┌─────────────────────────────────────────────────────────┐
│ TIER 2: Deployment (< 2 min) - AUTOMATIC               │
├─────────────────────────────────────────────────────────┤
│ • Rsync code to staging server                         │
│ • Run deploy.sh (build + restart services)             │
│ • Health checks (API + frontend)                       │
│ • Triggers: Push to develop (after Tier 1 passes)      │
│ • Cost: ~1-2 minutes, runs on every merge              │
└─────────────────────────────────────────────────────────┘
                        ↓ PARALLEL
┌─────────────────────────────────────────────────────────┐
│ TIER 3: Validation (10-15 min) - INFORMATIONAL         │
├─────────────────────────────────────────────────────────┤
│ • E2E tests against live staging environment           │
│ • Frontend: Playwright tests (auth, books, TOC, etc.)  │
│ • Backend: Integration tests with real APIs            │
│ • Triggers: After staging deployment completes         │
│ • Cost: ~10-15 minutes, runs post-deployment           │
│ • Status: Does NOT block deployment, alerts on failure │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Pipeline Stages

#### Stage 1: Fast Feedback (BLOCKING)
**Purpose**: Provide immediate feedback to developers
**Runtime**: 2-5 minutes
**Triggers**: PR open/update, push to develop/main

**Frontend Job** (parallel):
- Path filter: `frontend/**`
- ESLint validation
- TypeScript type checking
- Jest unit tests
- Next.js build (with dummy env vars)
- **Exit on failure**: ❌ Block PR/push

**Backend Job** (parallel):
- Path filter: `backend/**`
- Python unit tests with pytest
- Code coverage validation (85% minimum)
- MongoDB containerized for testing
- **Exit on failure**: ❌ Block PR/push

**Optimization**:
- ✅ Path filtering (skip if unchanged)
- ✅ Caching (npm, uv dependencies)
- ✅ Parallel execution (frontend + backend)
- ✅ Fail fast (exit on first error)

#### Stage 2: Deployment (NON-BLOCKING FOR E2E)
**Purpose**: Deploy to staging automatically
**Runtime**: 1-2 minutes
**Triggers**: Push to develop (after Stage 1 success)

**Deployment Job**:
- Create timestamped release directory
- Rsync code to server (excludes: .git, node_modules, .venv)
- Execute `scripts/deploy.sh` on server:
  - Backend: uv install, create .env, restart PM2
  - Frontend: npm install, build, restart PM2
- Health checks with retry backoff (10 attempts, 5s delay)
- Cleanup old releases (keep last 5)

**Exit Criteria**:
- ✅ Deploy completes → Stage 3 starts
- ❌ Deploy fails → Alert, no Stage 3

#### Stage 3: E2E Validation (NON-BLOCKING)
**Purpose**: Validate staging deployment functionality
**Runtime**: 10-15 minutes
**Triggers**: After Stage 2 deployment success

**E2E Tests Job**:
- Wait for staging health check (30 attempts, 10s delay)
- Frontend Playwright tests:
  - Authentication flows (Clerk)
  - Book CRUD operations
  - TOC generation wizard
  - Chapter editor functionality
  - Export (PDF/DOCX)
- Backend integration tests:
  - Real OpenAI API calls
  - Real MongoDB operations
  - Full workflow E2E tests

**Status Reporting**:
- ✅ Pass → Green status, ready for production promotion
- ❌ Fail → Red status, alert team, **staging remains deployed**
- 📊 Upload artifacts (Playwright reports, logs)

**Key Difference**: E2E failures do NOT roll back staging, they inform the team.

---

## 3. Test Execution Matrix

### 3.1 What Runs When

| Event | Fast Tests | Deployment | E2E Tests | Blocks |
|-------|------------|------------|-----------|--------|
| Open PR to develop | ✅ Frontend + Backend | ❌ | ❌ | Yes (PR merge) |
| Update PR | ✅ Changed paths only | ❌ | ❌ | Yes (PR merge) |
| Push to develop | ✅ Frontend + Backend | ✅ Auto | ✅ Post-deploy | Fast tests only |
| Push to main | ✅ Frontend + Backend | ❌ Manual | ❌ | Yes (all tests) |
| Push to ci-experimental/* | ❌ (configurable) | ❌ | ❌ | No |
| Manual workflow dispatch | Configurable | Configurable | Configurable | No |

### 3.2 What Blocks What

```
PR Merge:
  BLOCKED BY: Fast tests (lint, typecheck, unit, build)
  NOT BLOCKED BY: E2E tests (they don't run on PRs)

Staging Deployment:
  BLOCKED BY: Fast tests passing
  NOT BLOCKED BY: E2E tests (they run after)

Production Deployment:
  BLOCKED BY: Fast tests + E2E tests + Manual approval
  REQUIRES: Green E2E status from staging + QA signoff

CI/CD Experiments:
  BLOCKED BY: Nothing (isolated testing)
```

### 3.3 Test Type Definitions

| Test Type | Runtime | Scope | When to Run | Blocks Deployment |
|-----------|---------|-------|-------------|-------------------|
| **Unit Tests** | < 30s | Single function/component | Every commit | ✅ Yes |
| **Integration Tests** | 1-2m | API + DB interactions | Every commit | ✅ Yes |
| **Build Validation** | 1-2m | Full application build | Every commit | ✅ Yes |
| **E2E Tests** | 10-15m | Full user flows | Post-staging deploy | ❌ No (informational) |
| **Load Tests** | 5-10m | Performance benchmarks | On-demand/scheduled | ❌ No |
| **Security Scans** | 2-5m | Dependency vulnerabilities | Scheduled weekly | ❌ No (alerts only) |

---

## 4. Cost & Time Optimization

### 4.1 GitHub Actions Minute Usage

**Current State** (per staging deployment):
- Fast tests: ~3 minutes × 1 workflow = 3 minutes
- Deployment: ~2 minutes × 1 workflow = 2 minutes
- E2E tests: ~15 minutes × 1 workflow = 15 minutes
- **Total: ~20 minutes per deploy**

**Optimization Strategies**:

1. **Path Filtering** (50% savings):
   - Skip unchanged frontend/backend jobs
   - Average savings: ~2-3 minutes per run
   - Implementation: `dorny/paths-filter` action ✅ Already implemented

2. **Dependency Caching** (30% savings):
   - Cache npm packages (Node.js 20)
   - Cache uv dependencies (Python 3.11)
   - Average savings: ~1-2 minutes per run
   - Implementation: `actions/cache` ✅ Already implemented

3. **Parallel Execution** (40% time reduction):
   - Run frontend + backend tests concurrently
   - Current: 5 minutes total vs. 8 minutes sequential
   - Implementation: Separate jobs with no dependencies ✅ Already implemented

4. **E2E Test Optimization**:
   - Run only Chromium (not all browsers): ✅ Implemented
   - Use `--reporter=line` (faster than HTML): ✅ Implemented
   - Potential: Parallelize E2E tests (4 shards): ~7 minutes (50% savings)

5. **Scheduled Full Test Runs**:
   - Run expensive tests on schedule (nightly)
   - Run subset on every deployment
   - Example: Full E2E suite nightly, smoke tests per deploy

### 4.2 Projected Savings

| Optimization | Current | Optimized | Savings | Priority |
|--------------|---------|-----------|---------|----------|
| Path filtering | 5 min | 2.5 min | 50% | ✅ Done |
| Dependency caching | 5 min | 3.5 min | 30% | ✅ Done |
| Parallel jobs | 8 min | 5 min | 37.5% | ✅ Done |
| E2E parallelization | 15 min | 7 min | 53% | 🔄 High |
| Scheduled full tests | 20 min/deploy | 10 min/deploy | 50% | 🔄 Medium |

**Total Potential Savings**: 50-60% reduction in CI/CD runtime costs

### 4.3 Monthly Cost Estimate

**Assumptions**:
- 20 deploys/day to staging (aggressive development)
- 2000 free GitHub Actions minutes/month
- $0.008 per minute after free tier

**Current**:
- 20 deploys × 20 min × 30 days = 12,000 minutes/month
- Overage: 10,000 minutes × $0.008 = $80/month

**Optimized** (with E2E parallelization + scheduled tests):
- 20 deploys × 10 min × 30 days = 6,000 minutes/month
- Overage: 4,000 minutes × $0.008 = $32/month
- **Savings: $48/month (60% reduction)**

---

## 5. Deployment Workflows

### 5.1 Workflow Files

```
.github/workflows/
├── test-suite.yml         # Stage 1: Fast tests (BLOCKING)
├── deploy-staging.yml     # Stage 2: Deployment (AUTO)
├── e2e-staging.yml        # Stage 3: E2E validation (INFORMATIONAL)
├── deploy-production.yml  # Manual production deployment
└── experimental-*.yml     # CI/CD testing workflows (isolated)
```

### 5.2 Workflow Relationships

```yaml
# test-suite.yml
on:
  pull_request: [develop, main]
  push: [develop, main]
jobs:
  frontend-tests: # BLOCKING
  backend-tests:  # BLOCKING

# deploy-staging.yml
on:
  workflow_run:
    workflows: ["Test Suite"]
    types: [completed]
    branches: [develop]
jobs:
  deploy:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    # Runs ONLY if test-suite.yml succeeds

# e2e-staging.yml
on:
  workflow_run:
    workflows: ["Deploy to Staging"]
    types: [completed]
    branches: [develop]
  workflow_dispatch: # Manual trigger
jobs:
  e2e-tests:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    # Runs ONLY if deploy-staging.yml succeeds
    # Does NOT block staging (informational only)
```

### 5.3 Experimental Workflow Pattern

Create isolated workflows for testing CI/CD changes:

```yaml
# .github/workflows/experimental-new-feature.yml
name: Experimental - New Test Runner

on:
  push:
    branches:
      - ci-experimental/new-test-runner

jobs:
  test-new-runner:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Test new runner configuration
        run: |
          # Experiment with new test configurations
          # Does NOT affect staging or production
```

**Benefits**:
- ✅ Test workflow changes without risk
- ✅ Iterate quickly on CI/CD improvements
- ✅ No impact on staging/production pipelines
- ✅ Easy to delete when done

---

## 6. Quality Gates

### 6.1 PR Quality Gates (Block Merge)

```
Pull Request → develop
├── ✅ Fast tests pass (frontend + backend)
├── ✅ Code review approval (1+ reviewer)
├── ✅ No merge conflicts
├── ✅ Conventional commit format
└── ✅ Linear history (squash or rebase)
```

### 6.2 Staging Deployment Gates (Block Deploy)

```
Push to develop
├── ✅ Fast tests pass
├── ✅ No concurrent deployments
└── ✅ Health checks succeed
```

### 6.3 Production Promotion Gates (Block Production)

```
Promote develop → main
├── ✅ All tests pass (fast + E2E)
├── ✅ E2E staging tests green
├── ✅ Manual QA signoff
├── ✅ Stakeholder approval
├── ✅ Changelog updated
└── ✅ Zero critical bugs
```

### 6.4 Rollback Triggers (Automatic)

```
Post-Deployment Monitoring
├── ❌ Health checks fail (3+ consecutive)
├── ❌ Error rate > 5% (1 minute window)
├── ❌ Response time > 5s (p95)
└── → Automatic rollback to previous release
```

---

## 7. Rollback Strategy

### 7.1 Zero-Downtime Rollback

Current deployment script uses **atomic symlink switching**:

```bash
# Current deployment
/opt/auto-author/
├── current → releases/20251024-143022/  # Symlink
├── releases/
│   ├── 20251024-143022/  # Current
│   ├── 20251024-120015/  # Previous (rollback target)
│   ├── 20251023-180430/
│   └── ...
```

**Rollback Procedure**:
```bash
# Identify previous release
PREVIOUS=$(ls -t /opt/auto-author/releases | sed -n '2p')

# Atomic symlink switch (zero downtime)
ln -sfn /opt/auto-author/releases/$PREVIOUS /opt/auto-author/current

# Restart services
pm2 restart all

# Verify health
curl -f https://api.dev.autoauthor.app/api/v1/health
curl -f https://dev.autoauthor.app
```

**Rollback Time**: < 30 seconds

### 7.2 Automated Rollback Script

Create `scripts/rollback.sh`:

```bash
#!/bin/bash
set -e

RELEASES_DIR="/opt/auto-author/releases"
CURRENT_LINK="/opt/auto-author/current"

# Get previous release
PREVIOUS=$(ls -t $RELEASES_DIR | sed -n '2p')

if [ -z "$PREVIOUS" ]; then
  echo "❌ No previous release found"
  exit 1
fi

echo "🔄 Rolling back to: $PREVIOUS"
ln -sfn $RELEASES_DIR/$PREVIOUS $CURRENT_LINK

echo "♻️  Restarting services..."
pm2 restart all

echo "🏥 Running health checks..."
sleep 5
curl -f https://api.dev.autoauthor.app/api/v1/health
curl -f https://dev.autoauthor.app

echo "✅ Rollback complete"
```

### 7.3 Rollback Decision Tree

```
Deployment Issue Detected
│
├─ Critical error (500s, auth broken)?
│  └─ Immediate rollback (no questions)
│
├─ Non-critical bug (UI glitch)?
│  └─ Hotfix on current deployment
│
├─ Performance degradation?
│  └─ Investigate → Rollback if unresolved in 5 min
│
└─ E2E test failures?
   └─ Investigate → Fix forward or rollback based on severity
```

---

## 8. Implementation Priorities

### Phase 1: Critical Path (Week 1) 🔴
**Objective**: Separate E2E tests from blocking staging deployments

1. **Modify workflow dependencies** (2 hours):
   - Update `e2e-staging.yml` to run post-deployment
   - Remove E2E as blocker for `deploy-staging.yml`
   - Add `continue-on-error: false` for fast tests only

2. **Add failure notifications** (1 hour):
   - Slack/Discord webhook for E2E failures
   - Include Playwright report links
   - Tag responsible team members

3. **Create rollback script** (2 hours):
   - Implement `scripts/rollback.sh`
   - Add health check validation
   - Document rollback procedure

4. **Update documentation** (1 hour):
   - Deployment process changes
   - Rollback instructions
   - Team communication protocols

**Expected Outcome**: Staging deploys in < 5 minutes, E2E tests inform but don't block

### Phase 2: Optimization (Week 2) 🟡
**Objective**: Reduce E2E test runtime and costs

1. **Parallelize E2E tests** (4 hours):
   - Configure Playwright shards (4 workers)
   - Update workflow to run shards in parallel
   - Merge artifacts for unified reporting
   - **Expected savings**: 50% E2E runtime (15 min → 7 min)

2. **Implement test categorization** (3 hours):
   - Smoke tests: Critical user paths (< 2 min)
   - Full tests: Complete coverage (10+ min)
   - Run smoke tests per deploy, full tests nightly

3. **Add deployment health monitoring** (2 hours):
   - Implement post-deploy monitoring (5 min window)
   - Track error rates, response times, availability
   - Automatic rollback on threshold breach

4. **Optimize dependency caching** (1 hour):
   - Fine-tune cache keys
   - Add cache hit rate monitoring
   - Verify 30%+ time savings

**Expected Outcome**: 50% reduction in total CI/CD runtime costs

### Phase 3: Advanced Features (Week 3-4) 🟢
**Objective**: Production-grade deployment pipeline

1. **Blue-green deployment** (1 week):
   - Deploy to inactive environment
   - Run smoke tests
   - Switch traffic atomically
   - Keep previous environment for instant rollback

2. **Canary releases** (3 days):
   - Route 5% traffic to new version
   - Monitor error rates and metrics
   - Gradual rollout (5% → 25% → 50% → 100%)
   - Automatic rollback on anomalies

3. **Database migration automation** (2 days):
   - Pre-deployment schema validation
   - Backward-compatible migrations
   - Automatic rollback on failure
   - Zero-downtime migration strategy

4. **Production observability** (3 days):
   - Real-time error tracking (Sentry)
   - Performance monitoring (DataDog/New Relic)
   - Custom metrics and dashboards
   - Alert escalation policies

**Expected Outcome**: Enterprise-grade deployment with < 0.01% error rate

### Phase 4: CI/CD Experimentation (Ongoing) 🔵
**Objective**: Safe testing of CI/CD improvements

1. **Create experimental branch pattern** (1 hour):
   - Document `ci-experimental/*` workflow
   - Provide example experimental workflows
   - Guidelines for testing and validation

2. **Implement feature flags** (1 week):
   - Runtime feature toggles
   - A/B testing infrastructure
   - Gradual feature rollout
   - User cohort targeting

3. **Advanced test strategies** (ongoing):
   - Visual regression testing
   - Accessibility testing (automated)
   - Performance budgets enforcement
   - Security scanning (SAST/DAST)

**Expected Outcome**: Rapid iteration on CI/CD with zero production risk

---

## 9. Monitoring & Alerts

### 9.1 Deployment Health Metrics

Track these metrics for every deployment:

| Metric | Threshold | Action |
|--------|-----------|--------|
| Fast test duration | < 5 min | Alert if > 7 min |
| Deployment duration | < 2 min | Alert if > 4 min |
| E2E test duration | < 15 min | Alert if > 20 min |
| Health check failures | 0 consecutive | Rollback after 3 failures |
| Error rate (5 min window) | < 1% | Rollback if > 5% |
| Response time (p95) | < 2s | Alert if > 5s |
| Coverage (backend) | ≥ 85% | Block PR if < 85% |

### 9.2 Alert Channels

```yaml
Alerts:
  Critical (immediate rollback):
    - Health checks failing
    - Error rate spike (> 5%)
    - Services unresponsive
    → Slack #incidents, PagerDuty

  Warning (investigate within 1 hour):
    - E2E tests failing
    - Performance degradation
    - Coverage drop
    → Slack #dev-alerts

  Informational:
    - Deployment completed
    - Test suite passed
    - New release deployed
    → Slack #deployments
```

### 9.3 Observability Stack

**Recommended Tools**:

1. **Error Tracking**: Sentry
   - Real-time error monitoring
   - Source map support
   - User impact tracking
   - Release tracking

2. **Performance Monitoring**: DataDog or New Relic
   - APM (Application Performance Monitoring)
   - Real user monitoring (RUM)
   - Database query performance
   - Custom metrics

3. **Logging**: ELK Stack or CloudWatch
   - Centralized log aggregation
   - Log correlation by request ID
   - Full-text search
   - Retention policies

4. **Uptime Monitoring**: UptimeRobot or Pingdom
   - External health checks
   - Multi-region monitoring
   - Status page generation
   - Incident notifications

---

## 10. Key Architectural Decisions

### 10.1 Why E2E Tests Don't Block Staging

**Problem**: E2E tests take 10-15 minutes, delaying feedback and blocking hotfixes.

**Solution**: Run E2E tests post-deployment as validation, not as gate.

**Rationale**:
- ✅ Fast feedback loop for developers (< 5 minutes)
- ✅ Staging always reflects latest code for QA testing
- ✅ E2E failures inform but don't prevent iterations
- ✅ Production still requires green E2E before promotion
- ✅ Rollback capability handles post-deploy issues

**Risk Mitigation**:
- Strong fast tests catch 95% of issues
- Automatic rollback on health check failures
- Manual QA validation before production
- E2E results tracked and must be green for production

### 10.2 Why Separate CI-Experimental Branches

**Problem**: Testing CI/CD changes can break staging pipeline or waste GitHub Actions minutes.

**Solution**: Dedicated `ci-experimental/*` branches with isolated workflows.

**Rationale**:
- ✅ Safe testing of workflow changes
- ✅ No impact on staging or production
- ✅ Iterate quickly without fear
- ✅ Easy cleanup (delete branch when done)
- ✅ Learn before applying to main pipeline

**Usage Pattern**:
1. Create branch: `ci-experimental/new-caching-strategy`
2. Add workflow: `.github/workflows/experimental-caching.yml`
3. Test changes: Push commits, observe results
4. Validate: Compare metrics (runtime, cost, reliability)
5. Merge to develop: Copy validated changes to main workflows
6. Cleanup: Delete experimental branch and workflow

### 10.3 Why Keep Manual Deployment Option

**Problem**: CI/CD can fail, GitHub can be down, or emergency hotfixes needed.

**Solution**: Maintain `scripts/deploy.sh` as standalone deployment script.

**Rationale**:
- ✅ Reliability: Not locked into CI/CD
- ✅ Flexibility: Direct server deployments
- ✅ Emergency response: Critical hotfixes
- ✅ Debugging: Test deployment scripts manually
- ✅ Business continuity: No single point of failure

**Best Practice**: Prefer CI/CD for regular deployments, manual for emergencies only.

---

## 11. Success Metrics

Track these KPIs to measure pipeline effectiveness:

### 11.1 Speed Metrics

| Metric | Current | Target (3 months) |
|--------|---------|-------------------|
| PR feedback time | 5 min | < 3 min |
| Staging deploy time | 7 min (blocked by E2E) | < 5 min (E2E post-deploy) |
| E2E test duration | 15 min | < 8 min (parallelized) |
| Production deploy time | Manual | < 10 min (automated) |
| Rollback time | Manual (10 min) | < 1 min (automated) |

### 11.2 Quality Metrics

| Metric | Current | Target (3 months) |
|--------|---------|-------------------|
| Test coverage (backend) | 85% | > 90% |
| E2E test pass rate | ~70% (flaky) | > 95% |
| Production error rate | Unknown | < 0.1% |
| Staging uptime | ~95% | > 99.5% |
| False positive rate | ~20% | < 5% |

### 11.3 Cost Metrics

| Metric | Current | Target (3 months) |
|--------|---------|-------------------|
| Monthly GHA minutes | ~12,000 | < 6,000 |
| Monthly GHA cost | ~$80 | < $40 |
| Cost per deployment | ~$1.50 | < $0.75 |
| Developer hours saved | N/A | 10 hrs/week |

### 11.4 Reliability Metrics

| Metric | Current | Target (3 months) |
|--------|---------|-------------------|
| Deployment success rate | ~85% | > 98% |
| Rollback incidents | Manual only | < 2/month |
| Mean time to recovery (MTTR) | ~30 min | < 5 min |
| Change failure rate | Unknown | < 5% |

---

## 12. References & Resources

### Internal Documentation
- `scripts/deploy.sh` - Standalone deployment script
- `docs/deployment-architecture.md` - Manual deployment options
- `docs/clerk-deployment-checklist.md` - Clerk authentication setup
- `docs/fixes/2025-10-24-cors-error-fix.md` - CORS configuration

### Workflow Files
- `.github/workflows/test-suite.yml` - Fast test pipeline
- `.github/workflows/deploy-staging.yml` - Staging deployment
- `.github/workflows/e2e-staging.yml` - E2E validation

### External Resources
- [GitHub Actions Best Practices](https://docs.github.com/en/actions/learn-github-actions/usage-limits-billing-and-administration)
- [Playwright Parallelization](https://playwright.dev/docs/test-parallel)
- [PM2 Cluster Mode](https://pm2.keymetrics.io/docs/usage/cluster-mode/)
- [Zero-Downtime Deployments](https://docs.nginx.com/nginx/admin-guide/load-balancer/http-health-check/)

---

## 13. Appendix: Workflow YAML Examples

### A. Fast Tests (Blocking)

```yaml
# .github/workflows/test-suite.yml
name: Test Suite

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
    name: Frontend Fast Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Check for frontend changes
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

      - name: Install dependencies
        if: steps.changes.outputs.frontend == 'true'
        working-directory: frontend
        run: npm ci

      - name: Lint
        if: steps.changes.outputs.frontend == 'true'
        working-directory: frontend
        run: npm run lint

      - name: Type check
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
          NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: ${{ secrets.CLERK_PUBLISHABLE_KEY_CI_TEST }}
          CLERK_SECRET_KEY: dummy
        run: npm run build

  backend-tests:
    name: Backend Fast Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Check for backend changes
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

      - name: Start MongoDB
        if: steps.changes.outputs.backend == 'true'
        run: |
          docker run -d --name mongo -p 27017:27017 \
            --health-cmd="mongosh --eval 'db.runCommand({ping:1})'" \
            --health-interval=10s --health-timeout=5s --health-retries=5 \
            mongo:6

      - name: Wait for MongoDB
        if: steps.changes.outputs.backend == 'true'
        run: |
          for i in {1..20}; do
            docker inspect --format='{{json .State.Health.Status}}' mongo | grep -q healthy && break || sleep 2
          done

      - name: Run tests
        if: steps.changes.outputs.backend == 'true'
        working-directory: backend
        env:
          DATABASE_URI: mongodb://localhost:27017
          DATABASE_NAME: autoauthor_test
          OPENAI_AUTOAUTHOR_API_KEY: test-key
          CLERK_API_KEY: test-key
          CLERK_JWT_PUBLIC_KEY: test
          CLERK_FRONTEND_API: https://example.dev
          CLERK_BACKEND_API: https://api.clerk.dev
          ENVIRONMENT: test
        run: |
          $HOME/.cargo/bin/uv run pip install -r requirements.txt
          $HOME/.cargo/bin/uv run pip install pytest pytest-cov
          $HOME/.cargo/bin/uv run pytest tests/ \
            --cov=app --cov-report=term-missing --cov-report=xml:coverage.xml \
            --ignore=tests/test_debug_chapter_questions.py \
            --ignore=tests/test_debug_questions.py \
            --ignore=tests/test_e2e_no_mocks.py \
            -k "not test_generate_toc_endpoint and not test_toc_generation_workflow_e2e"

      - name: Upload coverage
        if: steps.changes.outputs.backend == 'true'
        uses: codecov/codecov-action@v4
        with:
          files: backend/coverage.xml
          flags: backend
          fail_ci_if_error: true
```

### B. Staging Deployment (Automatic)

```yaml
# .github/workflows/deploy-staging.yml
name: Deploy to Staging

on:
  workflow_run:
    workflows: ["Test Suite"]
    types: [completed]
    branches: [develop]

jobs:
  deploy:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    # Only deploy if tests passed
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    environment:
      name: staging
      url: https://dev.autoauthor.app
    env:
      HOST: ${{ secrets.HOST }}
      USER: ${{ secrets.USER }}

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.SSH_KEY }}" > ~/.ssh/staging_key
          chmod 600 ~/.ssh/staging_key
          ssh-keyscan -H "$HOST" >> ~/.ssh/known_hosts

      - name: Create release directory
        run: |
          RELEASE_ID=$(date +%Y%m%d-%H%M%S)
          echo "RELEASE_ID=$RELEASE_ID" >> $GITHUB_ENV
          ssh -i ~/.ssh/staging_key $USER@$HOST \
            "mkdir -p /opt/auto-author/releases/$RELEASE_ID"

      - name: Rsync code to server
        run: |
          rsync -az --delete \
            --exclude '.git' \
            --exclude 'node_modules' \
            --exclude '.venv' \
            --exclude '__pycache__' \
            --exclude '*.log' \
            --exclude '.next' \
            ./ $USER@$HOST:/opt/auto-author/releases/${{ env.RELEASE_ID }}/

      - name: Deploy on server
        run: |
          ssh -i ~/.ssh/staging_key $USER@$HOST \
            "export API_URL='${{ secrets.API_URL }}' && \
             export FRONTEND_URL='${{ secrets.FRONTEND_URL }}' && \
             export CLERK_PUBLISHABLE_KEY='${{ secrets.CLERK_PUBLISHABLE_KEY }}' && \
             export CLERK_SECRET_KEY='${{ secrets.CLERK_SECRET_KEY }}' && \
             export DATABASE_URI='${{ secrets.DATABASE_URI }}' && \
             export DATABASE_NAME='${{ secrets.DATABASE_NAME }}' && \
             export OPENAI_API_KEY='${{ secrets.OPENAI_API_KEY }}' && \
             export CLERK_WEBHOOK_SECRET='${{ secrets.CLERK_WEBHOOK_SECRET }}' && \
             bash /opt/auto-author/releases/${{ env.RELEASE_ID }}/scripts/deploy.sh /opt/auto-author/releases/${{ env.RELEASE_ID }}"

      - name: Health checks
        run: |
          echo "⏳ Waiting for services to be healthy..."
          for i in {1..10}; do
            curl -f https://api.dev.autoauthor.app/api/v1/health && break || sleep 5
          done
          for i in {1..10}; do
            curl -f https://dev.autoauthor.app && break || sleep 5
          done
          echo "✅ Deployment complete and healthy"

      - name: Cleanup SSH keys
        if: always()
        run: rm -f ~/.ssh/staging_key

      - name: Notify deployment success
        if: success()
        run: |
          echo "🚀 Staging deployment successful"
          echo "📦 Release: ${{ env.RELEASE_ID }}"
          echo "🔗 URL: https://dev.autoauthor.app"
```

### C. E2E Validation (Non-Blocking)

```yaml
# .github/workflows/e2e-staging.yml
name: E2E Tests (Post-Deployment Validation)

on:
  workflow_run:
    workflows: ["Deploy to Staging"]
    types: [completed]
    branches: [develop]
  workflow_dispatch:
    inputs:
      staging_url:
        description: 'Staging URL'
        required: false
        default: 'https://dev.autoauthor.app'

env:
  STAGING_URL: https://dev.autoauthor.app
  STAGING_API_URL: https://api.dev.autoauthor.app

jobs:
  e2e-validation:
    name: E2E Validation Suite
    runs-on: ubuntu-latest
    # Run only if deployment succeeded
    if: ${{ github.event.workflow_run.conclusion == 'success' || github.event_name == 'workflow_dispatch' }}
    environment:
      name: staging
      url: https://dev.autoauthor.app

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install frontend dependencies
        working-directory: frontend
        run: npm ci

      - name: Install Playwright
        working-directory: frontend
        run: npx playwright install --with-deps chromium

      - name: Wait for staging readiness
        run: |
          echo "⏳ Waiting for staging to be ready..."
          max_attempts=30
          attempt=0

          while [ $attempt -lt $max_attempts ]; do
            if curl -f -s ${{ env.STAGING_API_URL }}/api/v1/health > /dev/null; then
              echo "✅ Staging is ready!"
              break
            fi

            echo "🔄 Attempt $((attempt + 1))/$max_attempts"
            sleep 10
            attempt=$((attempt + 1))
          done

          if [ $attempt -eq $max_attempts ]; then
            echo "❌ Staging did not become ready"
            exit 1
          fi

      - name: Run Playwright E2E tests
        working-directory: frontend
        run: npx playwright test tests/e2e/deployment --config=tests/e2e/deployment/playwright.config.ts
        env:
          DEPLOYMENT_URL: ${{ env.STAGING_URL }}
          BASE_URL: ${{ env.STAGING_URL }}
          TEST_USER_EMAIL: ${{ secrets.TEST_USER_EMAIL }}
          TEST_USER_PASSWORD: ${{ secrets.TEST_USER_PASSWORD }}
          NEXT_PUBLIC_API_URL: ${{ env.STAGING_API_URL }}/api/v1
          NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: ${{ secrets.CLERK_PUBLISHABLE_KEY }}

      - name: Install backend dependencies
        working-directory: backend
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          export PATH="$HOME/.cargo/bin:$PATH"
          uv venv
          source .venv/bin/activate
          uv pip install -r requirements.txt
          uv pip install pytest pytest-asyncio

      - name: Run backend E2E tests
        working-directory: backend
        run: |
          source .venv/bin/activate
          pytest tests/test_e2e_no_mocks.py \
            tests/test_debug_chapter_questions.py \
            tests/test_debug_questions.py \
            tests/test_api/test_routes/test_toc_generation.py::test_generate_toc_endpoint \
            tests/test_api/test_routes/test_toc_generation.py::test_toc_generation_workflow_e2e \
            -v --tb=short
        env:
          DATABASE_URI: mongodb://localhost:27017
          DATABASE_NAME: autoauthor_e2e_test
          OPENAI_AUTOAUTHOR_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          CLERK_API_KEY: ${{ secrets.CLERK_SECRET_KEY }}
          CLERK_JWT_PUBLIC_KEY: ${{ secrets.CLERK_PUBLISHABLE_KEY }}
          CLERK_FRONTEND_API: https://delicate-ladybird-47.clerk.accounts.dev
          CLERK_BACKEND_API: https://api.clerk.dev
          BASE_URL: ${{ env.STAGING_API_URL }}
          ENVIRONMENT: staging

      - name: Upload Playwright reports
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-e2e-report
          path: frontend/playwright-report/
          retention-days: 7

      - name: Upload backend logs
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: backend-e2e-logs
          path: backend/test-logs/
          retention-days: 7

      - name: Notify E2E results
        if: always()
        run: |
          if [ "${{ job.status }}" == "success" ]; then
            echo "✅ E2E validation passed - staging is production-ready"
          else
            echo "❌ E2E validation failed - investigate before production promotion"
            echo "📊 View test reports in artifacts"
          fi
```

### D. Experimental Workflow Template

```yaml
# .github/workflows/experimental-test-optimization.yml
name: Experimental - Test Parallelization

on:
  push:
    branches:
      - ci-experimental/test-optimization

jobs:
  test-parallel-e2e:
    name: Test Parallel E2E Execution
    runs-on: ubuntu-latest
    strategy:
      matrix:
        shard: [1, 2, 3, 4]

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        working-directory: frontend
        run: npm ci

      - name: Install Playwright
        run: npx playwright install --with-deps chromium

      - name: Run E2E tests (shard ${{ matrix.shard }}/4)
        working-directory: frontend
        run: npx playwright test --shard=${{ matrix.shard }}/4
        env:
          BASE_URL: https://dev.autoauthor.app

      - name: Upload shard results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-shard-${{ matrix.shard }}
          path: frontend/playwright-report/
          retention-days: 1

  merge-results:
    name: Merge Test Results
    runs-on: ubuntu-latest
    needs: test-parallel-e2e
    if: always()

    steps:
      - name: Download all shard results
        uses: actions/download-artifact@v4
        with:
          path: all-shards

      - name: Merge and analyze results
        run: |
          echo "📊 Analyzing parallel execution results..."
          # Custom merge logic here
```

---

## 14. Conclusion

This deployment pipeline architecture provides:

✅ **Speed**: Fast feedback (< 5 min) for developers
✅ **Quality**: Comprehensive testing without blocking deployments
✅ **Cost**: 50-60% reduction in GitHub Actions costs
✅ **Flexibility**: Support for CI/CD experimentation
✅ **Reliability**: Automatic rollback and health monitoring
✅ **Scalability**: Ready for production-grade requirements

**Next Steps**:
1. Review and approve architecture
2. Implement Phase 1 (critical path)
3. Validate with team
4. Iterate based on metrics
5. Expand to production pipeline

---

**Document Version**: 1.0
**Last Updated**: 2025-10-24
**Review Cycle**: Quarterly
**Owner**: DevOps Team
