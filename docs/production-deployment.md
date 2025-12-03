# Production Deployment Guide

**Last Updated**: 2025-12-03
**Purpose**: Complete guide for deploying Auto-Author to production environment

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Production Environment](#production-environment)
4. [Deployment Process](#deployment-process)
5. [Rollback Procedures](#rollback-procedures)
6. [Troubleshooting](#troubleshooting)
7. [Post-Deployment Validation](#post-deployment-validation)
8. [Monitoring](#monitoring)

---

## Overview

Auto-Author uses a **GitHub Actions-based deployment workflow** with the following features:

- **Manual approval gate** - Requires explicit approval before production deployment
- **Automated testing** - All tests must pass before deployment
- **Health checks** - Automatic validation after deployment
- **Automatic rollback** - Rolls back on health check failure
- **Manual rollback** - Quick rollback via GitHub Actions
- **Zero-downtime deployment** - Atomic symlink updates
- **Release history** - Keeps last 5 releases for rollback

### Deployment Architecture

```
GitHub Actions Workflow
  ↓
Build & Test
  ↓
Manual Approval (Production Environment)
  ↓
Deploy to Server (/opt/auto-author-production/)
  ↓
Health Checks
  ↓
Success ✅ or Rollback ❌
```

### Server Structure

```
/opt/auto-author-production/
├── current -> releases/20251203-120000/  (symlink)
├── releases/
│   ├── 20251203-120000/  (latest)
│   ├── 20251203-100000/
│   ├── 20251202-150000/
│   └── ...
├── backup/
│   ├── pre-deploy-20251203-120000/
│   ├── pre-deploy-20251203-100000/
│   └── ...
└── shared/
    └── .env files (if needed)
```

---

## Prerequisites

### 1. GitHub Repository Configuration

**Required GitHub Secrets** (Production):

Navigate to: **Settings → Environments → production → Environment secrets**

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `PROD_SSH_KEY` | Private SSH key for server access | (multiline SSH private key) |
| `PROD_HOST` | Production server hostname/IP | `autoauthor.app` |
| `PROD_USER` | SSH username | `root` |
| `PROD_API_URL` | Backend API URL | `https://api.autoauthor.app` |
| `PROD_FRONTEND_URL` | Frontend URL | `https://autoauthor.app` |
| `PROD_MONGODB_URI` | MongoDB connection string | `mongodb+srv://...` |
| `PROD_DATABASE_NAME` | Database name | `auto_author_production` |
| `PROD_CLERK_PUBLISHABLE_KEY` | Clerk publishable key | `pk_live_...` |
| `PROD_CLERK_SECRET_KEY` | Clerk secret key | `sk_live_...` |
| `PROD_CLERK_API_KEY` | Clerk API key | `clerk_...` |
| `PROD_CLERK_FRONTEND_API` | Clerk frontend API | `your-app.clerk.accounts.dev` |
| `PROD_CLERK_BACKEND_API` | Clerk backend API | `api.clerk.com` |
| `PROD_CLERK_WEBHOOK_SECRET` | Clerk webhook secret | `whsec_...` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `SLACK_WEBHOOK_URL` | (Optional) Slack notifications | `https://hooks.slack.com/...` |

**Environment Protection Rules** (Recommended):

1. Go to **Settings → Environments → production**
2. Enable **Required reviewers** (at least 1 reviewer)
3. Enable **Wait timer** (optional, e.g., 5 minutes)
4. Add deployment branches rule: `main` only

### 2. Server Setup

**Server Requirements:**
- Ubuntu 20.04+ (or compatible Linux distribution)
- Node.js 18+
- Python 3.9+
- MongoDB (or MongoDB Atlas connection)
- PM2 (process manager)
- Nginx (reverse proxy)
- SSL certificates (Let's Encrypt recommended)

**Port Assignments:**
- **Backend**: Port 8001 (internal)
- **Frontend**: Port 3001 (internal)
- **Nginx**: Ports 80/443 (external, proxies to internal ports)

**Directory Setup:**

```bash
# Create production directory structure
sudo mkdir -p /opt/auto-author-production/{releases,backup,shared}
sudo chown -R $USER:$USER /opt/auto-author-production
```

### 3. Nginx Configuration

**Backend API** (`/etc/nginx/sites-available/api.autoauthor.app`):

```nginx
server {
    server_name api.autoauthor.app;

    # SSL configuration (managed by certbot)
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/api.autoauthor.app/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.autoauthor.app/privkey.pem;

    location / {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # CORS headers (if needed at nginx level)
        add_header 'Access-Control-Allow-Origin' 'https://autoauthor.app' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;
        add_header 'Access-Control-Expose-Headers' 'Content-Length,Content-Range' always;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}

# HTTP redirect to HTTPS
server {
    listen 80;
    server_name api.autoauthor.app;
    return 301 https://$server_name$request_uri;
}
```

**Frontend** (`/etc/nginx/sites-available/autoauthor.app`):

```nginx
server {
    server_name autoauthor.app www.autoauthor.app;

    # SSL configuration (managed by certbot)
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/autoauthor.app/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/autoauthor.app/privkey.pem;

    location / {
        proxy_pass http://localhost:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;

        # Next.js specific
        proxy_buffering off;
    }

    # Static assets with caching
    location /_next/static {
        proxy_pass http://localhost:3001;
        proxy_cache_valid 200 60m;
        add_header Cache-Control "public, immutable";
    }
}

# HTTP redirect to HTTPS
server {
    listen 80;
    server_name autoauthor.app www.autoauthor.app;
    return 301 https://$server_name$request_uri;
}
```

**Enable configurations:**

```bash
sudo ln -s /etc/nginx/sites-available/api.autoauthor.app /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/autoauthor.app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. SSL Certificates

**Using Let's Encrypt (Certbot):**

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Generate certificates
sudo certbot --nginx -d autoauthor.app -d www.autoauthor.app
sudo certbot --nginx -d api.autoauthor.app

# Auto-renewal is configured automatically
# Test renewal:
sudo certbot renew --dry-run
```

---

## Deployment Process

### Method 1: Tag-Based Deployment (Recommended)

**Trigger deployment by creating a release tag:**

```bash
# 1. Ensure all changes are committed to main
git checkout main
git pull origin main

# 2. Create and push a version tag
git tag v1.0.0
git push origin v1.0.0

# 3. Deployment workflow will automatically trigger
# 4. Go to GitHub Actions tab to approve deployment
```

**Tag naming convention:**
- `v1.0.0` - Major release
- `v1.0.1` - Patch release
- `v1.1.0` - Minor release

### Method 2: Manual Deployment

**Trigger deployment manually via GitHub Actions:**

1. Go to **GitHub → Actions → Deploy to Production**
2. Click **Run workflow**
3. Select branch: `main`
4. Optional: Check **Skip tests** (emergency only)
5. Click **Run workflow**
6. **Wait for approval gate** (if configured)
7. **Approve deployment** in Environments tab

### Deployment Steps (Automated)

The workflow performs these steps automatically:

1. **Validation Phase** (if not skipped):
   - Frontend linting and type checking
   - Frontend unit tests with coverage
   - Backend linting
   - Backend unit tests with coverage
   - Security scan for secrets

2. **Build Phase**:
   - Checkout code
   - Setup Node.js and Python
   - Install dependencies
   - Build frontend with production environment variables
   - Create deployment package

3. **Deploy Phase**:
   - Upload package to server
   - Extract to new release directory
   - Setup backend (uv venv, install dependencies, create .env)
   - Setup frontend (install dependencies, build, create .env.production)
   - Generate PM2 ecosystem config
   - Update symlink to new release
   - Restart PM2 services (delete + start for clean pickup)

4. **Validation Phase**:
   - Wait 15 seconds for services to start
   - Backend health check (10 retries, 3s interval)
   - Frontend health check (10 retries, 3s interval)
   - External health checks (5 retries, 5s interval)
   - CORS verification
   - Smoke tests (API docs endpoint)

5. **Success/Failure**:
   - On success: Send notification, cleanup old releases
   - On failure: Automatic rollback to previous release

### Monitoring Deployment

**View deployment logs:**

1. Go to **GitHub → Actions → Deploy to Production**
2. Click on the running workflow
3. Expand job steps to see detailed logs

**SSH to server during deployment:**

```bash
ssh root@autoauthor.app

# Watch PM2 logs
pm2 logs auto-author-api-prod --lines 50
pm2 logs auto-author-web-prod --lines 50

# Check PM2 status
pm2 list

# Check health endpoints
curl http://localhost:8001/api/v1/health
curl http://localhost:3001
```

---

## Rollback Procedures

### Automatic Rollback

If health checks fail during deployment, the workflow **automatically rolls back** to the previous release.

**Rollback process:**
1. Restore symlink to backup directory
2. Restart PM2 services
3. Run health checks
4. Send failure notification

### Manual Rollback

**Trigger manual rollback via GitHub Actions:**

1. Go to **GitHub → Actions → Rollback Production**
2. Click **Run workflow**
3. **Enter rollback reason** (required)
4. Optional: Enter specific **Release ID** (e.g., `20251203-100000`)
   - Leave empty to rollback to latest backup
5. Click **Run workflow**
6. **Approve rollback** (if environment protection enabled)

**Via SSH (Emergency):**

```bash
# SSH to server
ssh root@autoauthor.app

# Check available backups
ls -lt /opt/auto-author-production/backup/

# Manual rollback to specific backup
cd /opt/auto-author-production
ln -snf backup/pre-deploy-20251203-100000 current

# Restart services
pm2 restart auto-author-api-prod
pm2 restart auto-author-web-prod

# Verify health
curl http://localhost:8001/api/v1/health
curl http://localhost:3001
```

### Rollback Verification

After rollback, verify:

1. **Health checks pass** (both internal and external)
2. **CORS working** (frontend can communicate with backend)
3. **Application functional** (test critical user flows)
4. **No error spikes** in logs
5. **PM2 processes stable** (`pm2 list`)

---

## Troubleshooting

### Common Issues

#### 1. Health Check Failures

**Symptom**: Deployment fails with "Backend/Frontend health check failed"

**Diagnosis**:

```bash
# SSH to server
ssh root@autoauthor.app

# Check PM2 status
pm2 list

# Check logs
pm2 logs auto-author-api-prod --lines 100
pm2 logs auto-author-web-prod --lines 100

# Check if ports are listening
sudo lsof -i :8001
sudo lsof -i :3001

# Check health endpoints
curl http://localhost:8001/api/v1/health
curl http://localhost:3001
```

**Solutions**:
- **Port conflict**: Another service using port 8001/3001
- **Environment variables**: Check `.env` files in release directory
- **Database connection**: Verify `DATABASE_URI` is correct
- **Build failure**: Check frontend build completed successfully
- **Memory issues**: Check `pm2 list` for memory usage

#### 2. CORS Errors

**Symptom**: Frontend cannot communicate with backend, CORS errors in browser console

**Diagnosis**:

```bash
# Test CORS headers
curl -I -X OPTIONS https://api.autoauthor.app/api/v1/books \
  -H "Origin: https://autoauthor.app" \
  -H "Access-Control-Request-Method: POST"

# Check backend CORS configuration
ssh root@autoauthor.app
cd /opt/auto-author-production/current/backend
grep BACKEND_CORS_ORIGINS .env
```

**Solutions**:
- Verify `BACKEND_CORS_ORIGINS` includes production URLs
- Check nginx CORS headers (if configured at nginx level)
- Restart backend: `pm2 restart auto-author-api-prod`

#### 3. Frontend Build Failures

**Symptom**: Frontend shows 500 errors or pages don't load

**Diagnosis**:

```bash
# Check frontend build logs
ssh root@autoauthor.app
cd /opt/auto-author-production/current/frontend
cat ~/.pm2/logs/auto-author-web-prod-error.log

# Check .next directory exists
ls -la .next/
```

**Solutions**:
- Verify `.env.production` has all required variables
- Check `NEXT_PUBLIC_API_URL` is correct
- Rebuild frontend: `npm run build`
- Restart: `pm2 restart auto-author-web-prod`

#### 4. Database Connection Issues

**Symptom**: Backend starts but returns 500 errors on API calls

**Diagnosis**:

```bash
# Test MongoDB connection
mongosh "$DATABASE_URI" --eval "db.adminCommand('ping')"

# Check backend logs for MongoDB errors
pm2 logs auto-author-api-prod | grep -i mongo
```

**Solutions**:
- Verify `DATABASE_URI` in backend `.env`
- Check MongoDB Atlas network access (whitelist server IP)
- Verify database credentials
- Check MongoDB Atlas cluster is running

#### 5. PM2 Process Crashes

**Symptom**: PM2 shows `errored` or `stopped` status

**Diagnosis**:

```bash
# Check PM2 status
pm2 list

# View recent logs
pm2 logs auto-author-api-prod --lines 200
pm2 logs auto-author-web-prod --lines 200

# Check process info
pm2 info auto-author-api-prod
```

**Solutions**:
- Check logs for error messages
- Verify all environment variables are set
- Check memory usage (`pm2 list` shows memory)
- Restart: `pm2 restart <app-name>`
- If persistent: `pm2 delete <app-name> && pm2 start ecosystem.config.production.js`

### Emergency Procedures

#### Total Failure - Full System Rollback

```bash
# 1. SSH to server
ssh root@autoauthor.app

# 2. Rollback to last known good release
cd /opt/auto-author-production
LAST_BACKUP=$(ls -t backup/ | head -1)
ln -snf "backup/$LAST_BACKUP" current

# 3. Restart all services
pm2 restart all

# 4. Verify
curl http://localhost:8001/api/v1/health
curl http://localhost:3001
```

#### Nginx Issues

```bash
# Test nginx config
sudo nginx -t

# View nginx error logs
sudo tail -f /var/log/nginx/error.log

# Restart nginx
sudo systemctl restart nginx
```

#### SSL Certificate Issues

```bash
# Check certificate expiry
sudo certbot certificates

# Renew certificates
sudo certbot renew

# Reload nginx
sudo systemctl reload nginx
```

---

## Post-Deployment Validation

**Complete within 15 minutes of deployment:**

### 1. Smoke Tests

```bash
# Backend API health
curl -f https://api.autoauthor.app/api/v1/health

# Frontend homepage
curl -f https://autoauthor.app

# API docs
curl -f https://api.autoauthor.app/docs

# CORS check
curl -I -X OPTIONS https://api.autoauthor.app/api/v1/books \
  -H "Origin: https://autoauthor.app" \
  -H "Access-Control-Request-Method: POST"
```

### 2. User Flow Testing

Manually test critical user flows:

1. **Authentication**: Login/logout works
2. **Book Creation**: Can create new book
3. **TOC Generation**: AI wizard works
4. **Chapter Editing**: Can write and save chapters
5. **Export**: Can export to PDF/DOCX

### 3. Error Monitoring

```bash
# Watch logs for errors
ssh root@autoauthor.app
pm2 logs --lines 100

# Check for error spikes in monitoring dashboard (if configured)
```

### 4. Performance Check

- **Response times**: API responses < 500ms
- **Page load times**: Frontend pages < 3s
- **No memory leaks**: PM2 memory usage stable

### 5. Checklist

- [ ] Backend health endpoint responds
- [ ] Frontend homepage loads
- [ ] API docs accessible
- [ ] CORS working
- [ ] User can login
- [ ] User can create book
- [ ] TOC generation works
- [ ] Chapter editing works
- [ ] Export works
- [ ] No error spikes in logs
- [ ] PM2 processes stable
- [ ] Response times normal

**If ANY validation fails:**
1. Immediate rollback (manual or automatic)
2. Alert team
3. Debug issue
4. Fix forward or stay rolled back

---

## Monitoring

### PM2 Monitoring

```bash
# View PM2 dashboard
pm2 monit

# List processes
pm2 list

# View logs
pm2 logs
pm2 logs auto-author-api-prod
pm2 logs auto-author-web-prod

# Flush logs
pm2 flush
```

### Server Monitoring

```bash
# System resources
htop

# Disk usage
df -h

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Application Monitoring

**Setup external monitoring** (recommended):

- **Uptime monitoring**: UptimeRobot, Pingdom
- **Error tracking**: Sentry (configure in backend)
- **Log aggregation**: Papertrail, Loggly
- **APM**: New Relic, DataDog

**Slack/Discord Notifications**:

Configure `SLACK_WEBHOOK_URL` or `DISCORD_WEBHOOK_URL` in GitHub Secrets to receive:
- Deployment success/failure notifications
- Rollback notifications
- Health check failures

---

## Release Management

### Creating a Release

```bash
# 1. Update version in package.json (if applicable)
# 2. Update CHANGELOG.md
# 3. Commit changes
git add .
git commit -m "chore: bump version to 1.0.0"

# 4. Create tag
git tag -a v1.0.0 -m "Release v1.0.0"

# 5. Push to trigger deployment
git push origin main
git push origin v1.0.0

# 6. Monitor deployment in GitHub Actions
# 7. Approve deployment when prompted
```

### Release Notes Template

```markdown
## v1.0.0 - 2025-12-03

### Features
- New feature X
- Enhancement to Y

### Bug Fixes
- Fixed issue #123
- Resolved problem with Z

### Breaking Changes
- API endpoint /api/v1/old changed to /api/v1/new

### Deployment Notes
- Requires database migration (run before deploying)
- New environment variable: NEW_VAR
```

---

## Appendix

### Useful Commands

```bash
# SSH to server
ssh root@autoauthor.app

# View PM2 status
pm2 list

# View logs
pm2 logs

# Restart services
pm2 restart auto-author-api-prod
pm2 restart auto-author-web-prod

# Check health
curl http://localhost:8001/api/v1/health
curl http://localhost:3001

# View nginx logs
sudo tail -f /var/log/nginx/error.log

# Test nginx config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx

# Check disk space
df -h

# Check release history
ls -lt /opt/auto-author-production/releases
```

### Security Best Practices

1. **Never commit secrets** to repository
2. **Use environment variables** for all sensitive data
3. **Rotate API keys** regularly
4. **Keep SSL certificates** up to date
5. **Monitor for vulnerabilities** (Dependabot, npm audit)
6. **Use HTTPS** for all external communication
7. **Implement rate limiting** on API endpoints
8. **Regular security audits**

### Maintenance Schedule

- **Daily**: Check PM2 status, review error logs
- **Weekly**: Review performance metrics, check disk space
- **Monthly**: Update dependencies, rotate API keys, review SSL certificates
- **Quarterly**: Security audit, load testing, disaster recovery drill

---

**Document Version**: 1.0
**Last Updated**: 2025-12-03
**Owner**: DevOps Team
**Next Review**: 2026-01-03
