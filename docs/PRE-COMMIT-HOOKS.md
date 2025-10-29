# Pre-Commit Hooks Setup

**Status**: ✅ Active
**Last Updated**: 2025-10-24

---

## Overview

This project uses [pre-commit](https://pre-commit.com/) to automatically check for common issues before commits are accepted. This prevents accidental commits of secrets, malformed files, and other problems.

## What Gets Checked

Every time you commit, the following checks run automatically:

### Security Checks ✅
- **Gitleaks**: Scans for hardcoded secrets (API keys, passwords, tokens)
- **Private Key Detection**: Prevents committing SSH private keys
- **.env File Prevention**: Blocks `.env` files (except `.env.example`)
- **Large File Detection**: Prevents files over 1MB

### Code Quality Checks ✅
- **Trailing Whitespace**: Automatically removes trailing spaces
- **End of File**: Ensures files end with a newline
- **Merge Conflicts**: Detects unresolved merge conflict markers
- **JSON/YAML/TOML Validation**: Ensures structured files are valid
- **Python Syntax**: Validates Python files parse correctly
- **Debug Statements**: Catches forgotten `pdb` or `ipdb` statements

### Workflow Checks ✅
- **Direct Commits to main/master**: Warns against committing directly to protected branches
- **Unstaged Changes Warning**: Reminds you about unstaged files

---

## Installation

### For This Project (Already Done ✅)

Pre-commit hooks are already installed in this repository. Nothing to do!

### For Other/New Projects

```bash
# Install pre-commit globally (if not already installed)
pipx install pre-commit

# In your project directory
pre-commit install

# (Optional) Run against all files
pre-commit run --all-files
```

### Automatic Installation in All New Repos

Pre-commit is configured globally to install automatically in all new/cloned repositories:

```bash
# Already configured globally for your user
git config --global init.templateDir '~/.git-template'
```

This means:
- ✅ Every new `git init` will have pre-commit hooks
- ✅ Every `git clone` will have pre-commit hooks (if `.pre-commit-config.yaml` exists)

---

## Usage

### Normal Commits

Just commit as usual - the hooks run automatically:

```bash
git add file.py
git commit -m "feat: add new feature"
# Hooks run automatically ✅
```

### If a Hook Fails

**Example: Secret detected**
```bash
$ git commit -m "fix: update config"
Detect secrets with gitleaks.............................................Failed
❌ Found hardcoded secret in config.py:
    aws_secret = "(redacted secret value)"
```

**What to do:**
1. Remove the secret from the file
2. Store it in `.env.local` or environment variable
3. Update code to read from environment
4. Try committing again

### Skip Hooks (Use Sparingly!)

**Only use this if you know what you're doing:**

```bash
# Skip all pre-commit hooks
git commit --no-verify -m "your message"

# Or use the alias
git commit-force -m "your message"
```

**⚠️ Warning**: Skipping hooks bypasses all security checks!

---

## Helpful Git Aliases

These aliases are configured globally to help with safer commits:

```bash
# Show status before committing
git c            # Instead of: git commit

# Show staged diff before committing
git cm "message" # Instead of: git commit -m "message"

# Show status before adding
git a file.py    # Instead of: git add file.py

# Review changes before pushing
git p            # Instead of: git push

# Quick status view
git s            # Instead of: git status

# Show what will be committed
git staged       # Instead of: git diff --cached
```

---

## For AI Assistants (Warp/Claude Code)

### Best Practices When Making Commits

1. **Always review before committing:**
   ```bash
   git status
   git diff --staged
   ```

2. **Don't use `git add -A` blindly:**
   ```bash
   # BAD: Stages everything without review
   git add -A

   # GOOD: Stage specific files
   git add file1.py file2.py

   # GOOD: Use the alias to see what's being staged
   git a file1.py file2.py
   ```

3. **Verify staged changes:**
   ```bash
   # Before committing, check what's staged
   git staged
   ```

4. **If hooks fail, understand why:**
   - Don't immediately use `--no-verify`
   - Read the error message
   - Fix the underlying issue
   - Commit again

5. **Never commit secrets:**
   - Use environment variables
   - Use `.env.local` (already in `.gitignore`)
   - Use secret management tools

### Quick Checklist for AI Commits

- [ ] Run `git status` to see what will be staged
- [ ] Stage only relevant files
- [ ] Run `git staged` to review changes
- [ ] Ensure no secrets in diff
- [ ] Commit with descriptive message
- [ ] If hooks fail, fix the issue (don't skip)

---

## Configuration

The configuration is in `.pre-commit-config.yaml` at the project root.

### Update Hook Versions

```bash
# Auto-update to latest versions
pre-commit autoupdate

# Migrate deprecated stage names
pre-commit migrate-config
```

### Run Hooks Manually

```bash
# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run gitleaks --all-files

# Run on specific files
pre-commit run --files file1.py file2.py
```

### Temporarily Disable a Hook

Edit `.pre-commit-config.yaml` and comment out the hook:

```yaml
# - repo: https://github.com/gitleaks/gitleaks
#   rev: v8.18.1
#   hooks:
#     - id: gitleaks
```

---

## Troubleshooting

### Hook Fails on Clean File

**Problem**: Hook fails but the file looks fine

**Solution**: Check for hidden issues:
```bash
# Check for trailing whitespace
cat -A file.py

# Check file encoding
file file.py

# Run specific hook with verbose output
pre-commit run gitleaks --files file.py --verbose
```

### Hooks Take Too Long

**Problem**: Commits are slow due to hooks

**Solution**:
- Most hooks should complete in <5 seconds
- Gitleaks may take 10-20 seconds on first run (caches after)
- If consistently slow, check hook configuration

### Can't Commit After Incident

**Problem**: Old secrets triggering hook even after removal

**Solution**:
```bash
# Clear git cache
git rm --cached -r .
git add .

# Or skip hooks for that commit (if certain it's clean)
git commit --no-verify
```

---

## Related Documentation

- [Security Incident Report](../claudedocs/SECURITY-INCIDENT-2025-10-18.md) - Past security incident and lessons learned
- [GitHub Actions Workflows](../.github/workflows/) - CI/CD pipelines also run security checks
- [.gitignore](../.gitignore) - Files excluded from git

---

## Additional Resources

- [Pre-commit Documentation](https://pre-commit.com/)
- [Gitleaks Documentation](https://github.com/gitleaks/gitleaks)
- [Git Hooks Documentation](https://git-scm.com/docs/githooks)

---

**Remember**: Pre-commit hooks are your first line of defense against accidental security issues. They catch problems before they reach git history!
