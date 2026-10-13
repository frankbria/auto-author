# Issue #821: the backend`s stale transitives are upgraded, and a baseline entry has to earn its place

*2026-10-13T06:46:44Z by Showboat 0.6.1*
<!-- showboat-id: 86597009-d322-42cc-9fb5-90dd5e8912a4 -->

Five acceptance criteria: the lock is upgraded with a fourteen-day cut-off, with click at 8.3.3 or later and certifi from 2026; the baseline is empty; resolved baseline entries fail the gate; entries need a reason; the stale comments are corrected.

## The lock

`lockdiff.py` compares two lock files package by package.

```bash
sed -n '1,2p;13,16p' /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/lockdiff.py
```

```output
"""lockdiff.py <old uv.lock> <new uv.lock>: what moved, and in which direction."""
import sys, tomllib
for n in down:
    print(f"  DOWNGRADED {n} {old[n]} -> {new[n]}")
if "--all" in sys.argv:
    for n in up:
```

main`s lock against this branch`s. 38 packages went up, none went down, and setuptools is no longer needed by anything.

```bash
uvx -q --with packaging python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/lockdiff.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/uv.lock.main /home/frankbria/projects/worktrees/issue-821-stale-transitives/backend/uv.lock --all | sed -n '1p'; uvx -q --with packaging python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/lockdiff.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/uv.lock.main /home/frankbria/projects/worktrees/issue-821-stale-transitives/backend/uv.lock --all | grep -E ' (click|certifi|starlette|anyio|cffi|packaging|typing-extensions) '
```

```output
91 -> 90 packages; upgraded 38, downgraded 0, removed ['setuptools'], added []
  anyio 4.14.2 -> 4.15.1
  certifi 2025.7.14 -> 2026.7.22
  cffi 1.17.1 -> 2.1.1
  click 8.2.1 -> 8.5.0
  packaging 25.0 -> 26.3
  starlette 1.6.0 -> 1.7.0
  typing-extensions 4.14.1 -> 4.16.0
```

```bash
cd /home/frankbria/projects/worktrees/issue-821-stale-transitives/backend && uv lock --check 2>&1 | tail -1; grep -c 'exclude-newer' uv.lock | sed 's/^/times the lock mentions exclude-newer: /'
```

```output
Resolved 90 packages in 1ms
times the lock mentions exclude-newer: 0
```

What the command in the issue does on its own, run on a copy of main`s `pyproject.toml` and lock. It takes botocore **down**, because the version already locked is younger than the cut-off, and it writes the cut-off into the lock.

```bash
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/bare && uv lock --upgrade --exclude-newer 2026-09-28T00:00:00Z 2>&1 | grep -E 'Resolved|botocore'; uvx -q --with packaging python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/lockdiff.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/uv.lock.main uv.lock | head -3; grep -n 'exclude-newer' uv.lock
```

```output
Resolved 90 packages in 89ms
Updated botocore v1.43.111 -> v1.43.103
91 -> 90 packages; upgraded 38, downgraded 1, removed ['setuptools'], added []
  DOWNGRADED botocore 1.43.111 -> 1.43.103
6:exclude-newer = "2026-09-28T00:00:00Z"
```

## pip-audit, as CI runs it

On main`s lock and on this branch`s: no advisory in either. The upgrade is about staleness, not about an advisory the gate was showing.

```bash
for name in main branch; do printf '%s: ' $name; python3 -c "import json; d = json.load(open('/tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/pip-audit-$name.json')); print(len(d['dependencies']), 'packages audited,', sum(len(x.get('vulns', [])) for x in d['dependencies']), 'advisories')"; done
```

```output
main: 83 packages audited, 0 advisories
branch: 82 packages audited, 0 advisories
```

## The image built from this branch

It starts, answers its health route with a database beside it, and still redirects. The versions are the upgraded ones. The image scan finds nothing in it.

```bash
docker rm -f aa821-be aa821-mongo >/dev/null 2>&1; docker network create aa821-net >/dev/null 2>&1; docker run -d --name aa821-mongo --network aa821-net mongo:7 >/dev/null; docker run -d --name aa821-be --network aa821-net -p 127.0.0.1:18821:8000 -e ENVIRONMENT=test -e MONGODB_URI=mongodb://aa821-mongo:27017 -e DATABASE_NAME=aa821 -e BETTER_AUTH_SECRET=test-secret-for-ci-minimum-32-characters-long-safe-for-testing -e OPENAI_API_KEY=sk-smoke-test aa821-backend >/dev/null; for _ in $(seq 1 30); do c=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:18821/api/v1/health || true); [ "$c" = 200 ] && break; sleep 2; done; echo "health -> $c"; curl -s --max-time 5 http://127.0.0.1:18821/api/v1/health | cut -c1-60; echo; curl -s -o /dev/null -w 'GET /api/v1/books -> %{http_code}\n' --max-time 5 http://127.0.0.1:18821/api/v1/books; docker exec aa821-be python -c "from importlib.metadata import version; print(' | '.join(f'{name} {version(name)}' for name in ('starlette', 'click', 'certifi', 'anyio')))"; docker rm -f aa821-be aa821-mongo >/dev/null 2>&1; docker network rm aa821-net >/dev/null 2>&1
```

```output
health -> 200
{"status":"healthy","checks":{"mongodb":"ok","config":"ok","

GET /api/v1/books -> 307
starlette 1.7.0 | click 8.5.0 | certifi 2026.7.22 | anyio 4.15.1
```

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo818/scan.sh aa821-backend
```

```output
findings: 0
```

The new CA bundle, loaded the way TLS loads it. The one test that failed on the upgrade had looked for `BEGIN CERTIFICATE` in the bundle`s first 500 characters.

```bash
cd /home/frankbria/projects/worktrees/issue-821-stale-transitives/backend && uv run python -c "import ssl, certifi; print('certifi', certifi.__version__, '-', len(ssl.create_default_context(cafile=certifi.where()).get_ca_certs()), 'roots load'); print('BEGIN CERTIFICATE in the first 500 characters:', 'BEGIN CERTIFICATE' in open(certifi.where()).read(500))" 2>&1 | tail -2
```

```output
certifi 2026.07.22 - 121 roots load
BEGIN CERTIFICATE in the first 500 characters: False
```

## The gate

Against the real baseline: two advisories, both known, both with a reason.

```bash
cd /home/frankbria/projects/worktrees/issue-821-stale-transitives && python3 scripts/audit_gate.py --npm-audit /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/npm-audit.json --pip-audit /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/pip-audit-branch.json --baseline security-baseline.json | grep -v '^$'; echo "exit ${PIPESTATUS[0]}"
```

```output
Scanned 2 advisories against security-baseline.json
PASS — no new advisories (2 known, already in the baseline).
exit 0
```

Against the same baseline with one more entry, for an advisory that is no longer found. On main this was a note and a pass.

```bash
cd /home/frankbria/projects/worktrees/issue-821-stale-transitives && python3 scripts/audit_gate.py --npm-audit /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/npm-audit.json --pip-audit /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/pip-audit-branch.json --baseline /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/baseline-with-a-resolved-entry.json | grep -v '^$' | cut -c1-120; echo "exit ${PIPESTATUS[0]}"
```

```output
Scanned 2 advisories against /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/
Resolved — prune these from the baseline (1):
  [npm] GHSA-0000-0000-gone
FAIL — fix a new advisory, or add its ID to the baseline with a reason if it is accepted debt; prune a resolved entry; g
exit 1
```

```bash
cd /home/frankbria/projects/auto-author && git log --oneline -1 | cut -c1-40 && python3 scripts/audit_gate.py --npm-audit /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/npm-audit.json --pip-audit /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/pip-audit-branch.json --baseline /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/baseline-with-a-resolved-entry.json | grep -v '^$' | cut -c1-120; echo "exit ${PIPESTATUS[0]}"
```

```output
418a7d2 fix(security): the npm advisory 
Scanned 2 advisories against /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/
Resolved — prune these from the baseline:
  [npm] GHSA-0000-0000-gone
PASS — no new advisories (2 known, already in the baseline).
exit 0
```

Against the real baseline with one entry`s reason removed.

```bash
cd /home/frankbria/projects/worktrees/issue-821-stale-transitives && python3 scripts/audit_gate.py --npm-audit /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/npm-audit.json --pip-audit /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/pip-audit-branch.json --baseline /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/baseline-with-no-reason.json | grep -v '^$' | cut -c1-120; echo "exit ${PIPESTATUS[0]}"
```

```output
Scanned 2 advisories against /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/
Baseline entries with no reason (1):
  [npm] GHSA-hp3w-g68c-fv3c
FAIL — fix a new advisory, or add its ID to the baseline with a reason if it is accepted debt; prune a resolved entry; g
exit 1
```

Regenerating a baseline keeps what was written and invents nothing. Here the file with one reason missing is regenerated: the reason that was there is still there, and the empty one is still empty.

```bash
cd /home/frankbria/projects/worktrees/issue-821-stale-transitives && cp /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/baseline-with-no-reason.json /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/regenerated.json && python3 scripts/audit_gate.py --npm-audit /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/npm-audit.json --pip-audit /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/pip-audit-branch.json --baseline /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/regenerated.json --write-baseline && python3 -c "import json; [print(k, '=>', repr(v[:50])) for k, v in json.load(open('/tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/regenerated.json'))['npm'].items()]"
```

```output
Wrote 2 entries to /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo821/regenerated.json
1 of them have no reason yet. The gate fails until each has one.
GHSA-hp3w-g68c-fv3c => ''
GHSA-vfj7-8cjw-p6xm => 'braces 3.0.3 (no patched version, all <=3.0.3 affe'
```

## The baseline is not empty

The Python side is. The npm side has two entries, and neither advisory has a version that fixes it.

```bash
cd /home/frankbria/projects/worktrees/issue-821-stale-transitives && python3 -c "import json; b = json.load(open('security-baseline.json')); print('pypi:', len(b['pypi']), 'entries'); print('npm: ', len(b['npm']), 'entries')"; for g in GHSA-vfj7-8cjw-p6xm GHSA-hp3w-g68c-fv3c; do gh api /advisories/$g --jq '.vulnerabilities[] | "  \(.package.name): vulnerable \(.vulnerable_version_range), first patched version: \(.first_patched_version)"'; done
```

```output
pypi: 0 entries
npm:  2 entries
  braces: vulnerable <= 3.0.3, first patched version: null
  sprintf-js: vulnerable <= 1.1.3, first patched version: null
```

## Tests and CI

The gate`s tests, and this pull request`s own run: the whole backend suite on the upgraded lock, the audit, and the end-to-end suite against a backend running it.

```bash
cd /home/frankbria/projects/worktrees/issue-821-stale-transitives && uvx --with pytest --with pyyaml pytest scripts/test_audit_gate.py -q 2>&1 | tail -1
```

```output
42 passed in 0.05s
```

```bash
cd /home/frankbria/projects/worktrees/issue-821-stale-transitives && gh run view 38357438503 --json headSha,jobs --jq '"commit \(.headSha[0:7])", (.jobs[] | select(.name|test("Backend Tests|Security Audit|E2E Tests")) | "\(.name): \(.conclusion)")'
```

```output
commit 1c02664
Backend Tests: success
Security Audit: success
E2E Tests (Playwright): success
```

```bash
cd /home/frankbria/projects/worktrees/issue-821-stale-transitives && gh run view 38357438503 --log 2>/dev/null | grep -E '^Backend Tests' | grep -E '[0-9]+ passed' | sed -E 's/^[^Z]*Z //' | cut -c1-90 | tail -1
```

```output
========== 1870 passed, 10 skipped, 67 warnings in 123.88s (0:02:03) ===========
```
