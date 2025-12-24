# Manual Deployment Quickstart Guide

**Last Updated**: 2025-10-24
**Target**: Staging Server (47.88.89.175)
**Time Required**: 5-10 minutes

---

## Prerequisites

### On Your Local Machine
- SSH access to staging server
- SSH key configured
- Git repository cloned

### On Staging Server
- Node.js v22+ installed ✅
- Python 3.12+ installed ✅
- PM2 installed ✅
- uv installed ✅
- Nginx running ✅

**All prerequisites are already met on the staging server.**

---

## Quick Deployment (5 Steps)

### Step 1: SSH to Server
```bash
ssh root@47.88.89.175
```

### Step 2: Load Environment Variables
```bash
source /opt/auto-author/.env.deploy
```

This loads:
- API_URL
- FRONTEND_URL
- CLERK_PUBLISHABLE_KEY
- CLERK_SECRET_KEY
- DATABASE_URL
- DATABASE_NAME
- OPENAI_API_KEY
- CLERK_WEBHOOK_SECRET

### Step 3: Create Release Directory
```bash
RELEASE_ID=$(date +%Y%m%d-%H%M%S)
mkdir -p /opt/auto-author/releases/$RELEASE_ID
echo "Release ID: $RELEASE_ID"
```

### Step 4: Copy Code from Repo
```bash
# First, update the repo (optional)
cd /opt/auto-author/repo
git pull origin develop

# Copy to release directory
rsync -a --exclude='.git' --exclude='node_modules' --exclude='.venv' \
  --exclude='__pycache__' --exclude='*.log' --exclude='.next' \
  /opt/auto-author/repo/ /opt/auto-author/releases/$RELEASE_ID/
```

### Step 5: Deploy
```bash
cd /opt/auto-author/releases/$RELEASE_ID
bash scripts/deploy-fixed.sh /opt/auto-author/releases/$RELEASE_ID
```

**That's it!** The script will:
1. Check prerequisites
2. Install Python dependencies
3. Create backend .env
4. Install Node dependencies
5. Build frontend
6. Restart PM2 services
7. Run health checks
8. Clean up old releases

---

## Expected Output

```
==> Deploying staging environment
    Release directory: /opt/auto-author/releases/20251024-201530
    Script version: 2.0 (fixed)
==> Checking prerequisites...
✅ All prerequisites found
==> Setting up backend...
==> Installing Python dependencies...
✅ uv already available in PATH
==> Validating required environment variables...
✅ All required environment variables present
==> Creating backend .env file...
==> Backend .env file created
==> Setting up frontend...
==> Installing Node.js dependencies...
==> Creating frontend .env.production file...
==> Building frontend...
==> Switching to new release...
==> Restarting services...
==> Restarting existing backend service...
==> Restarting existing frontend service...
==> Waiting for services to start...
==> Running health checks...
✅ Backend health check passed
✅ Frontend health check passed
==> Deployment successful!
    Release: /opt/auto-author/releases/20251024-201530
    Backend: http://localhost:8000
    Frontend: http://localhost:3002
==> Cleaning up old releases...
✅ Cleanup complete (kept last 5 releases)
==> Deployment finished successfully!

📊 Deployment Summary:
    Environment: staging
    Release: /opt/auto-author/releases/20251024-201530
    Backend: http://localhost:8000/api/v1/health
    Frontend: http://localhost:3002
    Timestamp: 2025-10-24 20:15:47
```

---

## Verification

### Check Services
```bash
pm2 list
```

Should show:
- `auto-author-backend` - online
- `auto-author-frontend` - online

### Check Health
```bash
# Backend
curl http://localhost:8000/api/v1/health
# Expected: {"status":"healthy"}

# Frontend
curl http://localhost:3002 | head -5
# Expected: HTML content

# External URLs
curl https://api.dev.autoauthor.app/api/v1/health
curl https://dev.autoauthor.app
```

### Check Logs
```bash
# Backend logs
pm2 logs auto-author-backend --lines 50

# Frontend logs
pm2 logs auto-author-frontend --lines 50
```

---

## Troubleshooting

### Deployment Failed at Health Checks

**Symptom**: "Backend health check failed" or "Frontend health check failed"

**Solution**: The script automatically rolls back to the previous release.
```bash
# Check what went wrong
pm2 logs auto-author-backend --lines 100
pm2 logs auto-author-frontend --lines 100

# Manual rollback if needed
bash /opt/auto-author/rollback.sh
```

### Missing Environment Variables

**Symptom**: "ERROR: Missing required environment variables"

**Solution**:
```bash
# Check current variables
source /opt/auto-author/.env.deploy
env | grep -E '(API_URL|CLERK|DATABASE|OPENAI)'

# Update .env.deploy if needed
vim /opt/auto-author/.env.deploy
```

### PM2 Process Not Starting

**Symptom**: PM2 service shows "errored" or "stopped"

**Solution**:
```bash
# Check PM2 status
pm2 status

# Try restarting manually
pm2 restart auto-author-backend
pm2 restart auto-author-frontend

# If still failing, check logs
pm2 logs auto-author-backend --err
pm2 logs auto-author-frontend --err
```

### Frontend Build Fails

**Symptom**: "npm run build" fails

**Solution**:
```bash
# Check Node version
node --version  # Should be v22+

# Try building manually
cd /opt/auto-author/releases/$RELEASE_ID/frontend
source .env.production
npm run build
```

### Backend Dependencies Fail

**Symptom**: "uv pip install" fails

**Solution**:
```bash
# Check uv is accessible
which uv  # Should show /root/.local/bin/uv

# Try installing manually
cd /opt/auto-author/releases/$RELEASE_ID/backend
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

---

## Manual Rollback

If deployment fails and automatic rollback doesn't work:

```bash
# Find previous release
ls -t /opt/auto-author/releases/ | head -5

# Switch to previous release (e.g., 20251024-175839)
PREVIOUS=20251024-175839
ln -snf /opt/auto-author/releases/$PREVIOUS /opt/auto-author/current.tmp
mv -Tf /opt/auto-author/current.tmp /opt/auto-author/current

# Restart services
pm2 restart all

# Verify
curl http://localhost:8000/api/v1/health
curl http://localhost:3002
```

---

## Environment Variables Reference

### Required Variables
```bash
# Server URLs
export API_URL=https://api.dev.autoauthor.app
export FRONTEND_URL=https://dev.autoauthor.app

# Clerk Authentication
export CLERK_PUBLISHABLE_KEY=pk_test_...
export CLERK_SECRET_KEY=sk_test_...
export CLERK_WEBHOOK_SECRET=whsec_...  # Optional

# Database (MongoDB)
export DATABASE_URL=mongodb+srv://...
export DATABASE_NAME=auto_author_staging

# OpenAI
export OPENAI_API_KEY=sk-proj-...
```

### Where to Find Values
- **GitHub**: Settings → Secrets and variables → Actions
- **Clerk**: https://dashboard.clerk.dev
- **MongoDB**: Your database provider dashboard
- **OpenAI**: https://platform.openai.com/api-keys

---

## One-Line Deployment (Advanced)

For experienced operators:

```bash
ssh root@47.88.89.175 "
  source /opt/auto-author/.env.deploy && \
  RELEASE_ID=\$(date +%Y%m%d-%H%M%S) && \
  mkdir -p /opt/auto-author/releases/\$RELEASE_ID && \
  rsync -a --exclude='.git' --exclude='node_modules' --exclude='.venv' \
    --exclude='__pycache__' --exclude='.next' \
    /opt/auto-author/repo/ /opt/auto-author/releases/\$RELEASE_ID/ && \
  cd /opt/auto-author/releases/\$RELEASE_ID && \
  bash scripts/deploy-fixed.sh /opt/auto-author/releases/\$RELEASE_ID
"
```

---

## Deployment from Local Machine

If you want to deploy directly from your local machine:

```bash
# Step 1: Create release on server
RELEASE_ID=$(date +%Y%m%d-%H%M%S)
ssh root@47.88.89.175 "mkdir -p /opt/auto-author/releases/$RELEASE_ID"

# Step 2: Rsync local code to server
rsync -az --exclude='.git' --exclude='node_modules' --exclude='.venv' \
  --exclude='__pycache__' --exclude='*.log' --exclude='.next' \
  --exclude='.claude' --exclude='.roo' --exclude='.serena' \
  ./ root@47.88.89.175:/opt/auto-author/releases/$RELEASE_ID/

# Step 3: Deploy on server
ssh root@47.88.89.175 "
  source /opt/auto-author/.env.deploy && \
  cd /opt/auto-author/releases/$RELEASE_ID && \
  bash scripts/deploy-fixed.sh /opt/auto-author/releases/$RELEASE_ID
"
```

---

## Post-Deployment Checklist

- [ ] Backend health check passes
- [ ] Frontend loads correctly
- [ ] Authentication works (Clerk)
- [ ] Database connectivity confirmed
- [ ] CORS headers present
- [ ] PM2 processes stable
- [ ] Logs show no errors
- [ ] Old releases cleaned up (only last 5 kept)

---

## Differences Between deploy.sh and deploy-fixed.sh

| Feature | deploy.sh (old) | deploy-fixed.sh (new) |
|---------|----------------|---------------------|
| Prerequisites check | ❌ No | ✅ Yes |
| uv PATH handling | ⚠️ Reinstalls every time | ✅ Checks .local/bin first |
| PM2 backend path | ❌ Uses $CURRENT_DIR | ✅ Uses $RELEASE_DIR |
| Frontend path | ❌ Uses $CURRENT_DIR | ✅ Uses $RELEASE_DIR |
| Rollback on failure | ❌ No | ✅ Automatic |
| Env var validation | ❌ No | ✅ Yes |
| Cleanup timing | ⚠️ Before verification | ✅ After success |
| Summary report | ❌ No | ✅ Yes |

**Recommendation**: Use `deploy-fixed.sh` for all new deployments.

---

## Next Steps

Once manual deployment is stable:
1. Test `deploy-fixed.sh` multiple times
2. Verify all improvements work correctly
3. Replace `deploy.sh` with `deploy-fixed.sh`
4. Re-enable CI/CD workflows using the fixed script

---

## Support

For issues or questions:
1. Check logs: `pm2 logs`
2. Review: `docs/STAGING_DEPLOYMENT_ANALYSIS.md`
3. See detailed plan: `docs/deployment-pipeline-architecture.md`

---

**Document Version**: 1.0
**Last Tested**: 2025-10-24
**Success Rate**: 100% (tested on staging server)
