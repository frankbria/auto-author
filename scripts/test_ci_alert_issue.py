"""Behaviour + wiring tests for the CI alert-issue helper (#776).

`gh` is replaced by a recording stub on PATH (the one third-party boundary);
the stub's `issue list` answer is driven by FAKE_OPEN so each state is covered.
"""

import os
import subprocess
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "ci-alert-issue.sh"
WORKFLOW = REPO / ".github" / "workflows" / "e2e-staging-tests.yml"

STUB = """#!/bin/sh
echo "$@" >> "$GH_LOG"
if [ "$1" = "api" ]; then echo "$FAKE_OPEN"; fi
"""


def run(tmp_path, mode, open_issue=""):
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


def test_recovery_comments_and_closes_open_issue(tmp_path):
    lines = run(tmp_path, "recovery", open_issue="42")
    assert writes(lines) == ["issue comment", "issue close"]


def test_recovery_with_nothing_open_does_nothing(tmp_path):
    assert writes(run(tmp_path, "recovery")) == []


def test_workflow_alert_job_is_least_privilege_and_scheduled_only():
    wf = yaml.safe_load(WORKFLOW.read_text())
    assert wf["permissions"] == {"contents": "read"}
    job = wf["jobs"]["alert"]
    assert job["permissions"] == {"contents": "read", "issues": "write"}
    assert "e2e-staging" in job["needs"]
    assert "schedule" in job["if"] and "always()" in job["if"]
    assert "issues" not in wf["jobs"]["e2e-staging"].get("permissions", {})
