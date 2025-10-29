# GitHub Secrets Verification Checklist

## Required Secrets for Staging Environment

Go to: https://github.com/frankbria/auto-author/settings/secrets/actions

### Environment: `staging`

| Secret Name | Expected Value | Notes |
|-------------|---------------|-------|
| `HOST` | `47.88.89.175` | Staging server IP address |
| `USER` | `root` | SSH username for staging server |
| `SSH_KEY` | Private SSH key | Must include BEGIN/END markers |
| `API_URL` | `https://api.dev.autoauthor.app` | Backend API URL |
| `FRONTEND_URL` | `https://dev.autoauthor.app` | Frontend URL |
| `CLERK_PUBLISHABLE_KEY` | `pk_test_...` | Clerk public key for staging |
| `CLERK_SECRET_KEY` | `sk_test_...` | Clerk secret key for staging |

### Environment: `production`

| Secret Name | Expected Value | Notes |
|-------------|---------------|-------|
| `HOST` | TBD | Production server IP |
| `USER` | `root` | SSH username for production server |
| `SSH_KEY` | Private SSH key | Must include BEGIN/END markers |
| `API_URL` | `https://api.autoauthor.app` | Backend API URL |
| `FRONTEND_URL` | `https://autoauthor.app` | Frontend URL |
| `CLERK_PUBLISHABLE_KEY` | `pk_live_...` | Clerk public key for production |
| `CLERK_SECRET_KEY` | `sk_live_...` | Clerk secret key for production |

### Optional

| Secret Name | Expected Value | Notes |
|-------------|---------------|-------|
| `SLACK_WEBHOOK_URL` | Slack webhook URL | For deployment notifications |

## Critical Issue: SSH_KEY Format

The current deployment failure is caused by the `SSH_KEY` secret having an invalid format.

### How to Verify USER Secret

```bash
# Check if you can SSH with root user
ssh root@47.88.89.175 "whoami"
# Should output: root
```

If this fails, the `USER` secret might be incorrect OR the SSH key isn't authorized for the root user.

### How to Fix SSH_KEY Secret

1. **Get the correct private key:**
   ```bash
   # This is the key that works for: ssh root@47.88.89.175
   cat ~/.ssh/id_rsa  # or wherever your key is located
   ```

2. **Verify it works locally:**
   ```bash
   ssh -i ~/.ssh/id_rsa root@47.88.89.175 "echo 'SSH works!'"
   ```

3. **Copy the ENTIRE key output** (including `-----BEGIN` and `-----END`)

4. **Update GitHub Secret:**
   - Go to: https://github.com/frankbria/auto-author/settings/secrets/actions
   - Click on `SSH_KEY` → Update
   - Paste the private key exactly as shown
   - Click "Update secret"

## Verification Steps

After updating secrets:

1. **Test the USER secret is correct:**
   ```bash
   ssh root@47.88.89.175 "echo 'User is correct'"
   ```

2. **Test the SSH_KEY works:**
   ```bash
   ssh -i ~/.ssh/id_rsa root@47.88.89.175 "echo 'Key works'"
   ```

3. **Trigger a new deployment:**
   ```bash
   git commit --allow-empty -m "test: trigger deployment after secrets verification"
   git push origin develop
   ```

4. **Monitor the workflow:**
   https://github.com/frankbria/auto-author/actions

## Common Issues

### Issue 1: "Permission denied" with correct username
**Cause:** SSH key not authorized for root user
**Fix:** Add public key to `/root/.ssh/authorized_keys` on staging server

### Issue 2: "error in libcrypto"
**Cause:** SSH_KEY secret is corrupted or incomplete
**Fix:** Re-copy the private key following the steps above

### Issue 3: Connection works locally but fails in GitHub Actions
**Cause:** Using a different SSH key locally vs what's in GitHub Secrets
**Fix:** Ensure the same key that works locally is copied to GitHub Secrets
