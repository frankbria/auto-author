#!/bin/bash
set -e

# Rollback script for Auto-Author staging environment
# This script rolls back to the previous release by updating the symlink

RELEASES_DIR="/opt/auto-author/releases"
CURRENT_LINK="/opt/auto-author/current"

# Get previous release (second most recent)
PREVIOUS=$(ls -t $RELEASES_DIR | sed -n '2p')

if [ -z "$PREVIOUS" ]; then
  echo "❌ No previous release found"
  exit 1
fi

echo "🔄 Rolling back to: $PREVIOUS"
ln -sfn $RELEASES_DIR/$PREVIOUS $CURRENT_LINK

echo "♻️  Restarting services..."
pm2 restart all

echo "🏥 Running health checks..."
sleep 5

# Backend health check
if ! curl -f https://api.dev.autoauthor.app/api/v1/health; then
  echo "❌ Backend health check failed"
  exit 1
fi

# Frontend health check
if ! curl -f https://dev.autoauthor.app; then
  echo "❌ Frontend health check failed"
  exit 1
fi

echo "✅ Rollback complete"
echo "📦 Rolled back to: $PREVIOUS"
