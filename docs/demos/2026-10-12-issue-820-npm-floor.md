# Issue #820: the npm advisory gate starts at moderate

*2026-10-13T05:58:08Z by Showboat 0.6.1*
<!-- showboat-id: 5f89ec7b-297c-4bb7-adce-5822640b3eea -->

Three acceptance criteria: pull requests #741 and #742 are merged; the npm gate runs with `--min-severity moderate`; a test asserts the floor.

## The two pull requests the issue names

Both merged two days before this work.

```bash
cd /home/frankbria/projects/auto-author && for n in 741 742; do gh pr view $n --json number,state,mergedAt,title --jq '"#\(.number) \(.state) \(.mergedAt[0:10])  \(.title[0:70])"'; done
```

```output
#741 MERGED 2026-10-10  chore(deps): bump dompurify from 3.4.14 to 3.4.16 in /frontend in the 
#742 MERGED 2026-10-10  chore(deps): bump fast-uri from 3.1.7 to 3.1.8 in /frontend
```

## Before: main

`npm audit` on main`s lockfile, given to the gate as CI gives it. One advisory is seen, it is in the baseline, and the gate passes.

```bash
cd /home/frankbria/projects/auto-author/frontend && npm audit --json > /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo820/audit-main.json 2>/dev/null; cd /home/frankbria/projects/auto-author && git log --oneline -1 | cut -c1-60 && python3 scripts/audit_gate.py --npm-audit /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo820/audit-main.json --baseline security-baseline.json | grep -v '^$'
```

```output
212acae fix(ci): uv is pinned in the image build and install
Scanned 1 advisories against security-baseline.json
PASS — no new advisories (1 known, already in the baseline).
```

The same report with the floor at `moderate`: two advisories the gate had never shown.

```bash
cd /home/frankbria/projects/auto-author && python3 scripts/audit_gate.py --npm-audit /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo820/audit-main.json --baseline security-baseline.json --min-severity moderate | grep -v '^$'; echo "exit ${PIPESTATUS[0]}"
```

```output
Scanned 3 advisories against security-baseline.json
New advisories not in the baseline (2):
  [npm] GHSA-hp3w-g68c-fv3c  sprintf-js  severity=moderate  fix=yes
  [npm] GHSA-rj75-hqrm-r3gf  postcss-selector-parser  severity=moderate  fix=yes
FAIL — fix these, or add each ID to the baseline with a reason if it is accepted debt.
exit 1
```

## After: this branch

The gate with no flag. The floor is `moderate` by default, two advisories are seen, both are in the baseline, and it passes. `postcss-selector-parser` is not among them: it is no longer in npm`s report at all.

```bash
cd /home/frankbria/projects/worktrees/issue-820-npm-floor/frontend && npm audit --json > /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo820/audit-branch.json 2>/dev/null; cd /home/frankbria/projects/worktrees/issue-820-npm-floor && python3 scripts/audit_gate.py --help | grep -A1 -e '--min-severity' | tr -s ' ' | tail -1; python3 scripts/audit_gate.py --npm-audit /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo820/audit-branch.json --baseline security-baseline.json | grep -v '^$'; echo "exit ${PIPESTATUS[0]}"
```

```output
 npm severity floor (default: moderate). Python
Scanned 2 advisories against security-baseline.json
PASS — no new advisories (2 known, already in the baseline).
exit 0
```

```bash
cd /home/frankbria/projects/worktrees/issue-820-npm-floor && python3 -c "import json; d = json.load(open('/tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo820/audit-branch.json'))['vulnerabilities']; print('postcss-selector-parser in the report:', 'postcss-selector-parser' in d); print('sprintf-js in the report:', 'sprintf-js' in d)"
```

```output
postcss-selector-parser in the report: False
sprintf-js in the report: True
```

The one that has no fix, with the reason it is accepted.

```bash
cd /home/frankbria/projects/worktrees/issue-820-npm-floor && python3 -c "import json, textwrap; print(textwrap.fill(json.load(open('security-baseline.json'))['npm']['GHSA-hp3w-g68c-fv3c'], 100))"; gh api /advisories/GHSA-hp3w-g68c-fv3c --jq '.vulnerabilities[] | "\(.package.name): vulnerable \(.vulnerable_version_range), first patched version: \(.first_patched_version)"'
```

```output
sprintf-js 1.0.3 (no patched version, all <=1.1.3 affected; a format string with a huge precision
exhausts memory); test-time only via jest > babel-plugin-istanbul > @istanbuljs/load-nyc-config >
js-yaml 3 > argparse 1, which formats its own fixed help text with it, never input. Prune when
sprintf-js ships a fix or jest's coverage chain drops js-yaml 3.
sprintf-js: vulnerable <= 1.1.3, first patched version: null
```

## The override changes nothing that ships

`@tailwindcss/typography` pins `postcss-selector-parser` at 6.0.10 exactly, and its newest release still does. The override gives it 7.1.6. The plugin uses the parser to write the selectors of the `prose` styles, so the test is the stylesheet: compiled from the same source with each parser.

```bash
cd /home/frankbria/projects/worktrees/issue-820-npm-floor && npm view @tailwindcss/typography@latest version dependencies.postcss-selector-parser 2>/dev/null | tr '\n' ' '; echo; git diff 212acae -- frontend/package.json | grep '^[+-]' | grep -v '^+++\|^---'
```

```output
version = '0.5.20' dependencies.postcss-selector-parser = '6.0.10' 
-    "sharp": "^0.35.5"
+    "sharp": "^0.35.5",
+    "@tailwindcss/typography": {
+      "postcss-selector-parser": "^7.1.6"
+    }
```

```bash
for dir in /home/frankbria/projects/auto-author /home/frankbria/projects/worktrees/issue-820-npm-floor; do cd $dir/frontend && printf 'parser %s: ' $(node -p "require('./node_modules/postcss-selector-parser/package.json').version") && npx @tailwindcss/cli -i ./src/app/globals.css -o /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo820/$(basename $dir).css >/dev/null 2>&1 && sha256sum /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo820/$(basename $dir).css | cut -c1-64 | tr '\n' ' ' && wc -c < /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo820/$(basename $dir).css; done; cmp /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo820/auto-author.css /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo820/issue-820-npm-floor.css && echo 'the two stylesheets are the same file, byte for byte'
```

```output
parser 6.0.10: 39ceda04d1b85ff276993f763ef9f1257e34b7b79a831e0d28e8c1fa4cabad02 129758
parser 7.1.6: 39ceda04d1b85ff276993f763ef9f1257e34b7b79a831e0d28e8c1fa4cabad02 129758
the two stylesheets are the same file, byte for byte
```

## Tests

```bash
cd /home/frankbria/projects/worktrees/issue-820-npm-floor && uvx --with pytest --with pyyaml pytest scripts/test_audit_gate.py -k 'moderate or low_advisory or floor or says_why or below_threshold' -v 2>&1 | grep -E 'PASSED|FAILED|passed|failed' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^scripts.test_audit_gate.py:://' -e 's/^=* //' -e 's/ =*$//'
```

```output
test_parse_npm_audit_filters_below_threshold PASSED
test_a_moderate_advisory_fails_the_gate_without_any_flag PASSED
test_a_low_advisory_is_still_below_the_floor PASSED
test_writing_the_baseline_keeps_its_moderate_entries PASSED
test_ci_runs_the_gate_at_the_moderate_floor PASSED
test_every_entry_in_the_real_baseline_says_why PASSED
6 passed, 28 deselected in 0.03s
```

## CI

This pull request`s own `Security Audit` job: `npm audit`, then the gate at the new floor.

```bash
cd /home/frankbria/projects/worktrees/issue-820-npm-floor && gh run view 38353049282 --json headSha,jobs --jq '"commit \(.headSha[0:7])", (.jobs[] | select(.name == "Security Audit") | "\(.name): \(.conclusion)", (.steps[] | select(.name|test("npm audit|against the baseline|audit gate")) | "    \(.name): \(.conclusion)"))'
```

```output
commit 6553c61
Security Audit: success
    Run npm audit: success
    Check advisories against the baseline: success
    Test the audit gate and dependabot config: success
```

```bash
cd /home/frankbria/projects/worktrees/issue-820-npm-floor && gh run view 38353049282 --log 2>/dev/null | grep 'Check advisories against the baseline' | grep -E 'min-severity|Scanned|PASS|FAIL' | sed -E 's/^[^Z]*Z //; s/\x1b\[[0-9;]*m//g' | cut -c1-110
```

```output
  --min-severity moderate \
Scanned 2 advisories against security-baseline.json
PASS — no new advisories (2 known, already in the baseline).
```
