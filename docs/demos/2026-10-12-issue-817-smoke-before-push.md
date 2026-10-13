# Issue #817: an image is pushed only after its smoke test has booted it

*2026-10-13T03:06:14Z by Showboat 0.6.1*
<!-- showboat-id: 4a6f1d5f-c735-408b-8d4e-a24962bb0dc8 -->

Two acceptance criteria: the image is built with `load`, smoke-tested, then pushed; a broken `CMD` publishes no tag.

## Before: main

One step builds and pushes. The smoke test comes after it, so by the time it boots the image the tags are already in the registry.

```bash
cd /home/frankbria/projects/worktrees/issue-817-smoke-before-push && git show 666291b:.github/workflows/build-images.yml | grep -n -E '^      - name: |^          (push|load):' | sed -n '/Build/,$p'
```

```output
92:      - name: Set up Docker Buildx
98:      - name: Log in to GHCR
106:      - name: Derive tags
120:      - name: Build and push
124:          push: ${{ github.event_name != 'pull_request' }}
142:      - name: Smoke test the built image
185:      - name: Report published tags
```

## After: this branch

The build loads the image into the runner`s own Docker and pushes nothing. The smoke test boots it. A step of its own pushes it.

```bash
cd /home/frankbria/projects/worktrees/issue-817-smoke-before-push && cat .github/workflows/build-images.yml | grep -n -E '^      - name: |^          (push|load):' | sed -n '/Build/,$p'
```

```output
92:      - name: Set up Docker Buildx
98:      - name: Log in to GHCR
106:      - name: Derive tags
123:      - name: Build
127:          load: true
146:      - name: Smoke test the built image
191:      - name: Push the image that passed
200:      - name: Report published tags
```

```bash
cd /home/frankbria/projects/worktrees/issue-817-smoke-before-push && sed -n '/- name: Push the image that passed/,/done <<< /p' .github/workflows/build-images.yml
```

```output
      - name: Push the image that passed
        if: github.event_name != 'pull_request'
        env:
          TAGS: ${{ steps.meta.outputs.tags }}
        run: |
          while read -r tag; do
            docker push "$tag"
          done <<< "$TAGS"
```

## On GitHub: a good build

This branch`s workflow, dispatched on this branch. Both images build, boot and are pushed.

```bash
cd /home/frankbria/projects/worktrees/issue-817-smoke-before-push && gh run view 38339476225 --json conclusion,headBranch,headSha,jobs --jq '"\(.headBranch) \(.headSha[0:7]): \(.conclusion)", (.jobs[] | "  \(.name): \(.conclusion)", (.steps[] | select(.name|test("^Build$|Smoke|Push the image")) | "    \(.name): \(.conclusion)"))'
```

```output
feature/issue-817-smoke-before-push e7ad3a0: success
  Build backend image: success
    Build: success
    Smoke test the built image: success
    Push the image that passed: success
  Build frontend (staging) image: success
    Build: success
    Smoke test the built image: success
    Push the image that passed: success
```

Both tags are in the registry, and the backend image that was published is the one built from that commit.

```bash
for t in auto-author-backend:sha-e7ad3a0 auto-author-frontend:sha-e7ad3a0-staging; do printf '%-44s ' $t; docker manifest inspect ghcr.io/frankbria/$t >/dev/null 2>&1 && echo 'in the registry' || echo 'not there'; done
```

```output
auto-author-backend:sha-e7ad3a0              in the registry
auto-author-frontend:sha-e7ad3a0-staging     in the registry
```

```bash
docker pull -q ghcr.io/frankbria/auto-author-backend:sha-e7ad3a0 >/dev/null && docker run --rm --entrypoint sh ghcr.io/frankbria/auto-author-backend:sha-e7ad3a0 -c 'echo GIT_SHA=$GIT_SHA' | cut -c1-15
```

```output
GIT_SHA=e7ad3a0
```

## On GitHub: a `CMD` that cannot start

A throwaway branch off this one, never merged and since deleted, whose only change is that both Dockerfiles start something that does not exist: `uvicorn app.no_such_module:app` and `node no-such-server.js`. The same workflow, dispatched on it.

Both images still build. Both smoke tests fail. Both push steps are skipped.

```bash
cd /home/frankbria/projects/worktrees/issue-817-smoke-before-push && gh run view 38339488082 --json conclusion,headBranch,headSha,jobs --jq '"\(.headBranch) \(.headSha[0:7]): \(.conclusion)", (.jobs[] | "  \(.name): \(.conclusion)", (.steps[] | select(.name|test("^Build$|Smoke|Push the image")) | "    \(.name): \(.conclusion)"))'
```

```output
demo/817-broken-cmd 62c5f67: failure
  Build frontend (staging) image: failure
    Build: success
    Smoke test the built image: failure
    Push the image that passed: skipped
  Build backend image: failure
    Build: success
    Smoke test the built image: failure
    Push the image that passed: skipped
```

```bash
cd /home/frankbria/projects/worktrees/issue-817-smoke-before-push && gh run view 38339488082 --log-failed 2>/dev/null | grep -E 'image failed to serve|Cannot find module' | grep -v 'echo ' | sed 's/^[^Z]*Z //' | cut -c1-110
```

```output
##[error]frontend image failed to serve http://localhost:3002/
Error: Cannot find module '/app/no-such-server.js'
##[error]backend image failed to serve http://localhost:8000/api/v1/health
```

Neither tag exists. On main the same two commits would have left both in the registry before the smoke test ran.

```bash
for t in auto-author-backend:sha-62c5f67 auto-author-frontend:sha-62c5f67-staging; do printf '%-44s ' $t; docker manifest inspect ghcr.io/frankbria/$t >/dev/null 2>&1 && echo 'in the registry' || echo 'not there'; done
```

```output
auto-author-backend:sha-62c5f67              not there
auto-author-frontend:sha-62c5f67-staging     not there
```

## The guard

It pins the order, that nothing else publishes, and that the push runs exactly when the smoke test does. It also runs the smoke test`s and the push step`s own scripts against a stand-in docker: an image that does not serve fails; every tag is pushed; a push that fails stops the job.

```bash
cd /home/frankbria/projects/worktrees/issue-817-smoke-before-push && uvx --with pytest --with pyyaml pytest scripts/test_image_is_smoke_tested_before_push.py -q 2>&1 | tail -1
```

```output
10 passed in 0.33s
```

Against main`s workflow the same guard fails.

```bash
cd /home/frankbria/projects/worktrees/issue-817-smoke-before-push && git checkout -q 666291b -- .github/workflows/build-images.yml && uvx --with pytest --with pyyaml pytest scripts/test_image_is_smoke_tested_before_push.py -q 2>&1 | grep -E '^FAILED|[0-9]+ (passed|failed)' | sed 's/^FAILED scripts.test_image_is_smoke_tested_before_push.py:://' | cut -c1-120; git checkout -q HEAD -- .github/workflows/build-images.yml; git diff --quiet HEAD -- .github && echo 'workflow restored'
```

```output
test_the_build_step_keeps_the_image_on_the_runner_and_publishes_nothing
test_the_image_is_booted_before_it_is_pushed
test_nothing_else_publishes
test_a_push_never_follows_a_smoke_test_that_failed_or_did_not_run
test_the_push_step_pushes_every_tag
test_a_push_that_fails_stops_the_job
6 failed, 4 passed in 0.34s
workflow restored
```
