#!/usr/bin/env python3
"""Was the previous staging health run also a failed probe? (two-strike alert)

A single failed probe is usually a short network blip between GitHub's runners
and the staging host: of 45 failures from Oct 14 to Nov 21, 2026 almost all
were one run between two green ones, and the box was healthy each time. So the
workflow alerts only on the second failed probe in a row, about 15 to 30
minutes into a real outage.

This script runs only after a failed probe. It finds the latest earlier run of
this workflow that reached a verdict and writes `strike=2` to $GITHUB_OUTPUT if
that run's probe failed too, else `strike=1`. A run's probe failed if either of
the two steps below ran: the first-strike step (which ends green) or the
second-strike step (which fails the run). Step names, not the run's colour,
because a strike-1 run is green on purpose and a run can go red for other
reasons, such as a failed checkout.

If GitHub cannot be asked, it answers 2: alerting on one failure is the old
behaviour, never a missed outage.

Run (in the workflow): python3 scripts/staging_health_strike.py
Env: GH_REPO, RUN_ID, WORKFLOW_FILE (default staging-health.yml), GITHUB_OUTPUT
"""

import json
import os
import subprocess
import sys

# These must match the step names in .github/workflows/staging-health.yml
# (scripts/test_staging_triggers.py checks they do).
FIRST_STRIKE_STEP = "First failed probe: not alerting yet"
SECOND_STRIKE_STEP = "Fail the run: probe failed twice in a row"

VERDICTS = {"success", "failure"}


def previous_probe_failed(steps):
    """True if a run whose job steps are `steps` had a failed probe."""
    for step in steps:
        if step.get("name") == FIRST_STRIKE_STEP and step.get("conclusion") == "success":
            return True
        if step.get("name") == SECOND_STRIKE_STEP and step.get("conclusion") == "failure":
            return True
    return False


def previous_run(runs, current_id):
    """The latest earlier run that reached a verdict (cancelled runs are skipped)."""
    for run in runs:
        if str(run.get("id")) != str(current_id) and run.get("conclusion") in VERDICTS:
            return run
    return None


def gh_json(path):
    out = subprocess.run(["gh", "api", path], check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def strike():
    repo = os.environ["GH_REPO"]
    current = os.environ.get("RUN_ID", "")
    workflow = os.environ.get("WORKFLOW_FILE", "staging-health.yml")
    runs = gh_json(f"repos/{repo}/actions/workflows/{workflow}/runs?status=completed&per_page=10")
    run = previous_run(runs.get("workflow_runs", []), current)
    if run is None:
        return 1
    jobs = gh_json(f"repos/{repo}/actions/runs/{run['id']}/jobs")
    steps = [step for job in jobs.get("jobs", []) for step in job.get("steps", [])]
    return 2 if previous_probe_failed(steps) else 1


def main():
    try:
        result = strike()
        print(f"strike {result}: previous probe {'failed' if result == 2 else 'did not fail'}")
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError) as err:
        result = 2
        print(f"strike 2: could not read the previous run ({err}), so alerting as before")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a") as fh:
            fh.write(f"strike={result}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
