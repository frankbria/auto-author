# Deployment Architecture & Options

## Current State: Hybrid Approach

**Answer: No, deployment is NOT completely reliant on GitHub CI/CD.** You have multiple deployment options:

### 1. Automated CI/CD (Primary Method) ✅
**Trigger**: Automatic when code is pushed to `develop` branch
**Path**: GitHub Actions → Test Suite → Deploy to Staging

**Advantages**:
- Fully automated
- Always runs tests first
- Consistent deployments
- No manual intervention needed

**How it works**:
```
Push to develop → Test Suite runs → If tests pass → Deploy workflow triggers
                                                  ↓
                                          Rsync code to server
                                                  ↓
                                          Run scripts/deploy.sh on server
                                                  ↓
                                          Health checks verify deployment
```

### 2. Manual Deployment (Available) ✅
**When**: You need to deploy without pushing to GitHub or override CI/CD

The `scripts/deploy.sh` script is **standalone and can be run manually**:

#### Option A: Deploy from Server (Direct)
```bash
# SSH into the staging server
ssh user@dev.autoauthor.app

# Navigate to the project
cd /opt/auto-author/current

# Pull latest changes
git pull origin develop

# Set environment variables (see below)
export API_URL='https://api.dev.autoauthor.app'
export FRONTEND_URL='https://dev.autoauthor.app'
export CLERK_PUBLISHABLE_KEY='pk_...'
export CLERK_SECRET_KEY='sk_...'
export DATABASE_URL='mongodb://...'
export DATABASE_NAME='auto_author_staging'
export OPENAI_API_KEY='sk-...'

# Run deployment script
bash scripts/deploy.sh /opt/auto-author/current
```

#### Option B: Deploy from Local Machine
```bash
# From your local machine, sync code to server
RELEASE_ID=$(date +%Y%m%d-%H%M%S)
rsync -az --delete \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.log' \
  --exclude '.next' \
  ./ user@dev.autoauthor.app:/opt/auto-author/releases/$RELEASE_ID/

# SSH and run deploy
ssh user@dev.autoauthor.app "
  export API_URL='https://api.dev.autoauthor.app' && \
  export FRONTEND_URL='https://dev.autoauthor.app' && \
  export CLERK_PUBLISHABLE_KEY='pk_...' && \
  export CLERK_SECRET_KEY='sk_...' && \
  export DATABASE_URL='mongodb://...' && \
  export DATABASE_NAME='auto_author_staging' && \
  export OPENAI_API_KEY='sk-...' && \
  bash /opt/auto-author/releases/$RELEASE_ID/scripts/deploy.sh /opt/auto-author/releases/$RELEASE_ID
"
```

### 3. Partial Manual Deployment (Service Control)
**When**: You only need to restart services, not redeploy code

```bash
# SSH into server
ssh user@dev.autoauthor.app

# Restart backend only
pm2 restart auto-author-backend

# Restart frontend only
pm2 restart auto-author-frontend

# Restart both
pm2 restart all

# Check status
pm2 status
pm2 logs auto-author-backend --lines 50
pm2 logs auto-author-frontend --lines 50
```

## Deployment Script Breakdown

The `scripts/deploy.sh` is **self-contained** and handles:

1. **Backend Setup**:
   - Install Python dependencies with uv
   - Create `.env` file with all required variables
   - Configure CORS origins

2. **Frontend Setup**:
   - Install Node.js dependencies
   - Create `.env.production` file
   - Build Next.js application

3. **Service Management**:
   - Restart PM2 processes (backend + frontend)
   - Atomic symlink switching for zero-downtime

4. **Verification**:
   - Health checks (backend + frontend)
   - Cleanup old releases (keep last 5)

## Required Environment Variables

For manual deployments, you need these variables:

### Backend
```bash
API_URL='https://api.dev.autoauthor.app'
FRONTEND_URL='https://dev.autoauthor.app'
DATABASE_URL='mongodb://...'
DATABASE_NAME='auto_author_staging'
OPENAI_API_KEY='sk-...'
```

### Clerk Authentication
```bash
CLERK_PUBLISHABLE_KEY='pk_...'
CLERK_SECRET_KEY='sk_...'
CLERK_WEBHOOK_SECRET='whsec_...'  # Optional
```

**Where to find these**:
- GitHub Secrets: Settings → Secrets and variables → Actions
- Clerk Dashboard: https://dashboard.clerk.dev
- MongoDB: Your database provider dashboard

## Deployment Decision Tree

```
Need to deploy?
│
├─ Regular deployment after code changes?
│  └─ Push to develop → Let CI/CD handle it ✅
│
├─ Emergency hotfix or CI/CD is down?
│  └─ Use Manual Deployment (Option A or B) ✅
│
├─ Just need to restart services?
│  └─ Use PM2 commands ✅
│
└─ Testing deploy script changes?
   └─ Use Manual Deployment from server ✅
```

## Advantages of Current Hybrid Approach

### ✅ Flexibility
- Can deploy via CI/CD (preferred)
- Can deploy manually when needed
- Can restart services independently

### ✅ Reliability
- Not locked into CI/CD
- Can bypass broken CI/CD workflows
- Can deploy directly from server

### ✅ Debugging
- Can test deploy script changes manually
- Can troubleshoot deployment issues directly
- Can verify environment variables on server

### ✅ Emergency Response
- Can hotfix production issues quickly
- No dependency on GitHub being available
- Direct server access for critical fixes

## Best Practices

### 1. Prefer CI/CD for Regular Deployments
- Ensures tests run first
- Creates audit trail
- Consistent process

### 2. Use Manual Deployment For:
- Emergency hotfixes
- Testing deploy script changes
- CI/CD troubleshooting
- Quick iterations during development

### 3. Document Your Deployments
- Log manual deployments in commit messages
- Update deployment documentation
- Track what was deployed and why

### 4. Keep Secrets Secure
- Never commit `.env` files
- Use GitHub Secrets for CI/CD
- Store production secrets securely (1Password, Vault, etc.)

## Future Improvements

### Consider Adding:
1. **Rollback Script**: Quick rollback to previous release
2. **Pre-flight Checks**: Validate environment before deployment
3. **Deployment Notifications**: Slack/Discord webhooks
4. **Blue-Green Deployment**: Zero-downtime with traffic switching
5. **Database Migrations**: Automated schema updates

## References

- Deployment Script: `scripts/deploy.sh`
- CI/CD Workflow: `.github/workflows/deploy-staging.yml`
- Clerk Setup: `docs/clerk-deployment-checklist.md`
- CORS Fix: `docs/fixes/2025-10-24-cors-error-fix.md`
