# Claude Code Configuration - SPARC Development Environment

## 🚨 CRITICAL: CONCURRENT EXECUTION & FILE MANAGEMENT

**ABSOLUTE RULES**:
1. ALL operations MUST be concurrent/parallel in a single message
2. **NEVER save working files, text/mds and tests to the root folder**
3. ALWAYS organize files in appropriate subdirectories

### ⚡ GOLDEN RULE: "1 MESSAGE = ALL RELATED OPERATIONS"

**MANDATORY PATTERNS:**
- **TodoWrite**: ALWAYS batch ALL todos in ONE call (5-10+ todos minimum)
- **Task tool**: ALWAYS spawn ALL agents in ONE message with full instructions
- **File operations**: ALWAYS batch ALL reads/writes/edits in ONE message
- **Bash commands**: ALWAYS batch ALL terminal operations in ONE message
- **Memory operations**: ALWAYS batch ALL memory store/retrieve in ONE message

### 📁 File Organization Rules

**NEVER save to root folder. Use these directories:**
- `/src` - Source code files
- `/tests` - Test files
- `/docs` - Documentation and markdown files
- `/config` - Configuration files
- `/scripts` - Utility scripts
- `/examples` - Example code

---

## Recent Changes

### 2026-06-25
- **Flaky test fix + frontend coverage to 85% (#68)**: tests-mostly
  - **Flaky `TabStatePersistence`**: the "saves tab state…" case raced the 1s debounced auto-save under real timers. Now uses `jest.useFakeTimers()` + `advanceTimersByTime(1000)` and an `afterEach(jest.useRealTimers())` so it's deterministic and can't leak timer state into the full run.
  - **Coverage**: global was stmt 74 / lines 75 / func 67 / branch 62 → now **stmt 92 / lines 93 / func 90 / branch 83**, clearing the pre-commit gate (85/85/75) without `--no-verify`. ~700 unit tests added across `lib/errors/*`, `lib/api/bookClient.ts`, `lib/security.ts`, `lib/performance/*`, `lib/loading/timeEstimator.ts`, `lib/utils/toc-to-tabs-converter.ts`, `lib/toast.ts`, hooks (`useTocSync`, `usePerformanceTracking`), and components (`ErrorNotification`, `QuestionDisplay/Container/Navigation/Generator`, `ClarifyingQuestions`, `ChapterTabs`/`MobileChapterTabs`/`TabBar`/`TabContextMenu`/`TabOverflowMenu`, `ui/dropdown-menu`, `ui/sheet`).
  - **Real bugs fixed while testing**: `sanitizeFileName` regex `[^a-zA-Z0-9.-_]` was a char *range* (46–95) so `/ : \ @` slipped through while `-` was stripped — hyphen now escaped (path-traversal hardening); `showRecoveryNotification` printed "2 attempt" (singular) — fixed to plural; removed a dead empty `useEffect`/`getToken` + orphaned `useSession` in `ClarifyingQuestions.tsx`.
  - **Status**: ✅ Complete

- **Transcription test coverage + dead-code removal (#93)**: tests-only plan 009
  - **transcription.py**: 40% → 85% via new `backend/tests/test_api/test_transcription.py` (POST /transcribe auth/413/400/happy/service-error; GET /status; POST /validate). Router isn't mounted on the app, so tests mount it on a bare FastAPI app + override auth; transcription service patched (no AWS/audio)
  - **Drift**: `app/api/endpoints/book_cover_upload.py` was dead code (never imported) — an unmounted duplicate of the live cover endpoint in `books.py`. Removed it (same pattern as #92's `book_cascade_delete.py`); added a wrong-owner (404) case to the existing `test_book_cover_upload.py` which already exercises the live `books.py` path
  - **Status**: ✅ Complete (PR #131)

- **Writing style transformation (#58)**: New feature — rewrite existing chapter text into a chosen style (distinct from draft-from-Q&A)
  - **Backend**: `app/services/style_templates.py` (5 documented styles with distinct tone/vocab/structure guidance + `get_style_transformation_prompt`); `ai_service.transform_text_style(content, target_style)` (temp 0.7, preserves facts); new endpoint `POST /books/{id}/chapters/{cid}/transform-style` (auth + ownership + rate limit, **preview-only, no persistence**)
  - **Frontend**: `StyleTransformer.tsx` dialog (pick style → before/after preview → apply); wired into `ChapterEditor` toolbar with a **client-side snapshot revert** ("Revert style" button) — single-level undo, no backend version storage; `bookClient.transformChapterStyle`
  - **Tests**: backend `test_style_templates` + `test_ai_service_style_transformation` + `test_style_transformation` (15 tests: distinct prompts per style, validation, auth, AI-failure→503); frontend `StyleTransformer.test.tsx`; deterministic route-mocked E2E `frontend/src/e2e/style-transformation.spec.ts` (transform → preview → apply → revert)
  - **Note**: the stale deployment spec `tests/e2e/deployment/06-draft-writing-styles.spec.ts` still references the old 6 draft styles (real-auth suite) — not rewritten here
  - **Status**: ✅ Complete

- **AI Draft Generation alignment (#55)**: Feature was already ~95% built; closed the real gaps the stale issue/bot plans missed
  - **Writing styles**: both `DraftGenerator.tsx` and `DraftGenerationButton.tsx` now ship the 5 documented styles (Professional, Conversational, Academic, Creative, Technical) matching the user manual + AC, replacing the prior mismatched 6. Backend is style-agnostic (free-text into the prompt) → no backend change
  - **Bug fix**: `DraftGenerator.tsx` loading state was unreachable (ternary checked `!generatedDraft` before `isGenerating`, so the form always rendered during generation); reordered so the loading view shows. `DraftGenerationButton.tsx` already had a correct step machine
  - **A11y**: associated the style/length selects and the per-question input with labels in `DraftGenerator.tsx`
  - **Tests**: added a regression test asserting the loading state renders during generation; new deterministic route-mocked E2E `frontend/src/e2e/draft-generation.spec.ts` (open → pick style → generate → preview → insert into editor)
  - **Status**: ✅ Complete

### 2026-06-24
- **Error/Success Feedback Unification (#46)**: Closed user-facing feedback gaps and standardized the notification path
  - **Duplicate Toaster**: `layout.tsx` mounted two sonner Toasters → duplicate toasts; removed the redundant one, kept theme-aware `SonnerToaster`
  - **new-book silent failure**: create errors only `console.error`'d; now classified and shown via `showErrorNotification` with a retry action, plus a success toast on create
  - **ChapterTabs retry**: load-error "Retry" did a full `window.location.reload()`; now calls `refreshChapters()` (data refresh, no page reload)
  - **Standardization**: all toasts route through the single `@/lib/toast` wrapper (added a `variant` compat shim); migrated 5 direct-`sonner` + 6 `useToast` call sites by import swap
  - **Tests**: `NewBookPage.test.tsx` (success toast + redirect / error notification + no redirect), `ChapterTabs.test.tsx` (retry refreshes, no reload); migration mocks updated
  - **Status**: ✅ Complete (PR #115)

### 2026-06-22
- **TOC Generation Hardening (#48)**: Closed reliability gaps in the AI TOC flow
  - **analyze-summary endpoint**: now uses the same structured AI-error handling as generate-questions/generate-toc (timeouts → 503 with retry info, instead of an opaque 500)
  - **Frontend**: `bookClient` AI methods surface the backend's `detail.message`, and `TocGenerationWizard` shows it (meaningful error text + existing retry button) rather than a generic string
  - **Malformed AI responses**: `ai_service._parse_toc_response` now rejects unusable output (empty/title-less chapters, unparseable text) with a retryable `AI_INVALID_RESPONSE` error instead of silently fabricating a generic placeholder TOC; it also unwraps the common `table_of_contents` JSON wrapper so valid-but-wrapped responses parse correctly
  - **Tests**: backend integration tests for AI timeouts/invalid responses across all 3 TOC endpoints; `bookClient` error-surfacing unit tests; deterministic route-mocked E2E (`frontend/src/e2e/toc-generation-resilience.spec.ts`) for the error→retry recovery path
  - **Status**: ✅ Complete

### 2025-12-24
- **Cookie-Based Authentication Reconciliation**: Aligned backend auth with better-auth's cookie-based session management
  - **Problem**: Backend expected JWT tokens in Authorization headers, but better-auth uses httpOnly session cookies
  - **Solution**: Created new session validation module to read and validate better-auth session cookies
  - **Changes**:
    - New module: `backend/app/core/better_auth_session.py` for session cookie validation
    - New dependency: `get_current_user_from_session()` replaces JWT-based authentication
    - New role checker: `SessionRoleChecker` for cookie-based authorization
    - Updated all 25+ protected endpoints to use session-based auth
    - Frontend: Removed Bearer token logic, uses `credentials: 'include'` for cookies
  - **Files Modified**:
    - `backend/app/core/security.py` - Added session-based auth functions
    - `backend/app/core/better_auth_session.py` - New session validator
    - `backend/app/api/endpoints/*.py` - Updated all endpoints
    - `frontend/src/hooks/useAuthFetch.ts` - Cookie-based fetch
    - `frontend/src/lib/api/bookClient.ts` - Deprecated token methods
  - **Test Updates**: All test fixtures updated to mock session-based auth
  - **Documentation**: Updated migration guide with cookie-based auth section
  - **Status**: ✅ Complete - Backend now validates session cookies from better-auth

### 2025-12-17
- **Better-Auth Migration**: Complete migration from Clerk to better-auth authentication
  - **Scope**: 70+ files across frontend (Next.js) and backend (FastAPI)
  - **Changes**:
    - JWT algorithm: RS256 (Clerk) → HS256 (better-auth)
    - User ID field: `clerk_id` → `auth_id`
    - Frontend: Removed `@clerk/nextjs`, added `better-auth` with MongoDB adapter
    - Backend: Removed Clerk JWKS verification, added HS256 JWT validation
    - Environment: Simplified to `BETTER_AUTH_SECRET` and `BETTER_AUTH_URL`
  - **Security Fixes**:
    - **BLOCKER**: Removed hardcoded JWT secret, added strong validation (min 32 chars)
    - **HIGH**: Changed `NEXT_PUBLIC_BYPASS_AUTH` to server-only `BYPASS_AUTH` with production safety check
    - **HIGH**: Disabled auto-user creation from JWT - require explicit registration
  - **Test Results**: 231/251 backend tests passing (92%), all security tests updated for better-auth
  - **Cleanup**: Removed Clerk documentation, test files, and CSP headers
  - **Status**: ✅ Migration complete with all security vulnerabilities fixed

### 2025-11-22
- **Auto-Create Users from Clerk on First Login**: Enhanced authentication to automatically create user records
  - **Problem**: Users authenticating via Clerk weren't being created in backend database
  - **Solution**: Modified `security.py` to auto-create users from Clerk JWT on first login
  - **Changes**: Enhanced `get_current_user()` to create missing users, added comprehensive logging
  - **Impact**: Seamless user onboarding without manual database setup
  - **Status**: ✅ Deployed to staging - authentication now fully automated

- **Staging Deployment Workflow**: GitHub Actions workflow for automated staging deployments
  - **Achievement**: Complete CI/CD pipeline for staging environment
  - **Infrastructure**: SSH deployment, PM2 process management, health checks with retries
  - **Configuration**: Backend on port 8000, frontend on port 3003, CORS validation
  - **Process**: Uses `pm2 delete` + `pm2 start` instead of restart for clean release pickup
  - **Status**: ✅ Operational at https://dev.autoauthor.app (frontend) and https://api.dev.autoauthor.app (backend)

- **Public Access to Landing Page**: Fixed middleware to allow unauthenticated access to root
  - **Problem**: Root landing page was requiring authentication
  - **Solution**: Updated middleware.ts to explicitly allow public access to `/`
  - **Impact**: Marketing/landing page now accessible without login
  - **Status**: ✅ Deployed to staging

### 2025-11-07
- **E2E Test Suite Complete**: Comprehensive automated testing with 85%+ coverage
  - **Achievement**: Created comprehensive deployment test suite (01-05) with 54+ tests
  - **Infrastructure**: Fixtures (auth, test-data, performance), Helpers (console/network/CSP monitors), Page Objects (7 pages)
  - **Coverage**: Pre-flight (7 tests), User Journey (8 tests), Advanced Features (8 tests), Security/Performance (12 tests), Regression (19+ tests)
  - **Performance Budgets**: All operations validated (TOC <3000ms, Export <5000ms, Auto-save <1000ms, Page Nav <500ms)
  - **Status**: ✅ auto-author-59 completed - 85%+ automation coverage achieved, ready for CI/CD

- **MongoDB Atlas SSL Connection Fix**: Resolved test database connection issues
  - **Problem**: 13 tests failing with SSL handshake errors connecting to MongoDB Atlas
  - **Solution**: Updated test infrastructure to use local MongoDB for all tests
  - **Changes**: Added sessions_collection to conftest fixture, updated session.py to use base.sessions_collection
  - **Impact**: 9/15 session service tests now passing (was 3/15), all SSL errors eliminated
  - **Status**: ✅ auto-author-70 completed - tests now use local MongoDB correctly

- **Frontend Test Suite Status**: All environmental test issues resolved
  - **Test Results**: 732/735 tests passing (99.6% pass rate, 3 skipped)
  - **Test Suites**: 51/51 passing (100%)
  - **Resolution**: Mocks already in place (Next.js router, ResizeObserver, TipTap, Clerk)
  - **Excluded Tests**: ProfilePage.test.tsx, SystemIntegration.test.tsx (awaiting feature implementation)
  - **errorHandler.test.ts**: All 43 tests passing with Jest
  - **Status**: ✅ auto-author-60 completed - no fixes needed, infrastructure working correctly

### 2025-11-06
- **TOC JWT Bug Fix**: Fixed JWT token expiration during long TOC workflows (11+ seconds) by implementing token provider pattern in BookClient
- **E2E Tests Enabled**: Complete authoring journey E2E test now active in `frontend/src/e2e/complete-authoring-journey.spec.ts`
- **TDD Enforcement**: Pre-commit hooks now enforce unit tests, E2E tests, and ≥85% coverage for all commits
- **GitHub Actions**: Implemented automated test workflow for frontend, backend, and E2E tests
- **Documentation Automation**: Pre-commit hooks auto-sync CURRENT_SPRINT.md and IMPLEMENTATION_PLAN.md from bd tracker (local only - .beads/ is gitignored)

### 2025-11-01
- **Session Management (NEW)**
- **Session Tracking**: Automatic session creation and activity monitoring
- **Security Features**: Session fingerprinting, suspicious activity detection, concurrent session limits
- **Session Timeouts**: 30-minute idle timeout, 12-hour absolute timeout
- **Frontend Integration**: `useSession` hook with auto-refresh and warning notifications
- **API Endpoints**: Complete session management API (`/api/v1/sessions/*`)
- **Comprehensive Tests**: 85%+ test coverage for session management

### Security & Authentication (2025-10-29)
- **JWT Verification Fix**: Switched from hardcoded public key to Clerk JWKS endpoint (`https://clerk.{domain}/.well-known/jwks.json`)
- **Auth Bypass Mode**: Added `BYPASS_AUTH=true` environment variable for E2E testing
- **Security Audit**: Comprehensive authentication middleware review completed

### Testing Infrastructure
- **E2E Test Suite**: Complete Playwright tests with auth bypass support
- **Test Data Helpers**: Comprehensive fixtures for books, chapters, and TOC data
- **Condition-based Waiting**: Replaced arbitrary timeouts with state polling
- **Page Objects**: Full coverage (auth, dashboard, books, summary, TOC wizard, chapter editor, export)

### Test Analysis Reports
- `docs/POST_DEPLOYMENT_TEST_REPORT.md`: Comprehensive test status after staging deployment
  - Frontend: 99.6% pass rate (732/735 tests passing, 3 skipped)
  - Backend: 98.9% pass rate (2 asyncio failures), 41% coverage vs 85% target
- `backend/TEST_COVERAGE_REPORT.md`: Module-by-module coverage analysis with 4-week improvement plan
- `frontend/docs/TEST_FAILURE_ANALYSIS.md`: Categorized frontend failures with fix priorities

### Known Issues
- **Backend Coverage**: 41% vs 85% target
  - Critical gaps: `security.py` (18%). (`transcription.py` now 85% via #93; the dead `book_cover_upload.py` duplicate was removed — live cover endpoint lives in `books.py`.)
  - Path to 85%: 4-5 weeks, 207-252 new tests
- **Backend Asyncio**: 2 test failures related to event loop lifecycle
- **Backend Module Structure**: Missing `__init__.py` in `app/api/middleware/` causing import errors

### Package Updates
- Upgraded `lucide-react` to 0.468.0
- Resolved 5 npm audit vulnerabilities
- Updated `.gitignore` to exclude test artifacts

---

## Project Structure
- `frontend/` - Next.js application
- `backend/` - FastAPI Python application
- `docs/` - Project documentation
  - `POST_DEPLOYMENT_TEST_REPORT.md` - Comprehensive test analysis
  - `references/` - On-demand reference documentation (read when needed)
- `backend/TEST_COVERAGE_REPORT.md` - Backend coverage details
- `frontend/docs/TEST_FAILURE_ANALYSIS.md` - Frontend test categorization
- `claudedocs/` - Claude-specific analysis reports and detailed plans
- `archive/` - Historical planning documents (read-only)

---

## 📚 On-Demand Reference Documentation

For detailed information on specific topics, **read these files when needed** using the Read tool:

### Task Management
**File**: `docs/references/beads-workflow.md`
**When to read**: Before creating tasks, checking task status, or planning work
**Summary**: bd (Beads) is the single source of truth for all task tracking. Contains workflow patterns, commands, and integration guidelines.

### Documentation Standards
**File**: `docs/references/documentation-management.md`
**When to read**: Before creating new documentation, updating docs, or organizing files
**Summary**: Document hierarchy, decision trees, lifecycle management, and quality standards for all project documentation.

### Component Usage Patterns
**File**: `docs/references/component-documentation.md`
**When to read**: When using LoadingStateManager, ProgressIndicator, DeleteBookModal, or similar components
**Summary**: Comprehensive usage examples, props, integration patterns, and test coverage for reusable components.

### Quality Requirements
**File**: `docs/references/quality-standards.md`
**When to read**: Before marking features complete, submitting PRs, or implementing new features
**Summary**: Testing requirements (85% coverage), git workflow, documentation synchronization, and feature completion checklist.

### Performance Guidelines
**File**: `docs/references/performance-monitoring.md`
**When to read**: When implementing performance-sensitive features, tracking operations, or optimizing code
**Summary**: Performance tracking system, budgets (TOC: 3000ms, Export: 5000ms), Core Web Vitals, and integration patterns.

### Testing Practices
**File**: `docs/references/testing-infrastructure.md`
**When to read**: When writing tests, fixing test issues, or implementing TDD workflows
**Summary**: Test helpers (condition-based waiting, test data setup, error handling), E2E test suites, running tests, and known issues.

---

## Project Overview

This project uses SPARC (Specification, Pseudocode, Architecture, Refinement, Completion) methodology with Claude-Flow orchestration for systematic Test-Driven Development.

## Quick Start Commands

### SPARC Commands
- `npx claude-flow sparc modes` - List available modes
- `npx claude-flow sparc run <mode> "<task>"` - Execute specific mode
- `npx claude-flow sparc tdd "<feature>"` - Run complete TDD workflow

### Task Management (bd/Beads)
- `bd ready` - View unblocked tasks ready to start
- `bd list --status open` - View all open tasks
- `bd create "Task" -p 0 -t feature -d "Description"` - Create task
- `bd close <task-id> --reason "Completed"` - Close completed task

### Build & Test
- `npm run build` - Build project
- `npm test` - Run tests
- `npm run test:coverage` - Run tests with coverage
- `npm run lint` - Linting
- `npm run typecheck` - Type checking

### Backend Testing
```bash
cd backend
uv run pytest --cov=app tests/ --cov-report=term-missing
```

### E2E Testing
```bash
cd frontend
npx playwright test --ui    # Run with UI mode (recommended)

# With auth bypass (for testing without real auth)
BYPASS_AUTH=true npx playwright test
```

#### Staging E2E (real auth against https://dev.autoauthor.app)
```bash
cd frontend
cp tests/e2e/staging/.env.test.example tests/e2e/staging/.env.test  # set STAGING_TEST_EMAIL / STAGING_TEST_PASSWORD
npm run test:e2e:staging
```
- Specs: `tests/e2e/staging/complete-user-journey.spec.ts` (full journey) and `regressions.spec.ts` (Issue #83 regressions: session/401, ObjectId, #54 answer persistence).
- CI: `.github/workflows/e2e-staging-tests.yml` runs on a 6h schedule, manual dispatch, and PRs labeled `e2e-staging`. Requires GitHub Secrets `TEST_USER_EMAIL` / `TEST_USER_PASSWORD` (the fixture also accepts `STAGING_TEST_EMAIL` / `STAGING_TEST_PASSWORD` locally).
- See `tests/e2e/staging/README.md` for details.

---

## Key Features

### ✅ Production Ready
- User authentication (better-auth with HS256 JWT verification)
- **Session Management** (Activity tracking, security features, timeout handling)
- Book CRUD operations with metadata
- **Book Deletion UI** (Type-to-confirm with data loss warnings)
- TOC generation with AI wizard
- Chapter tabs interface (vertical layout with keyboard shortcuts)
- **Rich Text Editor** (TipTap with full formatting)
- **AI Draft Generation** (Q&A to narrative with multiple styles)
- **Auto-save System** (3s debounce + localStorage backup on network failure)
- **Keyboard Accessibility** (WCAG 2.1 compliant)
- **Voice Input Integration** (Browser Speech API)
- **Export functionality** (PDF/DOCX with customizable options)
- **Performance Monitoring** (Core Web Vitals + operation budgets)
- **Unified Error Handling** (automatic retry with exponential backoff)

### 🚧 In Progress
See `CURRENT_SPRINT.md` for active tasks or run `bd ready` for unblocked work.

### 🔧 Test Infrastructure Status
- **Frontend**: 88.7% pass rate (613/691 tests passing)
  - 75 failures are environmental (missing mocks, not code bugs)
  - Fix plan: 3.5-5.5 hours across 4 phases
- **Backend**: 98.9% pass rate (187/189 tests passing)
  - 41% coverage vs 85% target
  - Improvement plan: 4-5 weeks, 207-252 new tests
- **E2E**: Comprehensive Playwright suite with auth bypass support

---

## Code Style & Best Practices

- **Modular Design**: Files under 500 lines
- **Environment Safety**: Never hardcode secrets
- **Test-First**: Write tests before implementation (TDD)
- **Clean Architecture**: Separate concerns
- **Documentation**: Keep synchronized with code

---

## 🔒 MANDATORY: TDD & E2E Test Enforcement

**CRITICAL**: This project REQUIRES Test-Driven Development and E2E test coverage for ALL features. No feature is complete without proper test coverage.

### Pre-Commit Hook Requirements

**ALL commits MUST pass these gates:**

1. **Unit Tests**: All unit tests must pass
   ```bash
   # Frontend
   cd frontend && npm test

   # Backend
   cd backend && uv run pytest tests/
   ```

2. **E2E Tests**: All E2E tests must pass
   ```bash
   # Basic E2E tests
   cd frontend && npx playwright test

   # Deployment test suite (comprehensive)
   cd frontend && npx playwright test --config=tests/e2e/deployment/playwright.config.ts
   ```

3. **Test Coverage**: Minimum 85% coverage required
   ```bash
   # Frontend
   cd frontend && npm test -- --coverage --coverageThreshold='{"global":{"lines":85}}'

   # Backend
   cd backend && uv run pytest --cov=app tests/ --cov-fail-under=85
   ```

4. **Linting & Type Checking**: No errors allowed
   ```bash
   cd frontend && npm run lint && npm run typecheck
   cd backend && uv run mypy app/
   ```

### Feature Branch Workflow (MANDATORY)

**NEVER commit directly to `main` or `develop`. Always use feature branches:**

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit (pre-commit hooks will run automatically)
git add .
git commit -m "feat: implement your feature"

# Push to remote
git push -u origin feature/your-feature-name

# Create Pull Request for review
# PR must have:
# - All tests passing
# - ≥85% test coverage
# - E2E test for user-facing features
# - Updated documentation
```

### Feature Completion Checklist (ENFORCED)

**A feature is NOT complete until ALL of these are done:**

- [ ] **Unit tests written** (≥85% coverage for new code)
- [ ] **E2E test created** (for user-facing features)
- [ ] **All tests passing** (unit + E2E)
- [ ] **Documentation updated** (CLAUDE.md, API docs, user guides)
- [ ] **Performance validated** (meets operation budgets)
- [ ] **Accessibility verified** (WCAG 2.1 Level AA minimum)
- [ ] **Code reviewed** (PR approved by team)
- [ ] **bd task closed** (`bd close <task-id> --reason "Completed in PR #123"`)

### E2E Test Coverage Requirements

**EVERY user-facing feature MUST have an E2E test that validates:**

1. **Happy Path**: Complete user journey from start to finish
2. **Error Handling**: How the system handles failures
3. **Performance**: Operation completes within budget
4. **Accessibility**: Keyboard navigation works
5. **Data Integrity**: Data persists correctly

**Example - TOC Generation Feature:**
```typescript
// frontend/tests/e2e/toc-generation.spec.ts
test('user can generate TOC from book summary', async ({ page }) => {
  // 1. Create book with summary
  // 2. Navigate to TOC wizard
  // 3. Answer clarifying questions
  // 4. Verify TOC generates within 3000ms budget
  // 5. Verify TOC data saves to database
  // 6. Verify TOC appears in book view
});
```

### Pre-Commit Hook Setup

**✅ PRE-COMMIT HOOKS ARE CONFIGURED AND ENFORCED**

This project uses automated pre-commit hooks that run before every commit. These hooks enforce TDD and quality standards.

**Install pre-commit hooks (one-time setup):**

```bash
# Install pre-commit (if not already installed)
pip install pre-commit

# Install the git hook scripts
cd /home/frankbria/projects/auto-author
pre-commit install

# Test the hooks
pre-commit run --all-files
```

**What runs on every commit:**

1. **Documentation Auto-Sync** (always runs)
   - Exports current sprint from bd tracker
   - Exports implementation plan from bd tracker
   - Auto-adds updated docs to commit

2. **Frontend Quality Gates** (runs when frontend/ files change)
   - Linting (`npm run lint`)
   - Type checking (`npm run typecheck`)
   - Unit tests (`npm test`)
   - Coverage check (≥85% required)
   - E2E tests (Playwright)

3. **Backend Quality Gates** (runs when backend/ files change)
   - Linting (`ruff check`)
   - Unit tests (`pytest tests/`)
   - Coverage check (≥85% required)

4. **General Code Quality** (always runs)
   - Trailing whitespace removal
   - End-of-file fixing
   - YAML/JSON validation
   - Merge conflict detection
   - Large file detection (>1MB blocked)
   - Private key detection

**Configuration:** See `.pre-commit-config.yaml` in project root for full details.

**Bypassing hooks (emergency only):**
```bash
git commit --no-verify -m "hotfix: emergency fix"
# Then immediately create follow-up task:
bd create "Add tests for emergency hotfix" -p 0 -t bug
```

### Test Quality Standards

**Tests MUST be:**
- **Isolated**: No dependencies on external services (use mocks)
- **Repeatable**: Same result every time
- **Fast**: Unit tests <1s each, E2E tests <30s each
- **Meaningful**: Test behavior, not implementation
- **Maintainable**: Clear, well-documented test code

**Tests MUST NOT:**
- Use arbitrary timeouts (`await page.waitForTimeout(5000)` ❌)
- Depend on test execution order
- Leave side effects (data, files, processes)
- Test internal implementation details

---

## Deployment Information
- The staging server is located at: https://dev.autoauthor.app (frontend) and https://api.dev.autoauthor.app (backend)
- You can access the staging server with SSH with username root. The keys are local; no password is required.
- There are deployment scripts in the git workflow directories
- **IMPORTANT** there are other aplications on the server. Be aware of port considerations. Right now, the backend uses 8000 and the frontend uses 3002, but be aware that this could change. Check nginx settings for the latest information.
- The applications are managed via PM2 on the server. Since the deployment has a symlinked current release directory, sometimes that needs to be checked if things are out of sync.

---

## 🚀 Available Agents


---

## 🎯 Claude Code vs MCP Tools

### Claude Code Handles ALL:
- File operations (Read, Write, Edit, MultiEdit, Glob, Grep) unless the edits are complex or long
- Code generation and programming
- Bash commands and system operations
- Implementation work
- Project navigation and analysis
- TodoWrite and task management
- Git operations
- Package management
- Testing and debugging

---

## Important Workflow Notes

### Before Starting Work
1. Run `bd ready` to see unblocked tasks
2. Check `CURRENT_SPRINT.md` for sprint context
3. Read relevant reference docs from `docs/references/` as needed

### Before Completing Features
1. Read `docs/references/quality-standards.md` for completion checklist
2. Verify 85% test coverage minimum
3. Run linting and type checking
4. Commit with conventional commit messages
5. Close task in bd: `bd close <task-id> --reason "Completed in PR #123"`

### When Creating Documentation
1. Read `docs/references/documentation-management.md` first
2. Check existing documents before creating new ones
3. Default to updating IMPLEMENTATION_PLAN.md
4. Use bd for tasks: `bd create "Task" -p 1 -t feature`

### When Using Components
1. Read `docs/references/component-documentation.md` for usage patterns
2. Check LoadingStateManager, ProgressIndicator, DeleteBookModal examples
3. Follow accessibility standards (WCAG 2.1 compliant)

---

## Quick Reference: When to Read Reference Docs

| Scenario | Read This File |
|----------|---------------|
| Creating/checking tasks | `docs/references/beads-workflow.md` |
| Creating documentation | `docs/references/documentation-management.md` |
| Using reusable components | `docs/references/component-documentation.md` |
| Completing features | `docs/references/quality-standards.md` |
| Performance optimization | `docs/references/performance-monitoring.md` |
| Writing/fixing tests | `docs/references/testing-infrastructure.md` |
| Understanding test status | `docs/POST_DEPLOYMENT_TEST_REPORT.md` |
| Backend coverage details | `backend/TEST_COVERAGE_REPORT.md` |
| Frontend test failures | `frontend/docs/TEST_FAILURE_ANALYSIS.md` |

---

## Environment Information

**Package Management**:
- Python: uv for environment and package management
- Node.js: npm for frontend dependencies

**Task Tracking**:
- Use bd (Beads) for all task management
- Run `bd quickstart` to learn the system
- Markdown files (CURRENT_SPRINT.md, IMPLEMENTATION_PLAN.md) are auto-generated snapshots

**Documentation Structure**:
- `CLAUDE.md` (this file) - Quick reference and core guidelines
- `docs/references/*.md` - Detailed reference documentation (read on-demand)
- `claudedocs/*.md` - Technical analysis and detailed plans
- `archive/*.md` - Historical planning documents (read-only)

**Environment Variables**:
- `BYPASS_AUTH=true` - Disable authentication for E2E testing (development only)
- Standard Next.js and FastAPI environment variables (see `.env.example`)

---

## API Overview

### Authentication
- **Production**: Better-auth JWT verification using HS256 shared secret
- **Testing**: `BYPASS_AUTH=true` creates mock authenticated context
- **Security**: Never use auth bypass in production environments

### Core Endpoints
- `/api/v1/books` - Book CRUD operations
- `/api/v1/chapters` - Chapter management
- `/api/v1/toc` - Table of Contents generation
- `/api/v1/export` - PDF/DOCX export

See backend API documentation for full endpoint reference.
