# Demo — #512 Dependabot uv config opens unmergeable no-op PRs

**Date:** 2026-08-25 · **Branch:** `fix/dependabot-uv-transitive-noop` · **PR:** #521

Every acceptance criterion below is demonstrated with **outcome** evidence — what
Dependabot actually proposes — not "the YAML parses".

The harness is the real thing: `dependabot/cli` driving the published
`ghcr.io/dependabot/dependabot-updater-uv` image
(`sha256:4555a667…`) against `frankbria/auto-author`, `/backend`. Two runs, identical
source tree, differing only in the job's `exclude-paths`. (The updater never reads
`.github/dependabot.yml` — GitHub parses that and passes the result into the job — so
putting `exclude-paths` in the job file tests exactly what the config change will do.)

```bash
dependabot update -f job-before.yml   # no exclude-paths  == today's main
dependabot update -f job-after.yml    # exclude-paths: ["requirements.txt"]
```

---

## AC1 — A transitive bump either updates pyproject/uv.lock, or is not opened at all

Counting every `create_pull_request` the updater emitted, grouped by the files that
PR would change:

| files the PR would change | BEFORE | AFTER |
|---|---:|---:|
| `requirements.txt` only — **no-op, changes nothing installed** | **35** | **0** |
| `pyproject.toml` + `uv.lock` | 2 | 16 |
| `pyproject.toml` + `uv.lock` + `requirements.txt` | 14 | 0 |
| **total proposed PRs** | **51** | **16** |

The 35 export-only proposals include all three that had to be closed by hand in the
2026-08-25 sweep — `flask-cors` (#499), `tqdm` (#503), `pydantic-core` (#505) — plus
`annotated-doc`, `annotated-types`, `botocore`, `certifi`, `cffi`,
`charset-normalizer`, `click`, `coverage`, `dnspython`, `gevent`, `geventhttpclient`,
`idna`, `iniconfig`, `jiter`, `jmespath`, `lxml`, `markupsafe`, `packaging`, `psutil`,
`pycparser`, `pygments`, `python-engineio`, `pywin32`, `pyzmq`, `s3transfer`,
`sentry-sdk`, `typing-extensions`, `typing-inspection`, `tzdata`, `websocket-client`,
`wsproto`, `zope-interface`.

✅ **Outcome:** export-only no-op PRs go **35 → 0**, while the 16 real bumps survive
unchanged. Nothing that mattered was suppressed.

---

## AC1b — Why `allow: dependency-type: direct` (issue option 2) would not have worked

Worth recording, because it was the issue's stated fallback. The job already runs with
`"update-subdependencies": false` — visible in the updater's own job dump — and it
produced those 35 proposals anyway. Dependabot classifies a pinned line in
`requirements.txt` as a **direct** requirement of that file, regardless of the `# via`
provenance comment `uv export` writes above it. Filtering on dependency type could not
have separated them; removing the file from view is what does.

---

## AC2 — No backend Dependabot PR lands with `Security Audit` red

Stated precisely, because the measurement changes the shape of the claim rather than
just confirming it.

**Before:** the 35 export-only PRs were *structurally* red — the sync gate rejects an
export that disagrees with the lock, and there was no commit that could fix them short
of rewriting the PR. They could only be closed.

**After:** the 16 surviving PRs touch `pyproject.toml` + `uv.lock` and **do not**
update the export (see the table — `('pyproject.toml', 'uv.lock')`, no third file), so
the gate opens red and is cleared by one command on the branch:

```bash
cd backend && uv export --all-extras --no-emit-project --no-hashes \
  --format requirements-txt -o requirements.txt
```

Verified locally: that command reproduces the committed export byte-for-byte (`diff`
clean, filtering uv's self-referential output-path comment exactly as CI does).

✅ **Outcome:** red-and-unfixable becomes red-and-fixable-in-one-command. That is a
real trade, not a free win, and the measurement sizes it honestly: a full sweep asks
for the regen on up to 16 PRs rather than 0. `open-pull-requests-limit: 5` caps how
many are live at once, and #517 (Dependabot grouping) is the lever that would collapse
them into one PR and one regen.

The automated alternative was discarded before being built: GitHub's recursion guard
means a `GITHUB_TOKEN` push creates no new workflow run, so a bot that pushed the
regenerated export would leave the required checks un-run on the new head commit,
needing a manual re-run or a separate token to unblock — worse than the manual command
it replaces.

---

## AC3 — Manual procedure documented

`docs/references/quality-standards.md` → **Backend Dependency Updates**: the regen
command above, why a bot must not push it, and the manual transitive-bump procedure
(`uv lock --upgrade-package` → re-export → `uv sync --extra test && uv run pytest`).
`CLAUDE.md` carries a one-line pointer under Quality gates.

---

## AC4 — Verified by observing a live Dependabot run

**Not closed by this PR.** The `uv` ecosystem is on a weekly schedule, so a real
scheduled sweep lands after merge. The runs above are the closest available substitute
— the same updater image, the same repository, the same job schema — and they exercise
the actual code path rather than inspecting config.

---

## Regression guard

`scripts/test_dependabot_config.py`, written failing first:

```
$ uvx --with pytest --with pyyaml pytest scripts/ -q
31 passed
```

Mutation check — the realistic failure is a repo-relative glob, since `exclude-paths`
patterns resolve against the entry's `directory`:

```
$ sed -i 's|"requirements.txt"|"backend/requirements.txt"|' .github/dependabot.yml
$ uvx --with pytest --with pyyaml pytest scripts/test_dependabot_config.py -q
2 failed
$ git checkout -- .github/dependabot.yml && ... -q
2 passed
```

Without that second test the config would look correct and Dependabot would go on
producing all 35 no-ops.

---

## Known limitation found while verifying

`exclude-paths` scopes **update scans**, not the dependency graph. The export still
registers as a manifest for Dependabot *alerts*, visible today as one advisory
reported twice:

```
medium  pip  pytest  backend/uv.lock           direct
medium  pip  pytest  backend/requirements.txt  unknown
```

That duplication is unchanged by this PR. The same check surfaced a genuine gap in the
audit gate — it scans the production surface only, so a test-extra advisory can never
fail CI — filed as #522.
