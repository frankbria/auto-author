# Clerk to better-auth Migration - Execution Session

**Session Date**: 2025-12-17
**Branch**: `feature/migrate-clerk-to-better-auth`
**Status**: In Progress

## Overview

Migrating the entire authentication system from Clerk to better-auth across both Next.js frontend and FastAPI backend. This is a comprehensive migration touching 70+ files.

**Key Decision**: No active users currently, so database migration is simplified - we'll set up fresh better-auth tables instead of complex data migration.

## Execution Plan Summary

### Phase Structure

1. **Phase 1** - Pre-Migration Analysis (5 min, sequential)
2. **Phase 2** - Backend Migration (45-60 min, 4 parallel agents)
3. **Phase 3** - Frontend Core Migration (45-60 min, 4 parallel agents)
4. **Phase 4** - Frontend Component Migration (30-45 min, 3 parallel agents)
5. **Phase 5** - Frontend Tests Migration (30-45 min, 2 parallel agents)
6. **Phase 6** - Database Setup (SIMPLIFIED - fresh DB setup)
7. **Phase 7** - Integration Testing (20-30 min, sequential)
8. **Phase 8** - Documentation & Cleanup (15-20 min, 2 parallel agents)

---

## Phase 1: Pre-Migration Analysis

**Goal**: Validate migration plan with better-auth best practices

**Resources**:
- Skill: `using-better-auth`

**Expected Outcome**: Confirmation of plan soundness, identification of any critical gotchas

---

## Phase 2: Backend Migration (4 Parallel Agents)

### Agent 1: Backend Config
**Model**: Haiku
**Files**:
- `backend/app/core/config.py` - Remove Clerk config, add better-auth config
- `backend/requirements.txt` - Remove clerk dependencies
- `backend/.env.example` - Update env vars

**Task**: "Update backend configuration files to support better-auth JWT tokens instead of Clerk. Remove Clerk-specific config (CLERK_SECRET_KEY, CLERK_PUBLISHABLE_KEY), add better-auth config (BETTER_AUTH_SECRET, BETTER_AUTH_URL, BETTER_AUTH_ISSUER). Update requirements.txt to remove clerk dependencies."

### Agent 2: Backend Security
**Model**: Sonnet (complex logic)
**Files**:
- `backend/app/core/security.py` - Complete JWT validation rewrite
- `backend/app/api/dependencies.py` - Update auth dependencies
- `backend/app/api/middleware/session_middleware.py` - Update middleware

**Task**: "Rewrite security.py to validate better-auth JWT tokens instead of Clerk tokens. Remove get_clerk_user, get_clerk_jwks functions. Rewrite verify_jwt_token to validate better-auth JWT using BETTER_AUTH_SECRET. Update token payload structure to match better-auth format. Update get_current_user to fetch users by better-auth user ID instead of clerk_id. Update dependencies.py and session_middleware.py accordingly."

### Agent 3: Backend User Model
**Model**: Haiku
**Files**:
- `backend/app/models/user.py` - User model schema changes
- `backend/app/schemas/user.py` - User schemas update
- `backend/app/db/user.py` - Database operations
- `backend/app/db/database.py` - Update exports
- `backend/app/db/book.py` - Update user references
- `backend/app/db/book_cascade_delete.py` - Update user references
- `backend/app/db/toc_transactions.py` - Update user references
- `backend/app/api/endpoints/users.py` - User endpoints
- `backend/app/api/endpoints/books.py` - Update user ID references
- `backend/app/api/endpoints/sessions.py` - Update user ID references
- `backend/app/api/endpoints/export.py` - Update user ID references
- `backend/app/api/endpoints/book_cover_upload.py` - Update user ID references
- `backend/app/api/endpoints/webhooks.py` - Remove/rewrite Clerk webhooks
- `backend/app/services/question_generation_service.py` - Update user ID references
- `backend/app/models/book.py` - Update owner_id documentation
- `backend/app/populate_db_test_data.py` - Update test data

**Task**: "Update user model to match better-auth schema. Replace clerk_id with better-auth's user ID structure (auth_id field). Update UserBase, UserCreate, UserDB, UserRead models. Update all database operations (get_user_by_clerk_id → get_user_by_auth_id). Update all endpoints to use new user ID field instead of clerk_id. Update book, session, export endpoints. Remove/rewrite Clerk webhook handlers."

### Agent 4: Backend Tests
**Model**: Haiku
**Files**:
- `backend/tests/conftest.py` - Update test fixtures
- `backend/tests/factories/models.py` - Update UserFactory
- `backend/tests/fixtures/chapter_tabs_fixtures.py` - Update fixtures
- `backend/tests/test_api/test_dependencies.py` - Update tests
- `backend/tests/test_api/test_draft_generation_simple.py` - Update tests
- `backend/run_unit_tests.py` - Remove Clerk env vars
- `backend/test_config.py` - Remove Clerk env vars
- `backend/test_services_isolated.py` - Update env vars
- `backend/test_services_summary.py` - Update env vars

**Task**: "Update all backend tests to mock better-auth instead of Clerk. Replace Clerk JWT mocks with better-auth JWT mocks. Update conftest.py fixtures with better-auth user structure. Update UserFactory to generate better-auth compatible users. Remove CLERK_API_KEY and CLERK_JWT_PUBLIC_KEY from test configs. Ensure test coverage remains ≥85%."

**Validation After Phase 2**:
- Run `cd backend && uv run pytest tests/`
- Check for linting errors
- Verify no merge conflicts

---

## Phase 3: Frontend Core Migration (4 Parallel Agents)

### Agent 1: Frontend Config
**Model**: Haiku
**Files**:
- `frontend/package.json` - Add better-auth packages, remove @clerk/nextjs
- `frontend/.env.example` - Update env vars
- `frontend/src/lib/auth.ts` (NEW) - better-auth configuration
- `frontend/src/lib/auth-client.ts` (NEW) - Client-side auth helpers
- `frontend/src/app/api/auth/[...all]/route.ts` (NEW) - Auth API routes

**Task**: "Install better-auth packages (better-auth, @better-auth/react, mongodb adapter). Remove @clerk/nextjs and @clerk/themes. Create auth.ts with better-auth server config using MongoDB adapter. Create auth-client.ts with createAuthClient for React hooks. Create API route handler at /api/auth/[...all]/route.ts. Update .env.example with BETTER_AUTH_SECRET, BETTER_AUTH_URL, DATABASE_URL."

### Agent 2: Frontend Middleware
**Model**: Sonnet (routing logic)
**Files**:
- `frontend/src/middleware.ts` - Complete rewrite for better-auth
- `frontend/src/app/layout.tsx` - Replace ClerkProvider

**Task**: "Rewrite middleware.ts to use better-auth session handling. Replace clerkMiddleware with better-auth session validation. Keep BYPASS_AUTH logic for E2E testing. Update route matchers to protect same routes. In layout.tsx, replace ClerkProvider with SessionProvider from @/lib/auth-client. Remove Clerk theme imports."

### Agent 3: Frontend Auth Pages
**Model**: Haiku
**Files**:
- `frontend/src/app/auth/sign-in/page.tsx` (NEW) - Sign-in page
- `frontend/src/app/auth/sign-up/page.tsx` (NEW) - Sign-up page

**Task**: "Create custom sign-in page with email/password form using better-auth's signIn method. Include validation, error handling, redirect to dashboard on success, link to sign-up. Create custom sign-up page with email/password/name fields using better-auth's signUp method. Include password confirmation, validation, error handling, redirect on success, link to sign-in. Use Shadcn/UI components for consistent styling."

### Agent 4: Frontend Hooks & Components
**Model**: Haiku
**Files**:
- `frontend/src/components/auth/ProtectedRoute.tsx` - Update to use better-auth
- `frontend/src/lib/clerk-helpers.ts` → `frontend/src/lib/auth-helpers.ts` (RENAME) - Rewrite helpers
- `frontend/src/hooks/useAuthFetch.ts` - Update to use better-auth
- `frontend/src/hooks/useSession.ts` - Update to use better-auth
- `frontend/src/components/ui/user-button.tsx` (NEW) - Custom UserButton

**Task**: "Update ProtectedRoute.tsx to use useSession from @/lib/auth-client instead of useAuth from Clerk. Keep BYPASS_AUTH logic. Rename clerk-helpers.ts to auth-helpers.ts and rewrite getAuthToken, getUserInfo, hasRole, isAuthenticated to work with better-auth session. Update useAuthFetch to get token from better-auth session. Update useSession hook to use better-auth. Create custom UserButton component with user avatar, dropdown menu, sign-out functionality using Shadcn/UI."

**Validation After Phase 3**:
- Run `cd frontend && npm run typecheck`
- Check for compilation errors
- Verify auth pages accessible

---

## Phase 4: Frontend Component Migration (3 Parallel Agents)

### Agent 1: Dashboard & Books Components
**Model**: Haiku
**Files**:
- `frontend/src/app/page.tsx` - Replace Clerk components/hooks
- `frontend/src/app/dashboard/layout.tsx` - Replace UserButton
- `frontend/src/app/dashboard/page.tsx` - Replace Clerk hooks
- `frontend/src/app/dashboard/settings/page.tsx` - Replace useUser

**Task**: "Replace Clerk components (SignedIn, SignedOut, SignInButton, SignUpButton, SignOutButton) with better-auth equivalents in page.tsx. Replace useUser with useSession. In dashboard/layout.tsx, replace Clerk UserButton with custom UserButton. In dashboard/page.tsx and settings/page.tsx, replace useUser/useAuth with useSession from @/lib/auth-client. Update user property access to match better-auth structure."

### Agent 2: Book Editor Components
**Model**: Haiku
**Files**:
- `frontend/src/app/dashboard/books/[bookId]/page.tsx` - Update auth
- `frontend/src/app/dashboard/books/[bookId]/edit-toc/page.tsx` - Update auth
- `frontend/src/app/dashboard/books/[bookId]/export/page.tsx` - Update auth

**Task**: "Replace useAuth from Clerk with useSession from better-auth in all book pages. Update getToken calls to use better-auth's token retrieval. Update token provider setup for bookClient to use better-auth session tokens. Ensure auto-save functionality works with new auth."

### Agent 3: UI Components
**Model**: Haiku
**Files**:
- Search for remaining @clerk/nextjs imports and update

**Task**: "Search for any remaining @clerk/nextjs imports in components. Replace with better-auth equivalents. Update user context in modals, cards, and other UI components."

**Validation After Phase 4**:
- Run `cd frontend && npm run lint`
- Check for remaining Clerk imports: `grep -r "@clerk/nextjs" frontend/src/`
- Verify components compile

---

## Phase 5: Frontend Tests Migration (2 Parallel Agents)

### Agent 1: Unit Tests
**Model**: Haiku
**Files**:
- All test files in `frontend/src/__tests__/` that use Clerk mocks
- Create better-auth mocks in `frontend/__mocks__/`

**Task**: "Replace all Clerk mocks with better-auth mocks. Create mock for useSession hook from @/lib/auth-client. Update all test files to import from better-auth mocks instead of Clerk. Update user structure in tests to match better-auth (use session.user instead of user). Ensure ≥85% coverage maintained."

### Agent 2: E2E Tests
**Model**: Sonnet (auth flows)
**Files**:
- `frontend/tests/e2e/deployment/*.spec.ts` - All E2E tests
- E2E test fixtures and helpers

**Task**: "Update E2E tests to use better-auth authentication flow. Update BYPASS_AUTH logic to work with better-auth. Update authentication fixtures to create better-auth sessions. Ensure complete-authoring-journey test passes with new auth. Update page objects for sign-in/sign-up pages."

**Validation After Phase 5**:
- Run `cd frontend && npm test`
- Check coverage: should be ≥85%
- Run E2E tests: `cd frontend && npx playwright test`

---

## Phase 6: Database Setup (SIMPLIFIED)

**Note**: No active users, so we skip complex migration and just set up fresh better-auth tables.

**Manual Steps**:
1. Update MongoDB connection to point to better-auth database
2. Run better-auth migrations to create necessary tables (user, session, account, verification)
3. Clear any existing Clerk user data (optional - can keep for reference)

**Expected Outcome**: Fresh better-auth database ready for new user signups

---

## Phase 7: Integration Testing

**Goal**: End-to-end validation of complete migration

**Resources**:
- Run full test suite (backend + frontend)
- Run E2E tests
- Manual testing of auth flows
- Security review with `/fhb:code-review`

**Validation Checklist**:
- [ ] Backend tests: `cd backend && uv run pytest tests/` (≥85% coverage)
- [ ] Frontend tests: `cd frontend && npm test` (≥85% coverage)
- [ ] E2E tests: `cd frontend && npx playwright test`
- [ ] Type checking: `cd frontend && npm run typecheck`
- [ ] Linting: `cd frontend && npm run lint && cd ../backend && uv run ruff check`
- [ ] Manual sign-up flow works
- [ ] Manual sign-in flow works
- [ ] Protected routes redirect correctly
- [ ] User session persists across page reloads
- [ ] Sign-out clears session
- [ ] API requests include valid better-auth JWT
- [ ] Backend validates JWT correctly

**Expected Outcome**: All tests passing, security review complete, ready for deployment

---

## Phase 8: Documentation & Cleanup (2 Parallel Agents)

### Agent 1: Documentation
**Model**: Haiku
**Files**:
- `docs/better-auth-migration-guide.md` (NEW) - Migration documentation
- `CLAUDE.md` - Update authentication section
- `backend/ENV_VAR_CHANGELOG.md` - Document env var changes

**Task**: "Create comprehensive migration guide documenting Clerk → better-auth changes. Include overview, environment variable changes, code changes summary, testing strategy, deployment notes. Update CLAUDE.md authentication section to reflect better-auth usage. Update ENV_VAR_CHANGELOG.md with removed Clerk vars and new better-auth vars."

### Agent 2: Cleanup
**Model**: Haiku
**Files**:
- Delete: `docs/clerk-deployment-checklist.md`
- Delete: `docs/clerk-integration-guide.md`
- Delete: `docs/clerk-setup-guide.md`
- Remove any Clerk-specific comments in code
- Update .gitignore if needed

**Task**: "Remove all Clerk-specific documentation files. Search codebase for remaining Clerk references in comments and remove. Clean up any unused Clerk configuration files. Update .gitignore if needed for better-auth."

**Validation After Phase 8**:
- Documentation is complete and accurate
- No Clerk artifacts remain in codebase
- README.md has accurate setup instructions

---

## Final Validation Checklist

Before marking migration complete:

- [ ] All unit tests passing (frontend + backend, ≥85% coverage)
- [ ] All E2E tests passing
- [ ] No TypeScript errors
- [ ] No linting errors
- [ ] Backend JWT validation working with better-auth tokens
- [ ] Frontend auth pages functional (sign-in, sign-up)
- [ ] Session management working (auto-refresh, timeout)
- [ ] User data flows correctly (signup → DB → session)
- [ ] Security review passed (OWASP Top 10 compliant)
- [ ] Documentation complete (migration guide, CLAUDE.md updated)
- [ ] Clerk artifacts removed
- [ ] Pre-commit hooks passing
- [ ] Ready for staging deployment

---

## Risk Mitigation Notes

### High Risks Identified:
1. **JWT Token Format Mismatch**: Phase 1 validation catches this early
2. **Session Continuity**: N/A - no active users
3. **Database Schema**: Simplified - fresh DB setup

### Medium Risks:
1. **Parallel Agent Merge Conflicts**: File assignments carefully partitioned
2. **CORS Configuration**: Phase 3 Middleware Agent handles CORS
3. **MongoDB Connection**: Phase 1 reviews adapter config

### Validation Between Phases:
- After each phase, run relevant tests
- Check for compilation/linting errors
- Verify no merge conflicts
- If any agent fails: HALT, fix, restart that agent

---

## Execution Status

- [x] Feature branch created
- [x] Session.md written
- [ ] Phase 1: Pre-Migration Analysis
- [ ] Phase 2: Backend Migration (4 agents)
- [ ] Phase 3: Frontend Core Migration (4 agents)
- [ ] Phase 4: Frontend Component Migration (3 agents)
- [ ] Phase 5: Frontend Tests Migration (2 agents)
- [ ] Phase 6: Database Setup
- [ ] Phase 7: Integration Testing
- [ ] Phase 8: Documentation & Cleanup (2 agents)

---

## Notes for Agents

When working on this migration:

1. **Trust the plan**: Files and references are verified. Don't re-verify unless absolutely necessary.
2. **Follow better-auth patterns**: Use the `using-better-auth` skill if you need clarification
3. **Maintain test coverage**: ≥85% is mandatory
4. **Preserve functionality**: Auth should work identically to users, just with better-auth backend
5. **Update all references**: Search for Clerk imports/references in your assigned files and replace
6. **Consistent naming**: Use `auth_id` for user IDs (not clerk_id, not user_id)
7. **Error handling**: Maintain existing error handling patterns
8. **Session structure**: better-auth session = { user: { id, email, name, ... }, session: { ... } }

---

## Token Budget Tracking

- Phase 1: ~5k tokens
- Phase 2: ~60k tokens (4 agents × ~15k)
- Phase 3: ~60k tokens (4 agents × ~15k)
- Phase 4: ~45k tokens (3 agents × ~15k)
- Phase 5: ~30k tokens (2 agents × ~15k)
- Phase 6: ~5k tokens (simplified)
- Phase 7: ~10k tokens
- Phase 8: ~10k tokens (2 agents × ~5k)

**Total Estimated**: ~225k tokens (agents run in separate contexts)
