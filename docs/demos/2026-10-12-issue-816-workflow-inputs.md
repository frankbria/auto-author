# Issue #816: what a caller types into a workflow dispatch never becomes part of a shell command

*2026-10-13T01:45:49Z by Showboat 0.6.1*
<!-- showboat-id: 75b871b4-1cfc-41ed-8493-5338bcf4dd67 -->

Three acceptance criteria: inputs reach the shell through `env:` only; each input is checked against a pattern before use; a guard test fails if an input appears inside a `run:` block.

## Before: main

The staging deploy puts its `image_tag` input into the command it runs over SSH as root. GitHub pastes the expression into the script before any shell reads it.

```bash
cd /home/frankbria/projects/worktrees/issue-816-workflow-inputs && git show main:.github/workflows/deploy-staging-containers.yml | grep -n 'inputs.image_tag' | cut -c1-110
```

```output
116:             export IMAGE_TAG='${{ inputs.image_tag }}'
142:             export IMAGE_TAG='${{ inputs.image_tag }}' ENVIRONMENT=staging
178:            echo "- tag: \`${{ inputs.image_tag }}\` (frontend: \`${{ inputs.image_tag }}-staging\`)";
```

`emulate.py` does to a job`s scripts what GitHub does: it pastes each expression in, then runs the script. `ssh` is a stub that runs the command it is handed in an empty directory standing in for the box, where `docker` only prints what it was asked. It says afterwards whether a file named `pwned` exists on that box.

A real tag deploys. Nothing else happens.

```bash
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo816 && uvx --with pyyaml python emulate.py deploy-main.yml deploy image_tag sha-3931169
```

```output
step 'Pull and start': exit 0
  box: docker compose -f docker-compose.yml -f docker-compose.staging.yml pull (IMAGE_TAG=sha-3931169)
  box: docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d --remove-orphans (IMAGE_TAG=sha-3931169)
a file named pwned on the box: no
```

The same dispatch with a tag that closes the quote and adds a command. The deploy still looks normal, and the command ran on the box.

```bash
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo816 && uvx --with pyyaml python emulate.py deploy-main.yml deploy image_tag "sha-3931169'; touch pwned; echo '"
```

```output
step 'Pull and start': exit 0
  box: docker compose -f docker-compose.yml -f docker-compose.staging.yml pull (IMAGE_TAG=sha-3931169)
  box: docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d --remove-orphans (IMAGE_TAG=sha-3931169)
a file named pwned on the box: YES
```

## After: this branch

The input reaches the job as a variable, and the job`s first step checks it.

```bash
cd /home/frankbria/projects/worktrees/issue-816-workflow-inputs && sed -n '/^    env:/,/^      - name: Checkout/p' .github/workflows/deploy-staging-containers.yml | grep -v -e '^ *#' -e '^$' -e 'name: Checkout'
```

```output
    env:
      IMAGE_TAG: ${{ inputs.image_tag }}
    steps:
      - name: Check the image tag
        run: |
          if [[ ! "$IMAGE_TAG" =~ ^sha-[0-9a-f]{7,40}$ ]]; then
            echo "::error::image_tag must be a build's sha- tag, such as sha-3931169"
            exit 1
          fi
```

A real tag deploys as before.

```bash
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo816 && uvx --with pyyaml python emulate.py deploy-branch.yml deploy image_tag sha-3931169
```

```output
step 'Check the image tag': exit 0
step 'Pull and start': exit 0
  box: docker compose -f docker-compose.yml -f docker-compose.staging.yml pull (IMAGE_TAG=sha-3931169)
  box: docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d --remove-orphans (IMAGE_TAG=sha-3931169)
a file named pwned on the box: no
```

The crafted tag stops the job at its first step. Nothing reaches the box.

```bash
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo816 && uvx --with pyyaml python emulate.py deploy-branch.yml deploy image_tag "sha-3931169'; touch pwned; echo '"
```

```output
step 'Check the image tag': exit 1
  ::error::image_tag must be a build's sha- tag, such as sha-3931169
the job stops here
a file named pwned on the box: no
```

## Why the check, and not only the variable

The same crafted tag on this branch with the first step left out. The variable alone does not protect the box: the deploy`s script is a string handed to ssh, so the runner`s shell still puts the tag into it, and the box`s shell still reads it. This is why the guard test insists the check is the first step and cannot be skipped.

```bash
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo816 && uvx --with pyyaml python emulate.py deploy-branch.yml deploy image_tag "sha-3931169'; touch pwned; echo '" --skip-first-step
```

```output
step 'Pull and start': exit 0
  box: docker compose -f docker-compose.yml -f docker-compose.staging.yml pull (IMAGE_TAG=sha-3931169)
  box: docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d --remove-orphans (IMAGE_TAG=sha-3931169)
a file named pwned on the box: YES
```

## On GitHub, from this branch

The deploy workflow dispatched with `image_tag=staging`, which is not a build`s tag. It stops at step 2, before the checkout, the network and the box.

```bash
cd /home/frankbria/projects/worktrees/issue-816-workflow-inputs && gh run view 38332214701 --json conclusion,headBranch,jobs --jq '"\(.headBranch): \(.conclusion)", (.jobs[0].steps[] | select(.number < 9) | "  \(.number). \(.name): \(.conclusion)")'
```

```output
feature/issue-816-workflow-inputs: failure
  1. Set up job: success
  2. Check the image tag: failure
  3. Checkout repository: skipped
  4. Connect to Tailscale: skipped
  5. Setup SSH: skipped
  6. Ship compose files: skipped
  7. Pull and start: skipped
  8. Health check: skipped
```

Dispatched with the tag staging was already running, `sha-b6961ff`. It deploys, and the post-deploy E2E run that followed it is green.

```bash
cd /home/frankbria/projects/worktrees/issue-816-workflow-inputs && gh run view 38332266344 --json conclusion,headBranch,jobs --jq '"\(.headBranch): \(.conclusion)", (.jobs[0].steps[] | select(.number < 9) | "  \(.number). \(.name): \(.conclusion)")'
```

```output
feature/issue-816-workflow-inputs: success
  1. Set up job: success
  2. Check the image tag: success
  3. Checkout repository: success
  4. Connect to Tailscale: success
  5. Setup SSH: success
  6. Ship compose files: success
  7. Pull and start: success
  8. Health check: success
```

```bash
cd /home/frankbria/projects/worktrees/issue-816-workflow-inputs && gh run view 38332295117 --json conclusion,event --jq '"post-deploy E2E (\(.event)): \(.conclusion)"'
```

```output
post-deploy E2E (workflow_run): success
```

The staging E2E workflow dispatched with `staging_e2e_workers=0`, then with `2`.

```bash
cd /home/frankbria/projects/worktrees/issue-816-workflow-inputs && gh run view 38332631256 --json conclusion,headBranch,jobs --jq '"\(.headBranch): \(.conclusion)", (.jobs[0].steps[] | select(.number < 9) | "  \(.number). \(.name): \(.conclusion)")'
```

```output
feature/issue-816-workflow-inputs: failure
  1. Set up job: success
  2. Check the worker count: failure
  3. Checkout repository: skipped
  4. Setup Node.js: skipped
  5. Install dependencies: skipped
  6. Install Playwright browsers: skipped
  7. Run E2E tests against staging: skipped
  8. Write staging E2E summary: success
```

```bash
cd /home/frankbria/projects/worktrees/issue-816-workflow-inputs && gh run view 38332668160 --json conclusion,headBranch,jobs --jq '"\(.headBranch): \(.conclusion)", (.jobs[0].steps[] | select(.number < 9) | "  \(.number). \(.name): \(.conclusion)")'
```

```output
feature/issue-816-workflow-inputs: success
  1. Set up job: success
  2. Check the worker count: success
  3. Checkout repository: success
  4. Setup Node.js: success
  5. Install dependencies: success
  6. Install Playwright browsers: success
  7. Run E2E tests against staging: success
  8. Write staging E2E summary: success
```

## The guard

It reads every workflow. It fails if a dispatch input, anything from the event payload or a pull request`s branch name is pasted into a script; if a variable filled from one is missing from its table; if a job`s first step is not the check or can be skipped; and it runs each check`s own script against values that must pass and values that must not.

```bash
cd /home/frankbria/projects/worktrees/issue-816-workflow-inputs && uvx --with pytest --with pyyaml pytest scripts/test_workflow_inputs_not_in_run.py -q 2>&1 | tail -1
```

```output
83 passed in 0.59s
```

Against main`s workflows the same guard fails, and names each place.

```bash
cd /home/frankbria/projects/worktrees/issue-816-workflow-inputs && git checkout -q main -- .github/workflows && uvx --with pytest --with pyyaml pytest scripts/test_workflow_inputs_not_in_run.py -q -k 'pasted' 2>&1 | grep -E 'step [0-9]+ \(|passed|failed' | cut -c1-150; git checkout -q HEAD -- .github/workflows; git diff --quiet HEAD -- .github/workflows && echo 'workflows restored'
```

```output
E         deploy: step 4 (Pull and start): ${{ inputs.image_tag }}
E         deploy: step 5 (Health check): ${{ inputs.image_tag }}
E         deploy: step 8 (Summary): ${{ inputs.image_tag }}
E         deploy: step 8 (Summary): ${{ inputs.image_tag }}
E       assert not ['deploy: step 4 (Pull and start): ${{ inputs.image_tag }}', 'deploy: step 5 (Health check): ${{ inputs.image_tag }}', 'deploy: ste
E         e2e-staging: step 5 (Write staging E2E summary): ${{ github.event.inputs.staging_e2e_workers || '1' }}
E       assert not ["e2e-staging: step 5 (Write staging E2E summary): ${{ github.event.inputs.staging_e2e_workers || '1' }}"]
E         sync: step 7 (Summary): ${{ inputs.recreate }}
E       assert not ['sync: step 7 (Summary): ${{ inputs.recreate }}']
3 failed, 5 passed, 75 deselected in 0.06s
workflows restored
```

## Not exercised for real

`sync-staging-env.yml` was not dispatched: a run rewrites a credential on the box. Its change is the same shape as the other two and its check is run by the guard test.
