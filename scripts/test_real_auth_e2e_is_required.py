"""The required Playwright job runs one end-to-end test with real auth (#843).

Every other spec runs with BYPASS_AUTH, so this is the only required check of
the chain a real user depends on: better-auth signs a cookie, the backend
verifies it and scopes data to that user. It is easy to lose silently, by
dropping the step, by a bypass creeping into its config, or by the spec being
picked up by the bypassed run instead.

Run: uvx --with pytest --with pyyaml pytest scripts/test_real_auth_e2e_is_required.py -q
"""

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
WORKFLOW = REPO / ".github" / "workflows" / "tests.yml"
CONFIG = REPO / "frontend" / "playwright.real-auth.config.ts"
BYPASS_CONFIG = REPO / "frontend" / "playwright.config.ts"
SPECS = REPO / "frontend" / "src" / "e2e" / "real-auth"


def _e2e_job():
    jobs = yaml.safe_load(WORKFLOW.read_text())["jobs"]
    return next(job for job in jobs.values() if job.get("name") == "E2E Tests (Playwright)")


def _real_auth_step():
    return next(
        step
        for step in _e2e_job()["steps"]
        if "playwright.real-auth.config.ts" in step.get("run", "")
    )


def test_the_required_job_runs_the_real_auth_config():
    step = _real_auth_step()
    assert "npx playwright test" in step["run"]
    assert "if" not in step, "a condition could skip the only real-auth check"
    assert not step.get("continue-on-error"), "its failure must fail the job"


def test_the_step_and_its_config_never_turn_the_bypass_on():
    env = _real_auth_step().get("env", {})
    assert "BYPASS_AUTH" not in env and "E2E_ALLOW_BYPASS" not in env
    config = CONFIG.read_text()
    assert re.search(r"BYPASS_AUTH: 'false'", config)
    assert re.search(r"E2E_ALLOW_BYPASS: '0'", config)
    assert not re.search(r"BYPASS_AUTH: (process\.env|'true')", config)


def test_the_spec_signs_up_and_is_not_run_by_the_bypassed_suite():
    specs = list(SPECS.glob("*.spec.ts"))
    assert specs, "no real-auth spec to run"
    assert any("/auth/sign-up" in spec.read_text() for spec in specs)
    assert "testDir: './src/e2e/real-auth'" in CONFIG.read_text()
    assert "testIgnore: '**/real-auth/**'" in BYPASS_CONFIG.read_text()
