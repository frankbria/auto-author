# Deployment Pipeline Implementation Checklist
## Auto-Author CI/CD Optimization

**Project**: Auto-Author Next.js + FastAPI
**Goal**: Separate E2E tests from blocking staging deployments
**Expected Impact**: 60% faster deployments, 50% cost reduction

---

## Phase 1: Critical Path (Week 1) - IMMEDIATE IMPACT

### Day 1: Workflow Dependency Changes (2 hours)

- [ ] **1.1 Create ci-experimental branch for testing**
  ```bash
  git checkout -b ci-experimental/non-blocking-e2e develop
  ```

- [ ] **1.2 Update e2e-staging.yml workflow**
  - [ ] Change trigger to run AFTER deploy-staging.yml completes
  - [ ] Add `continue-on-error: false` to allow deployment despite E2E failures
  - [ ] Verify E2E job only runs post-deployment
  - [ ] Test workflow on experimental branch

- [ ] **1.3 Update deploy-staging.yml workflow**
  - [ ] Remove E2E test dependency (if any)
  - [ ] Ensure deployment runs immediately after fast tests pass
  - [ ] Add deployment success notification
  - [ ] Test workflow on experimental branch

- [ ] **1.4 Update test-suite.yml workflow**
  - [ ] Verify fast tests (lint, typecheck, unit, build) remain blocking
  - [ ] Ensure path filtering is working correctly
  - [ ] Test workflow on experimental branch

- [ ] **1.5 Validation**
  - [ ] Push test commit to experimental branch
  - [ ] Verify fast tests run and block if failing
  - [ ] Verify deployment happens immediately after fast tests pass
  - [ ] Verify E2E tests run post-deployment without blocking
  - [ ] Document results in PR description

### Day 2: Failure Notifications (1 hour)

- [ ] **2.1 Setup Slack/Discord webhook (choose one)**
  - [ ] Create incoming webhook URL
  - [ ] Add webhook URL to GitHub Secrets
  - [ ] Test webhook with curl

- [ ] **2.2 Add E2E failure notifications**
  - [ ] Create notification step in e2e-staging.yml
  - [ ] Include: commit info, test results, artifact links
  - [ ] Test notification with intentional test failure

- [ ] **2.3 Add deployment notifications**
  - [ ] Success notification (staging deployed)
  - [ ] Failure notification (deployment failed)
  - [ ] Include: release ID, health check status

- [ ] **2.4 Alert routing**
  - [ ] Critical failures → #incidents channel
  - [ ] E2E failures → #dev-alerts channel
  - [ ] Deployments → #deployments channel

### Day 3: Rollback Script (2 hours)

- [ ] **3.1 Create scripts/rollback.sh**
  ```bash
  #!/bin/bash
  # Script to rollback to previous release
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

  # Backend health check
  if ! curl -f https://api.dev.autoauthor.app/api/v1/health; then
    echo "❌ Backend health check failed"
    exit 1
  fi

  # Frontend health check
  if ! curl -f https://dev.autoauthor.app; then
    echo "❌ Frontend health check failed"
    exit 1
  fi

  echo "✅ Rollback complete"
  echo "📦 Rolled back to: $PREVIOUS"
  ```

- [ ] **3.2 Test rollback script**
  - [ ] Deploy to staging
  - [ ] SSH to server
  - [ ] Run rollback script: `bash scripts/rollback.sh`
  - [ ] Verify health checks pass
  - [ ] Verify symlink points to previous release

- [ ] **3.3 Document rollback procedure**
  - [ ] Add rollback instructions to deployment-architecture.md
  - [ ] Include when to use rollback vs fix-forward
  - [ ] Document rollback decision tree

- [ ] **3.4 Add rollback to deploy workflow (optional)**
  - [ ] Create rollback step that runs on deployment failure
  - [ ] Test automatic rollback

### Day 4-5: Documentation & Team Training (1 hour)

- [ ] **4.1 Update documentation**
  - [ ] Update CLAUDE.md with new workflow
  - [ ] Update deployment-architecture.md
  - [ ] Add rollback procedure to runbooks

- [ ] **4.2 Team training**
  - [ ] Schedule 30-min team meeting
  - [ ] Demo new deployment flow
  - [ ] Explain E2E non-blocking strategy
  - [ ] Show rollback procedure
  - [ ] Q&A session

- [ ] **4.3 Create quick reference cards**
  - [ ] Developer workflow card
  - [ ] DevOps rollback card
  - [ ] Emergency procedures

- [ ] **4.4 End-to-end validation**
  - [ ] Deploy feature to staging
  - [ ] Verify fast tests block bad code
  - [ ] Verify E2E failures don't block staging
  - [ ] Test rollback procedure
  - [ ] Monitor Slack notifications

- [ ] **4.5 Merge to develop**
  - [ ] Create PR from ci-experimental branch
  - [ ] Team review
  - [ ] Merge to develop
  - [ ] Monitor first production deployment

---

## Phase 2: Optimization (Week 2) - COST REDUCTION

### Day 1-2: Parallelize E2E Tests (4 hours)

- [ ] **1.1 Configure Playwright sharding**
  - [ ] Update playwright.config.ts
  - [ ] Add shard configuration (4 workers recommended)
  - [ ] Test locally: `npx playwright test --shard=1/4`

- [ ] **1.2 Update e2e-staging.yml workflow**
  - [ ] Add matrix strategy for sharding
  ```yaml
  strategy:
    matrix:
      shard: [1, 2, 3, 4]
  steps:
    - run: npx playwright test --shard=${{ matrix.shard }}/4
  ```
  - [ ] Add artifact upload per shard
  - [ ] Create merge job to combine results

- [ ] **1.3 Test parallel execution**
  - [ ] Run workflow with sharding
  - [ ] Verify runtime reduction (target: 50%)
  - [ ] Verify all tests execute
  - [ ] Check artifact merging

- [ ] **1.4 Validate cost savings**
  - [ ] Compare runtime: before vs after
  - [ ] Calculate GitHub Actions minute savings
  - [ ] Document in deployment-pipeline-architecture.md

### Day 3: Test Categorization (3 hours)

- [ ] **2.1 Categorize existing E2E tests**
  - [ ] Smoke tests: Critical user paths (< 3 min)
    - [ ] User authentication
    - [ ] Create book
    - [ ] Basic navigation
  - [ ] Full tests: Complete coverage (10+ min)
    - [ ] All existing E2E tests

- [ ] **2.2 Create smoke test workflow**
  - [ ] Create .github/workflows/smoke-tests.yml
  - [ ] Configure to run on every staging deployment
  - [ ] Run only smoke tests (3-5 critical tests)

- [ ] **2.3 Schedule full E2E tests**
  - [ ] Update e2e-staging.yml with schedule trigger
  ```yaml
  on:
    schedule:
      - cron: '0 2 * * *'  # 2 AM daily
    workflow_dispatch:  # Manual trigger
  ```
  - [ ] Run full E2E suite nightly
  - [ ] Keep manual trigger for on-demand testing

- [ ] **2.4 Update deployment flow**
  - [ ] Per-deploy: Fast tests + Deployment + Smoke tests (~8 min)
  - [ ] Nightly: Full E2E suite (~15 min)
  - [ ] Document in workflow diagrams

### Day 4-5: Health Monitoring (2 hours)

- [ ] **3.1 Add post-deployment monitoring**
  - [ ] Create monitoring script
  - [ ] Track error rates (5 min window)
  - [ ] Track response times (p95)
  - [ ] Track availability

- [ ] **3.2 Configure automatic rollback triggers**
  - [ ] Health checks fail (3+ consecutive)
  - [ ] Error rate > 5%
  - [ ] Response time > 5s (p95)

- [ ] **3.3 Add monitoring step to deploy-staging.yml**
  - [ ] Run monitoring for 5 minutes post-deploy
  - [ ] Trigger rollback if thresholds breached
  - [ ] Send alerts to Slack

- [ ] **3.4 Create metrics dashboard**
  - [ ] Setup basic dashboard (GitHub Pages or simple HTML)
  - [ ] Display: deployment frequency, success rate, MTTR
  - [ ] Add cost metrics

---

## Phase 3: Advanced Features (Week 3-4) - PRODUCTION READY

### Week 3: Blue-Green & Canary Deployments (1 week)

- [ ] **1.1 Blue-green deployment setup**
  - [ ] Configure two environments: blue, green
  - [ ] Deploy to inactive environment
  - [ ] Run smoke tests on inactive environment
  - [ ] Switch traffic atomically (Nginx/load balancer)
  - [ ] Keep previous environment for instant rollback

- [ ] **1.2 Canary release configuration**
  - [ ] Configure traffic routing (5% → 25% → 50% → 100%)
  - [ ] Monitor error rates per version
  - [ ] Automatic rollback on anomalies
  - [ ] Gradual rollout over 1 hour

- [ ] **1.3 Database migration automation**
  - [ ] Create migration validation script
  - [ ] Backward-compatible migration strategy
  - [ ] Automatic rollback on migration failure
  - [ ] Zero-downtime migration testing

- [ ] **1.4 Production observability**
  - [ ] Setup Sentry (error tracking)
  - [ ] Setup DataDog/New Relic (APM)
  - [ ] Custom metrics and dashboards
  - [ ] Alert escalation policies

---

## Phase 4: CI/CD Experimentation (Ongoing)

### Experimental Branch Pattern

- [ ] **1.1 Document ci-experimental/* pattern**
  - [ ] Guidelines for testing CI/CD changes
  - [ ] Example experimental workflows
  - [ ] Validation checklist before merging

- [ ] **1.2 Provide example workflows**
  - [ ] Caching optimization
  - [ ] Test parallelization
  - [ ] Alternative test runners
  - [ ] Cost optimization experiments

- [ ] **1.3 Feature flags implementation**
  - [ ] Runtime feature toggles
  - [ ] A/B testing infrastructure
  - [ ] Gradual feature rollout
  - [ ] User cohort targeting

---

## Validation Checklist

### Before Merging to Develop

- [ ] Fast tests still block PR merges
- [ ] E2E failures don't block staging deployments
- [ ] Rollback script tested and working
- [ ] Notifications working (Slack/Discord)
- [ ] Documentation updated
- [ ] Team trained on new workflow

### After Merging to Develop

- [ ] Monitor first 5 deployments closely
- [ ] Verify staging deploys in < 5 minutes
- [ ] Verify E2E tests run post-deployment
- [ ] Verify rollback procedure if needed
- [ ] Collect team feedback

### Success Metrics (Week 1)

- [ ] Staging deploy time: < 5 min (from 20+ min)
- [ ] E2E failures: Don't block staging
- [ ] Rollback time: < 1 min
- [ ] Team velocity: Increased (unblocked deployments)
- [ ] Cost: 40%+ reduction in GitHub Actions minutes

### Success Metrics (Week 2)

- [ ] E2E runtime: < 8 min (from 15 min, 50% reduction)
- [ ] Total cost reduction: 50%+
- [ ] Test reliability: 95%+ pass rate
- [ ] Health monitoring: Real-time alerts working

### Success Metrics (Week 4)

- [ ] Production deployments: < 10 min
- [ ] Zero-downtime: 100% uptime
- [ ] Error rate: < 0.1%
- [ ] MTTR: < 5 min (mean time to recovery)

---

## Rollback Plan (If Things Go Wrong)

### If New Workflow Causes Issues

1. **Revert workflow changes**
   ```bash
   git checkout develop
   git revert <commit-hash>
   git push origin develop
   ```

2. **Restore original workflows**
   - Restore e2e-staging.yml to block deployments
   - Restore deploy-staging.yml to wait for E2E
   - Push changes

3. **Notify team**
   - Explain what went wrong
   - Estimated time to fix
   - Temporary workflow (manual deployments)

### If Rollback Script Fails

1. **Manual rollback**
   ```bash
   ssh user@dev.autoauthor.app
   cd /opt/auto-author
   PREVIOUS=$(ls -t releases | sed -n '2p')
   ln -sfn releases/$PREVIOUS current
   pm2 restart all
   ```

2. **Verify health**
   ```bash
   curl -f https://api.dev.autoauthor.app/api/v1/health
   curl -f https://dev.autoauthor.app
   ```

3. **Debug rollback script**
   - Check permissions
   - Verify release directory structure
   - Check PM2 process names
   - Test health check URLs

---

## Common Issues & Solutions

### Issue: E2E tests still blocking deployment

**Symptom**: Deployment waits for E2E tests to complete

**Solution**:
1. Check workflow dependencies in deploy-staging.yml
2. Verify `needs` clause doesn't include e2e-tests job
3. Ensure e2e-staging.yml runs AFTER deploy-staging.yml

### Issue: Notifications not working

**Symptom**: No Slack/Discord alerts on E2E failures

**Solution**:
1. Verify webhook URL in GitHub Secrets
2. Test webhook with curl
3. Check if notification step is running (GitHub Actions logs)
4. Verify channel permissions

### Issue: Rollback script fails

**Symptom**: `rollback.sh` exits with error

**Solution**:
1. Check if previous release exists: `ls -t /opt/auto-author/releases`
2. Verify symlink exists: `ls -l /opt/auto-author/current`
3. Check PM2 processes: `pm2 list`
4. Verify health check URLs are correct

### Issue: Fast tests taking too long

**Symptom**: Fast tests exceed 5 minutes

**Solution**:
1. Check dependency caching (npm, uv)
2. Verify path filtering is working
3. Parallelize frontend + backend jobs
4. Optimize test configuration

---

## Resources & References

### Internal Documentation
- **Architecture**: `docs/deployment-pipeline-architecture.md`
- **Diagrams**: `docs/deployment-pipeline-diagram.md`
- **Current State**: `docs/deployment-architecture.md`

### Workflow Files
- **Fast Tests**: `.github/workflows/test-suite.yml`
- **Deployment**: `.github/workflows/deploy-staging.yml`
- **E2E Tests**: `.github/workflows/e2e-staging.yml`

### Scripts
- **Deployment**: `scripts/deploy.sh`
- **Rollback**: `scripts/rollback.sh` (to be created)

### External Resources
- [GitHub Actions: Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Playwright: Parallelization](https://playwright.dev/docs/test-parallel)
- [PM2: Cluster Mode](https://pm2.keymetrics.io/docs/usage/cluster-mode/)

---

## Sign-Off

### Phase 1 Complete
- [ ] All Phase 1 checklist items completed
- [ ] Team trained on new workflow
- [ ] Documentation updated
- [ ] Success metrics met
- [ ] **Signed off by**: ___________________ Date: ___________

### Phase 2 Complete
- [ ] All Phase 2 checklist items completed
- [ ] Cost reduction validated
- [ ] E2E tests parallelized
- [ ] Health monitoring active
- [ ] **Signed off by**: ___________________ Date: ___________

### Phase 3 Complete
- [ ] All Phase 3 checklist items completed
- [ ] Production deployments automated
- [ ] Blue-green/canary working
- [ ] Observability stack deployed
- [ ] **Signed off by**: ___________________ Date: ___________

---

**Document Version**: 1.0
**Last Updated**: 2025-10-24
**Owner**: DevOps Team
**Next Review**: 2025-11-24
