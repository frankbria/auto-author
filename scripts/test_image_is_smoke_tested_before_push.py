"""Guard: an image is published only after it has been booted (#817).

build-images.yml built and pushed in one step, then ran its smoke test. An
image whose CMD could not start already had its `sha-` tag, and on main the
floating `staging` tag, in the registry by the time the smoke test failed: a
tag the deploy would pull.

The order is now build into the runner's own Docker, boot it, push it. What is
pushed is the image that was booted, not a second build of it.
"""

import os
import re
import subprocess

import pytest

from test_frontend_image_per_environment import BUILD, _load

TAGS = "ghcr.io/owner/auto-author-backend:sha-abc1234\nghcr.io/owner/auto-author-backend:staging"


@pytest.fixture(scope="module")
def steps() -> list[dict]:
    return _load(BUILD)["jobs"]["build"]["steps"]


def _index(steps: list[dict], what: str) -> int:
    found = [i for i, step in enumerate(steps) if what in step.get("name", "") or what in step.get("uses", "")]
    assert len(found) == 1, f"expected one step matching {what!r}, found {len(found)}"
    return found[0]


def _paste(script: str, app: str) -> str:
    """What GitHub does to a script before the runner sees it, for the expressions these steps use."""
    script = script.replace("${{ matrix.app }}", app).replace("${{ steps.meta.outputs.tags }}", TAGS)
    assert "${{" not in script, script
    return script


def _run(script: str, tmp_path, curl_answers: str, **env) -> tuple[int, list[str]]:
    """Run a step's script with `docker`, `curl` and `sleep` replaced; return its exit code and the docker calls."""
    log = tmp_path / "docker.log"
    stubs = tmp_path / "bin"
    stubs.mkdir(exist_ok=True)
    (stubs / "docker").write_text(f'#!/usr/bin/env bash\necho "$*" >> {log}\n')
    (stubs / "curl").write_text(f'#!/usr/bin/env bash\nprintf {curl_answers}\n')
    (stubs / "sleep").write_text("#!/usr/bin/env bash\n")
    for stub in stubs.iterdir():
        stub.chmod(0o755)
    env = {"PATH": f"{stubs}:{os.environ['PATH']}", **env}
    code = subprocess.run(["bash", "-e", "-c", script], env=env, capture_output=True, timeout=60).returncode
    return code, log.read_text().splitlines() if log.exists() else []


def test_the_build_step_keeps_the_image_on_the_runner_and_publishes_nothing(steps):
    build = steps[_index(steps, "docker/build-push-action")]["with"]

    assert build.get("load") is True
    assert build.get("push") in (None, False), build.get("push")


def test_the_image_is_booted_before_it_is_pushed(steps):
    build, smoke, push = (_index(steps, what) for what in ("docker/build-push-action", "Smoke test", "Push"))

    assert build < smoke < push


def test_nothing_else_publishes(steps):
    push = _index(steps, "Push")
    others = [
        step.get("name", step.get("uses"))
        for i, step in enumerate(steps)
        if i != push and re.search(r"docker push|--push\b|push: true", str(step))
    ]

    assert not others, others


def test_a_push_never_follows_a_smoke_test_that_failed_or_did_not_run(steps):
    smoke, push = steps[_index(steps, "Smoke test")], steps[_index(steps, "Push")]

    # A step with no `always()` or `failure()` in its condition is skipped once an earlier step has failed.
    assert not re.search(r"always\(\)|failure\(\)|cancelled\(\)", str(push.get("if", "")))
    assert "continue-on-error" not in smoke and "continue-on-error" not in push
    assert push.get("if") == smoke.get("if"), "the push must run exactly when the smoke test does"


@pytest.mark.parametrize("app", ["backend", "frontend"])
def test_the_smoke_test_fails_an_image_that_does_not_serve(steps, tmp_path, app):
    script = _paste(steps[_index(steps, "Smoke test")]["run"], app)

    code, _ = _run(script, tmp_path, curl_answers="000", NEXT_PUBLIC_API_URL="https://api.example.test")

    assert code != 0


@pytest.mark.parametrize("app", ["backend", "frontend"])
def test_the_smoke_test_passes_an_image_that_serves_and_boots_the_first_tag(steps, tmp_path, app):
    script = _paste(steps[_index(steps, "Smoke test")]["run"], app)

    code, docker = _run(script, tmp_path, curl_answers="200", NEXT_PUBLIC_API_URL="https://api.example.test")

    assert code == 0
    assert any(call.startswith("run -d --name smoke ") and call.endswith(TAGS.splitlines()[0]) for call in docker), docker


def test_the_push_step_pushes_every_tag_and_stops_at_the_first_that_fails(steps, tmp_path):
    push = steps[_index(steps, "Push")]
    assert "${{" not in push["run"], "the tags reach the script as a variable"

    code, docker = _run(push["run"], tmp_path, curl_answers="200", TAGS=TAGS)

    assert code == 0
    assert docker == [f"push {tag}" for tag in TAGS.splitlines()]
