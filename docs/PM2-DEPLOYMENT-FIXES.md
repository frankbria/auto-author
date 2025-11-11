# PM2 Deployment Fixes - November 2025

## Issue Summary

On November 11, 2025, the auto-author-backend service failed to start due to PM2 attempting to execute a Python uvicorn script with Node.js as the interpreter.

### Root Cause

PM2 was configured incorrectly:
- **Interpreter**: Node.js (default) instead of Python
- **Script path**: Direct path to uvicorn binary instead of Python module
- **Working directory**: Old release path instead of current symlink

### Error Symptoms

```
SyntaxError: Invalid or unexpected token
at Object.<anonymous> (/usr/lib/node_modules/pm2/lib/ProcessContainerFork.js:33:23)
```

PM2 status showed:
- Status: `errored`
- Restarts: 15
- Interpreter: `/root/.nvm/versions/node/v24.4.1/bin/node`

## Solution

### 1. Correct PM2 Backend Command

**❌ WRONG (Old Way):**
```bash
pm2 start "$CURRENT_DIR/backend/.venv/bin/uvicorn" \
    --name auto-author-backend \
    -- app.main:app --host 0.0.0.0 --port 8000
```

**Problems:**
- PM2 defaults to Node.js interpreter
- Direct uvicorn path causes Python shebang to be ignored by PM2
- No working directory specified

**✅ CORRECT (New Way):**
```bash
cd "$CURRENT_DIR/backend"
pm2 start .venv/bin/python \
    --name auto-author-backend \
    --cwd "$CURRENT_DIR/backend" \
    -- -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Benefits:**
- Explicitly uses Python interpreter
- Uses Python module syntax (`-m uvicorn`)
- Specifies working directory with `--cwd`
- Works correctly with virtual environment

### 2. Delete Before Restart Pattern

**Issue:** PM2 saves absolute paths to release directories. On new deployments, `pm2 restart` uses the OLD release path.

**Solution:** Delete and recreate PM2 processes on each deployment:

```bash
if pm2 describe auto-author-backend > /dev/null 2>&1; then
    pm2 delete auto-author-backend
fi

pm2 start .venv/bin/python \
    --name auto-author-backend \
    --cwd "$CURRENT_DIR/backend" \
    -- -m uvicorn app.main:app --host 0.0.0.0 --port 8000

pm2 save
```

### 3. Python Version Alignment

**Issue:** GitHub Actions workflows used Python 3.9, but project requires Python 3.13.

**Fixed in:**
- `.github/workflows/deploy-staging.tbd`
- `.github/workflows/deploy-production.yml.disabled`

```yaml
env:
  NODE_VERSION: '18'
  PYTHON_VERSION: '3.13'  # Changed from 3.9
```

### 4. Ecosystem Config File

Created `ecosystem.config.js` for consistent PM2 configuration:

```javascript
module.exports = {
  apps: [
    {
      name: 'auto-author-backend',
      script: '.venv/bin/python',
      args: '-m uvicorn app.main:app --host 0.0.0.0 --port 8000',
      cwd: '/opt/auto-author/current/backend',
      interpreter: 'none', // Critical: prevents Node.js interpretation
      autorestart: true,
      max_restarts: 10,
    }
  ]
};
```

**Usage:**
```bash
pm2 start ecosystem.config.js
pm2 save
```

## Files Modified

1. **scripts/deploy.sh** - Fixed PM2 backend/frontend start commands
2. **scripts/deploy-fixed.sh** - Fixed PM2 commands with additional safety
3. **.github/workflows/deploy-staging.tbd** - Updated Python version
4. **.github/workflows/deploy-production.yml.disabled** - Updated Python version and PM2 commands
5. **ecosystem.config.js** - New PM2 configuration file

## Verification Steps

After deployment, verify:

```bash
# 1. Check PM2 status
pm2 list

# Should show:
# - auto-author-backend: online (not errored)
# - auto-author-frontend: online

# 2. Verify interpreter
pm2 describe auto-author-backend | grep interpreter
# Should show: interpreter: none

# 3. Verify working directory
pm2 describe auto-author-backend | grep "exec cwd"
# Should show: /opt/auto-author/current/backend

# 4. Check backend health
curl http://localhost:8000/
# Should return: {"message":"Welcome to the Auto Author API!"}

# 5. Check logs
pm2 logs auto-author-backend --lines 20
# Should show uvicorn startup logs, not syntax errors
```

## Prevention

To prevent this issue in future:

1. **Always use ecosystem.config.js** for PM2 configuration
2. **Set `interpreter: 'none'`** when starting Python applications
3. **Use `pm2 delete` before `pm2 start`** in deployment scripts
4. **Test deployments** in staging before production
5. **Monitor PM2 logs** after deployment
6. **Keep Python versions aligned** across:
   - `.python-version`
   - GitHub Actions workflows
   - Server environments

## Related Documentation

- [PM2 Documentation - Python](https://pm2.keymetrics.io/docs/usage/application-declaration/#interpreter)
- [Backend Deployment Guide](./Backend-Deployment.md)
- [Staging Deployment Analysis](./STAGING_DEPLOYMENT_ANALYSIS.md)

## Incident Timeline

- **19:37** - Backend entered errored state (15 restarts)
- **19:50** - Issue identified: Node.js interpreting Python code
- **19:52** - Fixed by deleting PM2 process and restarting with correct interpreter
- **19:53** - Backend confirmed online, health checks passing
- **19:55** - Deployment scripts updated to prevent recurrence

## Authors

- Incident Response: Warp AI Agent
- Date: November 11, 2025
