"""One frontend image per environment (#779).

Next inlines NEXT_PUBLIC_* into the client bundle at build time, so a frontend
image is only valid for the environment whose values it was built with. Before
#779 build-images.yml baked in repo-level vars with staging hostnames as the
fallback and tagged the result `sha-*` and `staging`: there was no way to get a
production image without repointing staging, and a missing var silently shipped
staging hosts.

The failure this guards against is quiet: a fallback reappearing in the build
args, or a variant losing its environment scope, still builds green and still
boots. It only shows up when a production browser calls the staging API.

Run: uvx --with pytest --with pyyaml pytest scripts/test_frontend_image_per_environment.py -q
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / ".github" / "workflows" / "build-images.yml"
COMPOSE_BUILD = ROOT / "docker-compose.build.yml"
COMPOSE_STAGING = ROOT / "docker-compose.staging.yml"
DOCKERFILE = ROOT / "frontend" / "Dockerfile"

BAKED = (
    "NEXT_PUBLIC_API_URL",
    "NEXT_PUBLIC_BETTER_AUTH_URL",
    "NEXT_PUBLIC_SENTRY_DSN",
    "NEXT_PUBLIC_ENVIRONMENT",
)


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf8"))


@pytest.fixture(scope="module")
def job() -> dict:
    return _load(BUILD)["jobs"]["build"]


@pytest.fixture(scope="module")
def build_step(job: dict) -> dict:
    steps = [s for s in job["steps"] if "docker/build-push-action" in s.get("uses", "")]
    assert len(steps) == 1, "expected exactly one build-push step"
    return steps[0]


def _build_args(step: dict) -> dict[str, str]:
    lines = step["with"]["build-args"].strip().splitlines()
    return dict(line.split("=", 1) for line in lines)


def test_frontend_is_built_once_per_environment(job: dict) -> None:
    frontends = [e for e in job["strategy"]["matrix"]["include"] if e["app"] == "frontend"]
    names = [e.get("environment") for e in frontends]
    # Staging is the only environment today (production arrives with #782). An
    # entry with no environment would build with no vars at all.
    assert "staging" in names and all(names) and len(names) == len(set(names)), names


def test_each_variant_reads_its_own_environments_vars(job: dict) -> None:
    # Environment-scoped vars resolve only in a job that names the environment.
    env = job["environment"]
    assert "matrix.environment" in env["name"]
    # Using an environment for its vars is not a deployment; without this every
    # main build would mark itself as the active production deployment.
    assert env["deployment"] is False


def test_build_args_have_no_fallback_values(build_step: dict) -> None:
    args = _build_args(build_step)
    assert set(BAKED) <= set(args), f"missing build args: {set(BAKED) - set(args)}"
    for name, value in args.items():
        assert "||" not in value and "http" not in value, (
            f"{name} has a literal fallback ({value}); a missing var must fail the "
            "build, not bake another environment's host into the bundle"
        )


def test_frontend_tags_name_their_environment(job: dict) -> None:
    meta = next(s for s in job["steps"] if "docker/metadata-action" in s.get("uses", ""))
    assert "suffix=" in meta["with"]["tags"] and "matrix.environment" in meta["with"]["tags"]


def test_a_publishing_run_fails_closed_on_a_missing_var(job: dict) -> None:
    guard = [s for s in job["steps"] if "Require" in s.get("name", "")]
    assert len(guard) == 1, "no fail-closed step for missing NEXT_PUBLIC_* vars"
    assert "exit 1" in guard[0]["run"]
    for name in ("NEXT_PUBLIC_API_URL", "NEXT_PUBLIC_BETTER_AUTH_URL"):
        assert name in guard[0]["run"]


def test_the_smoke_test_greps_the_bundle_for_its_own_api_host(job: dict) -> None:
    smoke = next(s for s in job["steps"] if s.get("name", "").startswith("Smoke test"))
    assert ".next/static" in smoke["run"] and "NEXT_PUBLIC_API_URL" in smoke["run"]


def test_local_compose_build_requires_values_instead_of_defaulting_to_staging() -> None:
    args = _load(COMPOSE_BUILD)["services"]["frontend"]["build"]["args"]
    for name in ("NEXT_PUBLIC_API_URL", "NEXT_PUBLIC_BETTER_AUTH_URL", "NEXT_PUBLIC_ENVIRONMENT"):
        assert re.fullmatch(rf"\$\{{{name}:\?[^}}]+\}}", args[name]), (
            f"{name} must be required (${{{name}:?...}}), got {args[name]!r}"
        )
    assert "NEXT_PUBLIC_SENTRY_DSN" in args


def test_staging_deploy_pulls_the_staging_variant() -> None:
    image = _load(COMPOSE_STAGING)["services"]["frontend"]["image"]
    assert image.endswith("}-staging"), image


def test_dockerfile_bakes_every_public_value() -> None:
    text = DOCKERFILE.read_text(encoding="utf8")
    for name in BAKED:
        assert re.search(rf"^ARG {name}$", text, re.M), f"Dockerfile lacks ARG {name}"
        assert f"{name}=${{{name}}}" in text, f"Dockerfile does not export {name}"
