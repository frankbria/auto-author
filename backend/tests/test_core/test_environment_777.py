"""ENVIRONMENT must be an explicit, known value (#777).

is_production_env() matches only "production", so a missing marker, a typo or
"prod" used to switch every production guard off. Settings now refuses to build
unless ENVIRONMENT is one of development/test/staging/production.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings

BACKEND_DIR = Path(__file__).resolve().parents[2]
REAL_SECRET = "s" * 64


def _assert_no_settings_echo(error):
    # A model-level error prints the whole input dict (Mongo URI, API keys) as
    # input_value into the startup log; the error must carry only this value.
    assert "input_value={" not in str(error), str(error)


@pytest.mark.parametrize(
    "value", ["development", "test", "staging", "production", "PRODUCTION", "Staging"]
)
def test_known_environment_is_accepted(monkeypatch, value):
    monkeypatch.setenv("ENVIRONMENT", value)
    monkeypatch.setenv("BETTER_AUTH_SECRET", REAL_SECRET)
    monkeypatch.setenv("BYPASS_AUTH", "false")

    Settings()


@pytest.mark.parametrize("value", ["prod", "dev", "staging ", "garbage", ""])
def test_unknown_environment_is_rejected(monkeypatch, value):
    monkeypatch.setenv("ENVIRONMENT", value)
    monkeypatch.setenv("BETTER_AUTH_SECRET", REAL_SECRET)

    with pytest.raises(ValidationError) as exc:
        Settings()

    assert "ENVIRONMENT" in str(exc.value)
    _assert_no_settings_echo(exc.value)


def test_missing_environment_is_rejected(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("BETTER_AUTH_SECRET", REAL_SECRET)

    with pytest.raises(ValidationError) as exc:
        # _env_file=None: a developer's backend/.env may set ENVIRONMENT.
        Settings(_env_file=None)

    assert "ENVIRONMENT" in str(exc.value)
    _assert_no_settings_echo(exc.value)


def _import_config(tmp_path: Path, dotenv: str, environment: str | None):
    """Import app.core.config in a fresh interpreter, cwd=tmp_path, so the
    module-level `settings = Settings()` runs exactly as it does at startup."""
    (tmp_path / ".env").write_text(dotenv)
    env = {k: v for k, v in os.environ.items() if k not in {
        "ENVIRONMENT", "NODE_ENV", "BYPASS_AUTH", "E2E_ALLOW_BYPASS", "BETTER_AUTH_SECRET",
    }}
    env["PYTHONPATH"] = str(BACKEND_DIR)
    if environment is not None:
        env["ENVIRONMENT"] = environment
    return subprocess.run(
        [sys.executable, "-c", "import app.core.config"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60,
    )


@pytest.mark.parametrize("environment", [None, "prod", "garbage"])
def test_startup_refuses_unknown_or_missing_environment(tmp_path, environment):
    result = _import_config(tmp_path, f"BETTER_AUTH_SECRET={REAL_SECRET}\n", environment)

    assert result.returncode != 0
    assert "ENVIRONMENT" in result.stderr


def test_environment_set_only_in_dotenv_drives_the_production_guards(tmp_path):
    # Settings reads backend/.env; the guards read os.environ. A value only in
    # .env must reach both, or ENVIRONMENT=production there would validate while
    # leaving BYPASS_AUTH's production hard-block off.
    result = _import_config(
        tmp_path,
        "ENVIRONMENT=production\nBYPASS_AUTH=true\nE2E_ALLOW_BYPASS=1\n"
        f"BETTER_AUTH_SECRET={REAL_SECRET}\n",
        None,
    )

    assert result.returncode != 0
    assert "BYPASS_AUTH cannot be enabled in production" in result.stderr


def test_startup_succeeds_with_development_in_dotenv(tmp_path):
    result = _import_config(
        tmp_path, f"ENVIRONMENT=development\nBETTER_AUTH_SECRET={REAL_SECRET}\n", None
    )

    assert result.returncode == 0, result.stderr
