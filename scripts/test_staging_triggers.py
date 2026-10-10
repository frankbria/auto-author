"""When the staging E2E suite and the staging health probe run (#916).

The E2E suite used to run every 6 hours against a build that had not changed in
weeks, spending live OpenAI calls to re-test it. It now runs after each
successful staging deploy, on the deployed commit. Infra drift between deploys
(the Atlas credential outage, #537) is the job of a separate, AI-free probe.

The probe is exercised against a local HTTP server standing in for staging.

Run: uvx --with pytest --with pyyaml pytest scripts/test_staging_triggers.py -q
"""

import json
import os
import re
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
WORKFLOWS = REPO / ".github" / "workflows"
E2E = WORKFLOWS / "e2e-staging-tests.yml"
DEPLOY = WORKFLOWS / "deploy-staging-containers.yml"
HEALTH = WORKFLOWS / "staging-health.yml"
PROBE = REPO / "scripts" / "staging_health_probe.py"


def load(path):
    wf = yaml.safe_load(path.read_text())
    # PyYAML reads the bare key `on:` as the boolean True (YAML 1.1).
    return wf, wf.get(True) or wf["on"]


def test_staging_e2e_runs_after_deploy_not_on_a_schedule():
    _, on = load(E2E)
    assert "schedule" not in on
    deploy_name = yaml.safe_load(DEPLOY.read_text())["name"]
    # workflow_run matches by the deploy workflow's `name:`; a rename there would
    # silently stop every post-deploy run, so the two are compared, not hardcoded.
    assert on["workflow_run"] == {"workflows": [deploy_name], "types": ["completed"]}
    assert "workflow_dispatch" in on and "pull_request" in on


def test_post_deploy_run_needs_a_green_deploy_and_tests_its_commit():
    wf, _ = load(E2E)
    job = wf["jobs"]["e2e-staging"]
    cond = " ".join(job["if"].split())
    assert "github.event.workflow_run.conclusion == 'success'" in cond
    assert "github.event.workflow_run.head_repository.full_name == github.repository" in cond
    # The #191 fork guard for labelled PRs is unchanged.
    assert "contains(github.event.pull_request.labels.*.name, 'e2e-staging')" in cond
    assert "github.event.pull_request.head.repo.full_name == github.repository" in cond
    checkout = next(s for s in job["steps"] if s.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["ref"] == "${{ github.event.workflow_run.head_sha }}"


def test_health_probe_is_scheduled_ai_free_and_alerts_with_its_own_label():
    wf, on = load(HEALTH)
    assert on["schedule"] and "workflow_dispatch" in on
    assert wf["permissions"] == {"contents": "read"}
    text = HEALTH.read_text()
    assert not re.search(r"\bsecrets\.\w", text), "public URLs only: the probe needs no secret"
    (job,) = wf["jobs"].values()
    assert job["permissions"] == {"contents": "read", "issues": "write"}
    probe = next(s for s in job["steps"] if "staging_health_probe.py" in s.get("run", ""))
    alert = next(s for s in job["steps"] if "ci-alert-issue.sh" in s.get("run", ""))
    assert probe["id"] == "probe"
    # Alert only on a real verdict: a skipped probe (checkout failed) or a
    # cancelled run must not read as "recovered" and close the issue.
    assert "steps.probe.outcome == 'failure'" in alert["if"]
    assert "steps.probe.outcome == 'success'" in alert["if"]
    assert alert["env"]["ALERT_LABEL"] == "ci-alert:staging-health"
    assert alert["env"]["ALERT_TITLE"].startswith("[P0.27.1] ")


class Staging(BaseHTTPRequestHandler):
    """Answers /health and / from the server's `answers` script, one per hit."""

    def do_GET(self):
        script = self.server.answers[self.path]
        status, body = script.pop(0) if len(script) > 1 else script[0]
        self.server.hits[self.path] = self.server.hits.get(self.path, 0) + 1
        self.send_response(status)
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *args):
        pass


HEALTHY = (200, json.dumps({"status": "healthy", "checks": {"mongodb": "ok", "config": "ok"}}))
UNHEALTHY = (
    503,
    json.dumps({"status": "unhealthy", "checks": {"mongodb": "error: OperationFailure", "config": "ok"}}),
)
PAGE = (200, "<html>ok</html>")


@pytest.fixture
def staging():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Staging)
    server.hits = {}
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.shutdown()


def probe(server, health, frontend, attempts=2):
    server.answers = {"/health": list(health), "/": list(frontend)}
    base = f"http://127.0.0.1:{server.server_address[1]}"
    env = {
        **os.environ,
        "API_HEALTH_URL": f"{base}/health",
        "FRONTEND_URL": f"{base}/",
        "PROBE_ATTEMPTS": str(attempts),
        "PROBE_DELAY": "0",
    }
    return subprocess.run([sys.executable, str(PROBE)], env=env, capture_output=True, text=True)


def test_probe_passes_when_api_is_healthy_and_frontend_serves(staging):
    result = probe(staging, [HEALTHY], [PAGE])
    assert result.returncode == 0, result.stdout + result.stderr


def test_probe_fails_on_unhealthy_api_and_names_the_failing_check(staging):
    result = probe(staging, [UNHEALTHY], [PAGE])
    assert result.returncode == 1
    assert "OperationFailure" in result.stdout
    assert staging.hits["/health"] == 2, "every attempt is used before failing"


def test_probe_fails_when_health_answers_200_without_a_healthy_verdict(staging):
    # e.g. nginx serving the frontend's HTML on the API host after a bad config
    result = probe(staging, [(200, "<html>not the api</html>")], [PAGE])
    assert result.returncode == 1


def test_probe_fails_when_frontend_root_is_not_200(staging):
    result = probe(staging, [HEALTHY], [(502, "Bad Gateway")])
    assert result.returncode == 1
    assert "502" in result.stdout


def test_probe_rides_out_one_transient_failure(staging):
    result = probe(staging, [UNHEALTHY, HEALTHY], [PAGE], attempts=3)
    assert result.returncode == 0, result.stdout
    assert staging.hits["/health"] == 2


def test_probe_fails_when_staging_is_unreachable():
    env = {
        **os.environ,
        "API_HEALTH_URL": "http://127.0.0.1:9/health",
        "FRONTEND_URL": "http://127.0.0.1:9/",
        "PROBE_ATTEMPTS": "1",
        "PROBE_DELAY": "0",
    }
    result = subprocess.run([sys.executable, str(PROBE)], env=env, capture_output=True, text=True)
    assert result.returncode == 1
