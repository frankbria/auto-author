"""Behaviour + wiring tests for the CI alert-issue helper (#776).

`gh` is replaced by a recording stub on PATH (the one third-party boundary);
the stub's `issue list` answer is driven by FAKE_OPEN so each state is covered.
"""

import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "ci-alert-issue.sh"
WORKFLOW = REPO / ".github" / "workflows" / "e2e-staging-tests.yml"

STUB = """#!/bin/sh
echo "$@" >> "$GH_LOG"
case "$1 $2" in
  "api repos/o/r/issues?"*) echo "$FAKE_OPEN" ;;
  "api repos/o/r/issues/"*) [ -z "${FAKE_UPDATED_FAILS:-}" ] || exit 1; echo "$FAKE_UPDATED" ;;
esac
"""


def hours_ago(hours):
    then = datetime.now(timezone.utc) - timedelta(hours=hours)
    return then.strftime("%Y-%m-%dT%H:%M:%SZ")


def run(tmp_path, mode, open_issue="", **extra):
    gh = tmp_path / "gh"
    gh.write_text(STUB)
    gh.chmod(0o755)
    log = tmp_path / "log"
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "GH_LOG": str(log),
        "FAKE_OPEN": open_issue,
        "GH_REPO": "o/r",
        "ALERT_LABEL": "ci-alert:test",
        "ALERT_TITLE": "[P0.28] Test alert",
        "RUN_URL": "https://example.test/run/1",
        **extra,
    }
    subprocess.run(["sh", str(SCRIPT), mode], env=env, check=True)
    return log.read_text().splitlines() if log.exists() else []


def writes(lines):
    cmds = ("label create", "issue create", "issue comment", "issue close")
    return [" ".join(line.split()[:2]) for line in lines if line.startswith(cmds)]


def test_failure_with_no_open_issue_creates_one(tmp_path):
    lines = run(tmp_path, "failure")
    assert writes(lines) == ["label create", "issue create"]
    create = next(line for line in lines if line.startswith("issue create"))
    assert "--label ci-alert:test" in create and "[P0.28] Test alert" in create


def test_repeated_failure_comments_instead_of_creating(tmp_path):
    lines = run(tmp_path, "failure", open_issue="42")
    lookup = next(line for line in lines if line.startswith("api"))
    assert "labels=ci-alert:test&state=open" in lookup
    assert writes(lines) == ["issue comment"]
    assert lines[-1].startswith("issue comment 42")


# P1.29 (#811): the health probe runs every 15 minutes. Commenting on every
# failing run would be 96 comments a day on an issue that is already open.
def test_a_repeat_failure_inside_the_quiet_period_writes_nothing(tmp_path):
    lines = run(tmp_path, "failure", open_issue="42", ALERT_QUIET_HOURS="6", FAKE_UPDATED=hours_ago(1))

    assert any(line.startswith("api repos/o/r/issues/42") for line in lines), "it has to ask when the issue last changed"
    assert writes(lines) == []


def test_a_repeat_failure_after_the_quiet_period_comments_once_more(tmp_path):
    lines = run(tmp_path, "failure", open_issue="42", ALERT_QUIET_HOURS="6", FAKE_UPDATED=hours_ago(7))

    assert writes(lines) == ["issue comment"]


def test_when_the_issue_cannot_be_read_the_failure_is_still_reported(tmp_path):
    """Not knowing when it last changed must not silence the alert or fail the step."""
    lines = run(tmp_path, "failure", open_issue="42", ALERT_QUIET_HOURS="6", FAKE_UPDATED_FAILS="1")

    assert writes(lines) == ["issue comment"]


def test_the_first_failure_opens_the_issue_whatever_the_quiet_period(tmp_path):
    assert writes(run(tmp_path, "failure", ALERT_QUIET_HOURS="6")) == ["label create", "issue create"]


def test_recovery_closes_at_once_even_inside_the_quiet_period(tmp_path):
    lines = run(tmp_path, "recovery", open_issue="42", ALERT_QUIET_HOURS="6", FAKE_UPDATED=hours_ago(1))

    assert writes(lines) == ["issue comment", "issue close"]


def test_recovery_comments_and_closes_open_issue(tmp_path):
    lines = run(tmp_path, "recovery", open_issue="42")
    assert writes(lines) == ["issue comment", "issue close"]


def test_recovery_with_nothing_open_does_nothing(tmp_path):
    assert writes(run(tmp_path, "recovery")) == []


def test_workflow_alert_job_is_least_privilege_and_fires_after_deploy():
    wf = yaml.safe_load(WORKFLOW.read_text())
    assert wf["permissions"] == {"contents": "read"}
    job = wf["jobs"]["alert"]
    assert job["permissions"] == {"contents": "read", "issues": "write"}
    assert "e2e-staging" in job["needs"]
    cond = " ".join(job["if"].split())
    # #916: post-deploy runs replaced the schedule; a manual dispatch from the
    # default branch also reports, so a green rerun closes the issue.
    assert "github.event_name == 'workflow_run'" in cond and "always()" in cond
    assert "github.event_name == 'workflow_dispatch'" in cond
    assert "github.ref_name == github.event.repository.default_branch" in cond
    assert "schedule" not in cond
    # Labelled-PR runs never alert: a red feature branch is not a staging outage.
    assert "pull_request" not in cond
    step = next(s for s in job["steps"] if "ci-alert-issue.sh" in s.get("run", ""))
    assert step["env"]["ALERT_LABEL"] == "ci-alert:staging-e2e"
    assert "issues" not in wf["jobs"]["e2e-staging"].get("permissions", {})
