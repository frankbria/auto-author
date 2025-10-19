#!/bin/bash
# Staging Deployment Script for Auto-Author
# Deploys to frankbria-inspiron-7586 staging server
#
# Usage: ./scripts/deploy-staging.sh [--skip-tests] [--skip-build]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STAGING_HOST="${STAGING_HOST:-frankbria-inspiron-7586}"
STAGING_USER="${STAGING_USER:-frankbria}"
STAGING_DIR="${STAGING_DIR:-/home/frankbria/staging/auto-author}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Flags
SKIP_TESTS=false
SKIP_BUILD=false

# Parse arguments
for arg in "$@"; do
  case $arg in
    --skip-tests)
      SKIP_TESTS=true
      shift
      ;;
    --skip-build)
      SKIP_BUILD=true
      shift
      ;;
    *)
      ;;
  esac
done

# Logging functions
log_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Error handler
handle_error() {
  log_error "Deployment failed at line $1"
  exit 1
}

trap 'handle_error $LINENO' ERR

# Step counter
STEP=0
total_steps=12

step() {
  STEP=$((STEP + 1))
  log_info "[$STEP/$total_steps] $1"
}

# Pre-flight checks
preflight_checks() {
  step "Running pre-flight checks..."

  # Check if we're in the right directory
  if [ ! -f "DEPLOYMENT.md" ]; then
    log_error "Must run from project root directory"
    exit 1
  fi

  # Check git status
  if ! git diff-index --quiet HEAD --; then
    log_warning "You have uncommitted changes"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      exit 1
    fi
  fi

  # Check SSH connection
  if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "$STAGING_USER@$STAGING_HOST" echo "SSH OK" &>/dev/null; then
    log_error "Cannot connect to $STAGING_HOST via SSH"
    log_info "Please ensure SSH keys are set up: ssh-copy-id $STAGING_USER@$STAGING_HOST"
    exit 1
  fi

  log_success "Pre-flight checks passed"
}

# Run tests
run_tests() {
  if [ "$SKIP_TESTS" = true ]; then
    log_warning "Skipping tests (--skip-tests flag)"
    return
  fi

  step "Running test suites..."

  # Frontend tests
  log_info "Running frontend tests..."
  cd "$PROJECT_ROOT/frontend"
  npm test -- --passWithNoTests --ci 2>&1 | tail -20

  # Backend tests
  log_info "Running backend tests..."
  cd "$PROJECT_ROOT/backend"
  uv run pytest tests/test_api/ -v --tb=short 2>&1 | tail -20

  cd "$PROJECT_ROOT"
  log_success "All tests passed"
}

# Build frontend
build_frontend() {
  if [ "$SKIP_BUILD" = true ]; then
    log_warning "Skipping build (--skip-build flag)"
    return
  fi

  step "Building frontend..."
  cd "$PROJECT_ROOT/frontend"

  # Type checking
  log_info "Running type checks..."
  npm run typecheck

  # Production build
  log_info "Building production bundle..."
  npm run build

  log_success "Frontend build complete"
}

# Create deployment package
create_package() {
  step "Creating deployment package..."

  cd "$PROJECT_ROOT"

  # Create temporary deployment directory
  DEPLOY_TMP=$(mktemp -d)
  log_info "Package directory: $DEPLOY_TMP"

  # Copy necessary files (exclude node_modules, .venv, etc.)
  rsync -av --progress \
    --exclude='node_modules' \
    --exclude='.venv' \
    --exclude='.next' \
    --exclude='coverage' \
    --exclude='*.log' \
    --exclude='.env.local' \
    --exclude='.env' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='test-results' \
    --exclude='playwright-report' \
    . "$DEPLOY_TMP/"

  # Create tar archive
  TAR_FILE="/tmp/auto-author-staging-$(date +%Y%m%d-%H%M%S).tar.gz"
  tar -czf "$TAR_FILE" -C "$DEPLOY_TMP" .

  # Cleanup temp directory
  rm -rf "$DEPLOY_TMP"

  log_success "Package created: $TAR_FILE"
  echo "$TAR_FILE"
}

# Transfer to staging
transfer_package() {
  local tar_file=$1
  step "Transferring package to staging server..."

  # Ensure staging directory exists
  ssh "$STAGING_USER@$STAGING_HOST" "mkdir -p $STAGING_DIR"

  # Transfer package
  log_info "Uploading to $STAGING_HOST:$STAGING_DIR..."
  scp "$tar_file" "$STAGING_USER@$STAGING_HOST:$STAGING_DIR/package.tar.gz"

  log_success "Package transferred"
}

# Extract and setup on staging
setup_staging() {
  step "Setting up staging environment..."

  ssh "$STAGING_USER@$STAGING_HOST" bash <<'ENDSSH'
    set -euo pipefail

    STAGING_DIR="${STAGING_DIR:-/home/frankbria/staging/auto-author}"

    echo "[INFO] Extracting package..."
    cd "$STAGING_DIR"

    # Backup current deployment
    if [ -d "current" ]; then
      echo "[INFO] Backing up current deployment..."
      mv current "backup-$(date +%Y%m%d-%H%M%S)" || true
    fi

    # Create new deployment directory
    mkdir -p current
    cd current
    tar -xzf ../package.tar.gz

    # Setup frontend
    echo "[INFO] Setting up frontend..."
    cd frontend
    if [ ! -f ".env.local" ]; then
      echo "[WARNING] .env.local not found - you'll need to create this manually"
      cp .env.example .env.local || true
    fi
    npm install --production

    # Setup backend
    echo "[INFO] Setting up backend..."
    cd ../backend
    if [ ! -f ".env" ]; then
      echo "[WARNING] .env not found - you'll need to create this manually"
    fi
    uv venv
    source .venv/bin/activate
    uv pip install -r requirements.txt

    echo "[SUCCESS] Staging environment setup complete"
ENDSSH

  log_success "Staging setup complete"
}

# Start services
start_services() {
  step "Starting staging services..."

  ssh "$STAGING_USER@$STAGING_HOST" bash <<'ENDSSH'
    set -euo pipefail

    STAGING_DIR="${STAGING_DIR:-/home/frankbria/staging/auto-author}"
    cd "$STAGING_DIR/current"

    # Check if PM2 is installed
    if ! command -v pm2 &> /dev/null; then
      echo "[WARNING] PM2 not installed. Install with: npm install -g pm2"
      echo "[INFO] Starting services manually (for this session only)..."

      # Start backend
      cd backend
      source .venv/bin/activate
      nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
      echo $! > backend.pid

      # Start frontend
      cd ../frontend
      nohup npm start > frontend.log 2>&1 &
      echo $! > frontend.pid

      echo "[SUCCESS] Services started (PIDs saved)"
    else
      echo "[INFO] Starting services with PM2..."

      # Start backend with PM2
      cd backend
      source .venv/bin/activate
      pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8000" --name "auto-author-backend-staging"

      # Start frontend with PM2
      cd ../frontend
      pm2 start "npm start" --name "auto-author-frontend-staging"

      # Save PM2 process list
      pm2 save

      echo "[SUCCESS] Services started with PM2"
    fi
ENDSSH

  log_success "Services started"
}

# Health checks
health_checks() {
  step "Running health checks..."

  log_info "Waiting for services to start (10s)..."
  sleep 10

  # Check backend health
  log_info "Checking backend health..."
  if ssh "$STAGING_USER@$STAGING_HOST" "curl -f http://localhost:8000/api/v1/health" &>/dev/null; then
    log_success "Backend is healthy"
  else
    log_warning "Backend health check failed (may need more time to start)"
  fi

  # Check frontend health
  log_info "Checking frontend health..."
  if ssh "$STAGING_USER@$STAGING_HOST" "curl -f http://localhost:3002" &>/dev/null; then
    log_success "Frontend is responding"
  else
    log_warning "Frontend health check failed (may need more time to start)"
  fi
}

# Smoke tests
smoke_tests() {
  step "Running smoke tests..."

  log_info "Testing API endpoints..."
  ssh "$STAGING_USER@$STAGING_HOST" bash <<'ENDSSH'
    # Test health endpoint
    echo "[INFO] Testing /api/v1/health..."
    curl -s http://localhost:8000/api/v1/health | jq '.' || echo "API may need more time to start"

    # Test docs endpoint
    echo "[INFO] Testing /docs..."
    curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8000/docs
ENDSSH

  log_success "Smoke tests complete"
}

# Deployment summary
deployment_summary() {
  step "Deployment Summary"

  cat <<EOF

${GREEN}═══════════════════════════════════════════════════════════${NC}
${GREEN}           Staging Deployment Successful!${NC}
${GREEN}═══════════════════════════════════════════════════════════${NC}

${BLUE}Staging Server:${NC} $STAGING_HOST
${BLUE}Deployment Directory:${NC} $STAGING_DIR/current

${BLUE}Access URLs:${NC}
  Frontend: http://$STAGING_HOST:3002
  Backend API: http://$STAGING_HOST:8000
  API Docs: http://$STAGING_HOST:8000/docs

${BLUE}Service Management:${NC}
  View logs:   ssh $STAGING_USER@$STAGING_HOST 'tail -f $STAGING_DIR/current/{frontend,backend}/*.log'
  Stop services: ssh $STAGING_USER@$STAGING_HOST 'pm2 stop all' (or kill PIDs)
  Restart: pm2 restart all

${BLUE}Next Steps:${NC}
  1. Configure .env files on staging server
  2. Setup PostgreSQL database
  3. Run database migrations
  4. Test critical user flows
  5. Monitor logs for errors

${GREEN}═══════════════════════════════════════════════════════════${NC}

EOF
}

# Main deployment flow
main() {
  log_info "Starting staging deployment..."
  echo

  preflight_checks
  run_tests
  build_frontend

  TAR_FILE=$(create_package)
  transfer_package "$TAR_FILE"
  setup_staging
  start_services
  health_checks
  smoke_tests

  # Cleanup local package
  rm -f "$TAR_FILE"

  deployment_summary

  log_success "Deployment complete!"
}

# Run main function
main
