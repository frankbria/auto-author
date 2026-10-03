"""Guard: compose never supplies a default ENVIRONMENT (#777).

`${ENVIRONMENT:-staging}` meant a box whose .env forgot the marker started as
staging, and the backend's production guards key off that marker. Compose must
require it, so every workflow that brings the stack up has to name it.
"""

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
WORKFLOWS = REPO / ".github" / "workflows"


def test_compose_requires_environment_with_no_default():
    compose = yaml.safe_load((REPO / "docker-compose.yml").read_text())
    value = compose["services"]["backend"]["environment"]["ENVIRONMENT"]

    assert value.startswith("${ENVIRONMENT:?"), value


def test_every_workflow_that_runs_compose_up_exports_environment():
    # A deploy that reaches `compose up` without ENVIRONMENT now aborts during
    # interpolation; catch that here rather than on the box.
    runs_up = [
        wf for wf in WORKFLOWS.glob("*.yml")
        if re.search(r"^[^#\n]*docker compose\b[^\n]*\bup\b", wf.read_text(), re.M)
    ]

    assert runs_up, "no workflow runs `docker compose up`; this guard is vacuous"
    for wf in runs_up:
        assert re.search(
            r"export ENVIRONMENT=(development|test|staging|production)\b", wf.read_text()
        ), wf.name


def test_backend_image_smoke_run_sets_environment():
    # The smoke test boots the backend image with `docker run`, not compose, and
    # the backend refuses to import without ENVIRONMENT. It must be a non-deployed
    # value: the smoke BETTER_AUTH_SECRET is the committed CI secret.
    text = (WORKFLOWS / "build-images.yml").read_text()
    backend_run = re.search(r"docker run -d --name smoke --network smoke-net(.*?)\"\$TAG\"", text, re.S)

    assert backend_run, "backend smoke `docker run` not found; this guard is vacuous"
    assert re.search(r"-e ENVIRONMENT=(test|development)\b", backend_run.group(1))
