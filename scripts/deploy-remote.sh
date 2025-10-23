#!/bin/bash
# Remote deployment script executed on staging/production server
# Usage: ./deploy-remote.sh <environment> <release-id> <api-url> <frontend-url>

set -euo pipefail

ENVIRONMENT=$1        # staging or production
RELEASE_ID=$2         # timestamp or tag (e.g., 20251021-143022 or v1.0.0)
API_URL=$3           # https://api.dev.autoauthor.app/api/v1
FRONTEND_URL=$4      # https://dev.autoauthor.app

DEPLOY_BASE="/opt/auto-author"
RELEASE_DIR="$DEPLOY_BASE/releases/$RELEASE_ID"
CURRENT_DIR="$DEPLOY_BASE/current"

echo "==> Deploying $ENVIRONMENT environment (Release: $RELEASE_ID)"

# Create release directory
mkdir -p "$RELEASE_DIR"

# Extract uploaded package
echo "==> Extracting deployment package..."
tar -xzf /tmp/deploy-package.tar.gz -C "$RELEASE_DIR"

# Setup backend environment
echo "==> Setting up backend..."
cd "$RELEASE_DIR/backend"

# Install Python dependencies
if ! command -v uv &> /dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.cargo/bin:$PATH"
fi

uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Update .env file (merge with existing)
if [ -f "$CURRENT_DIR/backend/.env" ]; then
  cp "$CURRENT_DIR/backend/.env" .env
fi

# Setup frontend environment
echo "==> Setting up frontend..."
cd "$RELEASE_DIR/frontend"

# Install Node dependencies (production only)
npm ci --production

# Create/update .env.production
cat > .env.production <<EOF
NEXT_PUBLIC_API_URL=$API_URL
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$CLERK_PUBLISHABLE_KEY
CLERK_SECRET_KEY=$CLERK_SECRET_KEY
NEXT_PUBLIC_ENVIRONMENT=$ENVIRONMENT
PORT=3002
EOF

# Build frontend
echo "==> Building frontend..."
npm run build

# Update symlink atomically
echo "==> Switching to new release..."
ln -snf "$RELEASE_DIR" "$CURRENT_DIR.tmp"
mv -Tf "$CURRENT_DIR.tmp" "$CURRENT_DIR"

# Restart services
echo "==> Restarting services..."
pm2 restart auto-author-backend || pm2 start "$CURRENT_DIR/backend/.venv/bin/uvicorn" --name auto-author-backend -- app.main:app --host 0.0.0.0 --port 8000
pm2 restart auto-author-frontend || pm2 start npm --name auto-author-frontend --cwd "$CURRENT_DIR/frontend" -- start

# Wait for services to start
sleep 5

# Health checks
echo "==> Running health checks..."
curl -f http://localhost:8000/api/v1/health || {
  echo "ERROR: Backend health check failed"
  exit 1
}

curl -f http://localhost:3002 || {
  echo "ERROR: Frontend health check failed"
  exit 1
}

echo "==> Deployment successful!"
echo "    Release: $RELEASE_ID"
echo "    Backend: http://localhost:8000"
echo "    Frontend: http://localhost:3002"

# Cleanup old releases (keep last 5)
cd "$DEPLOY_BASE/releases"
ls -t | tail -n +6 | xargs -r rm -rf

echo "==> Cleanup complete"
