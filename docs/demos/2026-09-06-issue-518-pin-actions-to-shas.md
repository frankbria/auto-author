# Demo — #518 Pin GitHub Actions to immutable SHAs

**Date:** 2026-09-06 · **Branch:** `feature/518-pin-actions-to-shas`

Hardening, not incident response: no upstream action here is known to have been repointed. The
change removes the capability, and the guard removes the chance of it coming back.

---

## What was unpinned

26 `uses:` references across the four active workflows that had any, spanning **10 distinct
actions**. Two references were already pinned and stayed as they were: `tailscale/github-action`
(×2) and the `frankbria/glm-review` reusable workflow.

`build-images.yml` is the reason this is P2 rather than hygiene — `docker/login-action` receives
the registry token and `docker/build-push-action` publishes the images
`deploy-staging-containers.yml` later pulls and runs on the staging box.

## The pins, and how each was verified

Every SHA below was resolved from the tag the workflow named, via
`gh api repos/<owner>/<repo>/git/ref/tags/<tag>`, then confirmed by listing the tags that point
at the resulting commit. **A pin is only as good as the verification behind it**, so both
directions were checked: tag → commit, and commit → tags.

| Action | Was | Pinned to | Tags on that commit |
|---|---|---|---|
| `actions/checkout` | `@v7` | `3d3c42e5…ba90b1` | `v7.0.1`, `v7` |
| `actions/setup-node` | `@v7.0.0` | `82076278…fe5020` | `v7.0.0`, `v7` |
| `actions/setup-python` | `@v7.0.0` | `5fda3b95…3e4b97` | `v7.0.0`, `v7` |
| `actions/upload-artifact` | `@v7` | `043fb46d…fc6a0a` | `v7.0.1`, `v7` |
| `astral-sh/setup-uv` | `@v10.0.1` | `20cfd1bf…fc9a30d` | `v10.0.1` |
| `codecov/codecov-action` | `@v7` | `fb8b3582…33a72f` | `v7.0.0`, `v7`, `v6.0.2`, `v6` |
| `docker/setup-buildx-action` | `@v4` | `37fe6310…7f5f0e` | `v4.3.0`, `v4` |
| `docker/login-action` | `@v4` | `dbcb8138…569679f` | `v4.6.0`, `v4` |
| `docker/metadata-action` | `@v6` | `dc802804…411302` | `v6.2.0`, `v6` |
| `docker/build-push-action` | `@v7` | `53b7df96…38856a` | `v7.3.0`, `v7` |

**Two of these rows are the interesting ones.**

`codecov/codecov-action@v7` is an **annotated** tag: the ref's `.object.type` is `tag`, so
`.object.sha` is the tag *object*, not the commit. Pinning that value would have produced a
reference resolving to nothing. It was dereferenced through
`git/tags/<sha>` before pinning. Nine of the ten were lightweight; this one was not, which is
exactly why the resolve procedure is written into `quality-standards.md` rather than left as
folklore.

`actions/setup-node@v7.0.0` and `setup-python@v7.0.0` were already *full semver* tags, and were
still unpinned in every sense that matters. A `vX.Y.Z` tag can be force-moved to a different
commit as easily as `vX`. Specificity is not immutability.

## The guard

`scripts/test_actions_are_sha_pinned.py`, run by `pytest scripts/ -q` in the `Security Audit`
job. Three rules: every `uses:` is SHA-pinned, every pin carries a version comment, and every
workflow still parses as YAML.

**Mutation-checked three ways, with the guard staged (`git add`) first** — an unstaged guard can
pass by not being seen:

| mutation | result |
|---|---|
| `docker/login-action` reverted to `@v4` | ❌ `test_every_action_is_pinned_to_a_commit_sha[build-images.yml]` |
| `codecov/codecov-action` version comment stripped | ❌ `test_every_pin_carries_a_version_comment[tests.yml]` |
| guard repointed at a non-existent directory | ❌ `test_there_are_workflows_to_check` |

The third is the one that matters most: without it, a rename or a moved directory turns every
other assertion vacuously green, and a passing check gets read as evidence.

**The guard found a real gap on its first run.** `glm-review.yml` was SHA-pinned but carried no
inline version anchor — its provenance lived only in a prose comment two lines above. It now
reads `# 2026-07-10 (main; no tags upstream)`. The rule was not loosened to accommodate it: the
first draft of that comment was `# main @ 2026-07-10`, which the guard rejected for not leading
with a version token, so the comment was reordered instead.

## Acceptance criteria

| # | Criterion | Evidence | |
|---|---|---|---|
| 1 | Every third-party `uses:` pinned to a full commit SHA with a version comment | 26 references, 10 actions; `grep -rn "uses:" .github/workflows/*.yml \| grep -vE "@[0-9a-f]{40}"` returns nothing | ✅ |
| 2 | Each SHA verified against the tag it claims | Table above — resolved tag → commit *and* commit → tags, with the one annotated tag dereferenced | ✅ |
| 3 | `Build Images` green, both build jobs | `build-images.yml` triggers on PRs touching itself, so both matrix jobs (`backend`, `frontend`) run on this PR — see checks | ✅ |
| 4 | Dependabot still opens update PRs against the pinned SHAs | **Cannot be verified pre-merge** — needs the next weekly sweep. See below. | ⏳ |
| 5 | Policy recorded so new workflows start pinned | `docs/references/quality-standards.md` → *GitHub Actions are pinned to commit SHAs*, plus the guard, which is the enforcing half | ✅ |

## Known limitation: AC4 is a prediction until the next sweep

Dependabot's `github-actions` ecosystem documents SHA-pin updates and version-comment rewriting,
and `.github/dependabot.yml` already covers `github-actions` at `/` — but that is the
documentation, not an observation of this repo. The last `actions` group PRs (#540, #563) were
tag bumps against unpinned refs, so nothing here has yet produced a SHA-diff PR.

The check is one command on the next sweep:

```bash
gh pr list --author "app/dependabot" --state open --json number,title,files \
  --jq '.[] | select(.title | test("actions")) | .number'
# then confirm the diff moves a 40-char SHA and rewrites the trailing "# vX.Y.Z"
```

Stated as ⏳ rather than ✅ deliberately. #539 is the recent lesson on this exact temptation —
an inference presented as an observation is worse than an open box, because nobody re-checks a
tick. If the next sweep shows Dependabot has stopped tracking these, the pins still hold and the
cost is manual bumps, not a broken build.
