# Staging Deployment Analysis - 2025-10-24

**Status**: ✅ Manual Deployment Works with Minor Issues
**Author**: DevOps Analysis
**Server**: 47.88.89.175 (root@)

---

## Executive Summary

Manual deployment to staging is **functional** but has several issues that need to be addressed before re-enabling CI/CD workflows. The current deployment at `/opt/auto-author` is running successfully with both backend and frontend services healthy.

**Key Findings**:
- ✅ Services running: Backend (port 8000), Frontend (port 3002)
- ✅ Health checks passing
- ✅ deploy.sh script works but has inefficiencies
- ⚠️ `uv` not in PATH (gets installed each time)
- ⚠️ Multiple deployment approaches causing confusion
- ⚠️ PM2 process management needs improvement

---

## 1. Current Server State

### 1.1 Server Information
```
Hostname: s878435
Uptime: 5 days, 1:39
Load: 0.10, 0.14, 0.16
```

### 1.2 Directory Structure
```
/opt/auto-author/
├── current -> releases/20251024-175839/  # Symlink to active release
├── releases/
│   ├── 20251024-175839/  (current, deployed at 18:02)
│   ├── 20251024-100806/
│   ├── 20251024-051954/
│   ├── 20251024-051409/
│   ├── 20251024-051244/
│   └── manual-20251022-040918/
├── repo/  # Git repository (develop branch)
├── .env.deploy  # Environment variables
├── deploy-remote.sh
├── rollback.sh
├── env/
├── scripts/
└── shared/
```

### 1.3 Running Services (PM2)
```
ID   Name                   Status   PID       Port    User    Uptime
17   auto-author-backend    online   1505642   8000    root    84m
18   auto-author-frontend   online   1507566   3002    root    82m
```

### 1.4 Health Status
```bash
# Backend
$ curl http://localhost:8000/api/v1/health
{"status":"healthy"}

# Frontend
$ curl http://localhost:3002
<!DOCTYPE html>... (HTML rendered successfully)
```

---

## 2. Issues Identified

### 2.1 CRITICAL: `uv` Not in PATH
**Issue**: `uv` is installed at `/root/.local/bin/uv` but not in the default PATH.

**Impact**:
- `deploy.sh` reinstalls `uv` on every deployment (lines 24-28)
- Wastes ~10 seconds per deployment
- Unnecessary network calls to install script

**Current Behavior** (deploy.sh:24-28):
```bash
if ! command -v uv &> /dev/null; then
    echo "==> Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
```

**Fix Required**:
1. Add `/root/.local/bin` to system PATH permanently
2. Or check `/root/.local/bin/uv` explicitly before installing

### 2.2 CRITICAL: PM2 Path Issue (Line 105-107)
**Issue**: When starting new PM2 backend process, script uses `$CURRENT_DIR` instead of `$RELEASE_DIR`.

**Problem Code**:
```bash
pm2 start "$CURRENT_DIR/backend/.venv/bin/uvicorn" \
    --name auto-author-backend \
    -- app.main:app --host 0.0.0.0 --port 8000
```

**Impact**:
- Points to OLD release's venv, not the NEW one
- Could cause version mismatches
- Only works because symlink is updated BEFORE PM2 restart

**Fix**: Change to `$RELEASE_DIR/backend/.venv/bin/uvicorn`

### 2.3 MODERATE: Cleanup Runs Before Verification (Lines 154-156)
**Issue**: Old releases are deleted before deployment is verified successful.

**Problem Code**:
```bash
cd "$DEPLOY_BASE/releases"
ls -t | tail -n +6 | xargs -r rm -rf
```

**Impact**:
- If new deployment fails health checks, good old releases are already gone
- No automatic rollback possible

**Fix**: Move cleanup to AFTER successful health checks

### 2.4 MODERATE: Environment File Management
**Issue**: Environment variables sourced from `/opt/auto-author/.env.deploy` but script expects them as exports.

**Current State**:
```bash
# .env.deploy contains:
export API_URL=https://api.dev.autoauthor.app
export FRONTEND_URL=https://dev.autoauthor.app
...
```

**Issue**: Works with `source` but not with direct execution. Inconsistent.

**Fix**: Document that `.env.deploy` must be sourced, or update script to handle both formats.

### 2.5 MINOR: Missing Prerequisites Check
**Issue**: No validation that required tools exist before running.

**Missing Checks**:
- `node` (required for frontend)
- `npm` (required for frontend)
- `pm2` (required for process management)
- `curl` (required for health checks)
- `rsync` (if deploying from local)

**Fix**: Add prerequisites check function at start of deploy.sh

### 2.6 MINOR: Frontend Environment Sourcing (Lines 113-115)
**Issue**: Changes to `$CURRENT_DIR/frontend` but .env.production is in `$RELEASE_DIR/frontend`.

**Problem Code**:
```bash
cd "$CURRENT_DIR/frontend"
set -a
source .env.production
set +a
```

**Impact**:
- Works because $CURRENT_DIR is updated before this step
- But semantically incorrect - should use $RELEASE_DIR

---

## 3. What's Working

### 3.1 ✅ Atomic Symlink Switching (Lines 92-94)
```bash
ln -snf "$RELEASE_DIR" "$CURRENT_DIR.tmp"
mv -Tf "$CURRENT_DIR.tmp" "$CURRENT_DIR"
```
This is correct and provides zero-downtime deployments.

### 3.2 ✅ PM2 Process Detection
```bash
if pm2 describe auto-author-backend > /dev/null 2>&1; then
    pm2 restart auto-author-backend
else
    pm2 start ...
fi
```
Properly handles both new and existing processes.

### 3.3 ✅ Health Checks (Lines 134-146)
Both backend and frontend health checks are implemented correctly.

### 3.4 ✅ Backend .env Creation (Lines 44-59)
Creates comprehensive `.env` file with all required variables, including proper CORS configuration.

### 3.5 ✅ Frontend Environment (Lines 72-89)
Creates `.env.production` and exports variables for build process.

---

## 4. Server Prerequisites Status

### 4.1 ✅ Installed
- **Node.js**: v22.20.0
- **Python**: 3.12.3
- **PM2**: 6.0.13 (needs update, currently 6.0.8 in memory)
- **Nginx**: Active
- **uv**: 0.9.5 (installed but not in PATH)

### 4.2 ⚠️ Configuration Needed
- **PATH**: Add `/root/.local/bin` to system PATH
- **PM2**: Run `pm2 update` to sync in-memory version

---

## 5. Deployment Flow Analysis

### Current Manual Deployment Process
```bash
# 1. SSH to server
ssh root@47.88.89.175

# 2. Source environment variables
source /opt/auto-author/.env.deploy

# 3. Create release directory
RELEASE_ID=$(date +%Y%m%d-%H%M%S)
mkdir -p /opt/auto-author/releases/$RELEASE_ID

# 4. Copy code from repo
rsync -a --exclude='.git' --exclude='node_modules' --exclude='.venv' \
  --exclude='__pycache__' --exclude='.next' \
  /opt/auto-author/repo/ /opt/auto-author/releases/$RELEASE_ID/

# 5. Run deployment script
cd /opt/auto-author/releases/$RELEASE_ID
bash scripts/deploy.sh /opt/auto-author/releases/$RELEASE_ID

# 6. Verify
curl http://localhost:8000/api/v1/health
curl http://localhost:3002
```

### Time Breakdown
- Create release dir: < 1 second
- Rsync code: 2-5 seconds
- Backend setup (uv install + dependencies): 30-60 seconds
- Frontend build: 60-120 seconds
- PM2 restart: 5-10 seconds
- Health checks: 5-10 seconds

**Total**: 2-4 minutes (acceptable for staging)

---

## 6. Comparison with Documentation

### deployment-architecture.md Claims
> "Manual deployment is available and works via deploy.sh"

**Status**: ✅ TRUE - Works with minor issues

### CI_CD_RECOVERY_PLAN.md Claims
> "Manual deployments via deploy.sh confirmed working"

**Status**: ✅ TRUE - Confirmed through testing

### Issues from CI_CD_RECOVERY_PLAN.md
The document correctly identified:
1. ✅ Missing GitHub Secrets (for CI/CD)
2. ✅ E2E tests taking 10+ minutes
3. ✅ Expensive OpenAI API calls in tests
4. ✅ CI/CD workflows blocking deployments

**Solution Implemented**: Workflows disabled, manual deployment restored.

---

## 7. Recommended Fixes

### Priority 1: Critical (Before Re-enabling CI/CD)

#### Fix 1: Add uv to PATH Permanently
```bash
# On server
echo 'export PATH="/root/.local/bin:$PATH"' >> /root/.bashrc
source /root/.bashrc

# Update deploy.sh (line 24-28)
if ! command -v uv &> /dev/null; then
    # Check in .local/bin explicitly
    if [ -f "$HOME/.local/bin/uv" ]; then
        export PATH="$HOME/.local/bin:$PATH"
    else
        echo "==> Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
    fi
fi
```

#### Fix 2: Correct PM2 Path
```bash
# deploy.sh line 105-107 (CHANGE)
pm2 start "$RELEASE_DIR/backend/.venv/bin/uvicorn" \
    --name auto-author-backend \
    -- app.main:app --host 0.0.0.0 --port 8000
```

#### Fix 3: Move Cleanup After Health Checks
```bash
# Move lines 154-156 AFTER line 151 (after health checks)
echo "==> Deployment successful!"

# Cleanup old releases (keep last 5)
echo "==> Cleaning up old releases..."
cd "$DEPLOY_BASE/releases"
ls -t | tail -n +6 | xargs -r rm -rf
```

### Priority 2: Moderate (Improvements)

#### Fix 4: Add Prerequisites Check
```bash
# Add at start of deploy.sh (after line 16)
echo "==> Checking prerequisites..."
for cmd in node npm pm2 curl; do
    if ! command -v $cmd &> /dev/null; then
        echo "❌ ERROR: $cmd is not installed"
        exit 1
    fi
done
echo "✅ All prerequisites found"
```

#### Fix 5: Update PM2
```bash
# On server, run once
pm2 update
pm2 save
```

### Priority 3: Nice-to-Have (Enhancements)

#### Fix 6: Add Rollback Function
```bash
# Add to deploy.sh
rollback() {
    echo "🔄 Rolling back to previous release..."
    PREVIOUS=$(ls -t $DEPLOY_BASE/releases | sed -n '2p')
    if [ -z "$PREVIOUS" ]; then
        echo "❌ No previous release found"
        return 1
    fi

    ln -snf "$DEPLOY_BASE/releases/$PREVIOUS" "$CURRENT_DIR.tmp"
    mv -Tf "$CURRENT_DIR.tmp" "$CURRENT_DIR"
    pm2 restart all
    echo "✅ Rollback complete to: $PREVIOUS"
}

# Use in health check failure (after line 138)
if ! curl -f http://localhost:8000/api/v1/health; then
    echo "❌ Backend health check failed"
    rollback
    exit 1
fi
```

---

## 8. CI/CD Re-enablement Plan

### Phase 1: Fix deploy.sh (This Week)
1. Apply Priority 1 fixes to deploy.sh
2. Test manual deployment with fixes
3. Commit fixed deploy.sh to develop branch

### Phase 2: Create Minimal CI/CD Workflows (Next Week)
1. Create `test-suite.yml`:
   - Fast tests only (< 5 minutes)
   - Lint, typecheck, unit tests, build
   - NO E2E tests

2. Create `deploy-staging.yml`:
   - Triggers after test-suite.yml succeeds
   - Uses fixed deploy.sh script
   - Automatic on push to develop

3. Create `e2e-staging.yml` (SEPARATE):
   - Manual trigger OR nightly schedule
   - Runs AFTER deployment
   - Does NOT block deployment

### Phase 3: Test in Feature Branch (Week 3)
1. Create `ci-experimental/fixed-workflows` branch
2. Test workflows in isolation
3. Validate against documentation

### Phase 4: Enable on Develop (Week 4)
1. Merge tested workflows to develop
2. Monitor for 2-3 days
3. Document lessons learned

---

## 9. Environment Variables Reference

### Required for Deployment
```bash
# Server URLs
API_URL=https://api.dev.autoauthor.app
FRONTEND_URL=https://dev.autoauthor.app

# Clerk Authentication
CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
CLERK_WEBHOOK_SECRET=whsec_... (optional)

# Database
DATABASE_URI=mongodb+srv://...
DATABASE_NAME=auto_author_staging

# OpenAI
OPENAI_API_KEY=sk-proj-...
```

### Current Storage Location
- Server: `/opt/auto-author/.env.deploy`
- GitHub Secrets: Settings → Secrets and variables → Actions

---

## 10. Testing Checklist

Before re-enabling CI/CD, verify:

- [ ] Manual deployment completes successfully
- [ ] Backend health check passes
- [ ] Frontend renders correctly
- [ ] CORS headers present on API responses
- [ ] PM2 processes start correctly
- [ ] Old releases cleaned up (keeps last 5)
- [ ] Rollback script works
- [ ] Environment variables loaded correctly
- [ ] No unnecessary uv reinstalls
- [ ] Health checks prevent bad deployments

---

## 11. Conclusion

**Current Status**: Manual deployment is **functional** with minor issues that don't prevent deployment but should be fixed for production-readiness.

**Recommended Action**:
1. Apply Priority 1 fixes to deploy.sh
2. Test thoroughly
3. Begin Phase 2 (CI/CD workflows) once fixes confirmed

**Timeline**:
- **Week 1**: Fix deploy.sh ✅ Ready to start
- **Week 2**: Minimal CI/CD workflows
- **Week 3**: Test in feature branch
- **Week 4**: Enable on develop

**Risk Level**: LOW - Changes are reversible, current deployment stable.

---

**Document Version**: 1.0
**Last Updated**: 2025-10-24
**Next Review**: After deploy.sh fixes applied
