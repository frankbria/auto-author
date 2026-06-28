# Issue #118 — Restore pre-commit/CI gate enforcement (P1.15, capstone)

## Verified preconditions (all blockers closed)
- #68, #93, #116, #117 all CLOSED. No open coverage child issues remain.
- Backend coverage gate: **92.44%** ✅ (was ~41%) — `pytest --cov=app --cov-fail-under=85` passes, 888 passed/15 skipped.
- Frontend coverage gate: ✅ passes 85/85/75/85 thresholds, 1856 passed/8 skipped, 90 suites.

## Findings
- `main` has **no branch protection** (404). Item 3 is greenfield.
- CI `tests.yml` has `continue-on-error: true` on BOTH coverage-threshold steps (lines 50, 106) — coverage regressions don't fail the job today. Must remove to truly enforce.
- No PR template file exists (`.github/` has only workflows + DEPLOYMENT.md) → scope item 4 "PR template" is N/A.
- Bypass boilerplate lives in CLAUDE.md (line 44 NB; pre-commit section).
- CI check contexts: `Frontend Tests`, `Backend Tests`, `E2E Tests (Playwright)`, `Quality Summary`, `Build and Deploy to Staging`. E2E explicitly out of scope per issue.

## Plan
1. `.github/workflows/tests.yml`: remove `continue-on-error: true` from the frontend + backend coverage-threshold steps so coverage is enforced in CI.
2. `CLAUDE.md`: neutralize the line-44 `--no-verify`/baseline-gates-red NB; update the pre-commit/TDD section to state gates are green & enforced; add a Recent Changes entry.
3. Branch protection on `main` via `gh api`: required status checks (strict) = Frontend Tests + Backend Tests; route merges through PR. (Strictness = user decision — see Phase 4.)
4. Demonstrate: `pre-commit run --all-files` green; open PR; merge through required checks **without** `--admin`.
5. Update stale auto-memory note (coverage gate now green/enforced).

## Acceptance criteria mapping
- [ ] `pre-commit run --all-files` zero failures → demo evidence (Phase 11)
- [ ] PR merged through required checks without `--admin` → Phase 13
- [ ] Branch protection requires coverage/test checks → step 3
- [ ] CLAUDE.md / PR template no longer instruct bypassing → step 2 (no PR template exists)
- [ ] No open coverage gate red → verified above
