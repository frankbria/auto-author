"""Two-strike staging alert: the decision script and its workflow wiring.

`gh` is replaced by a stub on PATH that serves canned run and job lists, so the
script is run as the workflow runs it. The wiring tests pin the step names the
script looks for, since a renamed step would silently make every failure a
first strike (no alert, ever).

Run: uvx --with pytest --with pyyaml pytest scripts/test_staging_health_strike.py -q
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "staging_health_strike.py"
HEALTH = REPO / ".github" / "workflows" / "staging-health.yml"

sys.path.insert(0, str(REPO / "scripts"))
import staging_health_strike as strike

STUB = """#!/bin/sh
[ -z "${FAKE_GH_FAILS:-}" ] || exit 1
case "$2" in
  *"/runs?"*) cat "$FAKE_RUNS" ;;
  *"/jobs") cat "$FAKE_JOBS" ;;
  *) exit 1 ;;
esac
"""

FIRST = {"name": strike.FIRST_STRIKE_STEP}
SECOND = {"name": strike.SECOND_STRIKE_STEP}


def steps(first="skipped", second="skipped"):
    return [
        {"name": "Probe API health and frontend root", "conclusion": "success"},
        {**FIRST, "conclusion": first},
        {"name": "Open, update or close the alert issue", "conclusion": "success"},
        {**SECOND, "conclusion": second},
    ]


def run(tmp_path, runs, job_steps, **extra):
    gh = tmp_path / "gh"
    gh.write_text(STUB)
    gh.chmod(0o755)
    (tmp_path / "runs.json").write_text(json.dumps({"workflow_runs": runs}))
    (tmp_path / "jobs.json").write_text(json.dumps({"jobs": [{"steps": job_steps}]}))
    out = tmp_path / "output"
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "FAKE_RUNS": str(tmp_path / "runs.json"),
        "FAKE_JOBS": str(tmp_path / "jobs.json"),
        "GH_REPO": "o/r",
        "RUN_ID": "100",
        "GITHUB_OUTPUT": str(out),
        **extra,
    }
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    return out.read_text()


PREVIOUS = [{"id": 99, "conclusion": "success"}]


def test_previous_green_run_makes_this_failure_strike_one(tmp_path):
    assert run(tmp_path, PREVIOUS, steps()) == "strike=1\n"


def test_previous_first_strike_makes_this_failure_strike_two(tmp_path):
    # The first strike's run is green on purpose, so its colour says nothing.
    assert run(tmp_path, PREVIOUS, steps(first="success")) == "strike=2\n"


def test_an_ongoing_outage_keeps_alerting(tmp_path):
    runs = [{"id": 99, "conclusion": "failure"}]
    assert run(tmp_path, runs, steps(second="failure")) == "strike=2\n"


def test_a_red_run_for_another_reason_is_not_a_strike(tmp_path):
    # e.g. checkout failed: the probe never ran, so neither strike step did.
    runs = [{"id": 99, "conclusion": "failure"}]
    assert run(tmp_path, runs, steps()) == "strike=1\n"


def test_no_earlier_run_is_strike_one(tmp_path):
    assert run(tmp_path, [], steps(first="success")) == "strike=1\n"


def test_unreadable_history_alerts_as_before(tmp_path):
    assert run(tmp_path, PREVIOUS, steps(), FAKE_GH_FAILS="1") == "strike=2\n"


def test_cancelled_and_current_runs_are_skipped():
    runs = [
        {"id": 100, "conclusion": None},
        {"id": 98, "conclusion": "cancelled"},
        {"id": 97, "conclusion": "success"},
    ]
    assert strike.previous_run(runs, "100")["id"] == 97


@pytest.mark.parametrize(
    "first, second, failed",
    [("skipped", "skipped", False), ("success", "skipped", True), ("skipped", "failure", True)],
)
def test_previous_probe_failed_reads_only_the_strike_steps(first, second, failed):
    assert strike.previous_probe_failed(steps(first, second)) is failed


def workflow_steps():
    wf = yaml.safe_load(HEALTH.read_text())
    (job,) = wf["jobs"].values()
    return {s.get("name"): s for s in job["steps"]}


def test_workflow_step_names_match_what_the_script_reads():
    named = workflow_steps()
    assert strike.FIRST_STRIKE_STEP in named
    assert strike.SECOND_STRIKE_STEP in named


def test_workflow_alerts_and_fails_only_on_strike_two():
    named = workflow_steps()
    probe = next(s for s in named.values() if s.get("id") == "probe")
    check = next(s for s in named.values() if s.get("id") == "strike")
    alert = next(s for s in named.values() if "ci-alert-issue.sh" in s.get("run", ""))
    first, second = named[strike.FIRST_STRIKE_STEP], named[strike.SECOND_STRIKE_STEP]
    # A failed probe alone must not turn the run red.
    assert probe["continue-on-error"] is True
    assert "staging_health_strike.py" in check["run"]
    assert check["if"] == "steps.probe.outcome == 'failure'"
    assert "steps.strike.outputs.strike == '1'" in first["if"]
    for step in (alert, second):
        assert "steps.strike.outputs.strike == '2'" in step["if"]
    assert "exit 1" in second["run"]
