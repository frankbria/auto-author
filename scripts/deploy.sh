#!/bin/bash
set -euo pipefail

# Deployment script for Auto-Author staging environment
# This script is called by the GitHub Actions deploy-staging workflow

RELEASE_DIR="${1:-$(pwd)}"
ENVIRONMENT="staging"
DEPLOY_BASE="/opt/auto-author"
CURRENT_DIR="$DEPLOY_BASE/current"

echo "==> Deploying $ENVIRONMENT environment"
echo "    Release directory: $RELEASE_DIR"

# Ensure we're in the release directory
cd "$RELEASE_DIR"

# Setup backend environment
echo "==> Setting up backend..."
cd "$RELEASE_DIR/backend"

# Install Python dependencies using uv
echo "==> Installing Python dependencies..."
if ! command -v uv &> /dev/null; then
    echo "==> Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
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
    echo "NEXT_PUBLIC_API_URL=$API_URL/api/v1"
    echo "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$CLERK_PUBLISHABLE_KEY"
    echo "CLERK_SECRET_KEY=$CLERK_SECRET_KEY"
    echo "NEXT_PUBLIC_ENVIRONMENT=$ENVIRONMENT"
    echo "PORT=3002"
} > .env.production

# Export environment variables for build process
export NEXT_PUBLIC_API_URL=$API_URL/api/v1
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

# Restart backend
if pm2 describe auto-author-backend > /dev/null 2>&1; then
    echo "==> Restarting existing backend service..."
    pm2 restart auto-author-backend
else
    echo "==> Starting new backend service..."
    pm2 start "$CURRENT_DIR/backend/.venv/bin/uvicorn" \
        --name auto-author-backend \
        -- app.main:app --host 0.0.0.0 --port 8000
fi

# Restart frontend
cd "$CURRENT_DIR/frontend"
# Load environment variables from .env.production
set -a
source .env.production
set +a

if pm2 describe auto-author-frontend > /dev/null 2>&1; then
    echo "==> Restarting existing frontend service..."
    pm2 restart auto-author-frontend
else
    echo "==> Starting new frontend service..."
    pm2 start npm --name auto-author-frontend --cwd "$CURRENT_DIR/frontend" -- start
fi

# Save PM2 configuration
pm2 save

# Wait for services to start
echo "==> Waiting for services to start..."
sleep 5

# Health checks
echo "==> Running health checks..."
if curl -f http://localhost:8000/api/v1/health; then
    echo "✅ Backend health check passed"
else
    echo "❌ Backend health check failed"
    exit 1
fi

if curl -f http://localhost:3002; then
    echo "✅ Frontend health check passed"
else
    echo "❌ Frontend health check failed"
    exit 1
fi

echo "==> Deployment successful!"
echo "    Release: $RELEASE_DIR"
echo "    Backend: http://localhost:8000"
echo "    Frontend: http://localhost:3002"

# Cleanup old releases (keep last 5)
echo "==> Cleaning up old releases..."
cd "$DEPLOY_BASE/releases"
ls -t | tail -n +6 | xargs -r rm -rf

echo "==> Cleanup complete"
echo "==> Deployment finished successfully!"
