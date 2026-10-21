# Testing Setup Guide

This guide walks you through setting up the complete testing environment for the Auto-Author application.

## Prerequisites

### System Requirements
- Node.js 24+ (for frontend)
- Python 3.13+ and [uv](https://docs.astral.sh/uv/) (for backend)
- MongoDB on `localhost:27017` (backend tests use a real database)
- Git

### Environment Setup

Clone the repository (`git clone https://github.com/frankbria/auto-author.git`), then install the frontend and backend dependencies as below. The root `package.json` has only the `npm test` script; there is nothing to install at the root.

## Frontend Testing Setup

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Configuration

Jest is configured in `frontend/jest.config.cjs` (built on `next/jest`, jsdom environment, setup in `frontend/src/jest.setup.ts`). It sets no coverage threshold; the 85/85/75/85 (lines/statements/branches/functions) gate is passed on the command line by CI (`.github/workflows/tests.yml`) and the `frontend-coverage` pre-commit hook:
```bash
cd frontend
npm test -- --coverage --coverageThreshold='{"global":{"lines":85,"statements":85,"branches":75,"functions":85}}'
```

### 3. Test Scripts
`frontend/package.json` defines `test`, `test:watch`, `test:coverage`, `test:e2e`, `test:e2e:ui`, `test:e2e:debug` and the `test:e2e:staging*` scripts.

## Backend Testing Setup

### 1. Install Dependencies
```bash
cd backend
uv sync --extra test    # creates .venv; test tooling (pytest, pytest-asyncio, pytest-cov, ruff, ...) is in the `test` extra
```

### 2. Configuration Files

- `backend/pytest.ini`: `testpaths = tests`, `asyncio_mode = auto`, markers `integration` and `unit`.
- `backend/.coveragerc`: measures `app`, omits tests.
- The 85% coverage floor is passed on the command line (`--cov=app --cov-fail-under=85`) by CI and the `backend-coverage` pre-commit hook.

### 3. Test Database

Tests use a real MongoDB, not SQLite or SQLAlchemy. Start MongoDB on `localhost:27017`; `backend/tests/conftest.py` does the rest:
- It sets `ENVIRONMENT=test`.
- It connects to `TEST_MONGO_URI` (default `mongodb://localhost:27017/auto-author-test`).
- The `motor_reinit_db` fixture drops that database before and after the test and points the data-access modules at a fresh Motor client. Tests that touch the database request it, directly or through `auth_client_factory` / `async_client_factory`.
- `backend/tests/db_guard.py` aborts collection if the URI is not a local test database.

No `.env.test` file is used.

## IDE Integration

### VS Code Extensions
Install these recommended extensions:
- Jest Runner
- Python Test Explorer
- Coverage Gutters
- Test Adapter Converter

### IntelliJ/PyCharm
1. Configure Python interpreter to use virtual environment
2. Set test runner to pytest
3. Enable coverage integration

## Mock Services Setup

Recorded AI provider outputs used by backend tests live in `backend/tests/fixtures/ai_provider_outputs/`. Frontend mocks are in `frontend/src/__mocks__/` and per-test `jest.mock` calls.

## Running Tests

### Whole repo
```bash
# Backend and frontend unit suites (the repo-wide gate; E2E is excluded)
npm test
```

### Frontend
```bash
cd frontend

# All tests
npm test

# Specific test files
npm test ChapterQuestions
npm test -- --testNamePattern="should handle question generation"

# Coverage
npm run test:coverage

# Watch mode
npm run test:watch
```

### Backend
```bash
cd backend

# All tests
uv run pytest

# Specific test files
uv run pytest tests/test_api/test_partial_patch.py

# With coverage
uv run pytest --cov

# Verbose output
uv run pytest -v

# Fast fail
uv run pytest -x

# Integration tests only
uv run pytest tests/integration/ -v
```

### End-to-end (Playwright)
```bash
cd frontend
npx playwright install            # one-time browser download

npm run test:e2e                  # all specs
npm run test:e2e:ui               # interactive UI mode
npm run test:e2e:debug            # step through with the inspector
```

Run against staging with real auth (`npm run test:e2e:staging`) and the no-bypass local config: see [CLAUDE.md](../../CLAUDE.md) (Commands) and `frontend/tests/e2e/staging/README.md`.

### Staging load smoke
CI runs this after each staging deploy, with the staging test account in `STAGING_TEST_EMAIL` and `STAGING_TEST_PASSWORD` (see `.github/workflows/e2e-staging-tests.yml`).
```bash
cd backend
uv sync --extra load
uv run locust -f tests/load/staging_smoke.py StagingSmokeUser --headless --host=https://dev.autoauthor.app
```

## Troubleshooting

### Common Issues

#### Frontend
1. **Module resolution issues**
   - Check `jest.config.cjs` `moduleNameMapper`
   - Verify tsconfig.json paths

2. **Jest environment issues**
   - Ensure `jest-environment-jsdom` is installed
   - Check Jest configuration

#### Backend
1. **Database connection issues**
   - Check that MongoDB is running on `localhost:27017` (or that `TEST_MONGO_URI` points at a local test database)

2. **Import path issues**
   - Run pytest from `backend/` (`pytest.ini` sets `pythonpath = .`)

### Performance Issues
- Use `--maxWorkers=50%` for Jest on limited resources

## Next Steps

1. Run initial test suite to verify setup
2. Review [Best Practices](./best-practices.md)
