# Issue #191: block fork PRs from the label-gated staging E2E job (pwn-request)

*2026-07-10T21:22:31Z*

The e2e-staging workflow triggers on labeled pull_request (including synchronize) and runs PR-controlled code — npm ci lifecycle scripts and Playwright specs — inside the staging GitHub environment, which holds TEST_USER_EMAIL/TEST_USER_PASSWORD and Slack/Discord webhook secrets. On main, the job gate checks only the label. So: a maintainer labels a benign fork PR e2e-staging, the attacker force-pushes malicious code, and the synchronize event re-runs the workflow with the label still attached — attacker code executes against live staging. This is the pwn-request pattern. First, the vulnerable gate as it exists on main:

```bash
git -C /home/frankbria/projects/auto-author show main:.github/workflows/e2e-staging-tests.yml | sed -n "48,52p"
```

```output
    # Skip on PRs unless explicitly labeled `e2e-staging`.
    if: >-
      github.event_name != 'pull_request' ||
      contains(github.event.pull_request.labels.*.name, 'e2e-staging')

```

To prove behavior rather than eyeball YAML, we evaluate the real workflow file with act (nektos/act 0.2.89), which implements the GitHub Actions expression engine. The synthetic event below is exactly what GitHub delivers for the attack: a synchronize event on a PR whose head repo is a fork (attacker/auto-author) and which already carries the e2e-staging label.

```bash
cat /tmp/claude-1000/-home-frankbria-projects-auto-author/9fb35b48-9a42-4ec9-bedc-6f9c42d232b4/scratchpad/events/fork-labeled.json
```

```output
{
  "action": "synchronize",
  "pull_request": {
    "labels": [{"name": "e2e-staging"}],
    "head": {"repo": {"full_name": "attacker/auto-author"}}
  },
  "repository": {"full_name": "frankbria/auto-author"}
}
```

BEFORE (main): the labeled fork PR sails through the gate — act plans every step of the e2e-staging job, i.e. fork-controlled npm ci + Playwright would execute in the staging environment.

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/9fb35b48-9a42-4ec9-bedc-6f9c42d232b4/scratchpad/tools/act pull_request -W /tmp/claude-1000/-home-frankbria-projects-auto-author/9fb35b48-9a42-4ec9-bedc-6f9c42d232b4/scratchpad/main-e2e-staging.yml -e /tmp/claude-1000/-home-frankbria-projects-auto-author/9fb35b48-9a42-4ec9-bedc-6f9c42d232b4/scratchpad/events/fork-labeled.json -n 2>&1 | grep -E "Run Main" | head -6
```

```output
*DRYRUN* [E2E Staging Tests/E2E Staging (Playwright)] ⭐ Run Main Checkout repository
*DRYRUN* [E2E Staging Tests/E2E Staging (Playwright)] ⭐ Run Main Setup Node.js
*DRYRUN* [E2E Staging Tests/E2E Staging (Playwright)] ⭐ Run Main Install dependencies
*DRYRUN* [E2E Staging Tests/E2E Staging (Playwright)] ⭐ Run Main Install Playwright browsers
*DRYRUN* [E2E Staging Tests/E2E Staging (Playwright)] ⭐ Run Main Run E2E tests against staging
*DRYRUN* [E2E Staging Tests/E2E Staging (Playwright)] ⭐ Run Main Write staging E2E summary
```

THE FIX (this branch, per AC branch 2): the job gate now also requires the PR head to live in this repository. Fork heads can never satisfy it — full_name is globally unique on GitHub, and a null head.repo (deleted fork) compares false, so the guard fails closed.

```bash
sed -n "50,59p" /home/frankbria/projects/auto-author/.github/workflows/e2e-staging-tests.yml
```

```output
    # Skip on PRs unless explicitly labeled `e2e-staging` AND the head branch is
    # in this repo. The same-repo guard blocks pwn-requests (#191): without it, a
    # maintainer labeling a fork PR lets later attacker pushes (`synchronize`)
    # re-run fork-controlled code (npm lifecycle scripts, Playwright specs) in the
    # `staging` environment against the live staging site.
    if: >-
      github.event_name != 'pull_request' ||
      (github.event.pull_request.head.repo.full_name == github.repository &&
       contains(github.event.pull_request.labels.*.name, 'e2e-staging'))

```

AFTER: the identical fork-labeled synchronize event now plans ZERO steps — the job is skipped before the staging environment (and its secrets) is ever bound.

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/9fb35b48-9a42-4ec9-bedc-6f9c42d232b4/scratchpad/tools/act pull_request -W /home/frankbria/projects/auto-author/.github/workflows/e2e-staging-tests.yml -e /tmp/claude-1000/-home-frankbria-projects-auto-author/9fb35b48-9a42-4ec9-bedc-6f9c42d232b4/scratchpad/events/fork-labeled.json -n 2>&1 | grep -c 'Run Main' || true
```

```output
0
```

Legitimate runs are untouched. A same-repo PR carrying the label (the documented, in-use path) still plans the full job:

```bash
cat /tmp/claude-1000/-home-frankbria-projects-auto-author/9fb35b48-9a42-4ec9-bedc-6f9c42d232b4/scratchpad/events/samerepo-labeled.json && echo '---' && /tmp/claude-1000/-home-frankbria-projects-auto-author/9fb35b48-9a42-4ec9-bedc-6f9c42d232b4/scratchpad/tools/act pull_request -W /home/frankbria/projects/auto-author/.github/workflows/e2e-staging-tests.yml -e /tmp/claude-1000/-home-frankbria-projects-auto-author/9fb35b48-9a42-4ec9-bedc-6f9c42d232b4/scratchpad/events/samerepo-labeled.json -n 2>&1 | grep -E 'Run Main' | head -3
```

```output
{
  "action": "synchronize",
  "pull_request": {
    "labels": [{"name": "e2e-staging"}],
    "head": {"repo": {"full_name": "frankbria/auto-author"}}
  },
  "repository": {"full_name": "frankbria/auto-author"}
}
---
*DRYRUN* [E2E Staging Tests/E2E Staging (Playwright)] ⭐ Run Main Checkout repository
*DRYRUN* [E2E Staging Tests/E2E Staging (Playwright)] ⭐ Run Main Setup Node.js
*DRYRUN* [E2E Staging Tests/E2E Staging (Playwright)] ⭐ Run Main Install dependencies
```

The 6-hourly scheduled run is also unaffected (this is why AC branch 1 — required reviewers on the staging environment — was rejected: environment protection rules gate every run referencing the environment, which would stall the cron every 6 hours):

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/9fb35b48-9a42-4ec9-bedc-6f9c42d232b4/scratchpad/tools/act schedule -W /home/frankbria/projects/auto-author/.github/workflows/e2e-staging-tests.yml -n 2>&1 | grep -E 'Run Main Checkout' | head -1
```

```output
*DRYRUN* [E2E Staging Tests/E2E Staging (Playwright)] ⭐ Run Main Checkout repository
```

And an unlabeled fork PR remains skipped, same as before (0 steps planned):

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/9fb35b48-9a42-4ec9-bedc-6f9c42d232b4/scratchpad/tools/act pull_request -W /home/frankbria/projects/auto-author/.github/workflows/e2e-staging-tests.yml -e /tmp/claude-1000/-home-frankbria-projects-auto-author/9fb35b48-9a42-4ec9-bedc-6f9c42d232b4/scratchpad/events/fork-unlabeled.json -n 2>&1 | grep -c 'Run Main' || true
```

```output
0
```

Static validation: actionlint 1.7.7 confirms the modified expression is syntactically valid GitHub Actions syntax.

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/9fb35b48-9a42-4ec9-bedc-6f9c42d232b4/scratchpad/tools/actionlint /home/frankbria/projects/auto-author/.github/workflows/e2e-staging-tests.yml && echo 'actionlint: clean (exit 0)'
```

```output
actionlint: clean (exit 0)
```

Summary — truth table for the e2e-staging job. BEFORE: fork+label RAN (the vulnerability). AFTER: fork+label SKIPPED; same-repo+label runs; schedule runs; unlabeled skipped. Note this repo is public, so GitHub already withholds secrets from fork pull_request runs — the guard is defense-in-depth: it stops fork code from executing against live staging at all, and closes the one-config-drift-away leak (a pull_request_target swap, or the repo going private with fork-secrets enabled).
