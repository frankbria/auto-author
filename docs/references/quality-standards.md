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
| `npm` /frontend `frontend-dev` | dev deps, **majors included** | — |
| `npm` /frontend `frontend-build` | `tailwindcss`, `postcss`, `autoprefixer` minor + patch | **their majors** |
| `npm` /frontend `frontend-prod` | prod minor + patch | **prod majors**, and `better-auth` always |
| `uv` /backend | minor + patch | **majors** |

A grouped PR is cheap to merge and expensive to review or revert, which is the wrong
trade for a change that reaches users — so anything shipping a major gets its own PR.

**The line is what a package ships, not which manifest section it sits in (#555).**
`tailwindcss`, `postcss` and `autoprefixer` live in `devDependencies` and generate the
CSS bundle every user downloads, so they get the production treatment despite the
classification — `tailwindcss` 3 → 4 otherwise rides into a batch on the same footing as
an eslint bump, which is what happened in #548. `frontend-dev` keeps its majors because
eslint and jest genuinely ship nothing *and* are peer-coupled: measured, `eslint` 8 → 10,
`eslint-config-next` 15 → 16 and `@typescript-eslint/{parser,eslint-plugin}` 6 → 8 each
fail `npm install` alone and only resolve together. Forcing them solo would strand four
permanently-unmergeable PRs.

**A blocked major belongs in `ignore`, not left to churn.** A major that cannot install
reopens every sweep, holds one of the five PR slots, and — while it sits inside a group —
takes the whole batch down with it. `typescript` (#514) and `tailwindcss` (#513) are
ignored at semver-major for exactly this reason; each entry names the issue whose
closure removes it. Check that list before assuming a bump is not being offered.
Security updates are never grouped (`applies-to` defaults to version-updates), so an
advisory patch still lands alone and fast.

Measured on the first live sweep after #517 landed (2026-08-26), which supersedes the
pre-merge `dependabot/cli` estimates in `docs/demos/` — those used a more permissive job
config and overcounted:

| | before | after |
|---|---:|---:|
| open Dependabot PRs | 10, all ungrouped | **5** |

The five: an `actions` group, a `backend` group carrying 10 updates, a `frontend-prod`
group carrying 26 — and `openai` 2.45.0 → 3.0.0 plus `pytest` 8.4.1 → 9.1.1 each on their
own, which is the design working.

**A note on `dependency-type`:** it classifies *direct* dependencies only. That has no
practical effect here, because Dependabot only opens PRs for direct npm dependencies in
the first place — a pre-merge harness run suggested an "indirect residue" of extra solo
PRs, but that was an artefact of running the job with `allowed-updates: all`, and the
live sweep produced none. The `uv` group sets no `dependency-type` at all.

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

## Staging secrets

Application secrets live in `/opt/auto-author/.env` **on the box**, not in GitHub.

**One exception, and it is the one that matters:** `MONGODB_URI` is synced from the
`staging` environment secret by `.github/workflows/sync-staging-env.yml`
(`workflow_dispatch`). Update the GitHub secret, dispatch that workflow, and it writes
the key, recreates the containers and verifies the credential end-to-end.

Every **other** key in that file — `AWS_*`, `CLOUDINARY_*`, `SENTRY_DSN`, and the rest of
the 26 — exists only on the box. Nothing in CI writes them. Editing a GitHub secret with
one of those names changes nothing that runs.

That asymmetry is deliberate. A whole-file render from GitHub secrets would delete the
keys that have no secret, and would let a *stale* secret overwrite a newer value on the
box — turning the sync into an outage source. Add a key to the workflow only when there
is a specific need, and only after confirming the box's value is not the newer one.

### Why this exists

Before #537, no workflow wrote that file at all. A rotated `MONGODB_URI` was pushed to
the GitHub secret, the secret's `updated_at` duly changed, and the running containers
kept the old credential — indistinguishable, from the outside, from a rotation that had
simply not worked. Staging was down for six days.

**Compose injects env at container *creation*.** A `restart` keeps the old values; only
`up -d --force-recreate` picks up an edited `.env`. The workflow does this for you.

## Backend Dependency Updates

`uv.lock` is the single source of truth. The Dockerfile, CI and the deploy all run
`uv sync`, so a bump is complete once `pyproject.toml` and `uv.lock` are updated — there
is nothing to regenerate afterwards.

**#534 removed `backend/requirements.txt`.** It was a generated export of `uv.lock` that
nothing installed from, kept for "tooling that cannot read a lock" that turned out not to
exist: the two scripts named as its consumers were unwired and both failed against the
current repo. It cost a manual `uv export` on every backend dependency PR (the export went
stale the moment the lock moved, and a CI step policed the drift), and the dependency graph
counted it as a second manifest, so advisories were reported twice. Deleting it took the
regen, the `requirements.txt matches uv.lock` CI step, the `exclude-paths` entry in
`.github/dependabot.yml` and the duplicate alerts with it.

Two things that follow:

1. **A Dependabot backend PR is now mergeable as it arrives.** No regen step, so nothing
   has to be pushed to the branch by hand. (Historical note: a bot could not have pushed
   the regen anyway — GitHub's recursion guard means a `GITHUB_TOKEN` push creates no new
   workflow run, leaving required checks un-run on the new head.)

2. **Routine transitive bumps are still yours to make by hand.** Dependabot *version*
   updates only cover what `pyproject.toml` declares; its *security* updates do reach
   lockfile-only dependencies and write to `uv.lock`. Transitive advisories surface in CI
   regardless — `scripts/audit_gate.py` fails on any advisory absent from
   `security-baseline.json`. To bump one yourself:
   ```bash
   cd backend
   uv lock --upgrade-package <name>            # or: uv add "<name>>=<fixed-version>"
   uv sync --extra test && uv run pytest tests/
   ```

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
