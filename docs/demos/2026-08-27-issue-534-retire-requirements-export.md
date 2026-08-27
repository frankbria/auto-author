# Demo — #534 Retire `backend/requirements.txt`

**Date:** 2026-08-27 · **Issue:** #534 · **PR:** #552

#534 asked for a decision and gated it on evidence:

> Option 1 is the likely answer, but it turns on whether those two scripts are alive.
> **Establish that first — do not delete on the assumption.**

So AC1 is discharged by *running* the scripts, not by reading them.

---

## AC1 — Are `run-test-suite.js` / `validate-test-environment.js` used, and do they still run? ✅ **No, and no.**

### Used by anyone? No.

```console
$ grep -rn "run-test-suite\|validate-test-environment" . --exclude-dir=node_modules --exclude-dir=.git
scripts/run-test-suite.js:173:      const ValidatorClass = require('./validate-test-environment.js');
docs/references/quality-standards.md:183: ... tooling that cannot read a lock (`scripts/run-test-suite.js`,
docs/testing/final-integration-guide.md:50,53,56 ...

$ python3 -c "import json;print(json.load(open('package.json'))['scripts'])"
{'test': 'bash scripts/test-all.sh'}
```

One requires the other; the rest are docs telling a human to run them by hand. The only
wired entrypoint, `scripts/test-all.sh`, runs `uv run pytest` and `npm test` and touches
neither.

### Still run? No — **both exit 1 against a healthy repo.**

`validate-test-environment.js`:

```console
$ node scripts/validate-test-environment.js ; echo "EXIT=$?"
✓ Successes: 26     ❌ Errors: 6

❌ Critical Issues to Fix:
1. ✗ Missing Accessibility testing dependency: axe-playwright
2. ✗ Missing Jest configuration: frontend/jest.config.js
3. ✗ Missing Interview prompts E2E test: frontend/src/e2e/interview-prompts.spec.ts
4. ✗ Missing Test suite workflow: .github/workflows/test-suite.yml
5. ✗ Missing Staging deployment workflow: .github/workflows/deploy-staging.yml
6. ✗ Missing Production deployment workflow: .github/workflows/deploy-production.yml
EXIT=1
```

Every one of those six is the **script** being stale, not the repo being broken: jest is
configured elsewhere, E2E lives in `frontend/tests/e2e/`, CI is `tests.yml`, and the two
deploy workflows were retired at the container cutover (#484). It reports **failure against
a perfectly healthy tree** — worse than useless, because a human following it would go
hunting for six non-problems.

`run-test-suite.js`:

```console
$ node scripts/run-test-suite.js quick ; echo "EXIT=$?"
INFO: Running frontend unit tests...
Test Suites: 133 passed, 133 total     Tests: 2288 passed
INFO: Running backend unit tests...
INFO: Executing: python -m pytest tests/ -x --tb=short -q
ImportError while loading conftest '.../backend/tests/conftest.py'.
E   ModuleNotFoundError: No module named 'pymongo'

📊 Backend Tests:  Unit Tests: ❌ FAILED
EXIT=1
```

It shells to **system `python`** in a `uv`-managed project. The very same suite:

```console
$ cd backend && uv run pytest tests/ -q
1236 passed, 9 skipped in 126.63s
```

### Neither actually depends on the export

- the validator **greps** it for three strings (`pytest`, `locust`, `faker`);
- the runner's `pip install -r requirements.txt` sits inside a `try/catch` that downgrades
  failure to `WARNING` and carries on.

**Conclusion:** the *"tooling that cannot read a lock"* `DEPLOYMENT.md` invoked does not
exist. Option 3 is factually excluded; Option 2 would automate a regen for a file with no
reader.

---

## AC2 — Decision recorded, with the reason ✅

**Option 1 — delete the export.** Recorded on #534 with the evidence above.

---

## AC3 — The export, the CI step, the scripts, their docs, and `exclude-paths` + its test go together ✅

```console
$ git diff --stat origin/main...HEAD
 .github/dependabot.yml                  |  21 ---     <- exclude-paths block
 .github/workflows/tests.yml             |  33 ---     <- sync-gate step
 backend/requirements.txt                | 268 ---     <- the export
 scripts/run-test-suite.js               | 312 ---     <- dead script
 scripts/validate-test-environment.js    | 279 ---     <- dead script
 scripts/test_dependabot_config.py       |  ...        <- pinning test out, tripwire in
 docs/testing/final-integration-guide.md |  ...        <- their docs section
 ...
```

---

## The point of the change: the regen tax, measured on a real PR

Not simulated. **Dependabot PR #527** (`pytest` 8.4.1 → 9.1.1) is open right now and touches
only `backend/pyproject.toml` + `backend/uv.lock` — never the export. That *is* the drift.

### Before — on `main`, running the old gate verbatim from `tests.yml`

```console
$ git checkout <#527 head> && cd backend
$ grep -m1 "^pytest==" requirements.txt          # the export
pytest==8.4.1
$ grep -A1 'name = "pytest"$' uv.lock            # what is actually pinned
version = "9.1.1"

$ uv export --all-extras --no-emit-project --no-hashes --format requirements-txt > /tmp/raw
$ diff -u <(grep -v '^#    uv export' requirements.txt) <(grep -v '^#    uv export' /tmp/raw)
-pytest==8.4.1
+pytest==9.1.1
::error:: backend/requirements.txt is out of sync with uv.lock   -> exit 1
```

Red until a human checks out the bot's branch, runs `uv export`, and pushes.

### After — same bump applied to this branch

```console
$ git worktree add --detach wt feat/534-retire-requirements-export
$ cd wt && git apply <#527 diff>

$ ls backend/requirements.txt
ls: cannot access 'backend/requirements.txt': No such file or directory

$ grep -c "requirements.txt matches uv.lock" .github/workflows/tests.yml
0

$ grep -A1 'name = "pytest"$' backend/uv.lock
version = "9.1.1"

$ git status --short          # what a human still has to regenerate
 M backend/pyproject.toml
 M backend/uv.lock            # ... nothing. Only what Dependabot itself changed.
```

| | `main` | this branch |
|---|---|---|
| export present | yes, pinning `pytest==8.4.1` | **absent** |
| sync gate | **exit 1** on the drift | step does not exist |
| files a human must regenerate | `requirements.txt` | **none** |

---

## The tripwire, mutation-verified

Deleting the export removed *every* check that would notice it returning — the gate step,
`exclude-paths`, and the test pinning that exclusion all went with it. It comes back the
moment someone runs the `uv export` command still quoted in older CHANGELOG and demo
entries, and Dependabot would parse it as a manifest again, reviving #512's unmergeable
transitive-only PRs with nothing failing to say so.

```console
$ uvx --with pytest --with pyyaml pytest scripts/ -q          # baseline
35 passed, 1 skipped

$ echo "# mutation probe" > backend/requirements.txt          # break the invariant
$ uvx ... pytest scripts/ -k stays_deleted -q
FAILED test_the_generated_requirements_export_stays_deleted
1 failed

$ rm backend/requirements.txt                                 # revert
$ uvx ... pytest scripts/ -k stays_deleted -q
1 passed
```

RED when the file is back, GREEN when it is not — so the guard tests the thing it claims to.

---

## Verdict

**All acceptance criteria hold.** AC1 was settled by running both scripts rather than
reading them; AC3's removals landed as one set; and the change's purpose — killing the
per-PR regen tax — is demonstrated against a real open Dependabot PR rather than a
hypothetical.

## Known limitations

- **Inert `.tbd` / `.yml.disabled` workflows still say `pip install -r requirements.txt`.**
  None execute (none are `.yml`) and they already target the PM2 path retired in #484.
  **#520** owns retiring them; fixing them here would widen this PR into that issue.
- **Historical records are left as written.** `docs/CHANGELOG.md`, `docs/demos/*` and
  `archive/` still describe the export as live because they were accurate when written.
  Only live runbooks were updated — six of them, across `docs/testing/`, which would
  otherwise have told a human to install from a deleted file.
- **`pytest` 9.1.1 was applied only to demonstrate the gate**, in a throwaway worktree. It
  was not run against the suite; whether that major is safe is #527's question, not this one.
