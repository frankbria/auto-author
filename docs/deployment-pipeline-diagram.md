# Deployment Pipeline Visual Diagrams
## Auto-Author CI/CD Architecture

**Companion to**: `deployment-pipeline-architecture.md`
**Date**: 2025-10-24

---

## 1. Current State vs. Proposed Architecture

### Current State (Blocking)
```
┌─────────────────────────────────────────────────────────────────┐
│ Developer pushes to develop                                     │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 1: Fast Tests (3-5 min)                                  │
│ ├─ Frontend: lint, typecheck, unit, build                      │
│ └─ Backend: unit tests, coverage                               │
│ Result: ✅ PASS                                                 │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 2: E2E Tests (10-15 min) ⚠️ BLOCKS DEPLOYMENT            │
│ ├─ Playwright tests                                            │
│ └─ Backend integration tests                                   │
│ Result: ❌ FAILING (flaky, blocking staging)                   │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼ (ONLY IF E2E PASSES)
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 3: Deploy to Staging ⛔ BLOCKED                          │
│ └─ Waiting for E2E to pass...                                  │
└─────────────────────────────────────────────────────────────────┘

❌ Problems:
- Staging blocked by flaky E2E tests
- 15+ minute feedback loop
- Can't deploy hotfixes quickly
- Team blocked on CI/CD
```

### Proposed Architecture (Non-Blocking)
```
┌─────────────────────────────────────────────────────────────────┐
│ Developer pushes to develop                                     │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 1: Fast Tests (3-5 min) ✅ BLOCKS DEPLOYMENT             │
│ ├─ Frontend: lint, typecheck, unit, build                      │
│ └─ Backend: unit tests, coverage                               │
│ Result: ✅ PASS                                                 │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 2: Deploy to Staging (1-2 min) ✅ AUTOMATIC              │
│ ├─ Rsync code to server                                        │
│ ├─ Run deploy.sh                                               │
│ └─ Health checks                                               │
│ Result: ✅ DEPLOYED                                             │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 3: E2E Validation (10-15 min) ℹ️ INFORMATIONAL           │
│ ├─ Playwright tests (parallel)                                 │
│ └─ Backend integration tests                                   │
│ Result: ❌ FAILED → Alerts team, staging stays deployed        │
└─────────────────────────────────────────────────────────────────┘

✅ Benefits:
- Fast staging deployment (< 7 min total)
- E2E validates post-deployment
- Hotfixes unblocked
- Production requires green E2E
```

---

## 2. Branch Strategy Flow

```
┌───────────────────────────────────────────────────────────────────┐
│                          BRANCH STRUCTURE                         │
└───────────────────────────────────────────────────────────────────┘

                     ┌─────────────────┐
                     │   ci-experimental/*   │ 🧪 No protection
                     │   (CI/CD testing)     │ No auto-deploy
                     └─────────────────┘ No blocking tests
                            ↓ (merge after validation)
                     ┌─────────────────┐
                     │  feature/xyz    │ 🔨 Development
                     │  hotfix/urgent  │ Fast tests on PR
                     └─────────────────┘ Review required
                            ↓ (PR merge)
                     ┌─────────────────┐
                     │     develop     │ 🚀 Staging auto-deploy
                     │   (staging)     │ Fast tests block
                     └─────────────────┘ E2E post-deploy
                            ↓ (manual promotion)
                     ┌─────────────────┐
                     │      main       │ 🏆 Production
                     │  (production)   │ All tests required
                     └─────────────────┘ Manual approval


┌───────────────────────────────────────────────────────────────────┐
│                       DEPLOYMENT FLOW                             │
└───────────────────────────────────────────────────────────────────┘

Feature Development:
  1. Create: git checkout -b feature/new-feature develop
  2. Develop: Make changes, commit frequently
  3. PR: Open PR to develop → Fast tests run
  4. Review: Code review + fast tests pass
  5. Merge: Squash merge to develop
  6. Deploy: Automatic staging deployment
  7. Validate: E2E tests run (informational)

CI/CD Experimentation:
  1. Create: git checkout -b ci-experimental/new-workflow develop
  2. Add: .github/workflows/experimental-*.yml
  3. Test: Push changes, observe workflow behavior
  4. Validate: Compare metrics (time, cost, reliability)
  5. Merge: Copy validated changes to main workflows
  6. Cleanup: Delete experimental branch

Emergency Hotfix:
  1. Create: git checkout -b hotfix/critical-fix main
  2. Fix: Minimal changes to resolve issue
  3. Test: Run fast tests locally
  4. Deploy: Manual deployment (bypass CI/CD if needed)
  5. Verify: Manual QA + monitoring
  6. Merge: To main + backport to develop
```

---

## 3. Test Execution Decision Tree

```
┌───────────────────────────────────────────────────────────────────┐
│                      TEST EXECUTION MATRIX                        │
└───────────────────────────────────────────────────────────────────┘

Event: PR opened/updated
├─ Path filter
│  ├─ Frontend changed?
│  │  └─ Run: lint, typecheck, unit, build (3 min)
│  ├─ Backend changed?
│  │  └─ Run: unit tests, coverage check (2 min)
│  └─ Neither changed?
│     └─ Skip: No tests needed
├─ Result: PASS ✅
│  └─ Allow merge (after review)
└─ Result: FAIL ❌
   └─ Block merge

Event: Push to develop
├─ STAGE 1: Fast Tests (BLOCKING)
│  ├─ Run: Frontend + backend fast tests
│  ├─ Pass? Continue ✅
│  └─ Fail? Stop, alert ❌
│
├─ STAGE 2: Deployment (AUTOMATIC)
│  ├─ Run: Rsync + deploy.sh + health checks
│  ├─ Pass? Staging deployed ✅
│  └─ Fail? Stop, alert, rollback ❌
│
└─ STAGE 3: E2E Validation (INFORMATIONAL)
   ├─ Run: Playwright + backend E2E tests
   ├─ Pass? Ready for production ✅
   └─ Fail? Alert team, staging stays deployed ⚠️

Event: Push to main (production)
├─ STAGE 1: Fast Tests (BLOCKING)
│  └─ Must pass ✅
│
├─ STAGE 2: E2E Tests (BLOCKING)
│  └─ Must pass ✅
│
├─ STAGE 3: Manual Approval (BLOCKING)
│  └─ QA signoff required ✅
│
└─ STAGE 4: Production Deployment (MANUAL)
   ├─ Blue-green deployment
   ├─ Canary release (5% → 100%)
   └─ Monitoring + rollback ready
```

---

## 4. Test Type Breakdown

```
┌───────────────────────────────────────────────────────────────────┐
│                     TEST PYRAMID & TIMING                         │
└───────────────────────────────────────────────────────────────────┘

                        ┌───────────┐
                        │    E2E    │ 10-15 min
                        │  15 tests │ POST-DEPLOY ℹ️
                        └───────────┘ (Informational)
                      ┌───────────────┐
                      │  Integration  │ 1-2 min
                      │   40 tests    │ BLOCKS 🚫
                      └───────────────┘ (Pre-deploy)
                  ┌───────────────────────┐
                  │     Unit Tests        │ < 1 min
                  │     200+ tests        │ BLOCKS 🚫
                  └───────────────────────┘ (Pre-deploy)
              ┌─────────────────────────────┐
              │    Lint + Typecheck         │ < 1 min
              │   Static Analysis           │ BLOCKS 🚫
              └─────────────────────────────┘ (Pre-deploy)


┌───────────────────────────────────────────────────────────────────┐
│                    TEST COVERAGE BY LAYER                         │
└───────────────────────────────────────────────────────────────────┘

Unit Tests (< 1 min, 200+ tests):
├─ Frontend
│  ├─ Component rendering (Jest + RTL)
│  ├─ Utility functions
│  ├─ State management
│  └─ Form validation
└─ Backend
   ├─ Service layer logic
   ├─ Data models
   ├─ Utility functions
   └─ Error handling

Integration Tests (1-2 min, 40 tests):
├─ Frontend
│  ├─ API client integration
│  ├─ Route navigation
│  └─ Complex component interactions
└─ Backend
   ├─ API endpoints (mocked DB)
   ├─ Authentication flows
   ├─ Database operations (containerized)
   └─ External API integration (mocked)

E2E Tests (10-15 min, 15 tests):
├─ Frontend (Playwright)
│  ├─ User authentication (Clerk)
│  ├─ Book CRUD operations
│  ├─ TOC generation wizard
│  ├─ Chapter editor (TipTap)
│  └─ Export (PDF/DOCX)
└─ Backend (Real APIs)
   ├─ Complete workflows (OpenAI)
   ├─ Database persistence (MongoDB)
   └─ Authentication integration
```

---

## 5. Deployment Pipeline Detailed Flow

```
┌───────────────────────────────────────────────────────────────────┐
│              DETAILED DEPLOYMENT SEQUENCE                         │
└───────────────────────────────────────────────────────────────────┘

[Developer] git push origin develop
     │
     ▼
[GitHub] Trigger: test-suite.yml
     │
     ├─────────────────────────┬────────────────────────┐
     │                         │                        │
     ▼                         ▼                        ▼
[Frontend Tests]        [Backend Tests]         [Path Filter]
3-5 min                 2-3 min                  Skip if unchanged
     │                         │                        │
     └─────────────────────────┴────────────────────────┘
                               │
                         [All PASS?]
                               │
                    ┌──────────┴──────────┐
                    │                     │
                   YES ✅                NO ❌
                    │                     │
                    │                     └─> [Block] Stop, alert
                    │
                    ▼
     [GitHub] Trigger: deploy-staging.yml
                    │
                    ▼
          [Create Release Dir]
           timestamp: 20251024-143022
                    │
                    ▼
            [Rsync to Server]
         Excludes: .git, node_modules,
                .venv, __pycache__
                    │
                    ▼
          [Execute deploy.sh]
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
  [Backend Setup]        [Frontend Setup]
  - uv install           - npm install
  - Create .env          - Create .env.production
  - PM2 restart          - npm run build
                         - PM2 restart
        │                       │
        └───────────┬───────────┘
                    │
                    ▼
          [Atomic Symlink Switch]
       /opt/auto-author/current
    → /opt/auto-author/releases/20251024-143022
                    │
                    ▼
             [Health Checks]
          10 retries, 5s delay
        - API: /api/v1/health
        - Frontend: /
                    │
                    ▼
        ┌───────────┴───────────┐
        │                       │
      PASS ✅                 FAIL ❌
        │                       │
        │                       ├─> [Alert] DevOps team
        │                       └─> [Rollback] Previous release
        │
        ▼
[GitHub] Trigger: e2e-staging.yml
        │
        ├──────────────────┐
        │                  │
        ▼                  ▼
  [Playwright]      [Backend E2E]
   10 min             5 min
        │                  │
        └──────────┬───────┘
                   │
             [Results]
                   │
        ┌──────────┴──────────┐
        │                     │
      PASS ✅               FAIL ❌
        │                     │
        │                     ├─> [Alert] Test failures (Slack)
        │                     ├─> [Artifacts] Upload reports
        │                     └─> [Status] Staging remains deployed
        │
        ▼
   [Status Badge]
 Production Ready ✅
```

---

## 6. Rollback Strategy Flow

```
┌───────────────────────────────────────────────────────────────────┐
│                    ROLLBACK DECISION TREE                         │
└───────────────────────────────────────────────────────────────────┘

[Issue Detected]
      │
      ▼
[Severity Assessment]
      │
      ├─────────────────┬─────────────────┬──────────────────┐
      │                 │                 │                  │
      ▼                 ▼                 ▼                  ▼
[CRITICAL]        [HIGH]           [MEDIUM]           [LOW]
- 500 errors      - Broken feature - UI glitches     - Minor bugs
- Auth broken     - Data loss risk - Slow responses  - Cosmetic
- Site down       - Security issue - E2E failures    - Typos
      │                 │                 │                  │
      ▼                 ▼                 ▼                  ▼
[Immediate       [Rollback         [Investigate]     [Fix Forward]
 Rollback]        if unfixed       - 15 min window   - Next deploy
 < 1 min          in 5 min]        - Monitor closely - Track in issue
      │                 │                 │                  │
      └─────────────────┴─────────────────┴──────────────────┘
                               │
                               ▼
                      [Rollback Process]
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
              [Automatic]           [Manual]
          Health check failure   SSH to server
          Error rate > 5%        Run rollback.sh
                    │                     │
                    └──────────┬──────────┘
                               │
                               ▼
                    [Identify Previous Release]
                     ls -t releases | sed -n '2p'
                               │
                               ▼
                    [Atomic Symlink Switch]
                  ln -sfn releases/PREVIOUS current
                               │
                               ▼
                      [Restart Services]
                        pm2 restart all
                               │
                               ▼
                      [Verify Health Checks]
                     curl /api/v1/health
                               │
                               ▼
                      [Post-Rollback Actions]
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
              [Alert Team]          [Incident Report]
           Slack: #incidents       Document root cause
           Status: Rolled back     Action items
                                   Timeline
```

---

## 7. Cost Optimization Breakdown

```
┌───────────────────────────────────────────────────────────────────┐
│              GITHUB ACTIONS COST ANALYSIS                         │
└───────────────────────────────────────────────────────────────────┘

Current State (per deployment):
┌────────────────────────────────────────────────────────┐
│ Fast Tests:     3 min                                  │
│ E2E Tests:     15 min (BLOCKS deployment)              │
│ Deployment:     2 min (waits for E2E)                  │
├────────────────────────────────────────────────────────┤
│ Total:         20 min per deploy                       │
│                                                        │
│ Monthly (20 deploys/day × 30 days):                   │
│ = 20 × 20 × 30 = 12,000 minutes                       │
│ Cost: (12,000 - 2,000 free) × $0.008 = $80/month      │
└────────────────────────────────────────────────────────┘

Optimized State (with proposed architecture):
┌────────────────────────────────────────────────────────┐
│ Fast Tests:     3 min (parallel, cached)               │
│ Deployment:     2 min (IMMEDIATE after fast tests)     │
│ E2E Tests:      7 min (parallel, post-deploy)          │
├────────────────────────────────────────────────────────┤
│ Total:         12 min per deploy (40% reduction)       │
│                                                        │
│ Monthly (20 deploys/day × 30 days):                   │
│ = 20 × 12 × 30 = 7,200 minutes                        │
│ Cost: (7,200 - 2,000 free) × $0.008 = $41.60/month    │
│                                                        │
│ Savings: $38.40/month (48% reduction)                 │
└────────────────────────────────────────────────────────┘

With Scheduled Full Tests (night/weekend):
┌────────────────────────────────────────────────────────┐
│ Per-Deploy:                                            │
│ - Fast Tests:     3 min                                │
│ - Deployment:     2 min                                │
│ - Smoke E2E:      3 min (critical paths only)          │
│ = 8 min/deploy                                         │
│                                                        │
│ Scheduled (1x/night):                                  │
│ - Full E2E Suite: 15 min × 1/day × 30 days = 450 min  │
│                                                        │
│ Monthly Total:                                         │
│ = (20 × 8 × 30) + 450 = 5,250 minutes                 │
│ Cost: (5,250 - 2,000 free) × $0.008 = $26/month       │
│                                                        │
│ Savings: $54/month (67.5% reduction)                  │
└────────────────────────────────────────────────────────┘
```

---

## 8. Implementation Timeline

```
┌───────────────────────────────────────────────────────────────────┐
│                   IMPLEMENTATION ROADMAP                          │
└───────────────────────────────────────────────────────────────────┘

WEEK 1: Critical Path 🔴
├─ Day 1-2: Modify workflow dependencies
│  ├─ Update e2e-staging.yml (post-deploy)
│  ├─ Remove E2E as blocker
│  └─ Test workflow changes on ci-experimental branch
│
├─ Day 3: Add failure notifications
│  ├─ Slack webhook integration
│  ├─ E2E failure alerts
│  └─ Deployment status notifications
│
├─ Day 4: Create rollback script
│  ├─ scripts/rollback.sh
│  ├─ Health check validation
│  └─ Test rollback procedure
│
└─ Day 5: Documentation & validation
   ├─ Update deployment docs
   ├─ Team training session
   └─ End-to-end testing

WEEK 2: Optimization 🟡
├─ Day 1-2: Parallelize E2E tests
│  ├─ Configure Playwright shards (4 workers)
│  ├─ Update workflow matrix
│  └─ Validate 50% runtime reduction
│
├─ Day 3: Test categorization
│  ├─ Smoke tests: < 3 min
│  ├─ Full tests: 10+ min
│  └─ Schedule full tests (nightly)
│
└─ Day 4-5: Health monitoring
   ├─ Post-deploy monitoring (5 min window)
   ├─ Automatic rollback triggers
   └─ Metrics dashboard

WEEK 3-4: Advanced Features 🟢
├─ Blue-green deployment
├─ Canary releases (5% → 100%)
├─ Database migration automation
└─ Production observability

ONGOING: CI/CD Experimentation 🔵
└─ ci-experimental/* branches for testing


┌───────────────────────────────────────────────────────────────────┐
│                      SUCCESS METRICS                              │
└───────────────────────────────────────────────────────────────────┘

Week 1 Targets:
├─ Staging deploy time: < 5 min (from 20+ min)
├─ E2E failures: Don't block staging
├─ Rollback time: < 1 min (automated)
└─ Team velocity: Unblocked deployments

Week 2 Targets:
├─ E2E runtime: < 8 min (from 15 min)
├─ Cost reduction: 40%+ savings
├─ Test reliability: 95%+ pass rate
└─ Health monitoring: Real-time alerts

Week 4 Targets:
├─ Production deployments: < 10 min
├─ Zero-downtime: 100% uptime
├─ Error rate: < 0.1%
└─ MTTR: < 5 min (mean time to recovery)
```

---

## 9. Monitoring Dashboard

```
┌───────────────────────────────────────────────────────────────────┐
│                    CI/CD METRICS DASHBOARD                        │
└───────────────────────────────────────────────────────────────────┘

Pipeline Performance:
┌──────────────────────────┬─────────┬─────────┬──────────┐
│ Metric                   │ Current │ Target  │ Status   │
├──────────────────────────┼─────────┼─────────┼──────────┤
│ Fast Test Duration       │   5 min │  < 3 m  │ 🟡       │
│ Deployment Duration      │   2 min │  < 2 m  │ ✅       │
│ E2E Test Duration        │  15 min │  < 8 m  │ 🔴       │
│ Total Pipeline Time      │  22 min │ < 13 m  │ 🔴       │
│ Staging Deploy Time      │   7 min │  < 5 m  │ 🟡       │
└──────────────────────────┴─────────┴─────────┴──────────┘

Quality Metrics:
┌──────────────────────────┬─────────┬─────────┬──────────┐
│ Metric                   │ Current │ Target  │ Status   │
├──────────────────────────┼─────────┼─────────┼──────────┤
│ Test Coverage (Backend)  │     85% │  > 90%  │ 🟡       │
│ E2E Pass Rate            │     70% │  > 95%  │ 🔴       │
│ Deployment Success Rate  │     85% │  > 98%  │ 🟡       │
│ Staging Uptime           │     95% │ > 99.5% │ 🟡       │
│ Production Error Rate    │ Unknown │  < 0.1% │ ⚪       │
└──────────────────────────┴─────────┴─────────┴──────────┘

Cost Metrics:
┌──────────────────────────┬─────────┬─────────┬──────────┐
│ Metric                   │ Current │ Target  │ Status   │
├──────────────────────────┼─────────┼─────────┼──────────┤
│ Monthly GHA Minutes      │  12,000 │  < 6,000│ 🔴       │
│ Monthly GHA Cost         │     $80 │    < $40│ 🔴       │
│ Cost Per Deployment      │   $1.50 │  < $0.75│ 🔴       │
│ Dev Hours Saved/Week     │     N/A │      10h│ ⚪       │
└──────────────────────────┴─────────┴─────────┴──────────┘

Legend:
✅ On track  🟡 At risk  🔴 Needs attention  ⚪ Not yet measured
```

---

## 10. Quick Reference Cards

### For Developers
```
┌───────────────────────────────────────────────────────────────┐
│ DEVELOPER QUICK REFERENCE                                     │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│ Feature Development:                                          │
│ 1. git checkout -b feature/my-feature develop                │
│ 2. Make changes, commit                                       │
│ 3. git push origin feature/my-feature                         │
│ 4. Open PR to develop                                         │
│ 5. Wait for fast tests (3-5 min)                             │
│ 6. Merge after review + tests pass                           │
│ 7. Staging auto-deploys in ~5 min                            │
│                                                               │
│ CI/CD Experiments:                                            │
│ 1. git checkout -b ci-experimental/test-optimization develop │
│ 2. Add/modify workflow in .github/workflows/                 │
│ 3. Test changes (no impact on staging)                       │
│ 4. Validate results                                          │
│ 5. Merge validated changes to main workflows                 │
│                                                               │
│ Emergency Hotfix:                                             │
│ 1. SSH to server: ssh user@dev.autoauthor.app               │
│ 2. Rollback: bash /opt/auto-author/scripts/rollback.sh      │
│ 3. Verify: curl https://dev.autoauthor.app                  │
│ 4. Fix forward on develop                                    │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### For DevOps
```
┌───────────────────────────────────────────────────────────────┐
│ DEVOPS QUICK REFERENCE                                        │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│ Monitor Pipeline:                                             │
│ - GitHub Actions: https://github.com/org/repo/actions       │
│ - Slack alerts: #dev-alerts, #incidents                      │
│ - Metrics dashboard: (coming soon)                           │
│                                                               │
│ Rollback Staging:                                             │
│ ssh user@dev.autoauthor.app                                  │
│ bash /opt/auto-author/scripts/rollback.sh                    │
│                                                               │
│ Manual Staging Deploy:                                        │
│ ssh user@dev.autoauthor.app                                  │
│ cd /opt/auto-author/current                                  │
│ git pull origin develop                                       │
│ bash scripts/deploy.sh /opt/auto-author/current              │
│                                                               │
│ Check Service Status:                                         │
│ ssh user@dev.autoauthor.app                                  │
│ pm2 status                                                    │
│ pm2 logs auto-author-backend --lines 50                      │
│ pm2 logs auto-author-frontend --lines 50                     │
│                                                               │
│ Health Checks:                                                │
│ curl -f https://api.dev.autoauthor.app/api/v1/health        │
│ curl -f https://dev.autoauthor.app                          │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

**Document Version**: 1.0
**Last Updated**: 2025-10-24
**Companion To**: `deployment-pipeline-architecture.md`
