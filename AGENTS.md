# AGENTS.md

Auto Author is an AI-assisted long-form non-fiction writing app: a Next.js frontend (`frontend/`) and a FastAPI backend (`backend/`, managed with `uv`) over MongoDB, in one monorepo. [`CLAUDE.md`](CLAUDE.md) is the canonical project guide for any coding agent, whatever the tool: it covers the quality gates, deployment, environment variables and conventions. Docs are indexed in [`docs/README.md`](docs/README.md).

## Commands

Root `package.json` has only `npm test` (runs `scripts/test-all.sh`). Everything else runs inside `frontend/` or `backend/`.

```bash
# Frontend
cd frontend && npm run lint && npm run typecheck && npm test
npm run test:coverage

# Backend: test tooling lives in the `test` extra to keep prod installs lean
cd backend && uv sync --extra test         # one-time
uv run pytest --cov=app tests/ --cov-report=term-missing

# E2E
cd frontend && npx playwright test --ui
BYPASS_AUTH=true npx playwright test       # Playwright's webServer sets E2E_ALLOW_BYPASS=1
npx playwright test --config=playwright.real-auth.config.ts   # real auth, no bypass; starts its own servers on 3001/8001
```

Backend lint is `uv run --extra test ruff check app/ tests/`. No formatter is enforced, so do not reformat files you are not changing.

## Rules

- Keep files under 500 lines.
- Do not hardcode URLs. Read them from `.env` or `.env.local`.
- When you change an `.env` variable, change the matching `.env.example` (`frontend/` or `backend/`) too. Never put a secret in `.env.example`; use a placeholder value.
- Never hardcode secrets.
