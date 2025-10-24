#!/bin/bash
set -euo pipefail

# Deployment script for Auto-Author staging environment
# Fixed version addressing issues identified in STAGING_DEPLOYMENT_ANALYSIS.md
# Version: 2.0
# Last Updated: 2025-10-24

RELEASE_DIR="${1:-$(pwd)}"
ENVIRONMENT="staging"
DEPLOY_BASE="/opt/auto-author"
CURRENT_DIR="$DEPLOY_BASE/current"

echo "==> Deploying $ENVIRONMENT environment"
echo "    Release directory: $RELEASE_DIR"
echo "    Script version: 2.0 (fixed)"

# ============================================
# FIX 1: Prerequisites Check
# ============================================
echo "==> Checking prerequisites..."
for cmd in node npm pm2 curl; do
    if ! command -v $cmd &> /dev/null; then
        echo "❌ ERROR: $cmd is not installed"
        echo "    Please install $cmd and try again"
        exit 1
    fi
done
echo "✅ All prerequisites found"

# ============================================
# FIX 2: Rollback Function
# ============================================
rollback() {
    echo "🔄 Rolling back to previous release..."
    PREVIOUS=$(ls -t $DEPLOY_BASE/releases | sed -n '2p')
    if [ -z "$PREVIOUS" ]; then
        echo "❌ No previous release found for rollback"
        return 1
    fi

    echo "    Rolling back to: $PREVIOUS"
    ln -snf "$DEPLOY_BASE/releases/$PREVIOUS" "$CURRENT_DIR.tmp"
    mv -Tf "$CURRENT_DIR.tmp" "$CURRENT_DIR"
    pm2 restart all
    sleep 5

    # Verify rollback worked
    if curl -sf http://localhost:8000/api/v1/health > /dev/null; then
        echo "✅ Rollback complete to: $PREVIOUS"
        return 0
    else
        echo "❌ Rollback failed - manual intervention required"
        return 1
    fi
}

# Ensure we're in the release directory
cd "$RELEASE_DIR"

# Setup backend environment
echo "==> Setting up backend..."
cd "$RELEASE_DIR/backend"

# ============================================
# FIX 3: Improved uv Installation Check
# ============================================
echo "==> Installing Python dependencies..."
if ! command -v uv &> /dev/null; then
    # Check if uv exists in .local/bin but not in PATH
    if [ -f "$HOME/.local/bin/uv" ]; then
        echo "==> Found uv in $HOME/.local/bin, adding to PATH"
        export PATH="$HOME/.local/bin:$PATH"
    else
        echo "==> Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
    fi
else
    echo "✅ uv already available in PATH"
fi

# Verify uv is now accessible
if ! command -v uv &> /dev/null; then
    echo "❌ ERROR: uv installation failed"
    exit 1
fi

uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Get environment variables from systemd environment or fallback to defaults
# These should be set in the GitHub Actions workflow or on the server
API_URL="${API_URL:-https://api.dev.autoauthor.app}"
FRONTEND_URL="${FRONTEND_URL:-https://dev.autoauthor.app}"
CLERK_PUBLISHABLE_KEY="${CLERK_PUBLISHABLE_KEY:-}"
CLERK_SECRET_KEY="${CLERK_SECRET_KEY:-}"
DATABASE_URI="${DATABASE_URI:-}"
DATABASE_NAME="${DATABASE_NAME:-auto_author_staging}"
OPENAI_API_KEY="${OPENAI_API_KEY:-}"

# Validate required environment variables
echo "==> Validating required environment variables..."
MISSING_VARS=()
[ -z "$CLERK_PUBLISHABLE_KEY" ] && MISSING_VARS+=("CLERK_PUBLISHABLE_KEY")
[ -z "$CLERK_SECRET_KEY" ] && MISSING_VARS+=("CLERK_SECRET_KEY")
[ -z "$DATABASE_URI" ] && MISSING_VARS+=("DATABASE_URI")
[ -z "$OPENAI_API_KEY" ] && MISSING_VARS+=("OPENAI_API_KEY")

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo "❌ ERROR: Missing required environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        echo "    - $var"
    done
    echo "    Please set these variables and try again"
    exit 1
fi
echo "✅ All required environment variables present"

# Create backend .env file with all required variables
echo "==> Creating backend .env file..."
{
    echo "ENVIRONMENT=staging"
    echo "DATABASE_URI=$DATABASE_URI"
    echo "DATABASE_NAME=$DATABASE_NAME"
    echo "OPENAI_AUTOAUTHOR_API_KEY=$OPENAI_API_KEY"
    echo "CLERK_API_KEY=$CLERK_SECRET_KEY"
    echo "CLERK_JWT_PUBLIC_KEY=$CLERK_PUBLISHABLE_KEY"
    echo "CLERK_SECRET_KEY=$CLERK_SECRET_KEY"
    echo "CLERK_FRONTEND_API=https://delicate-ladybird-47.clerk.accounts.dev"
    echo "CLERK_BACKEND_API=https://api.clerk.dev"
    echo "CLERK_JWT_ALGORITHM=RS256"
    echo "CLERK_WEBHOOK_SECRET=${CLERK_WEBHOOK_SECRET:-}"
    echo 'BACKEND_CORS_ORIGINS=["'"$FRONTEND_URL"'","https://dev.autoauthor.app","http://localhost:3000"]'
} > .env

echo "==> Backend .env file created"

# Setup frontend environment
echo "==> Setting up frontend..."
cd "$RELEASE_DIR/frontend"

# Install Node dependencies (production only)
echo "==> Installing Node.js dependencies..."
npm ci --omit=dev

# Create/update .env.production with all required variables
echo "==> Creating frontend .env.production file..."
{
    echo "NEXT_PUBLIC_API_URL=$API_URL"
    echo "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$CLERK_PUBLISHABLE_KEY"
    echo "CLERK_SECRET_KEY=$CLERK_SECRET_KEY"
    echo "NEXT_PUBLIC_ENVIRONMENT=$ENVIRONMENT"
    echo "PORT=3002"
} > .env.production

# Export environment variables for build process
export NEXT_PUBLIC_API_URL=$API_URL
export NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$CLERK_PUBLISHABLE_KEY
export CLERK_SECRET_KEY=$CLERK_SECRET_KEY
export NEXT_PUBLIC_ENVIRONMENT=$ENVIRONMENT

# Build frontend with environment variables
echo "==> Building frontend..."
npm run build

# Update symlink atomically
echo "==> Switching to new release..."
ln -snf "$RELEASE_DIR" "$CURRENT_DIR.tmp"
mv -Tf "$CURRENT_DIR.tmp" "$CURRENT_DIR"

# Restart services using PM2
echo "==> Restarting services..."

# ============================================
# FIX 4: Correct PM2 Backend Path
# ============================================
if pm2 describe auto-author-backend > /dev/null 2>&1; then
    echo "==> Restarting existing backend service..."
    pm2 restart auto-author-backend
else
    echo "==> Starting new backend service..."
    # FIXED: Use $RELEASE_DIR instead of $CURRENT_DIR
    pm2 start "$RELEASE_DIR/backend/.venv/bin/uvicorn" \
        --name auto-author-backend \
        -- app.main:app --host 0.0.0.0 --port 8000
fi

# ============================================
# FIX 5: Correct Frontend Directory Path
# ============================================
# FIXED: Use $RELEASE_DIR instead of $CURRENT_DIR
cd "$RELEASE_DIR/frontend"
# Load environment variables from .env.production
set -a
source .env.production
set +a

if pm2 describe auto-author-frontend > /dev/null 2>&1; then
    echo "==> Restarting existing frontend service..."
    pm2 restart auto-author-frontend
else
    echo "==> Starting new frontend service..."
    # FIXED: Use $RELEASE_DIR instead of $CURRENT_DIR
    pm2 start npm --name auto-author-frontend --cwd "$RELEASE_DIR/frontend" -- start
fi

# Save PM2 configuration
pm2 save

# Wait for services to start
echo "==> Waiting for services to start..."
sleep 5

# ============================================
# FIX 6: Health Checks with Rollback
# ============================================
echo "==> Running health checks..."
HEALTH_CHECK_FAILED=false

if curl -sf http://localhost:8000/api/v1/health > /dev/null; then
    echo "✅ Backend health check passed"
else
    echo "❌ Backend health check failed"
    HEALTH_CHECK_FAILED=true
fi

if curl -sf http://localhost:3002 > /dev/null; then
    echo "✅ Frontend health check passed"
else
    echo "❌ Frontend health check failed"
    HEALTH_CHECK_FAILED=true
fi

if [ "$HEALTH_CHECK_FAILED" = true ]; then
    echo "❌ Deployment failed health checks"
    rollback
    exit 1
fi

echo "==> Deployment successful!"
echo "    Release: $RELEASE_DIR"
echo "    Backend: http://localhost:8000"
echo "    Frontend: http://localhost:3002"

# ============================================
# FIX 7: Cleanup AFTER Successful Deployment
# ============================================
echo "==> Cleaning up old releases..."
cd "$DEPLOY_BASE/releases"
# Keep last 5 releases (excluding current)
# Count releases first
RELEASE_COUNT=$(ls -t | wc -l)
if [ "$RELEASE_COUNT" -gt 5 ]; then
    RELEASES_TO_DELETE=$(ls -t | tail -n +6)
    if [ -n "$RELEASES_TO_DELETE" ]; then
        echo "    Removing old releases:"
        echo "$RELEASES_TO_DELETE" | while read release; do
            echo "    - $release"
            rm -rf "$release"
        done
    fi
    echo "✅ Cleanup complete (kept last 5 releases)"
else
    echo "    Only $RELEASE_COUNT releases found, no cleanup needed"
fi

echo "==> Deployment finished successfully!"
echo ""
echo "📊 Deployment Summary:"
echo "    Environment: $ENVIRONMENT"
echo "    Release: $RELEASE_DIR"
echo "    Backend: http://localhost:8000/api/v1/health"
echo "    Frontend: http://localhost:3002"
echo "    Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
