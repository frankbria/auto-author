#!/usr/bin/env bash
# Repo-wide verification gate. Runs backend + frontend unit suites.
# E2E (Playwright) is intentionally excluded — too slow for the default gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== Backend tests =="
(cd "$ROOT/backend" && uv run pytest tests/)

echo "== Frontend tests =="
(cd "$ROOT/frontend" && npm test -- --watchAll=false)

echo "== All suites completed =="
