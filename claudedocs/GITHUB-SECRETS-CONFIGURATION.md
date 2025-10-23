# GitHub Secrets Configuration Guide

**Status**: 🔴 REQUIRED - Must complete before first automated deployment
**Time Required**: 15 minutes
**Prerequisites**: GitHub repository admin access

---

## Overview

This guide provides step-by-step instructions for configuring GitHub secrets required for automated CI/CD deployments.

**Key Concept**: Secrets use **generic names** (e.g., `SSH_KEY`, `API_URL`) that are scoped to **environments** (e.g., `staging`, `production`). This allows the same workflow code to work across all environments.

---

## Step 1: Navigate to GitHub Secrets

1. Go to your repository: `https://github.com/frankbria/auto-author`
2. Click **Settings** (top navigation)
3. In left sidebar, click **Secrets and variables** → **Actions**

---

## Step 2: Create Staging Environment

1. In left sidebar, click **Environments**
2. Click **New environment** button
3. Name: `staging`
4. Click **Configure environment**
5. **No protection rules needed** (staging can auto-deploy)
6. Click **Add environment**

---

## Step 3: Add Staging Environment Secrets

Navigate to: Environments → staging → Environment secrets

Click **Add environment secret** for each of the following 7 secrets:

### Secret 1: SSH_KEY

**Name**: `SSH_KEY`

**Value**: Copy the entire output of this command (including BEGIN/END lines):

```bash
cat ~/.ssh/github_actions_staging
```

**Expected format**:
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAA...
... (multiple lines)
-----END OPENSSH PRIVATE KEY-----
```

⚠️ **Critical**: Must include `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----` lines

---

### Secret 2: HOST

**Name**: `HOST`

**Value**:
```
47.88.89.175
```

---

### Secret 3: USER

**Name**: `USER`

**Value**:
```
root
```

---

### Secret 4: API_URL

**Name**: `API_URL`

**Value**:
```
https://api.dev.autoauthor.app/api/v1
```

---

### Secret 5: FRONTEND_URL

**Name**: `FRONTEND_URL`

**Value**:
```
https://dev.autoauthor.app
```

---

### Secret 6: CLERK_PUBLISHABLE_KEY

**Name**: `CLERK_PUBLISHABLE_KEY`

**Value**: Get from server (run this command):

```bash
ssh root@47.88.89.175 "grep NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY /opt/auto-author/current/frontend/.env.production | cut -d= -f2"
```

**Expected format**: `pk_test_...`

---

### Secret 7: CLERK_SECRET_KEY

**Name**: `CLERK_SECRET_KEY`

**Value**: Get from server (run this command):

```bash
ssh root@47.88.89.175 "grep CLERK_SECRET_KEY /opt/auto-author/current/frontend/.env.production | cut -d= -f2"
```

**Expected format**: `sk_test_...`

---

## Step 4: Add Repository Secret (Optional - Slack Notifications)

1. Navigate back to: Settings → Secrets and variables → Actions
2. Click **New repository secret**

### Secret: SLACK_WEBHOOK_URL (Optional)

**Name**: `SLACK_WEBHOOK_URL`

**Value**: Your Slack webhook URL (if you want deployment notifications)

**Expected format**: `https://hooks.slack.com/services/...`

If you don't have a Slack webhook:
1. Go to your Slack workspace
2. Create an app: https://api.slack.com/apps
3. Enable Incoming Webhooks
4. Create a webhook for your channel
5. Copy the webhook URL

**Or skip this** - Workflow will continue without it, just won't send notifications.

---

## Step 5: Verify Secrets Configuration

After adding all secrets, verify the configuration:

1. **Navigate to**: Settings → Environments → staging
2. **Verify you see 7 environment secrets**:
   - SSH_KEY
   - HOST
   - USER
   - API_URL
   - FRONTEND_URL
   - CLERK_PUBLISHABLE_KEY
   - CLERK_SECRET_KEY

3. **Optional**: If configured, verify repository secret:
   - SLACK_WEBHOOK_URL (in Secrets and variables → Actions)

---

## Step 6: Test Configuration

After configuring secrets, test the deployment:

1. **Create test branch**:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b test/verify-ci-cd-secrets
   echo "# Testing CI/CD" >> README.md
   git add README.md
   git commit -m "test: verify GitHub Actions secrets configuration"
   git push origin test/verify-ci-cd-secrets
   ```

2. **Create Pull Request**:
   - Go to GitHub repository
   - Create PR: `test/verify-ci-cd-secrets` → `develop`
   - Watch Test Suite workflow run

3. **Merge PR** (after tests pass):
   - Merge the pull request
   - Deploy to Staging workflow should trigger automatically

4. **Monitor Deployment**:
   - Go to Actions tab: https://github.com/frankbria/auto-author/actions
   - Click on the "Deploy to Staging" workflow
   - Watch the deployment progress

5. **Verify Deployment Success**:
   ```bash
   # Test endpoints:
   curl https://api.dev.autoauthor.app/api/v1/health
   curl -I https://dev.autoauthor.app
   ```

---

## Understanding Secret Naming

### Why Generic Names?

Secrets use **generic names** without environment prefixes:
- ✅ `SSH_KEY` (not `STAGING_SSH_KEY`)
- ✅ `HOST` (not `STAGING_HOST`)
- ✅ `API_URL` (not `STAGING_API_URL`)

**Benefit**: The same workflow file works for both staging and production. The environment determines which secret values are used.

### How It Works

```yaml
# Same workflow code for all environments
environment:
  name: staging  # or production

# Uses SSH_KEY from the "staging" environment
${{ secrets.SSH_KEY }}
```

**Staging Environment** (`staging`):
- `SSH_KEY` → Staging server SSH key
- `HOST` → `47.88.89.175`
- `API_URL` → `https://api.dev.autoauthor.app/api/v1`

**Production Environment** (`production`):
- `SSH_KEY` → Production server SSH key
- `HOST` → Production server IP (TBD)
- `API_URL` → `https://api.autoauthor.app/api/v1`

---

## Troubleshooting

### Error: "Permission denied (publickey)"

**Cause**: SSH key not configured correctly

**Solution**:
1. Verify private key format includes BEGIN/END lines:
   ```bash
   cat ~/.ssh/github_actions_staging | head -1
   # Should show: -----BEGIN OPENSSH PRIVATE KEY-----
   ```

2. Re-copy the **entire** key including BEGIN/END lines to SSH_KEY secret

3. Test SSH connection locally:
   ```bash
   ssh -i ~/.ssh/github_actions_staging root@47.88.89.175 "echo OK"
   ```

### Error: "Build failed - Module not found"

**Cause**: Environment variables not set correctly

**Solution**:
1. Verify API_URL is set correctly in staging environment
2. Verify CLERK_PUBLISHABLE_KEY is set correctly
3. Check secrets are in **staging environment**, not repository secrets

### Error: "curl: (7) Failed to connect"

**Cause**: Server not reachable or services not running

**Solution**:
1. Verify HOST is correct: `47.88.89.175`
2. Check server is online:
   ```bash
   ping 47.88.89.175
   ```
3. SSH to server and check PM2:
   ```bash
   ssh root@47.88.89.175 "pm2 status"
   ```

---

## Security Best Practices

1. **Never commit secrets to git**
   - Secrets should only exist in GitHub Secrets
   - Never put secrets in code or config files that are committed

2. **Rotate SSH keys periodically**
   - Generate new key every 6-12 months
   - Update SSH_KEY secret in all environments
   - Remove old key from servers

3. **Use environment-specific keys**
   - Staging uses `github_actions_staging` key
   - Production should use separate `github_actions_production` key
   - Never reuse keys across environments

4. **Limit SSH key access**
   - Keys are only for deployment automation
   - Consider IP restrictions in `~/.ssh/authorized_keys`
   - Use separate deployment user (not root) for production

---

## Production Secrets (Future)

When ready for production deployment:

### 1. Generate Production SSH Key

```bash
ssh-keygen -t ed25519 -C "github-actions-production" -f ~/.ssh/github_actions_production -N ""

# Copy to production server (when available):
ssh-copy-id -i ~/.ssh/github_actions_production.pub user@production-server
```

### 2. Create Production Environment

1. **Navigate to**: Settings → Environments → New environment
2. **Name**: `production`
3. **Enable protection**:
   - ✅ Required reviewers (add yourself)
   - ✅ Wait timer: 5 minutes (optional)
4. **Click**: Add environment

### 3. Add Production Secrets

Same 7 secret names, different values:

| Secret Name | Production Value |
|-------------|------------------|
| SSH_KEY | Contents of `~/.ssh/github_actions_production` |
| HOST | Production server IP (TBD) |
| USER | Production SSH username (e.g., `deploy`) |
| API_URL | `https://api.autoauthor.app/api/v1` |
| FRONTEND_URL | `https://autoauthor.app` |
| CLERK_PUBLISHABLE_KEY | `pk_live_...` (Clerk production key) |
| CLERK_SECRET_KEY | `sk_live_...` (Clerk production secret) |

---

## Quick Reference

### Staging Secret Values

| Secret | Command to Get Value |
|--------|---------------------|
| SSH_KEY | `cat ~/.ssh/github_actions_staging` |
| HOST | `47.88.89.175` |
| USER | `root` |
| API_URL | `https://api.dev.autoauthor.app/api/v1` |
| FRONTEND_URL | `https://dev.autoauthor.app` |
| CLERK_PUBLISHABLE_KEY | `ssh root@47.88.89.175 "grep NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY /opt/auto-author/current/frontend/.env.production \| cut -d= -f2"` |
| CLERK_SECRET_KEY | `ssh root@47.88.89.175 "grep CLERK_SECRET_KEY /opt/auto-author/current/frontend/.env.production \| cut -d= -f2"` |

### Expected Formats

| Secret | Format |
|--------|--------|
| SSH_KEY | Multi-line, starts with `-----BEGIN OPENSSH PRIVATE KEY-----` |
| HOST | IP address: `47.88.89.175` |
| USER | Username: `root` |
| API_URL | Full URL with /api/v1: `https://api.dev.autoauthor.app/api/v1` |
| FRONTEND_URL | Full URL: `https://dev.autoauthor.app` |
| CLERK_PUBLISHABLE_KEY | Starts with `pk_test_` (staging) or `pk_live_` (production) |
| CLERK_SECRET_KEY | Starts with `sk_test_` (staging) or `sk_live_` (production) |

---

## Checklist

Use this checklist to verify all secrets are configured:

- [ ] Created `staging` environment in GitHub
- [ ] Added SSH_KEY to staging environment (includes BEGIN/END lines)
- [ ] Added HOST to staging environment (47.88.89.175)
- [ ] Added USER to staging environment (root)
- [ ] Added API_URL to staging environment
- [ ] Added FRONTEND_URL to staging environment
- [ ] Added CLERK_PUBLISHABLE_KEY to staging environment (pk_test_...)
- [ ] Added CLERK_SECRET_KEY to staging environment (sk_test_...)
- [ ] (Optional) Added SLACK_WEBHOOK_URL repository secret
- [ ] Verified all 7 staging secrets appear in environment
- [ ] Tested SSH key locally: `ssh -i ~/.ssh/github_actions_staging root@47.88.89.175`
- [ ] Ready to test first automated deployment

---

**Next Step**: After completing this checklist, follow the testing steps in:
- `claudedocs/GITHUB-ACTIONS-IMPLEMENTATION-SUMMARY.md` (Step 2: Test Deployment)

**Estimated Time**: 15 minutes for configuration + 30 minutes for first deployment test = 45 minutes total
