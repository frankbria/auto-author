# Issue #196 [P2.4]: Remove dead 'Session Management' subsystem

**Plan source**: CodeRabbit comment (2026-07-04), AC "remove" branch. Fork pre-resolved: better-auth `ActiveSessionsList` already serves real session UX; legacy subsystem is a duplicative parallel session store with zero live consumers (verified: `SessionMiddleware` gates on `request.state.user`, which nothing sets).

**Plan verification (2026-07-12)**: all 16 referenced files exist; no consumers of the session DAOs outside the subsystem itself; frontend `useSession` hook imported only by `SessionWarning.tsx` + its test (never mounted); `middleware/` package contains ONLY session middleware.

## Adaptations to the CodeRabbit plan
1. **Delete the whole `backend/app/api/middleware/` package** — after removing session_middleware it holds only an empty `__init__.py`; sole importer is `main.py`.
2. **Also remove `sessions_collection`** from `backend/app/db/base.py` (def + `__all__`) and the rebind in `backend/tests/conftest.py:139` — dead after removal (plan missed these).
3. **TDD/regression test** (#186 removal pattern): new test pinning the `/sessions/*` routes are gone — authenticated `GET /api/v1/sessions/list` returns 404 (RED on main: returns 200 empty list); no route path starts with `/api/v1/sessions`.
4. **Docs**: historical snapshots (docs/analysis/*, code-review/*, STAGING_VERIFICATION_RESULTS.md, BACKEND_TEST_FAILURE_ANALYSIS.md, claudedocs/*) kept as-is per #120/#186 precedent. Live docs edited: CLAUDE.md (Production Ready bullet + API endpoints line 473), delete docs/SESSION_MANAGEMENT.md, prune docs/production-readiness-gaps.md session-gap entries, fix docs/better-auth-migration-guide.md:403 stale "kept file" line. docs/session-management.md is better-auth-generic → keep (no legacy endpoint refs).

## Todo
- [ ] Branch `fix/196-remove-dead-session-subsystem`
- [ ] RED: regression test (sessions routes unregistered) fails on main-state code
- [ ] Backend: unregister middleware+router; delete 5 modules + middleware pkg; clean database.py/base.py/conftest re-exports
- [ ] Backend: delete 5 session test files; full suite green ≥85% cov
- [ ] Frontend: delete useSession.ts, SessionWarning.tsx, useSession.test.tsx; suite green
- [ ] Docs: CLAUDE.md, SESSION_MANAGEMENT.md, production-readiness-gaps.md, better-auth-migration-guide.md
- [ ] Deslop scan, quality gate (lint, tests, opencode/codex review pre-PR)
- [ ] PR, post-PR review, demo (main-vs-branch route differential), CI gate, merge
