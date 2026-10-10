"""Production deploy: gated, validated, and unable to borrow staging's config (#782).

The Clerk-era `deploy-production.tbd` deployed nothing (`echo ... # Add your
deployment commands here`). Its replacement runs on a box that serves paying
users, so the properties below are the ones whose absence would not show up as a
red run: a deploy that starts without approval, pulls a tag nobody built, falls
back to a staging secret, or brings the stack up as staging all "succeed".

Run: uvx --with pytest --with pyyaml pytest scripts/test_deploy_production_workflow.py -q
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
WORKFLOWS = REPO / ".github" / "workflows"
WORKFLOW = WORKFLOWS / "deploy-production-containers.yml"
OVERLAY = REPO / "docker-compose.production.yml"
TAG_STEP = "Validate image tag"


@pytest.fixture(scope="module")
def wf() -> dict:
    return yaml.safe_load(WORKFLOW.read_text())


@pytest.fixture(scope="module")
def job(wf: dict) -> dict:
    assert list(wf["jobs"]) == ["deploy"], "expected exactly one job"
    return wf["jobs"]["deploy"]


@pytest.fixture(scope="module")
def steps(job: dict) -> list[dict]:
    return job["steps"]


def _step(steps: list[dict], name: str) -> dict:
    found = [s for s in steps if s.get("name") == name]
    assert len(found) == 1, f"expected exactly one step named {name!r}"
    return found[0]


def _run_tag_check(steps: list[dict], tag: str) -> subprocess.CompletedProcess:
    # The step's own script, run the way Actions runs a bash `run:` block.
    script = _step(steps, TAG_STEP)["run"]
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", script],
        env={"IMAGE_TAG": tag, "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )


def test_the_clerk_era_scaffold_is_gone():
    assert not (WORKFLOWS / "deploy-production.tbd").exists()


def test_manual_dispatch_only_with_a_required_tag(wf: dict):
    # PyYAML reads the bare key `on` as boolean True.
    on = wf.get("on", wf.get(True))
    assert list(on) == ["workflow_dispatch"], "production must never deploy on push/schedule"
    tag = on["workflow_dispatch"]["inputs"]["image_tag"]
    assert tag["required"] is True and tag["type"] == "string"


def test_runs_in_the_production_environment(job: dict):
    # Required reviewers and the main-only branch policy live on this environment.
    assert job["environment"]["name"] == "production"


def test_least_privilege_and_no_racing_deploys(wf: dict):
    assert wf["permissions"] == {"contents": "read"}
    assert wf["concurrency"] == {"group": "deploy-production", "cancel-in-progress": False}


@pytest.mark.parametrize("tag", ["sha-abc1234", "sha-0123456789abcdef0123456789abcdef01234567"])
def test_tag_validation_accepts_a_sha_tag(steps: list[dict], tag: str):
    result = _run_tag_check(steps, tag)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "tag",
    [
        "",
        "latest",
        "staging",
        "sha-abc123",  # too short
        "sha-ABC1234",  # metadata-action emits lowercase
        "sha-abc1234-production",  # the overlay appends the suffix itself
        "sha-abc1234-staging",
        "sha-abc1234; rm -rf /",
        "sha-abc1234'$(id)'",
        "sha-abc1234\nsha-def5678",
    ],
)
def test_tag_validation_rejects_anything_else(steps: list[dict], tag: str):
    result = _run_tag_check(steps, tag)
    assert result.returncode != 0, f"accepted {tag!r}"
    assert "::error::" in result.stdout


def test_tag_is_validated_before_any_secret_is_touched(steps: list[dict]):
    first = next(i for i, s in enumerate(steps) if "secrets." in yaml.safe_dump(s))
    assert steps.index(_step(steps, TAG_STEP)) < first


def test_the_input_never_reaches_a_script_by_interpolation():
    # `${{ inputs.x }}` inside `run:` is pasted into the script before bash sees
    # it, so the validation could be bypassed by the value it validates. It may
    # only arrive through `env:`.
    for lineno, line in enumerate(WORKFLOW.read_text().splitlines(), 1):
        if "inputs." in line and "${{" in line:
            assert re.match(r"\s*IMAGE_TAG: \$\{\{ inputs\.image_tag \}\}\s*$", line), (
                f"line {lineno}: {line.strip()}"
            )


def test_secrets_never_fall_back_to_staging_names():
    # An environment secret that is unset resolves to the REPOSITORY secret of the
    # same name, and the repo-level SSH_KEY/USER/HOST are staging's.
    names = set(re.findall(r"secrets\.([A-Za-z0-9_]+)", WORKFLOW.read_text()))
    assert names, "no secrets referenced; parser is broken"
    assert all(n.startswith("PRODUCTION_") for n in names), sorted(names)


def test_preflight_requires_main_and_every_production_setting(steps: list[dict]):
    preflight = _step(steps, "Require main and production configuration")
    assert "refs/heads/main" in preflight["run"] and "exit 1" in preflight["run"]
    referenced = set(re.findall(r"(?:secrets|vars)\.([A-Z0-9_]+)", WORKFLOW.read_text()))
    assert referenced <= set(preflight["env"]), referenced - set(preflight["env"])


def test_host_key_is_pinned_not_trusted_on_first_use(steps: list[dict]):
    ssh = _step(steps, "Setup SSH")["run"]
    assert "StrictHostKeyChecking yes" in ssh
    assert "accept-new" not in WORKFLOW.read_text()


def test_every_compose_call_is_production(steps: list[dict]):
    compose_steps = [s for s in steps if "docker compose" in s.get("run", "")]
    assert len(compose_steps) >= 3, "pull/up, health logs and the env check all use compose"
    for s in compose_steps:
        run = s["run"]
        # docker-compose.yml requires ENVIRONMENT with no default (#777).
        assert "export ENVIRONMENT=production" in run, s["name"]
        for line in run.splitlines():
            if "docker compose" in line:
                assert "-f docker-compose.production.yml" in line, (s["name"], line)
    assert "docker-compose.staging.yml" not in WORKFLOW.read_text()


def test_ships_the_production_overlay(steps: list[dict]):
    run = _step(steps, "Ship compose files")["run"]
    assert "docker-compose.yml docker-compose.production.yml" in run


def test_health_check_then_secret_check_then_prune(steps: list[dict]):
    names = [s.get("name") for s in steps]
    order = ["Pull and start", "Health check", "Frontend carries no backend secret", "Prune old images"]
    assert [n for n in names if n in order] == order


def test_frontend_secret_check_cannot_pass_vacuously(steps: list[dict]):
    # Same check as staging (#781): read names only, and fail if the read is empty.
    run = _step(steps, "Frontend carries no backend secret")["run"]
    assert "grep -qx DATABASE_URL" in run
    assert "OPENAI|STRIPE|AWS|CLOUDINARY" in run


def test_summary_names_the_rollback_target(steps: list[dict]):
    summary = _step(steps, "Summary")
    assert summary["if"] == "always()"
    record = _step(steps, "Record running tag")
    assert record["id"] in summary["env"]["PREVIOUS_TAG"]
    assert "PREVIOUS_TAG" in summary["run"] and "rollback" in summary["run"]


def _run_summary(steps: list[dict], tag: str, tmp_path: Path) -> str:
    out = tmp_path / "summary.md"
    subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", _step(steps, "Summary")["run"]],
        env={"PATH": "/usr/bin:/bin", "IMAGE_TAG": tag, "PREVIOUS_TAG": "",
             "STATUS": "failure", "GITHUB_STEP_SUMMARY": str(out)},
        check=True,
    )
    return out.read_text()


@pytest.mark.parametrize(
    "tag",
    ["sha-abc1234\n- result: success", 'sha-abc1234 <img src="https://x.example/p">', "latest"],
)
def test_summary_never_echoes_a_rejected_tag(steps: list[dict], tag: str, tmp_path: Path):
    # The summary runs with `if: always()`, so it also runs after validation has
    # rejected the tag. GitHub renders it as markdown: a rejected value must not
    # reach the deploy record.
    summary = _run_summary(steps, tag, tmp_path)
    assert tag not in summary and "success" not in summary and "<img" not in summary
    assert "rejected" in summary


def test_summary_shows_a_valid_tag(steps: list[dict], tmp_path: Path):
    summary = _run_summary(steps, "sha-abc1234", tmp_path)
    assert "`sha-abc1234`" in summary and "`sha-abc1234-production`" in summary


def test_overlay_pins_production_images():
    services = yaml.safe_load(OVERLAY.read_text())["services"]
    backend, frontend = services["backend"]["image"], services["frontend"]["image"]
    assert backend.startswith("ghcr.io/frankbria/auto-author-backend:${IMAGE_TAG:?"), backend
    assert backend.endswith("}"), backend
    # One frontend image per environment (#779): NEXT_PUBLIC_* is baked at build.
    assert frontend.startswith("ghcr.io/frankbria/auto-author-frontend:${IMAGE_TAG:?"), frontend
    assert frontend.endswith("}-production"), frontend


def test_overlay_requires_the_auth_url():
    # The base file defaults BETTER_AUTH_URL to the staging origin; on production
    # that scopes the session cookie to the staging box (#778's class of bug).
    env = yaml.safe_load(OVERLAY.read_text())["services"]["frontend"]["environment"]
    assert env["BETTER_AUTH_URL"].startswith("${BETTER_AUTH_URL:?"), env["BETTER_AUTH_URL"]
