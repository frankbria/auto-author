#!/bin/bash
# Rollback to previous deployment
# Usage: ./rollback.sh <environment>

set -euo pipefail

ENVIRONMENT=$1
DEPLOY_BASE="/opt/auto-author"
CURRENT_DIR="$DEPLOY_BASE/current"

# Find previous release
PREVIOUS_RELEASE=$(ls -t "$DEPLOY_BASE/releases" | sed -n 2p)

if [ -z "$PREVIOUS_RELEASE" ]; then
  echo "ERROR: No previous release found"
  exit 1
fi

echo "==> Rolling back to: $PREVIOUS_RELEASE"

# Update symlink
ln -snf "$DEPLOY_BASE/releases/$PREVIOUS_RELEASE" "$CURRENT_DIR.tmp"
mv -Tf "$CURRENT_DIR.tmp" "$CURRENT_DIR"

# Restart services
pm2 restart auto-author-backend
pm2 restart auto-author-frontend

echo "==> Rollback complete!"
echo "    Previous release: $PREVIOUS_RELEASE"
echo "    Environment: $ENVIRONMENT"
