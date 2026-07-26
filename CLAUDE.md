# Auto Author

AI-assisted long-form non-fiction writing. Next.js frontend + FastAPI backend, MongoDB.

- `frontend/` — Next.js app
- `backend/` — FastAPI app (uv-managed)
- `docs/` — project docs; `docs/references/` = on-demand deep dives (table below)
- `claudedocs/` — analysis reports and detailed plans
- `archive/` — historical planning docs (read-only)

Detailed per-issue changelog: [`docs/CHANGELOG.md`](docs/CHANGELOG.md). Append new entries **there**, not here.

**Latest state (2026-07-24):** P0/P1 launch-review items through #336 complete (ToS/Privacy pages, Sentry, real `/health` dependency checks, loud password-reset failure, chapter-question status filter before pagination). CI gates green and enforced.

---

## Reference docs — read on demand

| When | File |
|------|------|
| Creating/checking tasks (bd is the source of truth) | `docs/references/beads-workflow.md` |
| Creating or reorganizing documentation | `docs/references/documentation-management.md` |
| Using LoadingStateManager, ProgressIndicator, DeleteBookModal | `docs/references/component-documentation.md` |
| Completing a feature / opening a PR | `docs/references/quality-standards.md` |
| Perf-sensitive work (TOC 3000ms, Export 5000ms budgets) | `docs/references/performance-monitoring.md` |
| Writing or fixing tests | `docs/references/testing-infrastructure.md` |
| Current test status | `docs/POST_DEPLOYMENT_TEST_REPORT.md`, `backend/TEST_COVERAGE_REPORT.md`, `frontend/docs/TEST_FAILURE_ANALYSIS.md` |

---

## Commands

Root `package.json` has only `npm test` (→ `scripts/test-all.sh`). Everything else runs inside `frontend/` or `backend/`.

```bash
# Tasks
bd ready                                   # unblocked work
bd close <id> --reason "Completed in PR #123"

# Frontend
cd frontend && npm run lint && npm run typecheck && npm test
npm run test:coverage

# Backend — test tooling lives in the `test` extra to keep prod installs lean
cd backend && uv sync --extra test         # one-time
uv run pytest --cov=app tests/ --cov-report=term-missing

# E2E
cd frontend && npx playwright test --ui
BYPASS_AUTH=true npx playwright test       # Playwright's webServer sets E2E_ALLOW_BYPASS=1
```

### Staging E2E (real auth against https://dev.autoauthor.app)

```bash
cd frontend
cp tests/e2e/staging/.env.test.example tests/e2e/staging/.env.test   # set STAGING_TEST_EMAIL / STAGING_TEST_PASSWORD
npm run test:e2e:staging
```

Specs: `tests/e2e/staging/complete-user-journey.spec.ts`, `regressions.spec.ts` (#83 session/401, ObjectId, #54 answer persistence). CI: `.github/workflows/e2e-staging-tests.yml` — 6h schedule, manual dispatch, or PRs labeled `e2e-staging`; needs GitHub Secrets `TEST_USER_EMAIL` / `TEST_USER_PASSWORD`. See `tests/e2e/staging/README.md`.

---

## Quality gates

Standards, checklists, and E2E requirements: **`docs/references/quality-standards.md`**. The repo-specific facts:

- **CI is the real gate.** `main` branch protection requires the `Frontend Tests` and `Backend Tests` checks (coverage included) to pass. Merge via PR — no `--admin`, no `--no-verify`. Gates have been green at baseline and enforced since #118.
- **The installed `.git/hooks/pre-commit` is the bd flush hook — it runs no quality gates.** `.pre-commit-config.yaml` defines lint/test/coverage/E2E hooks, but they only run if you invoke them:
  ```bash
  pre-commit install                              # wire them into git (optional, slow commits)
  pre-commit run --from-ref HEAD~1 --to-ref HEAD  # check just your commits before a PR
  ```
  Watch for a stale `.git/hooks/pre-commit.legacy` shadowing behavior.
- Coverage floor is 85% (frontend thresholds 85/85/75/85 lines/statements/branches/functions).
- Never commit to `main` directly — `feature/<name>`, PR, conventional commits.

---

## Code style

Files under 500 lines. Never hardcode secrets. Tests before implementation. WCAG 2.1 AA for user-facing UI.

---

## Deployment

- Staging: https://dev.autoauthor.app (frontend), https://api.dev.autoauthor.app (backend). SSH as `root`, keys are local.
- **Shared box — other apps run here.** Backend is on 8000, frontend on 3002, but check nginx for current truth before assuming a port is free.
- PM2-managed with a symlinked `current` release dir; when things look out of sync, check that the symlink points where you think it does.
- Deployment scripts live in the git workflow directories.

---

## Environment

- Python: `uv`. Node: `npm`.
- `BYPASS_AUTH=true` only takes effect alongside `E2E_ALLOW_BYPASS=1` in **every** environment (frontend middleware #272, backend FastAPI #307). Backend production is hard-blocked regardless. Never use in production.
- Otherwise standard Next.js / FastAPI vars — see `.env.example`.
- `CURRENT_SPRINT.md` and `IMPLEMENTATION_PLAN.md` are auto-generated bd snapshots; edit bd, not the markdown.

---

## API

Auth: better-auth JWT, HS256 shared secret. Session list/revoke via better-auth native APIs (Settings → Security).

Core endpoints: `/api/v1/books`, `/api/v1/chapters`, `/api/v1/toc`, `/api/v1/export`. Full reference in the backend OpenAPI docs.

Shipped features (for orientation): book CRUD + type-to-confirm deletion, AI TOC wizard, chapter tabs, TipTap editor, AI draft generation, auto-save (3s debounce + localStorage fallback), voice input, PDF/DOCX export, performance monitoring, unified error handling with retry.
