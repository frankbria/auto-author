# Staging's health is probed from outside every 15 minutes (#811)

*2026-10-12T19:19:12Z by Showboat 0.6.1*
<!-- showboat-id: d8bdc089-dc47-4bd7-b9ee-6d0f33f8b013 -->

Most of this issue was already done: a workflow probes staging from a GitHub runner and keeps one labelled issue open while it fails (#916, #776). It ran every six hours, because the alert commented on every failing run. This change makes it every fifteen minutes and stops the comments piling up. The alert script is run here against the real repository in its dry-run mode: the lookups are real and every write is only printed.

```bash
echo 'main:'; grep -n "cron:" /home/frankbria/projects/auto-author/.github/workflows/staging-health.yml | sed 's/^ *//'; echo 'branch:'; grep -n "cron:\|ALERT_QUIET_HOURS" /home/frankbria/projects/worktrees/issue-811-health-probe/.github/workflows/staging-health.yml | sed -E 's/: +/: /'
```

```output
main:
17:    - cron: '23 */6 * * *'
branch:
14:# hours (ALERT_QUIET_HOURS), so the cadence does not flood it.
18: - cron: '*/15 * * * *'
55: ALERT_QUIET_HOURS: '6'
```

The probe itself, unchanged, against staging now, and against an address nothing answers on. A failure exits 1, which is what makes the workflow call the alert.

```bash
cd /home/frankbria/projects/worktrees/issue-811-health-probe; python3 scripts/staging_health_probe.py; echo "exit $?"; API_HEALTH_URL=http://127.0.0.1:9/api/v1/health PROBE_ATTEMPTS=1 PROBE_DELAY=0 python3 scripts/staging_health_probe.py 2>&1 | cut -c1-160 | head -3; echo "exit ${PIPESTATUS[0]}"
```

```output
healthy: https://api.dev.autoauthor.app/api/v1/health, https://dev.autoauthor.app/ and its email provider (attempt 1/3)
exit 0
attempt 1/1 failed: http://127.0.0.1:9/api/v1/health -> None '<urlopen error [Errno 111] Connection refused>'
exit 1
```

A first failure, with no issue open under the probe's label: the script would create the label and the issue, as before.

```bash
cd /home/frankbria/projects/worktrees/issue-811-health-probe; export GH_REPO=frankbria/auto-author ALERT_TITLE="[P0.27.1] Staging health probe is failing" RUN_URL=https://example.invalid/run DRY_RUN=1; ALERT_LABEL=ci-alert:staging-health ALERT_QUIET_HOURS=6 sh scripts/ci-alert-issue.sh failure | head -2 | cut -c1-150
```

```output
DRY-RUN gh label create ci-alert:staging-health --force --color B60205 --description Automated CI alert (one open issue at a time)
DRY-RUN gh issue create --title [P0.27.1] Staging health probe is failing --label ci-alert:staging-health --body Failing run: https://example.invalid/
```

A repeat failure. Two real open issues stand in for the alert issue: one that changed today and one that has been quiet since the start of the month. With the six-hour quiet period the first gets no comment and the second would get one. On main, and for the post-deploy E2E alert, which sets no quiet period, both get a comment.

```bash
cd /home/frankbria/projects/worktrees/issue-811-health-probe; export GH_REPO=frankbria/auto-author ALERT_TITLE="[P0.27.1] Staging health probe is failing" RUN_URL=https://example.invalid/run DRY_RUN=1; for label in needs-operator blocked; do echo "the open issue labelled $label: $(gh api "repos/$GH_REPO/issues?labels=$label&state=open&per_page=1" --jq '.[0] | "#\(.number), last changed \(.updated_at[0:10])"')"; echo "  quiet period of 6 hours: $(ALERT_LABEL=$label ALERT_QUIET_HOURS=6 sh scripts/ci-alert-issue.sh failure | sed -E 's/last changed at [0-9TZ:-]+/last changed recently/')"; echo "  no quiet period:         $(ALERT_LABEL=$label sh scripts/ci-alert-issue.sh failure)"; done
```

```output
the open issue labelled needs-operator: #992, last changed 2026-10-12
  quiet period of 6 hours: Still failing; #992 last changed recently, inside the 6-hour quiet period. No comment.
  no quiet period:         DRY-RUN gh issue comment 992 --body Still failing: https://example.invalid/run
the open issue labelled blocked: #583, last changed 2026-10-01
  quiet period of 6 hours: DRY-RUN gh issue comment 583 --body Still failing: https://example.invalid/run
  no quiet period:         DRY-RUN gh issue comment 583 --body Still failing: https://example.invalid/run
```

Recovery is not held back by the quiet period: the next healthy run comments and closes.

```bash
cd /home/frankbria/projects/worktrees/issue-811-health-probe; export GH_REPO=frankbria/auto-author ALERT_TITLE="[P0.27.1] Staging health probe is failing" RUN_URL=https://example.invalid/run DRY_RUN=1; ALERT_LABEL=needs-operator ALERT_QUIET_HOURS=6 sh scripts/ci-alert-issue.sh recovery | sed -E 's/[0-9]+ --body/N --body/; s/close [0-9]+/close N/'
```

```output
DRY-RUN gh issue comment N --body Recovered on a green run: https://example.invalid/run
DRY-RUN gh issue close N
```

The same behaviour as tests.

```bash
cd /home/frankbria/projects/worktrees/issue-811-health-probe && uvx --quiet --with pyyaml --with pytest pytest scripts/test_ci_alert_issue.py scripts/test_staging_triggers.py -q 2>&1 | tail -1 | sed -E 's/ in [0-9.]+s//'
```

```output
23 passed
```
