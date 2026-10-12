"""In production /health fails for a deployment that cannot store uploads, bill
or report errors, and there is a liveness route that depends on nothing (#807).

``/health`` checked MongoDB and two secrets. A production box with no storage
provider, no Stripe values or no ``SENTRY_DSN`` passed the deploy gate while
uploads, checkout or error reporting were dead. And the container's liveness
check used the same route, so a database outage marked a healthy process
unhealthy.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings

CLOUDINARY = ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")
S3 = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_S3_BUCKET")
STRIPE = ("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_PRICE_ID_PRO")


def _ok_db():
    db = MagicMock()
    db.command = AsyncMock(return_value={"ok": 1})
    return db


@pytest.fixture
def deployment(monkeypatch):
    """A fully configured deployment in the named environment; ``without`` unsets fields."""

    def configure(environment: str, without=(), **overrides):
        monkeypatch.setenv("ENVIRONMENT", environment)
        values = {
            "ENVIRONMENT": environment,
            **dict.fromkeys(CLOUDINARY + STRIPE, "configured"),
            **dict.fromkeys(S3, ""),
            "SENTRY_DSN": "https://key@sentry.invalid/1",
            "BILLING_ENABLED": True,
            "OPENAI_API_KEY": "configured",
            # Not the CI placeholder, which production refuses.
            "BETTER_AUTH_SECRET": "s" * 40,
            **dict.fromkeys(without, ""),
            **overrides,
        }
        for name, value in values.items():
            monkeypatch.setattr(settings, name, value)

    return configure


def _health(client: TestClient):
    with patch("app.api.endpoints.router.get_database", return_value=_ok_db()):
        response = client.get("/api/v1/health")
    return response.status_code, response.json()


class TestProductionNeedsEverythingItSells:
    def test_a_fully_configured_production_is_healthy(self, client, deployment):
        deployment("production")

        status, body = _health(client)

        assert status == 200, body
        assert body["checks"] == {
            "mongodb": "ok",
            "config": "ok",
            "storage": "ok",
            "billing": "ok",
            "error_reporting": "ok",
        }

    @pytest.mark.parametrize(
        "without, check, says",
        [
            (CLOUDINARY, "storage", "missing: CLOUDINARY_* or AWS_*"),
            (CLOUDINARY[1:], "storage", "missing: CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET"),
            (STRIPE[:1], "billing", "missing: STRIPE_SECRET_KEY"),
            (STRIPE[1:2], "billing", "missing: STRIPE_WEBHOOK_SECRET"),
            (STRIPE[2:], "billing", "missing: STRIPE_PRICE_ID_PRO"),
            (STRIPE, "billing", "missing: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_ID_PRO"),
            (("SENTRY_DSN",), "error_reporting", "missing: SENTRY_DSN"),
        ],
        ids=[
            "no storage provider",
            "half a storage provider",
            "no Stripe key",
            "no Stripe webhook secret",
            "no Stripe price",
            "no Stripe at all",
            "no Sentry DSN",
        ],
    )
    def test_one_missing_capability_is_a_503_that_names_it(
        self, client, deployment, without, check, says
    ):
        deployment("production", without=without)

        status, body = _health(client)

        assert status == 503, body
        assert body["status"] == "unhealthy"
        assert body["checks"][check] == says
        others = {k: v for k, v in body["checks"].items() if k != check}
        assert set(others.values()) == {"ok"}

    def test_s3_is_a_storage_provider_too(self, client, deployment):
        deployment("production", without=CLOUDINARY, **dict.fromkeys(S3, "configured"))

        status, body = _health(client)

        assert (status, body["checks"]["storage"]) == (200, "ok")

    def test_billing_can_be_switched_off_on_purpose(self, client, deployment):
        """A deployment that does not sell anything says so; it is not "missing"."""
        deployment("production", without=STRIPE, BILLING_ENABLED=False)

        status, body = _health(client)

        assert (status, body["checks"]["billing"]) == (200, "disabled")

    def test_the_values_themselves_are_never_reported(self, client, deployment):
        deployment("production", STRIPE_SECRET_KEY="sk-value-that-must-not-appear")

        _, body = _health(client)

        assert "sk-value-that-must-not-appear" not in str(body)


class TestOtherEnvironmentsReportWithoutFailing:
    @pytest.mark.parametrize("environment", ["staging", "development", "test"])
    def test_the_same_gaps_are_shown_and_the_deploy_gate_still_passes(
        self, client, deployment, environment
    ):
        """Staging has no production billing to lose, and the answer for staging
        becomes visible from outside."""
        deployment(environment, without=CLOUDINARY + STRIPE + ("SENTRY_DSN",))

        status, body = _health(client)

        assert (status, body["status"]) == (200, "healthy")
        assert body["checks"]["storage"] == "missing: CLOUDINARY_* or AWS_*"
        assert body["checks"]["billing"].startswith("missing: STRIPE_SECRET_KEY")
        assert body["checks"]["error_reporting"] == "missing: SENTRY_DSN"

    def test_a_stray_node_env_does_not_turn_staging_into_production(
        self, client, deployment, monkeypatch
    ):
        """The box's shared .env reaches the backend whole; NODE_ENV=production
        left in it must not fail staging's deploy gate for having no Stripe."""
        deployment("staging", without=STRIPE + ("SENTRY_DSN",))
        monkeypatch.setenv("NODE_ENV", "production")

        status, body = _health(client)

        assert (status, body["status"]) == (200, "healthy")
        assert body["checks"]["billing"].startswith("missing: STRIPE_SECRET_KEY")


class TestLivenessDependsOnNothing:
    def test_it_answers_with_the_database_down_and_nothing_configured(self, client, deployment):
        deployment("production", without=CLOUDINARY + STRIPE + ("SENTRY_DSN", "OPENAI_API_KEY"))
        unreachable = MagicMock()
        unreachable.command = AsyncMock(side_effect=Exception("no route to host"))

        with patch("app.api.endpoints.router.get_database", return_value=unreachable) as database:
            response = client.get("/api/v1/health/live")

        assert (response.status_code, response.json()) == (200, {"status": "alive"})
        database.assert_not_called()

    def test_the_container_liveness_check_uses_it(self):
        """The readiness route stays the deploy gate; the container's own check
        must not restart a live process because the database is away."""
        compose = (Path(__file__).parents[3] / "docker-compose.yml").read_text()
        backend = compose[compose.index("\n  backend:") : compose.index("\n  frontend:")]

        probe = next(line for line in backend.splitlines() if line.strip().startswith("test:"))

        assert "/api/v1/health/live" in probe
