# Demo — #270: block fork PRs from the `ZHIPU_API_KEY` review job

**Issue:** `.github/workflows/glm-review.yml` triggers on `pull_request` and binds
`ZHIPU_API_KEY` into the `review` job — the same latent pwn-request class #191
(PR #269) closed for the staging E2E workflow.

**Fix:** add the same-repo head guard to the job's `if:`:
```yaml
if: |
  github.event.pull_request.head.repo.full_name == github.repository &&
  (github.event.pull_request.changed_files >= 5 ||
   github.event.pull_request.additions >= 20 ||
   github.event.pull_request.deletions >= 20)
```

Config-only change; no workflow test framework exists (the #189/#191 precedent),
so the evidence is `actionlint` (static) + an `act -n` truth table + a RED/GREEN
mutation check. Because the job calls a **remote reusable workflow** (`uses:`),
`act` can't run it directly, so the boolean guard is exercised in an **isolated
harness** that carries only the guard wrapping a stand-in step — if the step
plans, the guard passed and the secret would bind.

---

## AC1 — fork PRs can never reach a run that binds `ZHIPU_API_KEY`

`act -n` (dry-run) truth table over synthetic `pull_request` events,
`GITHUB_REPOSITORY=frankbria/auto-author`:

| Case | `head.repo.full_name` | diff size | Verdict |
|------|----------------------|-----------|---------|
| fork PR + large diff | `attacker/auto-author` | 40 files | **SKIPPED — secret never binds** |
| deleted-fork | `null` | 40 files | **SKIPPED — fails closed** |
| same-repo + large diff | `frankbria/auto-author` | 40 files | RUNS — legit review preserved |
| same-repo + tiny diff | `frankbria/auto-author` | 1 file | SKIPPED — pre-existing size threshold |

```
============ #270 same-repo head guard — truth table (act -n) ============
fork PR + large diff             expect=SKIP    => SKIPPED(secret never binds)
deleted-fork head.repo=null      expect=SKIP    => SKIPPED(secret never binds)
same-repo PR + large diff        expect=RUN     => RUNS   (secret would bind)
same-repo PR + tiny diff         expect=SKIP    => SKIPPED(secret never binds)
=========================================================================
```

### RED/GREEN mutation — the guard actually changes behavior

Fork PR, large diff, old (size-only) guard vs new guard:

```
MUTATION CHECK — fork PR, large diff:
  OLD guard (main):  RUNS  ← the vulnerability (secret exposed to fork code)
  NEW guard (fix) :  SKIPPED ← fixed (secret never binds)
```

## AC2 (bonus) — SHA-pin the action

Already done before this issue: the reusable workflow is pinned to
`@b877d15a0f8c0855d0d2ebdcce32ae09cec1bb2d` with an explanatory comment. No change
needed.

## Static validation

- `python3 -c "import yaml; yaml.safe_load(...)"` → valid YAML
- `actionlint .github/workflows/glm-review.yml` → clean (exit 0)

## Notes / limitations

- Operator precedence: in Actions expressions `&&` binds tighter than `||`, so the
  parens around the size OR-group are load-bearing — without them a *large* fork PR
  (`additions >= 20`) would satisfy the OR and run. Verified by opencode (GLM)
  pre-PR review.
- The repo is public today, so GitHub already withholds secrets from fork
  `pull_request` runs; this guard is defense-in-depth for the drift cases (repo
  goes private with fork-secrets, or trigger swaps to `pull_request_target`).
