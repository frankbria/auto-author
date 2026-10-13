# Issue #818: both images are scanned before they are pushed, and their base images are pinned and kept current

*2026-10-13T04:24:30Z by Showboat 0.6.1*
<!-- showboat-id: b59d7737-c958-4057-bdd5-10235818fbc1 -->

Two acceptance criteria: a SHA-pinned Trivy scan with `CRITICAL,HIGH` and `ignore-unfixed` on both images; Dependabot `docker` entries that exist and are asserted in `test_dependabot_config.py`.

`scan.sh` runs the scan the workflow runs (the same Trivy version, severities and flags) and prints one line per finding with where in the image it is.

```bash
sed -n '2,6p' /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo818/scan.sh | cut -c1-100
```

```output
# scan.sh <image>: the scan build-images.yml runs (Trivy 0.70.0, CRITICAL and HIGH,
# fixable only), printed as one line per finding with where in the image it is.
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache \
  ghcr.io/aquasecurity/trivy:0.70.0 image --quiet --severity CRITICAL,HIGH --ignore-unfixed \
  --scanners vuln --format json "$1" 2>/dev/null | python3 "$(dirname "$0")/scan_report.py"
```

## Before: the images staging is running, built from main

Four findings in the backend image and seven in the frontend image. None is in the application: every one is in pip or in npm, as shipped by the base image.

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo818/scan.sh ghcr.io/frankbria/auto-author-backend:sha-cf79c34
```

```output
  HIGH  GHSA-6v7p-g79w-8964  msgpack          pip, in the base image (pip carries its own copy)
  HIGH  CVE-2025-47273       setuptools       pip, in the base image (pip carries its own copy)
  HIGH  CVE-2026-97687       urllib3          pip, in the base image (pip carries its own copy)
  HIGH  CVE-2026-97689       urllib3          pip, in the base image (pip carries its own copy)
findings: 4
```

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo818/scan.sh ghcr.io/frankbria/auto-author-frontend:sha-cf79c34-staging
```

```output
  HIGH  CVE-2026-102276      brace-expansion  usr/local/lib/node_modules/npm/node_modules/brace-expansion/pa
  HIGH  CVE-2026-102278      brace-expansion  usr/local/lib/node_modules/npm/node_modules/brace-expansion/pa
  HIGH  CVE-2026-14257       brace-expansion  usr/local/lib/node_modules/npm/node_modules/brace-expansion/pa
  HIGH  CVE-2026-69152       brace-expansion  usr/local/lib/node_modules/npm/node_modules/brace-expansion/pa
  HIGH  CVE-2026-69192       ip-address       usr/local/lib/node_modules/npm/node_modules/ip-address/package
  HIGH  CVE-2026-73566       tar              usr/local/lib/node_modules/npm/node_modules/tar/package.json
  HIGH  CVE-2026-19534       undici           usr/local/lib/node_modules/npm/node_modules/undici/package.jso
findings: 7
```

## After: the images built from this branch

The runtime images install nothing, so the package managers are taken out of them. Nothing is left for the scan to report, and there is no ignore file.

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo818/scan.sh aa818-backend
```

```output
findings: 0
```

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo818/scan.sh aa818-frontend
```

```output
findings: 0
```

What is gone from each, and that both still start and serve what the workflow`s smoke test asks them for.

```bash
docker run --rm --entrypoint sh aa818-backend -c '/usr/local/bin/python3 -m pip --version 2>&1 | tail -1'
```

```output
/usr/local/bin/python3: No module named pip
```

```bash
docker run --rm --entrypoint sh aa818-frontend -c 'ls /usr/local/bin | tr "\n" " "; echo; ls /usr/local/lib/node_modules 2>&1 | tail -1; node --version'
```

```output
docker-entrypoint.sh node nodejs 
ls: /usr/local/lib/node_modules: No such file or directory
v24.21.0
```

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo818/boot.sh
```

```output
http://127.0.0.1:18818/api/v1/health -> 200
http://127.0.0.1:13818/ -> 200
```

## On GitHub: this branch`s workflow, on this branch

Each job builds, scans, boots and pushes, in that order.

```bash
cd /home/frankbria/projects/worktrees/issue-818-image-scan && gh run view 38344851000 --json conclusion,headBranch,headSha,jobs --jq '"\(.headBranch) \(.headSha[0:7]): \(.conclusion)", (.jobs[] | "  \(.name): \(.conclusion)", (.steps[] | select(.name|test("^Build$|^Scan|Smoke|Push the image")) | "    \(.name): \(.conclusion)"))'
```

```output
feature/issue-818-image-scan bdc8130: success
  Build frontend (staging) image: success
    Build: success
    Scan the image: success
    Smoke test the built image: success
    Push the image that passed: success
  Build backend image: success
    Build: success
    Scan the image: success
    Smoke test the built image: success
    Push the image that passed: success
```

```bash
cd /home/frankbria/projects/worktrees/issue-818-image-scan && gh run view 38344851000 --log 2>/dev/null | grep 'Scan the image' | grep -E 'sha-[0-9a-f]{7}.*│' | sed 's/^[^Z]*Z //' | cut -c1-120
```

```output
│ ghcr.io/frankbria/auto-author-frontend:sha-bdc8130-staging (alpine 3.24.2) │  alpine  │        0        │
│ ghcr.io/frankbria/auto-author-backend:sha-bdc8130 (debian 13.7)                  │   debian   │        0        │
```

## On GitHub: the package managers left in

A throwaway branch off this one, never merged and since deleted, whose only change is that the two removal lines are taken back out of the Dockerfiles. The same workflow, dispatched on it.

Both scans fail. The smoke tests and the pushes are skipped, and neither tag reaches the registry.

```bash
cd /home/frankbria/projects/worktrees/issue-818-image-scan && gh run view 38345574606 --json conclusion,headBranch,headSha,jobs --jq '"\(.headBranch) \(.headSha[0:7]): \(.conclusion)", (.jobs[] | "  \(.name): \(.conclusion)", (.steps[] | select(.name|test("^Build$|^Scan|Smoke|Push the image")) | "    \(.name): \(.conclusion)"))'
```

```output
demo/818-package-managers-left-in 9a1a8a4: failure
  Build frontend (staging) image: failure
    Build: success
    Scan the image: failure
    Smoke test the built image: skipped
    Push the image that passed: skipped
  Build backend image: failure
    Build: success
    Scan the image: failure
    Smoke test the built image: skipped
    Push the image that passed: skipped
```

```bash
cd /home/frankbria/projects/worktrees/issue-818-image-scan && gh run view 38345574606 --log 2>/dev/null | grep 'Scan the image' | grep -E 'Total: [0-9]+ \(' | sed 's/^[^Z]*Z //' | cut -c1-80
```

```output
Total: 7 (HIGH: 7, CRITICAL: 0)
Total: 4 (HIGH: 4, CRITICAL: 0)
```

```bash
for t in auto-author-backend:sha-9a1a8a4 auto-author-frontend:sha-9a1a8a4-staging; do printf '%-46s ' $t; docker manifest inspect ghcr.io/frankbria/$t >/dev/null 2>&1 && echo 'in the registry' || echo 'not there'; done
```

```output
auto-author-backend:sha-9a1a8a4                not there
auto-author-frontend:sha-9a1a8a4-staging       not there
```

## Dependabot, run for real

Dependabot`s own docker updater (`dependabot/cli` with the updater image), pointed at the repository. `dbot.sh` reads its output: which dependencies it recognised in the Dockerfile, and which pull requests it would open.

**main.** It recognises nothing: it does not resolve `FROM python:${PYTHON_VERSION}`. A `docker` entry added without touching the Dockerfiles would have updated nothing.

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo818/dbot.sh /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo818/dependabot-main-backend.log
```

```output
dependencies recognised: none
pull requests it would open: none
```

**This branch, with the entries` ignore rules left out.** It recognises both base images, and would move the language itself: Python 3.13 to 3.14, Node 24 to 26.

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo818/dbot.sh /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo818/dependabot-branch-backend-no-rules.log; /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo818/dbot.sh /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo818/dependabot-branch-frontend-no-rules.log
```

```output
dependencies recognised: ['python 3.13-slim']
pull requests it would open: ['chore(deps): bump python from 3.13-slim to 3.14-slim in /backend']
dependencies recognised: ['node 24-alpine']
pull requests it would open: ['chore(deps): bump node from 24-alpine to 26-alpine in /frontend']
```

**This branch, as configured.** Both recognised, and nothing to open today: the digests are current and a new language version is not taken from here.

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo818/dbot.sh /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo818/dependabot-branch-backend.log; /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo818/dbot.sh /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo818/dependabot-branch-frontend.log
```

```output
dependencies recognised: ['python 3.13-slim']
pull requests it would open: none
dependencies recognised: ['node 24-alpine']
pull requests it would open: none
```

## The guards

```bash
cd /home/frankbria/projects/worktrees/issue-818-image-scan && uvx --with pytest --with pyyaml pytest scripts/test_dependabot_config.py scripts/test_image_is_smoke_tested_before_push.py -q 2>&1 | tail -1
```

```output
35 passed, 5 skipped in 0.48s
```

Against main`s Dockerfiles, Dependabot config and workflow, the new ones fail.

```bash
cd /home/frankbria/projects/worktrees/issue-818-image-scan && git checkout -q cf79c34 -- .github backend/Dockerfile frontend/Dockerfile && uvx --with pytest --with pyyaml pytest scripts/test_dependabot_config.py scripts/test_image_is_smoke_tested_before_push.py -q 2>&1 | grep -E '^FAILED|[0-9]+ (passed|failed)' | sed 's/^FAILED scripts.test_[a-z_]*.py:://' | cut -c1-120; git checkout -q HEAD -- .github backend/Dockerfile frontend/Dockerfile; git diff --quiet HEAD -- .github backend frontend && echo 'files restored'
```

```output
test_each_image_has_a_docker_entry[/backend]
test_each_image_has_a_docker_entry[/frontend]
test_each_base_image_is_one_dependabot_can_read_and_is_pinned_to_a_digest[/backend-python]
test_each_base_image_is_one_dependabot_can_read_and_is_pinned_to_a_digest[/frontend-node]
test_the_language_version_is_not_moved_by_a_base_image_update[/backend-python]
test_the_language_version_is_not_moved_by_a_base_image_update[/frontend-node]
test_the_image_is_scanned_before_it_is_pushed_and_a_finding_stops_the_job
7 failed, 22 passed, 5 skipped in 0.48s
files restored
```
