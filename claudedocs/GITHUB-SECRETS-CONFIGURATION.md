# GitHub Secrets Configuration Guide

**Status**: 🔴 REQUIRED - Must complete before first automated deployment
**Time Required**: 15 minutes
**Prerequisites**: GitHub repository admin access

---

## Overview

This guide provides step-by-step instructions for configuring GitHub secrets required for automated CI/CD deployments.

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

Click **Add environment secret** for each of the following:

### Secret 1: STAGING_SSH_KEY

**Name**: `STAGING_SSH_KEY`

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

### Secret 2: STAGING_HOST

**Name**: `STAGING_HOST`

**Value**:
```
47.88.89.175
```

---

### Secret 3: STAGING_USER

**Name**: `STAGING_USER`

**Value**:
```
root
```

---

### Secret 4: STAGING_API_URL

**Name**: `STAGING_API_URL`

**Value**:
```
https://api.dev.autoauthor.app/api/v1
```

---

### Secret 5: STAGING_FRONTEND_URL

**Name**: `STAGING_FRONTEND_URL`

**Value**:
```
https://dev.autoauthor.app
```

---

### Secret 6: STAGING_CLERK_PUBLISHABLE_KEY

**Name**: `STAGING_CLERK_PUBLISHABLE_KEY`

**Value**: Get from server (run this command):

```bash
ssh root@47.88.89.175 "grep NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY /opt/auto-author/current/frontend/.env.production | cut -d= -f2"
```

**Expected format**: `pk_test_...`

---

### Secret 7: STAGING_CLERK_SECRET_KEY

**Name**: `STAGING_CLERK_SECRET_KEY`

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
   - STAGING_SSH_KEY
   - STAGING_HOST
   - STAGING_USER
   - STAGING_API_URL
   - STAGING_FRONTEND_URL
   - STAGING_CLERK_PUBLISHABLE_KEY
   - STAGING_CLERK_SECRET_KEY

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

## Troubleshooting

### Error: "Permission denied (publickey)"

**Cause**: SSH key not configured correctly

**Solution**:
1. Verify private key format includes BEGIN/END lines:
   ```bash
   cat ~/.ssh/github_actions_staging | head -1
   # Should show: -----BEGIN OPENSSH PRIVATE KEY-----
   ```

2. Re-copy the **entire** key including BEGIN/END lines to STAGING_SSH_KEY secret

3. Test SSH connection locally:
   ```bash
   ssh -i ~/.ssh/github_actions_staging root@47.88.89.175 "echo OK"
   ```

### Error: "Build failed - Module not found"

**Cause**: Environment variables not set correctly

**Solution**:
1. Verify STAGING_API_URL is set correctly
2. Verify STAGING_CLERK_PUBLISHABLE_KEY is set correctly
3. Check secrets are in **staging environment**, not repository secrets

### Error: "curl: (7) Failed to connect"

**Cause**: Server not reachable or services not running

**Solution**:
1. Verify STAGING_HOST is correct: `47.88.89.175`
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
   - Update STAGING_SSH_KEY secret
   - Remove old key from server

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

1. **Create production environment**:
   - Settings → Environments → New environment → `production`
   - **Enable**: Required reviewers (add yourself)
   - This requires manual approval before production deployments

2. **Generate production SSH key**:
   ```bash
   ssh-keygen -t ed25519 -C "github-actions-production" -f ~/.ssh/github_actions_production -N ""
   ```

3. **Add production secrets** (similar to staging):
   - PRODUCTION_SSH_KEY
   - PRODUCTION_HOST (TBD - production server IP)
   - PRODUCTION_USER (TBD - production SSH user)
   - PRODUCTION_API_URL: `https://api.autoauthor.app/api/v1`
   - PRODUCTION_FRONTEND_URL: `https://autoauthor.app`
   - PRODUCTION_CLERK_PUBLISHABLE_KEY: `pk_live_...`
   - PRODUCTION_CLERK_SECRET_KEY: `sk_live_...`

---

## Quick Reference

### Where to Find Secret Values

| Secret | Command to Get Value |
|--------|---------------------|
| STAGING_SSH_KEY | `cat ~/.ssh/github_actions_staging` |
| STAGING_HOST | `47.88.89.175` (hardcoded) |
| STAGING_USER | `root` (hardcoded) |
| STAGING_API_URL | `https://api.dev.autoauthor.app/api/v1` (hardcoded) |
| STAGING_FRONTEND_URL | `https://dev.autoauthor.app` (hardcoded) |
| STAGING_CLERK_PUBLISHABLE_KEY | `ssh root@47.88.89.175 "grep NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY /opt/auto-author/current/frontend/.env.production \| cut -d= -f2"` |
| STAGING_CLERK_SECRET_KEY | `ssh root@47.88.89.175 "grep CLERK_SECRET_KEY /opt/auto-author/current/frontend/.env.production \| cut -d= -f2"` |

### Expected Formats

| Secret | Format |
|--------|--------|
| STAGING_SSH_KEY | Multi-line, starts with `-----BEGIN OPENSSH PRIVATE KEY-----` |
| STAGING_HOST | IP address: `47.88.89.175` |
| STAGING_USER | Username: `root` |
| STAGING_API_URL | Full URL with /api/v1: `https://api.dev.autoauthor.app/api/v1` |
| STAGING_FRONTEND_URL | Full URL: `https://dev.autoauthor.app` |
| STAGING_CLERK_PUBLISHABLE_KEY | Starts with `pk_test_` |
| STAGING_CLERK_SECRET_KEY | Starts with `sk_test_` |

---

## Checklist

Use this checklist to verify all secrets are configured:

- [ ] Created `staging` environment in GitHub
- [ ] Added STAGING_SSH_KEY (includes BEGIN/END lines)
- [ ] Added STAGING_HOST (47.88.89.175)
- [ ] Added STAGING_USER (root)
- [ ] Added STAGING_API_URL (https://api.dev.autoauthor.app/api/v1)
- [ ] Added STAGING_FRONTEND_URL (https://dev.autoauthor.app)
- [ ] Added STAGING_CLERK_PUBLISHABLE_KEY (pk_test_...)
- [ ] Added STAGING_CLERK_SECRET_KEY (sk_test_...)
- [ ] (Optional) Added SLACK_WEBHOOK_URL repository secret
- [ ] Verified all 7 staging secrets appear in environment
- [ ] Tested SSH key locally: `ssh -i ~/.ssh/github_actions_staging root@47.88.89.175`
- [ ] Ready to test first automated deployment

---

**Next Step**: After completing this checklist, follow the testing steps in:
- `claudedocs/GITHUB-ACTIONS-IMPLEMENTATION-SUMMARY.md` (Step 2: Test Deployment)

**Estimated Time**: 15 minutes for configuration + 30 minutes for first deployment test = 45 minutes total
