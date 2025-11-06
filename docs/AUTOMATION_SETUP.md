# Documentation Automation Setup

**Created**: 2025-11-06
**Status**: Active
**Purpose**: Auto-sync planning documents with bd (Beads) issue tracker

---

## Overview

This project uses **Option A: Automated Export Scripts** to keep planning documentation synchronized with the bd issue tracker.

### What Gets Auto-Synced

- `CURRENT_SPRINT.md` - Current sprint tasks and status (auto-generated from bd)
- ~~`IMPLEMENTATION_PLAN.md`~~ - Deprecated (script has issues, use bd directly)

### How It Works

**Documentation sync happens via pre-commit hooks:**

1. **Pre-commit Hooks** (Local Development Only)
   - Runs on every `git commit`
   - Exports latest bd data to markdown
   - Auto-adds updated files to commit

**Why not GitHub Actions?**
- The `.beads/` database is gitignored (contains local development data)
- GitHub Actions runners don't have access to the database
- Documentation sync must happen locally where the database exists

---

## Setup Instructions

### 1. Install Pre-commit (One-time setup)

```bash
# Install pre-commit tool
pip install pre-commit

# Install git hooks
cd /home/frankbria/projects/auto-author
pre-commit install

# Test the hooks
pre-commit run --all-files
```

### 2. GitHub Actions

**File:**
- `.github/workflows/tests.yml` - Run tests on PR/push

**What Happens:**
- On push to `main`/`develop` or PR: All tests run (frontend, backend, E2E)
- Frontend: lint, typecheck, unit tests, coverage check
- Backend: pytest with coverage
- E2E: Playwright tests with auth bypass

### 3. Normal Development Workflow

```bash
# Make code changes
git add .

# Commit (pre-commit hooks run automatically)
git commit -m "feat: your feature"

# Result: CURRENT_SPRINT.md is auto-updated and included in commit
```

---

## How Pre-commit Hooks Work

**Configuration**: `.pre-commit-config.yaml`

**Hooks that run on every commit:**

1. **export-current-sprint** - Regenerates CURRENT_SPRINT.md from bd
2. **auto-add-exports** - Adds updated docs to commit
3. **frontend-lint** - Lints frontend code (if frontend/ files changed)
4. **frontend-typecheck** - Type checks (if frontend/ files changed)
5. **backend-lint** - Lints backend code (if backend/ files changed)
6. **General quality** - Trailing whitespace, merge conflicts, large files, etc.

**Performance**: Fast! Only linting/type-checking run conditionally.

---

## Bypassing Hooks (Emergency Only)

**Only for true emergencies:**

```bash
# Skip all hooks (emergency hotfix only)
git commit --no-verify -m "hotfix: critical bug"

# Then immediately create follow-up task
bd create "Add tests for emergency hotfix" -p 0 -t bug
```

---

## Troubleshooting

### Pre-commit hooks not running

```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install

# Verify installation
pre-commit run --all-files
```

### Docs out of sync

```bash
# Manually regenerate
./scripts/export-current-sprint.sh

# Check what changed
git diff CURRENT_SPRINT.md

# Commit if needed
git add CURRENT_SPRINT.md
git commit -m "docs: manual sync from bd tracker"
```

### GitHub Actions not running

- Check `.github/workflows/` files exist
- Verify GitHub Actions are enabled in repo settings
- Check Actions tab in GitHub for error logs

---

## What NOT to Do

❌ **Don't manually edit CURRENT_SPRINT.md** - It will be overwritten
❌ **Don't skip hooks without reason** - They ensure quality
❌ **Don't commit directly to main** - Use feature branches
❌ **Don't bypass tests in CI** - They catch bugs before production

✅ **Do use bd commands** - `bd list`, `bd ready`, `bd create`, `bd close`
✅ **Do let hooks run** - They keep docs in sync automatically
✅ **Do use feature branches** - `git checkout -b feature/my-feature`
✅ **Do trust the automation** - It's designed to help, not slow you down

---

## Files Created/Modified

### Created
- `.pre-commit-config.yaml` - Pre-commit hook configuration
- `.github/workflows/sync-docs.yml` - Auto-sync GitHub Action
- `.github/workflows/tests.yml` - Test automation GitHub Action
- `docs/AUTOMATION_SETUP.md` - This file

### Auto-Generated (Don't Edit Manually)
- `CURRENT_SPRINT.md` - Regenerated on every commit
- ~~`IMPLEMENTATION_PLAN.md`~~ - Deprecated due to script issues

### Source of Truth
- **bd database** (`.beads/*.db`) - ALL task data lives here
- Use `bd` commands to view/modify tasks

---

## Maintenance

### Weekly
- Review GitHub Actions logs for failures
- Check docs are syncing correctly

### Monthly
- Update pre-commit hook versions (`.pre-commit-config.yaml`)
- Review and update this documentation

### As Needed
- Add new hooks for new quality checks
- Update GitHub Actions workflows for new test types

---

## Benefits

✅ **Never out of sync** - Docs auto-update on every commit
✅ **No manual work** - Automation handles everything
✅ **Single source of truth** - bd database drives all documentation
✅ **Quality gates** - Linting and type-checking run automatically
✅ **Visible in commits** - Doc changes show in git history
✅ **CI/CD ready** - GitHub Actions enforce standards on PR

---

## Next Steps

1. ✅ Pre-commit hooks installed
2. ✅ GitHub Actions configured
3. ✅ Documentation automation active
4. 📋 **TODO**: Enable E2E tests in pre-commit (once tests are fixed)
5. 📋 **TODO**: Add coverage enforcement to pre-commit (once ≥85% reached)

---

**Questions?** See CLAUDE.md for full development workflow guidelines.
