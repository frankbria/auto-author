# Quick GitHub Secrets Setup - Copy & Paste Guide

**Time**: 5 minutes
**URL**: https://github.com/frankbria/auto-author/settings/secrets/actions

---

## Step 1: Create Staging Environment

1. Go to: https://github.com/frankbria/auto-author/settings/environments
2. Click **"New environment"**
3. Name: `staging`
4. Click **"Configure environment"**
5. Click **"Add environment"** (no protection rules needed)

---

## Step 2: Add 7 Secrets to Staging Environment

Navigate to: **Environments** → **staging** → **Environment secrets**

For each secret below, click **"Add environment secret"** and copy/paste the values:

---

### Secret 1/7: SSH_KEY

**Name**:
```
SSH_KEY
```

**Value** (copy everything including BEGIN/END lines):
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACDOBrLtjBqSNq+6GHxL/fQYiBDFeQZPzBZ3HtEKpKk+ogAAAKBzeGloc3hp
aAAAAAtzc2gtZWQyNTUxOQAAACDOBrLtjBqSNq+6GHxL/fQYiBDFeQZPzBZ3HtEKpKk+og
AAAEByogePKFLjuYk+KQmZM2xhUM82sYCApWZQ4ya6OjMZtc4Gsu2MGpI2r7oYfEv99BiI
EMV5Bk/MFnce0QqkqT6iAAAAFmdpdGh1Yi1hY3Rpb25zLXN0YWdpbmcBAgMEBQYH
-----END OPENSSH PRIVATE KEY-----
```

✅ Click **"Add secret"**

---

### Secret 2/7: HOST

**Name**:
```
HOST
```

**Value**:
```
47.88.89.175
```

✅ Click **"Add secret"**

---

### Secret 3/7: USER

**Name**:
```
USER
```

**Value**:
```
root
```

✅ Click **"Add secret"**

---

### Secret 4/7: API_URL

**Name**:
```
API_URL
```

**Value**:
```
https://api.dev.autoauthor.app/api/v1
```

✅ Click **"Add secret"**

---

### Secret 5/7: FRONTEND_URL

**Name**:
```
FRONTEND_URL
```

**Value**:
```
https://dev.autoauthor.app
```

✅ Click **"Add secret"**

---

### Secret 6/7: CLERK_PUBLISHABLE_KEY

**Name**:
```
CLERK_PUBLISHABLE_KEY
```

**Value**:
```
pk_test_ZGVsaWNhdGUtbGFkeWJpcmQtNDcuY2xlcmsuYWNjb3VudHMuZGV2JA
```

✅ Click **"Add secret"**

---

### Secret 7/7: CLERK_SECRET_KEY

**Name**:
```
CLERK_SECRET_KEY
```

**Value**:
```
sk_test_yxycVoEwI4EzhsYAJ8g0Re8VBKClBrfoQC5OTnS6zE
```

✅ Click **"Add secret"**

---

## Step 3: Verify All Secrets Are Added

You should now see **7 environment secrets** in the staging environment:

- ✅ SSH_KEY
- ✅ HOST
- ✅ USER
- ✅ API_URL
- ✅ FRONTEND_URL
- ✅ CLERK_PUBLISHABLE_KEY
- ✅ CLERK_SECRET_KEY

---

## Step 4 (Optional): Add Slack Notifications

If you want Slack notifications when deployments succeed/fail:

1. Navigate to: https://github.com/frankbria/auto-author/settings/secrets/actions
2. Click **"New repository secret"** (not environment secret)
3. Name: `SLACK_WEBHOOK_URL`
4. Value: Your Slack webhook URL (get from https://api.slack.com/apps)
5. Click **"Add secret"**

**Or skip this** - deployments will work without it, just won't send Slack notifications.

---

## ✅ You're Done!

Your GitHub Actions CI/CD is now fully configured and ready to use.

**Next Step**: Test the deployment by following the instructions in:
- `claudedocs/GITHUB-ACTIONS-IMPLEMENTATION-SUMMARY.md` (Step 2: Test Deployment)

Or simply:

```bash
git checkout develop
git pull origin develop
git checkout -b test/ci-cd-activation
echo "# Testing CI/CD" >> README.md
git add README.md
git commit -m "test: activate GitHub Actions CI/CD"
git push origin test/ci-cd-activation
```

Then create a PR to `develop` on GitHub, watch it run, and merge to trigger staging deployment!

---

**Troubleshooting**: If you have any issues, see `claudedocs/GITHUB-SECRETS-CONFIGURATION.md` for detailed troubleshooting steps.
