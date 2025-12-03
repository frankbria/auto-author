#!/bin/bash
# Production Deployment Script
# This script deploys the Auto-Author application to production
# IMPORTANT: This should only be run via GitHub Actions workflow

set -euo pipefail

# Configuration
ENVIRONMENT="production"
DEPLOY_BASE="/opt/auto-author-production"
BACKUP_DIR="$DEPLOY_BASE/backup"
RELEASE_ID="${RELEASE_ID:-$(date +%Y%m%d-%H%M%S)}"
RELEASE_DIR="$DEPLOY_BASE/releases/$RELEASE_ID"
CURRENT_DIR="$DEPLOY_BASE/current"

# Ports
BACKEND_PORT=8001
FRONTEND_PORT=3001

# PM2 App Names
BACKEND_APP="auto-author-api-prod"
FRONTEND_APP="auto-author-web-prod"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Rollback function
rollback() {
    log_error "Deployment failed. Rolling back..."

    if [ -L "$CURRENT_DIR" ] && [ -d "$BACKUP_DIR" ]; then
        LATEST_BACKUP=$(ls -t "$BACKUP_DIR" | head -1)
        if [ -n "$LATEST_BACKUP" ]; then
            log_info "Rolling back to: $LATEST_BACKUP"
            ln -snf "$BACKUP_DIR/$LATEST_BACKUP" "$CURRENT_DIR"

            # Restart PM2 services
            pm2 restart "$BACKEND_APP" 2>/dev/null || true
            pm2 restart "$FRONTEND_APP" 2>/dev/null || true

            log_info "Rollback complete"
            exit 1
        else
            log_error "No backup found for rollback"
            exit 1
        fi
    else
        log_error "Cannot rollback - no backup directory or current symlink"
        exit 1
    fi
}

# Trap errors and rollback
trap rollback ERR

# Check if running as correct user
if [ "$(whoami)" != "root" ]; then
    log_warn "This script should be run as root or with sudo"
fi

# Validate required environment variables
REQUIRED_VARS=(
    "API_URL"
    "FRONTEND_URL"
    "MONGODB_URI"
    "DATABASE_NAME"
    "CLERK_PUBLISHABLE_KEY"
    "CLERK_SECRET_KEY"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        log_error "Required environment variable $var is not set"
        exit 1
    fi
done

log_info "Starting PRODUCTION deployment (Release: $RELEASE_ID)"
log_warn "⚠️  WARNING: Deploying to PRODUCTION - this affects live users"

# Create directories
mkdir -p "$RELEASE_DIR"
mkdir -p "$BACKUP_DIR"

# Backup current release
if [ -L "$CURRENT_DIR" ]; then
    CURRENT_RELEASE=$(readlink -f "$CURRENT_DIR")
    log_info "Backing up current release: $CURRENT_RELEASE"
    cp -rL "$CURRENT_DIR" "$BACKUP_DIR/pre-deploy-$(date +%Y%m%d-%H%M%S)"
fi

# Extract deployment package (should be in /tmp/deploy-package.tar.gz)
if [ -f "/tmp/deploy-package.tar.gz" ]; then
    log_info "Extracting deployment package..."
    tar -xzf /tmp/deploy-package.tar.gz -C "$RELEASE_DIR"
else
    log_error "Deployment package not found at /tmp/deploy-package.tar.gz"
    exit 1
fi

# Setup backend
log_info "Setting up backend..."
cd "$RELEASE_DIR/backend"

# Install Python dependencies using uv
if ! command -v uv &> /dev/null; then
    log_info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

uv venv
source .venv/bin/activate
uv sync

# Create backend .env file
log_info "Creating backend .env file..."
cat > .env << EOF
# Database
DATABASE_URI=$MONGODB_URI
DATABASE_NAME=$DATABASE_NAME

# CORS Settings
BACKEND_CORS_ORIGINS=["$FRONTEND_URL","$API_URL"]

# OpenAI
OPENAI_AUTOAUTHOR_API_KEY=$OPENAI_API_KEY

# Clerk Authentication
CLERK_API_KEY=${CLERK_API_KEY:-}
CLERK_SECRET_KEY=$CLERK_SECRET_KEY
CLERK_FRONTEND_API=${CLERK_FRONTEND_API:-}
CLERK_BACKEND_API=${CLERK_BACKEND_API:-api.clerk.com}
CLERK_WEBHOOK_SECRET=${CLERK_WEBHOOK_SECRET:-}
CLERK_JWT_ALGORITHM=RS256

# API Settings
API_V1_PREFIX=/api/v1

# AWS Settings (Optional)
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-}
AWS_REGION=${AWS_REGION:-}
AWS_S3_BUCKET=${AWS_S3_BUCKET:-}

# Cloudinary Settings (Optional)
CLOUDINARY_CLOUD_NAME=${CLOUDINARY_CLOUD_NAME:-}
CLOUDINARY_API_KEY=${CLOUDINARY_API_KEY:-}
CLOUDINARY_API_SECRET=${CLOUDINARY_API_SECRET:-}
EOF

if [ ! -f .env ]; then
    log_error "Failed to create backend .env file"
    exit 1
fi
log_info "✓ Backend .env file created"

# Setup frontend
log_info "Setting up frontend..."
cd "$RELEASE_DIR/frontend"

# Create frontend .env.production
cat > .env.production << EOF
NEXT_PUBLIC_API_URL=$API_URL
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$CLERK_PUBLISHABLE_KEY
CLERK_SECRET_KEY=$CLERK_SECRET_KEY
NEXT_PUBLIC_ENVIRONMENT=production
PORT=$FRONTEND_PORT
EOF

# Export environment variables for build
export NEXT_PUBLIC_API_URL=$API_URL
export NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$CLERK_PUBLISHABLE_KEY
export CLERK_SECRET_KEY=$CLERK_SECRET_KEY
export NEXT_PUBLIC_ENVIRONMENT=production

# Clean and build
log_info "Cleaning old build cache..."
rm -rf .next

log_info "Installing frontend dependencies..."
npm ci

log_info "Building frontend..."
npm run build

# Generate PM2 ecosystem config
log_info "Generating PM2 ecosystem configuration..."
cd "$RELEASE_DIR"

cat > ecosystem.config.production.js << EOF
module.exports = {
  apps: [
    {
      name: '$BACKEND_APP',
      script: '.venv/bin/uvicorn',
      args: 'app.main:app --host 0.0.0.0 --port $BACKEND_PORT',
      cwd: '$RELEASE_DIR/backend',
      interpreter: 'none',
      env: {
        ENVIRONMENT: 'production',
      },
      error_file: '~/.pm2/logs/$BACKEND_APP-error.log',
      out_file: '~/.pm2/logs/$BACKEND_APP-out.log',
      time: true,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
      watch: false,
    },
    {
      name: '$FRONTEND_APP',
      script: 'npm',
      args: 'start',
      cwd: '$RELEASE_DIR/frontend',
      interpreter: 'none',
      env: {
        NODE_ENV: 'production',
        PORT: '$FRONTEND_PORT',
        NEXT_PUBLIC_API_URL: '$API_URL',
        NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: '$CLERK_PUBLISHABLE_KEY',
        CLERK_SECRET_KEY: '$CLERK_SECRET_KEY',
        NEXT_PUBLIC_ENVIRONMENT: 'production',
      },
      error_file: '~/.pm2/logs/$FRONTEND_APP-error.log',
      out_file: '~/.pm2/logs/$FRONTEND_APP-out.log',
      time: true,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
      watch: false,
    },
  ],
};
EOF

# Update symlink atomically
log_info "Switching to new release..."
ln -snf "$RELEASE_DIR" "$CURRENT_DIR.tmp"
mv -Tf "$CURRENT_DIR.tmp" "$CURRENT_DIR"

# Restart PM2 services
log_info "Restarting PM2 services..."
cd "$CURRENT_DIR"

# Delete old processes (ensures clean pickup of new release)
pm2 delete "$BACKEND_APP" 2>/dev/null || true
pm2 delete "$FRONTEND_APP" 2>/dev/null || true

# Start new processes
pm2 start ecosystem.config.production.js
pm2 save

# Wait for services to start
log_info "Waiting for services to initialize..."
sleep 15

# Health checks
log_info "Running health checks..."

# Backend health check
MAX_RETRIES=10
RETRY_COUNT=0
until curl -f "http://localhost:$BACKEND_PORT/api/v1/health" || [ $RETRY_COUNT -eq $MAX_RETRIES ]; do
    RETRY_COUNT=$((RETRY_COUNT+1))
    log_warn "Backend health check attempt $RETRY_COUNT/$MAX_RETRIES failed, retrying in 3s..."
    sleep 3
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    log_error "Backend health check failed after $MAX_RETRIES attempts"
    rollback
fi
log_info "✓ Backend health check passed"

# Frontend health check
RETRY_COUNT=0
until curl -f -s "http://localhost:$FRONTEND_PORT" >/dev/null || [ $RETRY_COUNT -eq $MAX_RETRIES ]; do
    RETRY_COUNT=$((RETRY_COUNT+1))
    log_warn "Frontend health check attempt $RETRY_COUNT/$MAX_RETRIES failed, retrying in 3s..."
    sleep 3
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    log_error "Frontend health check failed after $MAX_RETRIES attempts"
    log_info "PM2 logs:"
    pm2 logs "$FRONTEND_APP" --lines 50 --nostream
    rollback
fi
log_info "✓ Frontend health check passed"

log_info "✅ PRODUCTION DEPLOYMENT SUCCESSFUL!"
log_info "    Release: $RELEASE_ID"
log_info "    Backend: http://localhost:$BACKEND_PORT (proxied via $API_URL)"
log_info "    Frontend: http://localhost:$FRONTEND_PORT (proxied via $FRONTEND_URL)"

# Cleanup old releases (keep last 5)
log_info "Cleaning up old releases..."
cd "$DEPLOY_BASE/releases"
ls -t | tail -n +6 | xargs -r rm -rf

# Cleanup old backups (keep last 3)
cd "$BACKUP_DIR"
ls -t | tail -n +4 | xargs -r rm -rf

log_info "Cleanup complete"
log_info "🎉 Production deployment finished successfully!"
