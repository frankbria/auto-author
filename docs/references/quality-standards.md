# Feature Development Quality Standards

**CRITICAL**: All new features MUST meet the following mandatory requirements before being considered complete.

## Testing Requirements

- **Minimum Coverage**: 85% code coverage ratio required for all new code
- **Test Pass Rate**: 100% - all tests must pass, no exceptions
- **Test Types Required**:
  - Unit tests for all business logic and services
  - Integration tests for API endpoints
  - End-to-end tests for critical user workflows
- **Coverage Validation**: Run coverage reports before marking features complete:
  ```bash
  # Backend
  cd backend && uv run pytest --cov=app tests/ --cov-report=term-missing

  # Frontend
  cd frontend && npm run test:coverage
  ```
- **Test Quality**: Tests must validate behavior, not just achieve coverage metrics
- **Test Documentation**: Complex test scenarios must include comments explaining the test strategy

### Test Quality Rules

Tests MUST be **isolated** (no external service dependencies), **repeatable** (same result every run),
**fast** (unit <1s, E2E <30s), and **meaningful** (behavior, not implementation).

Tests MUST NOT use arbitrary timeouts (`await page.waitForTimeout(5000)` ❌ — use condition-based
waiting, see `testing-infrastructure.md`), depend on execution order, leave side effects, or assert
on internal implementation details.

### E2E Coverage Requirements

EVERY user-facing feature needs an E2E test covering all five:

1. **Happy path** — complete user journey start to finish
2. **Error handling** — how the system behaves on failure
3. **Performance** — operation completes within its budget (see `performance-monitoring.md`)
4. **Accessibility** — keyboard navigation works
5. **Data integrity** — data actually persists

```typescript
// frontend/tests/e2e/toc-generation.spec.ts
test('user can generate TOC from book summary', async ({ page }) => {
  // create book with summary → open TOC wizard → answer clarifying questions
  // → assert generation completes within the 3000ms budget
  // → assert TOC persisted and renders in the book view
});
```

## Git Workflow Requirements

Before moving to the next feature, ALL changes must be:

1. **Committed with Clear Messages**:
   ```bash
   git add .
   git commit -m "feat(module): descriptive message following conventional commits"
   ```
   - Use conventional commit format: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, etc.
   - Include scope when applicable: `feat(backend):`, `fix(frontend):`, `test(auth):`
   - Write descriptive messages that explain WHAT changed and WHY

2. **Pushed to Remote Repository**:
   ```bash
   git push origin <branch-name>
   ```
   - Never leave completed features uncommitted
   - Push regularly to maintain backup and enable collaboration
   - Ensure CI/CD pipelines pass before considering feature complete

3. **Branch Hygiene**:
   - Work on feature branches, never directly on `main`
   - Branch naming convention: `feature/<feature-name>`, `fix/<issue-name>`, `docs/<doc-update>`
   - Create pull requests for all significant changes

4. **Task Tracking (bd)**:
   - Create or update the bd issue before starting work (`bd ready`, `bd create`)
   - Move to in-progress when beginning implementation
   - Close on completion: `bd close <id> --reason "Completed in PR #123"`
   - Reference issue IDs in commit messages
   - `CURRENT_SPRINT.md` / `IMPLEMENTATION_PLAN.md` are generated snapshots — edit bd, not the markdown

## Dependency Batches

Since #517, `.github/dependabot.yml` **groups** version updates, so a weekly sweep
arrives as a few PRs rather than up to fifteen. What groups and what does not:

| Ecosystem | Grouped | Arrives alone |
|---|---|---|
| `github-actions` | everything, majors included | — |
| `npm` /frontend | all dev deps; prod minor + patch | **prod majors**, plus standalone indirect bumps |
| `uv` /backend | minor + patch | **majors** |

A grouped PR is cheap to merge and expensive to review or revert, which is the wrong
trade for a change that reaches users — so anything shipping a major gets its own PR.
Security updates are never grouped (`applies-to` defaults to version-updates), so an
advisory patch still lands alone and fast.

Measured against this repo with `dependabot/cli` (see `docs/demos/`, #517):

| | ungrouped | grouped |
|---|---:|---:|
| `uv` /backend | 13 PRs | **4** — one group of 13, plus `openai` 2→3, `pytest` 8→9, `pytest-cov` 6→7 |
| `npm` /frontend | ≥33 PRs | **6** — prod group (139), dev group (35), plus 4 solo |

**The npm residue is expected.** `dependency-type` classifies *direct* dependencies
only, so an indirect dep that Dependabot bumps on its own — rather than sweeping it
along with a direct bump — matches neither npm group and gets an individual PR. Three
of npm's four solo PRs were that (`@babel/runtime`, `@rushstack/eslint-patch`,
`@types/semver`; none appear in `package.json`); the fourth, `tailwind-merge` 2→3, is a
genuine prod major behaving as designed. The `uv` group sets no `dependency-type`, so
it has no such residue.

`scripts/test_dependabot_config.py` pins both halves and runs in the `Security Audit`
job. If you widen a group back to majors, that check fails with the reason.

### After every batch: audit for self-closed PRs

**Dependabot sometimes closes its own open PR with a false claim, and nothing surfaces
it.** During the 2026-08-25 sweep, with four PRs all touching
`.github/workflows/build-images.yml`, it closed #504 two minutes after #498 merged:

> Looks like docker/setup-buildx-action is up-to-date now, so this is no longer needed.

`main` still pinned `@v3`. Dependabot deletes the branch on close, so `gh pr reopen`
fails outright — #515 had to be recreated by hand. A self-closed PR is indistinguishable
from an intentionally-declined one, so had nobody re-read the file, the repo would have
silently kept the old pin. The same failure mode applies to a bump patching an advisory.

Grouping makes this much less likely — one PR per ecosystem cannot collide with itself —
but it does not make it impossible, so after any batch of two or more dependency PRs:

```bash
# 1. What did Dependabot close without merging in the last day?
gh pr list --state closed --author "app/dependabot" --limit 30 \
  --json number,title,closedAt,mergedAt \
  --jq '.[] | select(.mergedAt == null) | "#\(.number) \(.closedAt)  \(.title)"'

# 2. For each, confirm on main that the bump actually landed.
git fetch origin main && git show origin/main:<file> | grep <dependency>
```

Anything closed-but-not-merged whose version is still old on `main` was lost. Recreate it
as a fresh PR — the original branch is gone.

## Backend Dependency Updates

`backend/requirements.txt` is a **generated export** of `uv.lock`. Nothing that ships
installs from it — the Dockerfile, CI and the deploy all run `uv sync` — it exists for
tooling that cannot read a lock (`scripts/run-test-suite.js`,
`scripts/validate-test-environment.js`). The `Security Audit` job fails if it drifts
from the lock.

Since #512, `.github/dependabot.yml` hides the export from Dependabot's **update
scans** (`exclude-paths`). It does not hide it from the dependency graph, so alerts
still attribute advisories to it. Two consequences:

1. **A Dependabot backend PR that bumps a dependency leaves the export stale.**
   Regenerate it on the PR branch and push — the failing check prints this command:
   ```bash
   cd backend && uv export --all-extras --no-emit-project --no-hashes \
     --format requirements-txt -o requirements.txt
   ```
   Push it yourself rather than letting a bot do it: GitHub's recursion guard means a
   `GITHUB_TOKEN` push creates no new workflow run, so a bot-pushed commit leaves the
   required checks un-run on the new head and needs a manual re-run to unblock.

2. **Routine transitive bumps are yours to make by hand.** With the export out of
   scope, Dependabot *version* updates only cover what `pyproject.toml` declares. Its *security* updates do reach
   lockfile-only dependencies — and with the export hidden they must now write to
   `uv.lock`, which is the point: before #512 an advisory on a transitive produced a
   PR editing the export alone, structurally unmergeable and patching nothing.
   Transitive advisories also surface in CI regardless — `scripts/audit_gate.py` fails
   on any advisory absent from `security-baseline.json`. To bump one yourself:
   ```bash
   cd backend
   uv lock --upgrade-package <name>            # or: uv add "<name>>=<fixed-version>"
   uv export --all-extras --no-emit-project --no-hashes \
     --format requirements-txt -o requirements.txt
   uv sync --extra test && uv run pytest tests/
   ```
   Never edit `requirements.txt` alone — it changes nothing that is installed.

## Documentation Requirements

**ALL implementation documentation MUST remain synchronized with the codebase**:

1. **API Documentation**:
   - Update OpenAPI specifications when endpoints change
   - Document all request/response schemas
   - Include example requests and responses
   - Document error responses and status codes

2. **Code Documentation**:
   - Python: Docstrings for all public functions, classes, and modules
   - TypeScript: JSDoc comments for complex functions and components
   - Update inline comments when implementation changes
   - Remove outdated comments immediately

3. **Implementation Documentation**:
   - Update relevant sections in CLAUDE.md file
   - Update IMPLEMENTATION_PLAN.md when scope changes
   - Keep architecture diagrams current
   - Update configuration examples when defaults change
   - Document breaking changes prominently

4. **README Updates**:
   - Keep feature lists current
   - Update setup instructions when dependencies change
   - Maintain accurate command examples
   - Update version compatibility information

5. **Decision Records**:
   - Create architecture decision records for significant changes
   - Document technical choices and trade-offs
   - Update bd issue descriptions with implementation notes

## Feature Completion Checklist

Before marking ANY feature as complete, verify:

- [ ] All tests pass (backend and frontend)
- [ ] Code coverage meets 85% minimum threshold
- [ ] Coverage report reviewed for meaningful test quality
- [ ] Code formatted and linted (ruff, ESLint)
- [ ] Type checking passes (mypy for Python, tsc for TypeScript)
- [ ] All changes committed with conventional commit messages
- [ ] All commits pushed to remote repository
- [ ] E2E test added for user-facing changes (all five coverage requirements above)
- [ ] bd issue closed with the PR number
- [ ] API documentation updated (if applicable)
- [ ] Implementation documentation updated
- [ ] Inline code comments updated or added
- [ ] CLAUDE.md updated (if new patterns introduced)
- [ ] Breaking changes documented
- [ ] Security considerations reviewed
- [ ] Performance impact assessed
- [ ] CI/CD pipeline passes

## Rationale

These standards ensure:
- **Quality**: High test coverage and pass rates prevent regressions
- **Traceability**: Git commits and Backlog integration provide clear history of changes
- **Maintainability**: Current documentation reduces onboarding time and prevents knowledge loss
- **Collaboration**: Pushed changes and task management enable team visibility and code review
- **Reliability**: Consistent quality gates maintain production stability

**Enforcement**: AI agents should automatically apply these standards to all feature development tasks without requiring explicit instruction for each task.
