# Demo — #517 Dependabot grouping + auto-merge

**Date:** 2026-08-26 · **Branch:** `feature/517-dependabot-grouping-automerge` · **PR:** #538

Every acceptance criterion below is demonstrated with **outcome** evidence — what
Dependabot actually proposes, and what the GitHub API actually accepts — not "the YAML
parses".

The harness is the real thing: `dependabot/cli` v1.92.0 driving the published updater
images against `frankbria/auto-author` at `bae440a`:

- `ghcr.io/dependabot/dependabot-updater-uv` (`sha256:1f86f802…`)
- `ghcr.io/dependabot/dependabot-updater-npm` (`sha256:14062a6c…`)

Four runs, identical source tree, differing **only** in the job's `dependency-groups`.
The updater never reads `.github/dependabot.yml` — GitHub parses that and passes the
result into the job — so putting the groups in the job file tests exactly what the
config change will do.

```bash
dependabot update -f uv-before.yml    # no groups  == today's main
dependabot update -f uv-after.yml     # dependency-groups: backend (minor+patch)
dependabot update -f npm-before.yml   # no groups  == today's main
dependabot update -f npm-after.yml    # dependency-groups: frontend-dev, frontend-prod
```

Both `-before` jobs carry the same `cooldown`, `ignore-conditions` and `exclude-paths`
as production, so the only variable is grouping.

† **The ungrouped npm figure is a floor, not a total.** That run had emitted 33
`create_pull_request` events when it wedged on a single
`npm install @typescript-eslint/parser@8.67.0 --force` — 51 minutes at ~197% CPU with no
further updater output — and was killed. The ungrouped path runs one such install *per
dependency* across ~200 packages, so the true total is higher and unknown; the grouped
run over the same tree finished in ~26 minutes. Direction and magnitude are unambiguous
either way, so the run was not retried. (`npm-after` also ended non-zero: one dependency,
`fast-uri`, failed with `unknown_error` during the individual pass. That is a
single-dependency failure, not a grouping failure, and it does not affect the six PRs
counted above.)

---

## AC1 — A weekly run opens grouped PRs; multiple bumps to one file arrive as one PR

Counting every `create_pull_request` the updater emitted:

| ecosystem | BEFORE | AFTER |
|---|---:|---:|
| `uv` /backend | **13** | **4** |
| `npm` /frontend | **≥33** † | **6** |

### `uv` /backend — 13 → 4

| kind | PR |
|---|---|
| **group (13 updates)** | `bump the backend group in /backend with 13 updates` — boto3, botocore, coverage, coverage[toml], faker, fastapi, locust, pydantic-settings, pymongo, sentry-sdk, sentry-sdk[fastapi], stripe, uvicorn |
| solo — major | `openai` 2.45.0 → **3.0.0** |
| solo — major | `pytest` 8.4.1 → **9.1.1** |
| solo — major | `pytest-cov` 6.2.1 → **7.1.0** |

✅ **Outcome:** thirteen separate PRs become one, and every major arrives on its own.
`openai` 2 → 3 is the result that matters — a **production runtime** major, the AI
client the whole product depends on, landing as its own reviewable PR. That is exactly
the treatment `mongodb` 6 → 7 (#507) deserved and did not get by design, only by luck of
being the only major in its batch.

### `npm` /frontend — ≥33 → 6

| kind | PR |
|---|---|
| **group (139 updates)** | `bump the frontend-prod group in /frontend with 139 updates` |
| **group (35 updates)** | `bump the frontend-dev group in /frontend with 35 updates` |
| solo — **prod major** | `tailwind-merge` 2.6.0 → **3.6.0** (this is #513) |
| solo — indirect | `@babel/runtime` 7.28.4 → 7.29.7 |
| solo — indirect | `@rushstack/eslint-patch` 1.15.0 → 1.16.1 |
| solo — indirect | `@types/semver` 7.7.1 → 7.8.0 |

✅ **Outcome:** two groups absorb 174 updates. `tailwind-merge` 2 → 3 falls through to
its own PR, which is the design working.

---

## AC1b — The npm residue, and why it is left alone

Three of the four npm solo PRs are **not** majors, which was not the predicted result.
The cause is real and worth recording: **`dependency-type` classifies *direct*
dependencies only.** None of `@babel/runtime`, `@rushstack/eslint-patch` or
`@types/semver` appears in `frontend/package.json`. When Dependabot bumps such a dep on
its own — rather than sweeping it along with a direct bump, which is how the other ~170
indirect packages ended up inside the two groups — it matches neither
`dependency-type: production` nor `dependency-type: development`, and falls through to
an individual PR.

**Not suppressed, deliberately.** A third catch-all group (`patterns: ["*"]`, no
`dependency-type`) would absorb them, but only if Dependabot assigns each dependency to
the *first* matching group — otherwise the catch-all steals dev majors out of
`frontend-dev`. That ordering is not documented, so the fix would rest on observed
behaviour that can change under us, and it buys 3 PRs out of 33+.

The `uv` group sets no `dependency-type` at all, which is why it shows no such residue.

---

## AC2 — Auto-merge enabled, verified by `gh pr merge --auto` on a real PR

Before:

```console
$ gh api repos/frankbria/auto-author --jq .allow_auto_merge
false
```

The issue records the resulting failure: `GraphQL: Auto merge is not allowed for this
repository (enablePullRequestAutoMerge)`.

After:

```console
$ gh api -X PATCH repos/frankbria/auto-author -F allow_auto_merge=true --jq .allow_auto_merge
true

$ gh pr merge 529 --auto --squash
$ gh pr view 529 --json autoMergeRequest \
    --jq '.autoMergeRequest | {enabled: (. != null), method: .mergeMethod, by: .enabledBy.login}'
{"by":"frankbria","enabled":true,"method":"SQUASH"}
```

✅ **Outcome:** the API call that previously errored now succeeds and GitHub reports
auto-merge armed.

**#529 was chosen because it cannot actually merge** — its `Security Audit` check is
`FAILURE` (the #512 export-regen trade-off, tracked as #536), and that is a required
check — so arming auto-merge could not fire. It was disarmed immediately afterwards and
the PR left exactly as found:

```console
$ gh pr merge 529 --disable-auto
$ gh pr view 529 --json autoMergeRequest --jq '{auto_merge_enabled: (.autoMergeRequest != null)}'
{"auto_merge_enabled":false}
```

---

## AC3 — A batch of ≥3 dependency PRs lands without any being self-closed

⚠️ **Not demonstrable in this PR.** The self-close in the issue happened because four
PRs were racing on one file; the harness above shows the config now yields one PR per
ecosystem per sweep, which removes the collision, but proving "no PR self-closed" needs
a live Dependabot sweep against the merged config. The `npm`/`uv`/`github-actions`
schedules are all `weekly`.

What is in place instead of a promise: the audit procedure is written down in
`docs/references/quality-standards.md`, so the next batch is checked rather than
assumed. See **Known Limitations** in the PR body.

---

## AC4 — Documented in `docs/references/quality-standards.md`

New **Dependency Batches** section, covering:

- which ecosystem groups what, and the measured before/after counts above;
- why the npm residue exists;
- the post-batch audit — list closed-but-unmerged `app/dependabot` PRs, then confirm on
  `main` that each triaged bump actually landed, because Dependabot deletes the branch
  on close and `gh pr reopen` fails outright (#504 → recreated as #515).

---

## Guards

`scripts/test_dependabot_config.py`, written failing first, and run in CI by the
`Security Audit` job (`uvx --with pytest --with pyyaml pytest scripts/ -q`):

```console
$ uvx --with pytest --with pyyaml pytest scripts/test_dependabot_config.py -q
3 failed, 2 passed, 1 skipped      # before the config change
7 passed                           # after
```

Mutation-checked — each regression fails the test that claims to catch it, and only
that one:

| mutation | result |
|---|---|
| drop `update-types` from `frontend-prod` (re-admitting prod majors) | `test_shipping_groups_never_swallow_a_major[npm/frontend:frontend-prod]` FAILED |
| delete the `uv` group entirely | `test_every_ecosystem_groups_its_updates[uv/backend]` FAILED |
| add `"major"` to the `uv` group's `update-types` | `test_shipping_groups_never_swallow_a_major[uv/backend:backend]` FAILED |

The first guard also treats an **absent** `update-types` as a failure, which is the
silent way this protection would otherwise be lost — omitting the key means "all types",
so a group that merely stops mentioning majors would start shipping them.

---

## Third-party review

`opencode` (GLM) failed with a server-side `UnknownError` (`ref: err_20e325cd`), so the
review ran on the documented fallback:

```console
$ codex review --base origin/main
The changes add Dependabot grouping rules, corresponding documentation, and targeted
tests that align with the stated policy. I did not find a discrete introduced bug that
would break existing behavior or CI under the reviewed diff.
```
