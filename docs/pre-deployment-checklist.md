# Pre-Deployment Checklist
## Auto-Author Production & Staging Deployments

**Last Updated**: 2025-12-02
**Purpose**: Ensure safe, reliable deployments with proper configuration validation

---

## Overview

This checklist MUST be completed before deploying to staging or production environments. Each item is critical for application functionality.

---

## 1. CORS Configuration Verification

**Why Critical**: Without correct CORS headers, frontend cannot communicate with backend API. Application will be completely unusable.

### Automated Validation

```bash
# For staging deployment
./scripts/validate-cors.sh staging

# For production deployment
./scripts/validate-cors.sh production

# For local testing
./scripts/validate-cors.sh local
```

### Manual Verification

If automated script fails, manually verify CORS:

```bash
# Test OPTIONS preflight request
curl -I -X OPTIONS \
  -H "Origin: https://autoauthor.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type,Authorization" \
  https://api.autoauthor.app/api/v1/books

# Expected headers in response:
# Access-Control-Allow-Origin: https://autoauthor.app (or *)
# Access-Control-Allow-Methods: POST, GET, OPTIONS, PUT, DELETE (or *)
# Access-Control-Allow-Headers: Content-Type, Authorization (or *)
# Access-Control-Allow-Credentials: true
```

### Configuration Files

**Backend CORS Configuration**: `backend/app/core/config.py`

```python
BACKEND_CORS_ORIGINS: Union[List[str], str] = Field(
    default=[
        # Development origins
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:3002",
        "http://localhost:3003",
        # Staging origins
        "https://dev.autoauthor.app",
        "https://api.dev.autoauthor.app",
        # Production origins
        "https://autoauthor.app",
        "https://api.autoauthor.app",
    ],
    json_schema_extra={"env_parse_none_str": "null"}
)
```

**Environment Variable Override**:
```bash
# In .env file or deployment config
BACKEND_CORS_ORIGINS='["https://autoauthor.app","https://api.autoauthor.app"]'
```

### Checklist Items

- [ ] **CORS origins configured** in `backend/app/core/config.py`
- [ ] **Environment variables set** (if using `.env` file)
- [ ] **Validation script passes** (`./scripts/validate-cors.sh <environment>`)
- [ ] **Manual verification** (curl test shows correct headers)
- [ ] **Frontend can make API requests** (test in browser)

---

## 2. Environment Variables

**Why Critical**: Missing environment variables cause runtime errors and security vulnerabilities.

### Backend Environment Variables (`.env`)

**Required**:
```bash
# Database
DATABASE_URI=mongodb://localhost:27017  # or MongoDB Atlas URI
DATABASE_NAME=auto_author_production

# OpenAI
OPENAI_AUTOAUTHOR_API_KEY=sk-...

# Clerk Authentication
CLERK_API_KEY=clerk_...
CLERK_SECRET_KEY=sk_live_...
CLERK_PUBLISHABLE_KEY=pk_live_...
CLERK_FRONTEND_API=your-app.clerk.accounts.dev
CLERK_BACKEND_API=api.clerk.com
CLERK_WEBHOOK_SECRET=whsec_...
CLERK_JWT_ALGORITHM=RS256

# API Settings
API_V1_PREFIX=/api/v1
BACKEND_CORS_ORIGINS='["https://autoauthor.app","https://api.autoauthor.app"]'
```

**Optional** (for production features):
```bash
# AWS (for transcription/storage)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-bucket

# Cloudinary (for image storage)
CLOUDINARY_CLOUD_NAME=your-cloud
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

### Frontend Environment Variables (`.env.production`)

```bash
NEXT_PUBLIC_API_URL=https://api.autoauthor.app
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
CLERK_SECRET_KEY=sk_live_...
NEXT_PUBLIC_ENVIRONMENT=production
PORT=3000
```

### Checklist Items

- [ ] **All required backend variables set**
- [ ] **All required frontend variables set**
- [ ] **No hardcoded secrets** in code
- [ ] **`.env` files not committed** to git (verify `.gitignore`)
- [ ] **GitHub Secrets configured** for CI/CD
- [ ] **Environment-specific values** correct (staging vs production)

---

## 3. Port Conflicts (Shared VPS)

**Why Critical**: The VPS hosts multiple applications. Port conflicts prevent services from starting.

### Current Port Assignments

| Service | Environment | Port | Status |
|---------|-------------|------|--------|
| Backend | Staging | 8000 | In Use |
| Frontend | Staging | 3002 | In Use |
| Backend | Production | TBD | Available |
| Frontend | Production | TBD | Available |

### Verification Steps

```bash
# SSH to server
ssh root@dev.autoauthor.app  # or production server

# Check which ports are in use
sudo lsof -i -P -n | grep LISTEN | grep -E ':(3000|3001|3002|3003|8000|8001|8080)'

# Check PM2 processes
pm2 list

# Check nginx configurations
sudo nginx -T | grep -E 'listen|server_name'
```

### Checklist Items

- [ ] **Verify available ports** before deployment
- [ ] **Update ecosystem.config.js** with correct ports
- [ ] **Update nginx config** for new ports
- [ ] **Update frontend .env** with correct API URL
- [ ] **Test local port binding** before deploying

---

## 4. Database Connection

**Why Critical**: Application cannot function without database access.

### Verification Steps

```bash
# Test MongoDB connection
mongosh "mongodb+srv://..." --eval "db.adminCommand('ping')"

# Or for local MongoDB
mongosh --eval "db.adminCommand('ping')"

# Test from backend
cd backend
uv run python -c "from app.database.base import db; print('Connected!' if db.db else 'Failed')"
```

### Checklist Items

- [ ] **MongoDB running** (local or Atlas)
- [ ] **Connection string correct** in `.env`
- [ ] **Database name correct**
- [ ] **Network access allowed** (for MongoDB Atlas)
- [ ] **Credentials valid**
- [ ] **Test connection** before deploying

---

## 5. Health Checks

**Why Critical**: Deployment scripts depend on health endpoints to verify successful deployment.

### Backend Health Endpoint

```bash
# Test backend health
curl -f http://localhost:8000/api/v1/health

# Expected response:
# {"status": "ok", "timestamp": "2025-12-02T..."}
```

### Frontend Health Check

```bash
# Test frontend is serving
curl -f http://localhost:3000

# Should return HTML (status 200)
```

### Checklist Items

- [ ] **Backend health endpoint** responds correctly
- [ ] **Frontend root route** responds correctly
- [ ] **Health checks pass** within timeout (5 seconds)
- [ ] **Verify in deployment logs** that health checks passed

---

## 6. Build & Test Suite

**Why Critical**: Pre-commit hooks enforce TDD and quality standards.

### Run Pre-Deployment Tests

```bash
# Frontend tests
cd frontend
npm run lint
npm run typecheck
npm test -- --coverage --coverageThreshold='{"global":{"lines":85}}'

# Backend tests
cd backend
uv run pytest --cov=app tests/ --cov-fail-under=85

# E2E tests (optional for staging)
cd frontend
npx playwright test
```

### Checklist Items

- [ ] **All unit tests passing** (100% pass rate)
- [ ] **Test coverage ≥85%** (frontend and backend)
- [ ] **Linting passes** (no errors)
- [ ] **Type checking passes** (no errors)
- [ ] **E2E tests passing** (if running)
- [ ] **Pre-commit hooks installed** and working

---

## 7. Nginx Configuration (Staging/Production)

**Why Critical**: Nginx routes traffic to correct services. Misconfiguration causes 502/504 errors.

### Verify Nginx Config

```bash
# SSH to server
ssh root@dev.autoauthor.app

# Check nginx config
sudo nginx -T | grep -A 20 "dev.autoauthor.app"

# Test nginx config
sudo nginx -t

# Reload nginx (if changes made)
sudo systemctl reload nginx
```

### Expected Configuration

```nginx
# Frontend
server {
    server_name dev.autoauthor.app;
    location / {
        proxy_pass http://localhost:3002;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# Backend API
server {
    server_name api.dev.autoauthor.app;
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Checklist Items

- [ ] **Nginx config exists** for environment
- [ ] **Proxy pass ports correct**
- [ ] **Server names correct** (DNS)
- [ ] **SSL certificates valid** (if HTTPS)
- [ ] **Test nginx config** (`sudo nginx -t`)
- [ ] **Reload nginx** after changes

---

## 8. PM2 Process Management

**Why Critical**: PM2 manages application processes. Misconfiguration causes services to not start.

### Verify PM2 Configuration

```bash
# Check PM2 processes
pm2 list

# Check ecosystem config
cat /opt/auto-author/current/ecosystem.config.js

# Verify process names
pm2 describe auto-author-backend
pm2 describe auto-author-frontend
```

### Expected Ecosystem Config

```javascript
module.exports = {
  apps: [
    {
      name: 'auto-author-backend',
      cwd: '/opt/auto-author/current/backend',
      script: '.venv/bin/uvicorn',
      args: 'app.main:app --host 0.0.0.0 --port 8000',
      interpreter: 'none',
      env: {
        DATABASE_URI: process.env.MONGODB_URI,
        // ... other env vars
      }
    },
    {
      name: 'auto-author-frontend',
      cwd: '/opt/auto-author/current/frontend',
      script: 'npm',
      args: 'start',
      env: {
        PORT: 3002,
        NEXT_PUBLIC_API_URL: 'https://api.dev.autoauthor.app',
        // ... other env vars
      }
    }
  ]
};
```

### Checklist Items

- [ ] **Ecosystem config exists**
- [ ] **Process names unique** (no conflicts)
- [ ] **Working directories correct**
- [ ] **Ports correct**
- [ ] **Environment variables set**
- [ ] **Interpreter correct** (none for uvicorn, node for npm)

---

## 9. Rollback Readiness

**Why Critical**: Deployments can fail. Must be able to rollback quickly.

### Verify Rollback Capability

```bash
# Check previous releases exist
ssh root@dev.autoauthor.app
ls -lt /opt/auto-author/releases

# Test rollback script (dry run)
./scripts/rollback.sh --dry-run  # (if supported)
```

### Checklist Items

- [ ] **Previous release exists** (for rollback)
- [ ] **Rollback script tested**
- [ ] **Team knows rollback procedure**
- [ ] **Database migrations reversible** (if applicable)
- [ ] **Rollback takes <1 minute**

---

## 10. Monitoring & Alerts

**Why Critical**: Need to know immediately if deployment causes issues.

### Verify Monitoring

```bash
# Check logs
pm2 logs auto-author-backend --lines 50
pm2 logs auto-author-frontend --lines 50

# Check error rates (if monitoring tool available)
# Check response times
```

### Checklist Items

- [ ] **PM2 logs accessible**
- [ ] **Error tracking configured** (Sentry, etc.)
- [ ] **Alert notifications working** (Slack, Discord)
- [ ] **Team monitors first 15 minutes** post-deployment

---

## Quick Deployment Checklist

**Use this condensed checklist for rapid pre-deployment validation:**

```bash
# 1. Run validation script
./scripts/validate-cors.sh staging  # or production

# 2. Check environment variables
grep -q "DATABASE_URI" backend/.env && echo "✓ Backend .env exists"
grep -q "NEXT_PUBLIC_API_URL" frontend/.env.production && echo "✓ Frontend .env exists"

# 3. Run tests
cd frontend && npm test && cd ..
cd backend && uv run pytest && cd ..

# 4. Check ports (on server)
ssh root@dev.autoauthor.app "sudo lsof -i :8000 -i :3002"

# 5. Verify health endpoints (post-deploy)
curl -f https://api.dev.autoauthor.app/api/v1/health
curl -f https://dev.autoauthor.app

# 6. Check CORS (post-deploy)
./scripts/validate-cors.sh staging
```

### Condensed Checklist

- [ ] ✅ **CORS validation passes**
- [ ] ✅ **Environment variables set**
- [ ] ✅ **Tests pass (100%, ≥85% coverage)**
- [ ] ✅ **Ports available (no conflicts)**
- [ ] ✅ **Database connection works**
- [ ] ✅ **Health checks pass**
- [ ] ✅ **Nginx config correct**
- [ ] ✅ **PM2 config correct**
- [ ] ✅ **Rollback tested**
- [ ] ✅ **Monitoring active**

---

## Emergency Contacts

**Deployment Issues**: DevOps Team (Slack: #dev-alerts)
**Database Issues**: Backend Team (Slack: #backend)
**CORS/API Issues**: Backend Team (Slack: #backend)
**Frontend Issues**: Frontend Team (Slack: #frontend)

---

## Post-Deployment Validation

**Complete within 15 minutes of deployment:**

1. **Smoke Test**: Create book, generate TOC, write chapter, export
2. **Authentication**: Login/logout works
3. **API Health**: All endpoints responding
4. **Error Monitoring**: No spike in error rates
5. **Performance**: Response times normal
6. **CORS**: Frontend can communicate with backend

If ANY validation fails:
1. **Immediate rollback**: `./scripts/rollback.sh`
2. **Alert team**: Post in Slack #incidents
3. **Debug**: Check logs (`pm2 logs`)
4. **Fix forward or stay rolled back**

---

**Document Version**: 1.0
**Last Updated**: 2025-12-02
**Owner**: DevOps Team
**Next Review**: 2025-01-02
