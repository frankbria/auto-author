"""The API's own documentation is not served where real users are (#815).

`/docs`, `/redoc` and `/openapi.json` answered 200 on staging, and every
answer carried a Content-Security-Policy with the jsdelivr and 'unsafe-inline'
allowances that only the Swagger page needs.

Whether the routes exist is decided when the app is built, so the deployed
cases import the app in a fresh interpreter, as a deploy does.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

BACKEND_DIR = Path(__file__).resolve().parents[2]
DOCS = ["/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"]
LIVE = "/api/v1/health/live"
PROBE = f"""
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
print(json.dumps({{
    "status": {{path: client.get(path).status_code for path in {DOCS + [LIVE]!r}}},
    "csp": client.get({LIVE!r}).headers["content-security-policy"],
}}))
"""


def _served_by_an_app_built_for(environment: str, tmp_path: Path) -> dict:
    """Status of each documentation route, and the CSP, from an app imported with that ENVIRONMENT."""
    env = {k: v for k, v in os.environ.items() if k not in {"NODE_ENV", "BYPASS_AUTH", "E2E_ALLOW_BYPASS"}}
    # cwd is an empty directory: a developer's backend/.env must not decide this.
    env.update(ENVIRONMENT=environment, BETTER_AUTH_SECRET="s" * 64, PYTHONPATH=str(BACKEND_DIR))
    # Production refuses to start without somewhere to keep uploads.
    env.update(CLOUDINARY_CLOUD_NAME="x", CLOUDINARY_API_KEY="x", CLOUDINARY_API_SECRET="x")
    result = subprocess.run(
        [sys.executable, "-c", PROBE], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_a_deployed_api_serves_no_documentation(environment, tmp_path):
    served = _served_by_an_app_built_for(environment, tmp_path)

    assert {path: served["status"][path] for path in DOCS} == dict.fromkeys(DOCS, 404)
    assert served["status"][LIVE] == 200, "the API itself is still there"


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_a_deployed_api_allows_no_script_from_elsewhere_and_none_inline(environment, tmp_path):
    csp = _served_by_an_app_built_for(environment, tmp_path)["csp"]

    assert "default-src 'self'" in csp
    assert "unsafe-inline" not in csp
    assert "https:" not in csp, "no other origin is allowed anything"


def test_a_development_api_still_serves_its_documentation(tmp_path):
    served = _served_by_an_app_built_for("development", tmp_path)

    assert {path: served["status"][path] for path in DOCS} == dict.fromkeys(DOCS, 200)
    assert "https://cdn.jsdelivr.net" in served["csp"] and "'unsafe-inline'" in served["csp"]


def test_so_does_the_app_under_test():
    client = TestClient(app)

    assert client.get("/docs").status_code == 200
    assert "paths" in client.get("/openapi.json").json()
    assert "https://cdn.jsdelivr.net" in client.get("/docs").headers["content-security-policy"]
