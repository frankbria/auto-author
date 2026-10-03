"""A BETTER_AUTH_SECRET once published in the public repo must not boot a deployed
backend (#780). Only hashes of such values live in the code, so the tests use a
synthetic stand-in registered in the deny-list."""

import hashlib
import re
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core import config
from app.core.config import Settings

STAND_IN = "Zx9-stand-in-published-secret-0123456789ab"
REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def published(monkeypatch):
    monkeypatch.setattr(
        config,
        "PUBLISHED_SECRET_SHA256",
        config.PUBLISHED_SECRET_SHA256 | {hashlib.sha256(STAND_IN.encode()).hexdigest()},
    )
    monkeypatch.setenv("BETTER_AUTH_SECRET", STAND_IN)
    monkeypatch.setenv("BYPASS_AUTH", "false")


@pytest.mark.parametrize("env", ["staging", "production"])
def test_rejected_on_deployed_environments(monkeypatch, published, env):
    monkeypatch.delenv("NODE_ENV", raising=False)
    monkeypatch.setenv("ENVIRONMENT", env)
    with pytest.raises(ValidationError) as exc:
        Settings()
    assert "published" in str(exc.value)
    assert STAND_IN not in str(exc.value)


def test_allowed_in_development(monkeypatch, published):
    monkeypatch.delenv("NODE_ENV", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    assert Settings().BETTER_AUTH_SECRET == STAND_IN


def test_no_tracked_file_contains_a_published_secret():
    """Repo-wide grep by hash: never reproduces the literal."""
    files = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO_ROOT, capture_output=True, check=True
    ).stdout.split(b"\0")
    token = re.compile(rb"[A-Za-z0-9_-]{32,}")
    offenders = []
    for f in filter(None, files):
        path = REPO_ROOT / f.decode()
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        for m in token.finditer(path.read_bytes()):
            if hashlib.sha256(m.group()).hexdigest() in config.PUBLISHED_SECRET_SHA256:
                offenders.append(f.decode())
                break
    assert not offenders, f"published secret found in: {offenders}"
