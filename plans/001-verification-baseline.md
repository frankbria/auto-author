# Plan 001: A single command runs the whole test suite, and all backend tests are discoverable

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat e6980f3..HEAD -- package.json backend/pytest.ini backend/test_chapter_tabs_api.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: tests / dx
- **Planned at**: commit `e6980f3`, 2026-06-21
- **Issue**: https://github.com/frankbria/auto-author/issues/85

## Why this matters

There is no single command that tells a developer or CI whether the repo is
healthy. The root `package.json` `test` script is hardcoded to fail, and
several `test_*.py` files sit in `backend/` root where pytest (configured with
`testpaths = tests`) never discovers them — so ~1,350 lines of tests never
run and silently rot. A reliable, one-command verification baseline is a
prerequisite for every other plan in this set: an executor making a risky
change (e.g. plan 008, the cascade-delete refactor) needs a trustworthy
"is it green?" gate. This plan establishes that gate. It does **not** try to
raise coverage or fix failing tests — only to make the existing suite
runnable and discoverable.

## Current state

- `package.json:10` (repo root) — the only test script is a deliberate failure:
  ```json
  "scripts": {
    "test": "echo \"Error: no test specified\" && exit 1"
  },
  ```
- `backend/pytest.ini:1-6` — pytest only discovers tests under `tests/`:
  ```ini
  [pytest]
  testpaths = tests
  python_files = test_*.py
  python_classes = Test*
  python_functions = test_*
  pythonpath = .
  ```
- Loose test/validation files in `backend/` root that pytest never runs:
  `test_chapter_tabs_api.py`, `test_config.py`, `test_draft_generation_api.py`,
  `test_file_upload_service.py`, `test_services_isolated.py`,
  `test_services_summary.py`, `test_toc_transactions.py`,
  `validate_chapter_tabs.py`, `quick_validate.py`, `simple_validate.py`.
- Working per-component commands that already exist (verified):
  - Backend unit tests: `cd backend && uv run pytest tests/`
  - Frontend unit tests: `cd frontend && npm test`
  - Frontend typecheck: `cd frontend && npm run typecheck`
  - Frontend lint: `cd frontend && npm run lint`
- Repo convention: utility scripts live in `scripts/` (the directory exists at
  repo root). Backend uses `uv` for env/deps; frontend uses `npm`.

## Commands you will need

| Purpose            | Command                                   | Expected on success |
|--------------------|-------------------------------------------|---------------------|
| Backend deps       | `cd backend && uv sync`                   | exit 0              |
| Backend tests      | `cd backend && uv run pytest tests/`      | collection + run completes |
| Frontend deps      | `cd frontend && npm install`              | exit 0              |
| Frontend tests     | `cd frontend && npm test`                 | run completes       |
| Run new aggregate  | `bash scripts/test-all.sh`                | runs both suites    |

## Scope

**In scope** (the only files you should create/modify):
- `scripts/test-all.sh` (create)
- `package.json` (root — edit the `test` script only)
- The loose `backend/test_*.py` files listed above (move into `backend/tests/`)

**Out of scope** (do NOT touch):
- The contents/assertions of any test file — this plan relocates and wires up,
  it does not rewrite tests or fix failures.
- `backend/pytest.ini` test-discovery globs — leave `testpaths = tests`.
- Frontend Playwright/E2E config — E2E stays out of the aggregate script (too
  slow for the default gate).
- `validate_*.py`, `quick_validate.py`, `simple_validate.py` — these are ad-hoc
  scripts, not pytest tests; leave them where they are (plan 006 handles repo
  hygiene).

## Git workflow

- Branch: `advisor/001-verification-baseline`
- Conventional commits (repo style — see `git log`: `fix:`, `feat:`, `test:`,
  `chore:`). Example: `chore: add repo-wide test-all script and wire root test`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Relocate loose backend test files into the discovered directory

Move each loose pytest file from `backend/` into `backend/tests/` so pytest
discovers it. Use `git mv` to preserve history:

```
cd backend
git mv test_chapter_tabs_api.py tests/test_chapter_tabs_api.py
git mv test_config.py tests/test_config.py
git mv test_draft_generation_api.py tests/test_draft_generation_api.py
git mv test_file_upload_service.py tests/test_file_upload_service.py
git mv test_services_isolated.py tests/test_services_isolated.py
git mv test_services_summary.py tests/test_services_summary.py
git mv test_toc_transactions.py tests/test_toc_transactions.py
```

If a file with the same name already exists in `backend/tests/`, do NOT
overwrite it — STOP and report the collision (see STOP conditions).

**Verify**: `cd backend && ls test_*.py 2>/dev/null | wc -l` → `0`
(no loose test files remain in backend root).

### Step 2: Confirm the relocated tests are now collected

Collection may surface import errors in the moved files (they previously ran,
if ever, from a different working directory). Run collection only:

**Verify**: `cd backend && uv run pytest tests/ --collect-only -q` → exits
without a collection error, and the moved test modules appear in the listing.
If a moved file raises a collection/import error, that is expected fallout of
relocation — STOP and report the specific import error (do not edit the test
to fix it; that is out of scope and the reviewer will decide).

### Step 3: Create the aggregate test script

Create `scripts/test-all.sh` with this exact content:

```bash
#!/usr/bin/env bash
# Repo-wide verification gate. Runs backend + frontend unit suites.
# E2E (Playwright) is intentionally excluded — too slow for the default gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== Backend tests =="
(cd "$ROOT/backend" && uv run pytest tests/)

echo "== Frontend tests =="
(cd "$ROOT/frontend" && npm test -- --watchAll=false)

echo "== All suites completed =="
```

Make it executable: `chmod +x scripts/test-all.sh`

**Verify**: `test -x scripts/test-all.sh && echo OK` → `OK`

### Step 4: Wire the root `test` script to the aggregate

In root `package.json`, replace the `test` script. Change:

```json
    "test": "echo \"Error: no test specified\" && exit 1"
```

to:

```json
    "test": "bash scripts/test-all.sh"
```

**Verify**: `node -e "console.log(require('./package.json').scripts.test)"` →
`bash scripts/test-all.sh`

### Step 5: Run the aggregate end to end

**Verify**: `npm test` from the repo root → both suites execute. The suites
may report pre-existing test failures — that is acceptable for this plan
(fixing them is not in scope). What must be true: the script runs the backend
suite, then the frontend suite, without the old `exit 1` short-circuit. If the
script aborts before reaching the frontend suite because the backend suite has
failing tests, note that in your report (the `set -e` behavior) — see
Maintenance notes.

## Test plan

No new application tests. Verification is the wiring itself:
- `npm test` from root invokes `scripts/test-all.sh`.
- `cd backend && uv run pytest tests/ --collect-only -q` lists the 7 relocated
  modules.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `ls backend/test_*.py 2>/dev/null | wc -l` → `0`
- [ ] `cd backend && uv run pytest tests/ --collect-only -q` exits without a
      collection error and lists the relocated modules
- [ ] `test -x scripts/test-all.sh` succeeds
- [ ] `node -e "console.log(require('./package.json').scripts.test)"` prints
      `bash scripts/test-all.sh`
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- A relocated filename collides with an existing file in `backend/tests/`.
- A moved test file raises a collection/import error after relocation (report
  the error; do not edit the test).
- The backend suite cannot be collected at all (environment/`uv` problem).
- The `package.json` `test` script no longer matches the excerpt above
  (drift).

## Maintenance notes

- `set -e` in `test-all.sh` means a failing backend suite stops the script
  before the frontend suite runs. That is intentional for a gate, but if the
  team wants both suites to always run and report independently, switch to
  collecting exit codes and exiting non-zero at the end. Deferred — out of
  scope here.
- E2E is deliberately excluded. If a "full" gate is wanted later, add a
  `scripts/test-all-e2e.sh` rather than slowing the default `npm test`.
- Reviewer should confirm the relocated tests don't depend on a
  `backend/`-root working directory (relative paths to fixtures/data).
