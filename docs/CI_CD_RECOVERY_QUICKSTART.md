# CI/CD Recovery - Quick Start Guide

**Status:** 🚨 CRITICAL - Immediate Action Required
**Time to Execute:** 30 minutes
**Risk Level:** LOW (all changes reversible)

---

## TL;DR

The `develop` branch has failing CI/CD workflows blocking staging deployments. This guide provides **immediate recovery steps** to restore stable deployments while preserving all work.

---

## What Happened?

1. CI/CD workflows activated on `develop` branch (PR #8, commit `71f504f`)
2. Multiple issues discovered:
   - Missing GitHub Secrets
   - 10+ minute E2E tests blocking deployments
   - Expensive OpenAI API calls in test suite
3. Result: Staging deployments blocked, but code is stable

**Good News:**
- ✅ Local tests passing
- ✅ CORS fixes working (deploy.sh restored)
- ✅ All fixes preserved in git history
- ✅ Manual deployments via deploy.sh confirmed working

---

## Quick Recovery (3 Steps)

### Step 1: Backup Current State (2 minutes)

```bash
cd /home/frankbria/projects/auto-author

# Create backup branch
git checkout develop
git branch backup/develop-with-cicd-2025-10-24
git push origin backup/develop-with-cicd-2025-10-24

# Create CI/CD isolation branch for future work
git checkout -b feature/github-actions-cicd develop
git push -u origin feature/github-actions-cicd
```

### Step 2: Remove Failing Workflows (5 minutes)

```bash
# Return to develop
git checkout develop

# Remove active workflow files (keep .tbd placeholders)
git rm .github/workflows/test-suite.yml
git rm .github/workflows/deploy-staging.yml
git rm .github/workflows/e2e-staging.yml

# Verify placeholders remain
ls -la .github/workflows/*.tbd
# Should show: deploy-production.tbd, deploy-staging.tbd, test-suite.tbd

# Commit the removal
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

# Push to remote
git push origin develop
```

### Step 3: Verify Stable State (3 minutes)

```bash
# Check status
git status
# Expected: On branch develop, nothing to commit

# Verify workflows removed
ls -la .github/workflows/
# Expected: Only .tbd and .disabled files

# Verify deploy.sh exists
ls -la scripts/deploy.sh
# Expected: -rwxr-xr-x ... scripts/deploy.sh

# Run local tests
cd frontend && npm test
# Expected: Tests pass

cd ../backend && uv run pytest tests/ --co -q
# Expected: collected 194 items / 5 skipped
```

**Done!** Develop branch is now stable. Proceed to manual deployment.

---

## Manual Staging Deployment

### Prerequisites

Ensure you have these secrets (from GitHub Secrets or local .env):

```bash
# Server
HOST=<your-staging-server>
USER=root
SSH_KEY=<private-key>

# URLs
API_URL=https://api.dev.autoauthor.app
FRONTEND_URL=https://dev.autoauthor.app

# Clerk
CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
CLERK_WEBHOOK_SECRET=whsec_...

# Database
DATABASE_URL=mongodb://localhost:27017
DATABASE_NAME=auto_author_staging

# OpenAI
OPENAI_API_KEY=sk-...
```

### Deployment Steps

```bash
# 1. SSH into staging server
ssh root@<your-staging-server>

# 2. Navigate to deployment directory
cd /opt/auto-author/current

# 3. Pull latest code
git pull origin develop

# 4. Set environment variables (one-time setup)
cat > /opt/auto-author/.env.deploy << 'EOF'
export API_URL=https://api.dev.autoauthor.app
export FRONTEND_URL=https://dev.autoauthor.app
export CLERK_PUBLISHABLE_KEY=<your-key>
export CLERK_SECRET_KEY=<your-key>
export DATABASE_URL=mongodb://localhost:27017
export DATABASE_NAME=auto_author_staging
export OPENAI_API_KEY=<your-key>
export CLERK_WEBHOOK_SECRET=<your-secret>
EOF

# 5. Source environment
source /opt/auto-author/.env.deploy

# 6. Create release
RELEASE_ID=$(date +%Y%m%d-%H%M%S)
mkdir -p /opt/auto-author/releases/$RELEASE_ID
rsync -av --exclude='.git' --exclude='node_modules' --exclude='.venv' \
  /opt/auto-author/current/ /opt/auto-author/releases/$RELEASE_ID/

# 7. Deploy
cd /opt/auto-author/releases/$RELEASE_ID
bash scripts/deploy.sh /opt/auto-author/releases/$RELEASE_ID

# 8. Verify
curl -f http://localhost:8000/api/v1/health  # Backend
curl -f http://localhost:3002                 # Frontend
curl -f https://api.dev.autoauthor.app/api/v1/health  # External backend
curl -f https://dev.autoauthor.app            # External frontend
```

---

## What About CI/CD?

**Short Answer:** Work on it in isolation in `feature/github-actions-cicd` branch.

**Key Issues to Fix:**
1. Missing GitHub Secrets:
   - `CLERK_PUBLISHABLE_KEY_CI_TEST`
   - `TEST_USER_EMAIL`
   - `TEST_USER_PASSWORD`

2. E2E Test Strategy:
   - Remove E2E from test-suite.yml (lines 123-162)
   - Move to separate post-deployment workflow
   - Make E2E tests non-blocking (manual trigger or nightly)

3. Workflow Simplification:
   - Fast tests only in critical path (< 5 min)
   - Deployment after fast tests pass
   - E2E tests run post-deployment

**Timeline:**
- **Today:** Restore stable staging (completed above)
- **This week:** Fix CI/CD in feature branch
- **Next week:** Test workflows on feature branch
- **Week 3:** Re-enable CI/CD on develop (staged rollout)

---

## E2E Test Strategy

### Current Problem
- E2E tests: 10+ minutes runtime
- OpenAI API calls: $0.30 per test run
- Running on every push to develop
- **Cost:** ~$45/month + 50 min/day developer time

### New Strategy

#### Tier 1: Fast Tests (< 5 min) - CI/CD Critical Path
- Lint, type check, unit tests, build
- Run on every PR and push
- **NO E2E tests here**
- **NO OpenAI calls**

#### Tier 2: Integration Tests (5-10 min) - Optional
- Local database integration
- API contract tests
- Run locally before pushing

#### Tier 3: E2E Tests (10-20 min) - Post-Deployment
- Full Playwright suite
- Real OpenAI integration tests
- Run **after** deployment (non-blocking)
- Manual trigger or nightly schedule

**Savings:** ~$43/month + 4 hours/week developer time

---

## Success Criteria

### Phase 1: Recovery (Today)
- ✅ Backup branches created
- ✅ CI/CD workflows removed from develop
- ✅ Local tests still passing
- ✅ deploy.sh verified working

### Phase 2: Manual Deployment (Today)
- ✅ Successful deployment to staging
- ✅ No CORS errors
- ✅ Frontend and backend accessible

### Phase 3: CI/CD Re-Integration (Future)
- ✅ Fast tests (< 5 min) on every push
- ✅ Automated deployments working
- ✅ E2E tests separated and non-blocking
- ✅ All secrets configured

---

## Rollback Plan

If anything goes wrong:

```bash
# Restore from backup
git checkout develop
git reset --hard backup/develop-with-cicd-2025-10-24
git push origin develop --force

# Or restore specific files
git checkout backup/develop-with-cicd-2025-10-24 -- .github/workflows/
git commit -m "restore: bring back CI/CD workflows from backup"
git push origin develop
```

---

## Next Steps

1. ✅ Execute recovery steps above (30 minutes)
2. ✅ Test manual deployment to staging
3. 📝 Document any deployment issues
4. 🔧 Begin fixing CI/CD in `feature/github-actions-cicd` branch
5. 📊 Monitor staging stability for 2-3 days

---

## Additional Resources

- **Full Recovery Plan:** `/home/frankbria/projects/auto-author/docs/CI_CD_RECOVERY_PLAN.md` (1,222 lines, comprehensive)
- **Deploy Script:** `/home/frankbria/projects/auto-author/scripts/deploy.sh`
- **Testing Docs:** `/home/frankbria/projects/auto-author/docs/references/testing-infrastructure.md`

---

## Questions?

1. **Why remove CI/CD?**
   - Workflows are blocking deployments
   - Multiple issues need fixes
   - Manual deployment proven stable
   - Can re-enable after fixes

2. **Will we lose CI/CD work?**
   - No! Preserved in `feature/github-actions-cicd` branch
   - Also backed up in `backup/develop-with-cicd-2025-10-24`

3. **How long without CI/CD?**
   - 1-2 weeks to fix properly
   - Can run tests locally in meantime
   - Manual deployments work fine

4. **What about E2E tests?**
   - Still runnable locally: `npx playwright test --ui`
   - Will be post-deployment workflow (non-blocking)
   - Saves time and money

---

**Last Updated:** 2025-10-24
**Status:** Ready to Execute
**Estimated Time:** 30 minutes
**Risk:** LOW (reversible)
