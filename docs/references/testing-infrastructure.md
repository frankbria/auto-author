# Testing Infrastructure

## Overview
Testing runs in three layers: backend (pytest against a real MongoDB), frontend (Jest) and E2E (Playwright).

**Coverage gates** (enforced in CI and pre-commit; current numbers are in the CI run on `main`):
- Backend: 85% (`--cov-fail-under=85`)
- Frontend: 85% lines, 85% statements, 75% branches, 85% functions

## Test Helpers & Utilities

### 1. Condition-Based Waiting (`frontend/src/__tests__/helpers/conditionWaiting.ts`)

Replaces arbitrary timeouts with condition polling for reliable async testing.

**Usage**:
```typescript
import { waitForCondition } from '@/__tests__/helpers/conditionWaiting';

// Wait for element to appear
await waitForCondition(
  async () => await page.locator('[data-testid="save-status"]').isVisible(),
  {
    timeout: 5000,
    interval: 100,
    timeoutMessage: 'Save status indicator did not appear'
  }
);
```

**Benefits**:
- Tests complete faster (returns immediately when condition met)
- More reliable (no race conditions)
- Clearer error messages

### 2. Test Data Setup Helpers (`frontend/src/__tests__/helpers/testDataSetup.ts`)

Helpers meant to create E2E test data through the API instead of the UI.

**Usage**:
```typescript
import { testBookFactory } from '@/__tests__/helpers/testDataSetup';

// Create book with 3 chapters via API
const { book, chapters } = await testBookFactory.withChapters(token, 3);

// Navigate directly to chapter editor
await page.goto(`/dashboard/books/${book.id}/chapters/${chapters[0].id}`);

// Test the actual functionality without UI setup time
```

**Factory Patterns**:
- `testBookFactory.nonFiction(token, title?)` - Create non-fiction book
- `testBookFactory.fiction(token, title?)` - Create fiction book
- `testBookFactory.withChapters(token, count)` - Create book with N chapters

**Note**: `createTestBook`, `createTestChapter` and `deleteTestBook` are still placeholders that do not call the API (`frontend/src/__tests__/helpers/testDataSetup.ts`).

### 3. Retry helper (`frontend/src/lib/errors/errorHandler.ts`)

A second, simpler retry helper than the unified framework in [`docs/development/error-handling.md`](../development/error-handling.md); the question components use it.

**Features**:
- Error classification (NETWORK, VALIDATION, AUTH, SERVER, UNKNOWN)
- Automatic retry for transient errors (503, 429, network failures)
- Exponential backoff (1s, 2s, 4s, max 30s)
- Max retry limit (3 attempts, configurable)
- Toast notification integration
- TypeScript with full type safety

**Usage**:
```typescript
import { handleApiError } from '@/lib/errors';
import { useToast } from '@/components/ui/use-toast';

const { toast } = useToast();

// Automatic retry on transient errors
const books = await handleApiError(
  () => fetch('/api/books').then(r => r.json()),
  toast,
  { customMessage: 'Failed to load books' }
);
```

**Configuration**:
```typescript
import { ErrorHandler } from '@/lib/errors';

const handler = new ErrorHandler({
  maxRetries: 5,
  baseDelay: 2000,
  maxDelay: 60000
});
```

## E2E Test Suites

Specs live in `frontend/src/e2e/` and run with the bypass on (`BYPASS_AUTH=true`, with `E2E_ALLOW_BYPASS=1` set by Playwright's webServer).

### 1. Complete Authoring Journey (`frontend/src/e2e/complete-authoring-journey.spec.ts`)

One test that creates a book, generates a TOC, answers chapter questions and lands an AI draft in the editor. It uses condition-based waiting throughout.

### 2. Editing & Auto-save Flow (`frontend/src/e2e/editing-autosave-flow.spec.ts`)

Chapter editor auto-save (3-second debounce), localStorage backup on network failure, recovery, and save status indicators. Network failures are simulated with `page.route()`. Details: [`docs/testing/e2e-editing-autosave-flow.md`](../testing/e2e-editing-autosave-flow.md).

### 3. Error Recovery Flow (`frontend/src/e2e/error-recovery-flow.spec.ts`)

Retry with exponential backoff for transient errors, no retry for non-retryable ones, using API interception.

### 4. Real authentication, no bypass (`frontend/src/e2e/real-auth/`)

The suites above run with `BYPASS_AUTH`. This one does not (#843). It has its own
config, `frontend/playwright.real-auth.config.ts`, which starts a backend on port
8001 and a frontend on port 3001 with the bypass off and their own database, so it
can run next to the bypassed servers.

```bash
cd frontend && npx playwright test --config=playwright.real-auth.config.ts
```

- Needs MongoDB on `localhost:27017` and `uv`.
- New accounts must verify their email. No provider is configured, so the
  development server prints each email, and the spec reads the link from
  `test-results/real-auth-frontend.log`.
- Add auth flows that need a real server here (session revocation, password
  reset, 2FA), not to the bypassed suite.
- It runs in the required `E2E Tests (Playwright)` CI job;
  `scripts/test_real_auth_e2e_is_required.py` keeps it there.

## Test Organization

**Unit Tests**: `frontend/src/lib/**/*.test.ts`, `frontend/src/components/**/*.test.tsx`
**Integration Tests**: `frontend/src/__tests__/*.test.tsx`
**E2E Tests**: `frontend/src/e2e/*.spec.ts`; staging specs in `frontend/tests/e2e/staging/`
**Test Helpers**: `frontend/src/__tests__/helpers/`
**Test Documentation**: `docs/testing/`

## Running Tests

**Backend Tests**:
```bash
cd backend
uv run pytest --cov=app tests/ --cov-report=term-missing
```

**Frontend Unit/Integration Tests**:
```bash
cd frontend
npm test                    # Run all tests
npm run test:coverage       # With coverage report
npm test -- conditionWaiting.test  # Run specific test
```

**E2E Tests** (requires backend + frontend running):
```bash
cd frontend
npx playwright install      # One-time browser setup
npx playwright test         # Run all E2E tests
npx playwright test --ui    # Run with UI mode (recommended)
npx playwright test complete-authoring-journey  # Run specific test
```

## Quality Standards

All tests must meet:
- **100% Pass Rate**: No failing tests allowed
- **Meaningful Assertions**: Tests validate behavior, not just coverage
- **Condition-Based Waiting**: No arbitrary timeouts in E2E tests
- **Proper Cleanup**: All tests clean up resources
- **Documentation**: Complex tests include explanatory comments
- **Accessibility**: E2E tests verify WCAG 2.1 compliance where applicable

## Known Issues

- Backend tests that touch the database request the `motor_reinit_db` fixture (directly or via `auth_client_factory` / `async_client_factory`); without it they can hit a closed Motor client.

### Replica set

`delete_book` runs its cascade in a transaction when Mongo is a replica set, which Atlas is and a
developer's Mongo usually is not. The two tests for that branch
(`tests/test_db/test_cascade_delete_atomic.py`) skip on a standalone server. CI runs them in the
Backend Tests job's "Cascade delete on a single-node replica set" step (#839). To run them locally:

```bash
docker run -d --name mongo-rs --ulimit nofile=64000:64000 -p 27018:27018 mongo:7 --replSet rs0 --port 27018 --bind_ip_all
docker exec mongo-rs mongosh --quiet --port 27018 --eval 'rs.initiate({_id: "rs0", members: [{_id: 0, host: "localhost:27018"}]})'
cd backend && REQUIRE_REPLICA_SET=1 TEST_MONGO_URI='mongodb://localhost:27018/auto-author-test?replicaSet=rs0' \
  uv run pytest tests/test_db/test_cascade_delete_atomic.py --no-cov -v
docker rm -f mongo-rs
```

The member's host must be the address the tests connect to, port included: a client that asks for
`replicaSet=rs0` reconnects to whatever the server says its members are. `REQUIRE_REPLICA_SET` turns
the skip into a failure, so a run that was meant to have a replica set cannot pass without one.
