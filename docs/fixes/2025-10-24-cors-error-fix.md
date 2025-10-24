# CORS Error Fix - Staging Dashboard (2025-10-24)

## Problem
The staging dashboard at https://dev.autoauthor.app was experiencing CORS errors when trying to communicate with the backend API at https://api.dev.autoauthor.app.

## Root Cause Analysis

### Timeline of Events
1. **Commit 700cc96** (2025-10-23): Fixed CORS errors by creating backend `.env` file during deployment with proper `BACKEND_CORS_ORIGINS` configuration
2. **Commit 4c3123d** (2025-10-24): "Refactored deploy-staging workflow for clarity and efficiency"
   - Removed 214 lines of deployment logic
   - Delegated all deployment to `scripts/deploy.sh`
   - **Problem**: `scripts/deploy.sh` didn't exist!

### Impact
- Backend `.env` file was never created during deployment
- `BACKEND_CORS_ORIGINS` environment variable was not set
- Backend FastAPI defaulted to only allowing `localhost` origins
- Dashboard experienced CORS errors when making API requests

## Solution

### Files Created/Modified

#### 1. `scripts/deploy.sh` (NEW)
Complete deployment script that includes:
- Python environment setup with uv
- Backend `.env` file creation with all required variables:
  ```bash
  ENVIRONMENT=staging
  DATABASE_URI=$DATABASE_URI
  DATABASE_NAME=$DATABASE_NAME
  OPENAI_AUTOAUTHOR_API_KEY=$OPENAI_API_KEY
  CLERK_API_KEY=$CLERK_SECRET_KEY
  CLERK_JWT_PUBLIC_KEY=$CLERK_PUBLISHABLE_KEY
  CLERK_SECRET_KEY=$CLERK_SECRET_KEY
  CLERK_FRONTEND_API=https://delicate-ladybird-47.clerk.accounts.dev
  CLERK_BACKEND_API=https://api.clerk.dev
  CLERK_JWT_ALGORITHM=RS256
  CLERK_WEBHOOK_SECRET=$CLERK_WEBHOOK_SECRET
  BACKEND_CORS_ORIGINS=["$FRONTEND_URL","https://dev.autoauthor.app","http://localhost:3000"]
  ```
- Frontend `.env.production` file creation
- Frontend build process
- PM2 service restart
- Health checks
- Old release cleanup

#### 2. `.github/workflows/deploy-staging.yml` (MODIFIED)
Updated to pass all required secrets to the deploy script:
- API_URL
- FRONTEND_URL
- CLERK_PUBLISHABLE_KEY
- CLERK_SECRET_KEY
- DATABASE_URI
- DATABASE_NAME
- OPENAI_API_KEY
- CLERK_WEBHOOK_SECRET

Also fixed typo: `staging_keyts` → `staging_key`

## Testing

### Syntax Verification
```bash
bash -n scripts/deploy.sh  # No syntax errors
```

### Deployment
The fix has been committed to the `develop` branch and will be automatically deployed to staging by GitHub Actions when the test suite passes.

### Verification Steps
After deployment completes:
1. Check backend health: `curl https://api.dev.autoauthor.app/api/v1/health`
2. Check frontend: `curl https://dev.autoauthor.app`
3. Test CORS headers:
   ```bash
   curl -I -X OPTIONS https://api.dev.autoauthor.app/api/v1/books \
     -H "Origin: https://dev.autoauthor.app" \
     -H "Access-Control-Request-Method: GET"
   ```
   Should see: `Access-Control-Allow-Origin: https://dev.autoauthor.app`
4. Test dashboard functionality in browser

## Prevention

### Lesson Learned
When refactoring deployment workflows:
1. **Never remove deployment logic without replacement** - The refactoring removed critical .env file creation
2. **Test deployment changes** - The missing script would have been caught by running the workflow
3. **Document external script dependencies** - If workflow calls a script, ensure it exists in the repo

### Future Improvements
1. Add validation to deployment workflow to check if required scripts exist
2. Consider inline deployment steps vs external scripts for critical configuration
3. Add integration tests for deployment workflow

## References
- Commit 700cc96: Original CORS fix with inline .env creation
- Commit 4c3123d: Refactoring that removed deployment logic
- Commit f11798a: This fix - restored deployment script
- Backend config: `/home/frankbria/projects/auto-author/backend/app/core/config.py:22-25`
- Backend CORS setup: `/home/frankbria/projects/auto-author/backend/app/main.py:28-34`
