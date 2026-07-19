# Contributing to Auto-Author

Thanks for your interest in contributing! Auto-Author is in an early MVP phase,
and contributions, suggestions, and pull requests are welcome.

This guide covers how to get set up and the standards a change is expected to
meet before it can be merged.

## Project layout

- `frontend/` — Next.js app (TypeScript, Tailwind, Jest, Playwright)
- `backend/` — FastAPI app (Python, `uv`, pytest)
- `docs/` — project documentation

## Getting set up

### Backend (FastAPI + uv)

```bash
cd backend
uv sync --extra test          # installs runtime + test dependencies
uv run pytest --cov=app tests/ --cov-report=term-missing
```

### Frontend (Next.js + npm)

```bash
cd frontend
npm install
npm run dev                   # local dev server
npm test                      # unit tests
npx playwright test           # E2E tests
```

## Development workflow

1. **Branch from `main`.** Never commit directly to `main`. Use a descriptive
   branch name, e.g. `feature/short-description` or `fix/short-description`.
2. **Write tests first (TDD).** New code needs unit tests; user-facing features
   need an E2E test.
3. **Keep the quality gates green.** Before opening a PR:
   ```bash
   # Frontend
   cd frontend && npm run lint && npm run typecheck && npm test
   # Backend
   cd backend && uv run ruff check && uv run pytest tests/
   ```
4. **Update documentation** affected by your change.
5. **Open a pull request to `main`** with a clear description of what changed
   and why. Address review feedback before merge.

## Quality standards

- **Test coverage ≥ 85%** — enforced in CI for both frontend and backend. A PR
  that drops coverage below the threshold will fail its checks.
- **All tests pass** — 100% pass rate; no skipped tests standing in for real
  coverage.
- **Linting and type checking clean** — `ruff` (backend), `eslint` +
  `tsc --noEmit` (frontend).
- **No secrets in commits** — pre-commit hooks scan for private keys and
  credentials.

## Pre-commit hooks

The repo uses pre-commit hooks that run linting, tests, and coverage checks on
every commit. Install them once:

```bash
pip install pre-commit
pre-commit install
```

Bypassing hooks (`git commit --no-verify`) is reserved for genuine emergencies,
not routine work — `main` is branch-protected and requires the CI checks to pass
before merge regardless.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add EPUB export format
fix: prevent lost-update clobber on concurrent chapter saves
docs: add LICENSE and CONTRIBUTING guide
test: cover the batch response-save validation path
```

## Reporting issues

Open a GitHub issue describing the problem or suggestion. For bugs, include
steps to reproduce, expected vs. actual behavior, and relevant environment
details.

## License

By contributing, you agree that your contributions will be licensed under the
[MIT License](LICENSE) that covers this project.
