# Staging Server Deployment Guide

**Last Updated**: 2025-10-19
**Target Server**: frankbria-inspiron-7586
**Purpose**: Stable sprint demo and integration testing environment

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Initial Server Setup](#initial-server-setup)
4. [Automated Deployment](#automated-deployment)
5. [Manual Deployment](#manual-deployment)
6. [Service Management](#service-management)
7. [Troubleshooting](#troubleshooting)
8. [CI/CD Integration](#cicd-integration)

---

## Overview

The staging environment serves as:
- **Sprint Demo Environment**: Stable builds for stakeholder demonstrations
- **Integration Testing**: Full-stack testing before production
- **QA Environment**: Manual and automated testing
- **Pre-production Validation**: Final checks before production deployment

### Architecture

```
frankbria-inspiron-7586 (Staging Server)
├── Frontend (Next.js)  → Port 3002
├── Backend (FastAPI)   → Port 8000
└── PostgreSQL Database → Port 5432
```

---

## Prerequisites

### Local Machine

- [x] SSH access to staging server
- [x] Git repository cloned
- [x] Node.js 18+ installed
- [x] Python 3.11+ installed
- [x] uv package manager installed

### Staging Server Requirements

**Software:**
- Ubuntu 20.04 LTS or newer
- Node.js 18+ (for frontend)
- Python 3.11+ (for backend)
- PostgreSQL 14+ (for database)
- PM2 (optional, for process management)
- Nginx (optional, for reverse proxy)

**Resources:**
- 4GB RAM minimum (8GB recommended)
- 20GB disk space minimum
- Network: Ports 3002, 8000 accessible

---

## Initial Server Setup

### Step 1: SSH Key Setup

```bash
# On local machine
ssh-keygen -t ed25519 -C "staging-deployment"

# Copy to staging server
ssh-copy-id frankbria@frankbria-inspiron-7586

# Test connection
ssh frankbria@frankbria-inspiron-7586 echo "SSH connection successful"
```

### Step 2: Install Dependencies on Staging Server

```bash
# SSH into staging server
ssh frankbria@frankbria-inspiron-7586

# Update system
sudo apt update && sudo apt upgrade -y

# Install Node.js 18 LTS
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install uv (Python package manager)
pip3 install uv

# Install PM2 (process manager)
sudo npm install -g pm2

# Install PostgreSQL 14
sudo apt install -y postgresql postgresql-contrib

# (Optional) Install Nginx for reverse proxy
sudo apt install -y nginx
```

### Step 3: Create Deployment Directory

```bash
# On staging server
mkdir -p /home/frankbria/staging/auto-author
cd /home/frankbria/staging/auto-author
```

### Step 4: Configure PostgreSQL

```bash
# On staging server
sudo -u postgres psql

# In PostgreSQL console:
CREATE DATABASE autoauthor_staging;
CREATE USER autoauthor_staging WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE autoauthor_staging TO autoauthor_staging;
\q
```

### Step 5: Environment Variables

Create `.env` files on staging server:

**Backend** (`/home/frankbria/staging/auto-author/current/backend/.env`):

```bash
# Database
DATABASE_URL=postgresql://autoauthor_staging:your_password@localhost:5432/autoauthor_staging

# Authentication (Clerk)
CLERK_JWT_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----
... (copy from local .env) ...
-----END PUBLIC KEY-----

# OpenAI
OPENAI_API_KEY=sk-... (copy from local .env)

# Environment
ENVIRONMENT=staging
DEBUG=false
```

**Frontend** (`/home/frankbria/staging/auto-author/current/frontend/.env.local`):

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://frankbria-inspiron-7586:8000/api/v1

# Authentication (Clerk)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_... (copy from local)
CLERK_SECRET_KEY=sk_test_... (copy from local)

# Environment
NEXT_PUBLIC_ENVIRONMENT=staging
```

---

## Automated Deployment

> **Note**: Deployment is now fully automated via GitHub Actions. Legacy shell scripts have been removed.

### Deployment via GitHub Actions

Deployments to staging are handled automatically by the **Deploy to Staging** workflow (`.github/workflows/deploy-staging.yml`).

**Automatic Triggers:**
- Push to `develop` branch
- After successful test suite completion on `develop`

**Manual Trigger:**
```bash
# Via GitHub CLI
gh workflow run deploy-staging.yml

# Or use GitHub UI:
# Actions tab → Deploy to Staging → Run workflow
```

**The workflow automatically:**
1. ✅ Runs pre-flight checks
2. ✅ Executes test suites (frontend + backend)
3. ✅ Builds production frontend
4. ✅ Creates deployment package
5. ✅ Transfers to staging server via SSH
6. ✅ Extracts and sets up environment
7. ✅ Installs dependencies
8. ✅ Restarts services with PM2
9. ✅ Runs health checks
10. ✅ Executes smoke tests
11. ✅ Sends Slack notification (if configured)

### Required GitHub Secrets

Ensure the following secrets are configured in repository settings:

```
SSH_KEY              # Private SSH key for staging server
HOST                 # Staging server hostname
USER                 # SSH user
API_URL              # Backend API URL
FRONTEND_URL         # Frontend URL
CLERK_PUBLISHABLE_KEY
CLERK_SECRET_KEY
SLACK_WEBHOOK_URL    # (Optional) for notifications
```

### Monitoring Deployments

```bash
# View deployment status
gh run list --workflow=deploy-staging.yml

# View logs for latest deployment
gh run view --log

# Watch deployment in real-time
gh run watch
```

---

## Manual Deployment

If automated deployment fails or you need manual control:

### Step 1: Prepare Package Locally

```bash
# Run tests
cd frontend && npm test
cd ../backend && uv run pytest

# Build frontend
cd ../frontend && npm run build

# Create tar archive
cd ..
tar -czf auto-author.tar.gz \
  --exclude='node_modules' \
  --exclude='.venv' \
  --exclude='.next' \
  --exclude='*.log' \
  frontend/ backend/ docs/ scripts/
```

### Step 2: Transfer to Staging

```bash
scp auto-author.tar.gz frankbria@frankbria-inspiron-7586:/home/frankbria/staging/
```

### Step 3: Extract on Staging

```bash
ssh frankbria@frankbria-inspiron-7586

cd /home/frankbria/staging/auto-author

# Backup current
mv current "backup-$(date +%Y%m%d-%H%M%S)"

# Extract new
mkdir current
cd current
tar -xzf ../../auto-author.tar.gz
```

### Step 4: Setup Dependencies

```bash
# Frontend
cd frontend
npm install --production

# Backend
cd ../backend
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### Step 5: Run Database Migrations

```bash
cd backend
source .venv/bin/activate
uv run alembic upgrade head
```

### Step 6: Start Services

**Option A: With PM2 (Recommended)**

```bash
# Backend
cd backend
pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8000" \
  --name "auto-author-backend-staging"

# Frontend
cd ../frontend
pm2 start "npm start" --name "auto-author-frontend-staging"

# Save PM2 configuration
pm2 save
pm2 startup  # Follow instructions to enable on boot
```

**Option B: Manual (for testing)**

```bash
# Backend
cd backend
source .venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &

# Frontend
cd ../frontend
nohup npm start > frontend.log 2>&1 &
```

---

## Service Management

### PM2 Commands

```bash
# View all services
pm2 list

# View logs
pm2 logs auto-author-backend-staging
pm2 logs auto-author-frontend-staging

# Restart services
pm2 restart auto-author-backend-staging
pm2 restart auto-author-frontend-staging
pm2 restart all

# Stop services
pm2 stop all

# Delete services
pm2 delete all
```

### Manual Process Management

```bash
# Find processes
ps aux | grep uvicorn
ps aux | grep "npm start"

# Kill processes (if started manually)
kill $(cat /home/frankbria/staging/auto-author/current/backend/backend.pid)
kill $(cat /home/frankbria/staging/auto-author/current/frontend/frontend.pid)
```

### Database Management

```bash
# Connect to database
psql -U autoauthor_staging -d autoauthor_staging

# Backup database
pg_dump -U autoauthor_staging autoauthor_staging > backup-$(date +%Y%m%d).sql

# Restore database
psql -U autoauthor_staging autoauthor_staging < backup-20251019.sql
```

---

## Troubleshooting

### Services Won't Start

**Backend:**

```bash
# Check logs
cd /home/frankbria/staging/auto-author/current/backend
cat backend.log

# Common issues:
# 1. Database connection failed
#    - Verify DATABASE_URL in .env
#    - Check PostgreSQL is running: sudo systemctl status postgresql
#
# 2. Port 8000 already in use
#    - Find process: lsof -i :8000
#    - Kill it: kill $(lsof -t -i :8000)
#
# 3. Missing dependencies
#    - Reinstall: uv pip install -r requirements.txt
```

**Frontend:**

```bash
# Check logs
cd /home/frankbria/staging/auto-author/current/frontend
cat frontend.log

# Common issues:
# 1. Port 3002 already in use
#    - Find process: lsof -i :3002
#    - Kill it: kill $(lsof -t -i :3002)
#
# 2. Build artifacts missing
#    - Rebuild: npm run build
#
# 3. Environment variables missing
#    - Check .env.local exists
#    - Verify NEXT_PUBLIC_API_URL points to backend
```

### Health Check Failures

```bash
# Test backend health
curl http://localhost:8000/api/v1/health

# Test frontend
curl http://localhost:3002

# Check database connection
psql -U autoauthor_staging -d autoauthor_staging -c "SELECT 1"
```

### Deployment Script Issues

```bash
# SSH connection fails
ssh-keygen -f "$HOME/.ssh/known_hosts" -R "frankbria-inspiron-7586"
ssh-keygen -R frankbria-inspiron-7586
ssh-copy-id frankbria@frankbria-inspiron-7586

# Permission denied
chmod +x scripts/deploy-staging.sh

# Package transfer fails
# Check disk space on staging:
ssh frankbria@frankbria-inspiron-7586 'df -h'
```

---

## CI/CD Integration

### GitHub Actions Workflow

Future CI/CD automation can use this workflow structure:

```yaml
name: Deploy to Staging

on:
  push:
    branches: [ main, develop ]
  workflow_dispatch:

jobs:
  deploy-staging:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install uv
        run: pip install uv

      - name: Run Tests
        run: |
          cd frontend && npm test
          cd ../backend && uv run pytest

      - name: Deploy to Staging
        env:
          STAGING_HOST: ${{ secrets.STAGING_HOST }}
          STAGING_USER: ${{ secrets.STAGING_USER }}
          SSH_PRIVATE_KEY: ${{ secrets.SSH_PRIVATE_KEY }}
        run: |
          mkdir -p ~/.ssh
          echo "$SSH_PRIVATE_KEY" > ~/.ssh/id_ed25519
          chmod 600 ~/.ssh/id_ed25519
          ./scripts/deploy-staging.sh
```

### Webhook Integration

For automated deployments on git push:

```bash
# On staging server, setup webhook listener
npm install -g webhook

# Create webhook.json configuration
# Start webhook daemon to trigger deployments
```

### Monitoring Integration

Future monitoring setup:

- **Uptime Monitoring**: UptimeRobot, Pingdom
- **Error Tracking**: Sentry
- **Performance**: New Relic, DataDog
- **Logs**: ELK Stack, CloudWatch

---

## Best Practices

### Pre-Deployment Checklist

- [ ] All tests passing locally
- [ ] Code reviewed and merged to main/develop
- [ ] Database migrations prepared (if any)
- [ ] Environment variables documented
- [ ] Backup current staging deployment
- [ ] Notify team of deployment window

### Post-Deployment Verification

- [ ] Health checks pass
- [ ] Smoke tests complete
- [ ] Database migrations applied
- [ ] Frontend loads correctly
- [ ] API endpoints respond
- [ ] Authentication works
- [ ] Critical user flows tested

### Rollback Procedure

```bash
# On staging server
cd /home/frankbria/staging/auto-author

# Stop current services
pm2 stop all

# Restore previous deployment
mv current current-failed
mv backup-YYYYMMDD-HHMMSS current

# Restart services
pm2 restart all

# Verify
curl http://localhost:8000/api/v1/health
curl http://localhost:3002
```

---

## Security Considerations

### Secrets Management

- Never commit `.env` files to git
- Use different credentials for staging vs production
- Rotate credentials regularly
- Limit SSH access to authorized users

### Network Security

```bash
# (Optional) Configure UFW firewall
sudo ufw allow 22     # SSH
sudo ufw allow 3002   # Frontend
sudo ufw allow 8000   # Backend
sudo ufw enable
```

### SSL/TLS (Optional for internal staging)

```bash
# Install Let's Encrypt
sudo apt install certbot python3-certbot-nginx

# Generate certificate
sudo certbot --nginx -d staging.yourdomain.com
```

---

## Maintenance

### Regular Tasks

**Weekly:**
- Review application logs for errors
- Check disk space usage
- Verify backups are working

**Monthly:**
- Update system packages: `sudo apt update && sudo apt upgrade`
- Rotate logs: `pm2 flush`
- Review and clean old backups

**As Needed:**
- Database optimization: `VACUUM ANALYZE`
- Clear old deployment backups
- Update Node.js/Python versions

---

## Support

### Logs Location

```bash
# PM2 logs
~/.pm2/logs/

# Application logs
/home/frankbria/staging/auto-author/current/backend/backend.log
/home/frankbria/staging/auto-author/current/frontend/frontend.log

# System logs
/var/log/postgresql/
/var/log/nginx/
```

### Contact

For deployment issues:
- Check this documentation first
- Review deployment script output
- Check application logs
- Contact DevOps team

---

**Maintained By**: Development Team
**Review Frequency**: Before each major release
**Last Review**: 2025-10-19
