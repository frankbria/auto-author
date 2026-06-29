#!/bin/bash
# Quick runner for Issue #54 verification test

set -e

echo "=== Issue #54 Verification Test Runner ==="
echo ""

# Check if we're testing local or staging
if [ "$1" = "staging" ]; then
  echo "Testing against STAGING (requires auth)"
  echo "URL: https://dev.autoauthor.app"
  export BASE_URL=https://dev.autoauthor.app
  export NEXT_PUBLIC_API_URL=https://api.dev.autoauthor.app/api/v1
  export BYPASS_AUTH=false
else
  echo "Testing LOCALLY (with BYPASS_AUTH)"
  echo "URL: http://localhost:3000"
  export BASE_URL=http://localhost:3000
  export NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
  export BYPASS_AUTH=true
  export NEXT_PUBLIC_BYPASS_AUTH=true

  echo ""
  echo "⚠️  Make sure local services are running:"
  echo "  Terminal 1: cd backend && uv run uvicorn app.main:app --reload"
  echo "  Terminal 2: cd frontend && npm run dev"
  echo ""
  read -p "Press Enter when services are ready..."
fi

echo ""
echo "Running Playwright test..."
echo ""

# Run the test
npx playwright test src/e2e/staging-issue-54-verification.spec.ts \
  --project=chromium \
  --headed \
  --reporter=list

echo ""
echo "=== Test Complete ==="
