import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.core.config import settings


def test_health_check(client: TestClient):
    """
    Test that the root endpoint returns a 200 status code and health check message.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "Auto Author" in response.json().get(
        "message", ""
    )  # Assuming the root returns a message field


def _ok_db():
    """A db handle whose `.command('ping')` resolves — stand-in for a reachable
    Mongo, keeping the logic tests deterministic and event-loop independent (the
    import-time motor client binds to the first sync-TestClient request's loop)."""
    db = MagicMock()
    db.command = AsyncMock(return_value={"ok": 1})
    return db


class TestHealthCheckDependencies:
    """/health must actually verify dependencies so a broken release fails the
    deploy `curl -f` gate instead of passing a static 200 (issue #333)."""

    def test_health_ok_when_mongo_up_and_secrets_present(self, client: TestClient):
        """Mongo reachable + CI-default secrets present → 200 healthy."""
        with patch("app.api.endpoints.router.get_database", return_value=_ok_db()):
            response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["checks"]["mongodb"] == "ok"
        assert data["checks"]["config"] == "ok"

    def test_health_503_when_mongo_unreachable(self, client: TestClient):
        """A ping failure (wrong URI / un-allowlisted Atlas IP / Mongo down)
        returns 503 and names the failing component."""
        mock_db = MagicMock()
        mock_db.command = AsyncMock(side_effect=Exception("no route to host"))
        with patch("app.api.endpoints.router.get_database", return_value=mock_db):
            response = client.get("/api/v1/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["mongodb"].startswith("error")

    def test_health_503_when_required_secret_absent(self, client: TestClient, monkeypatch):
        """A required env key missing entirely → 503 naming the key, even when
        Mongo is fine."""
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "", raising=False)
        monkeypatch.setattr(settings, "OPENAI_AUTOAUTHOR_API_KEY", "", raising=False)
        with patch("app.api.endpoints.router.get_database", return_value=_ok_db()):
            response = client.get("/api/v1/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["mongodb"] == "ok"
        assert "OPENAI_API_KEY" in data["checks"]["config"]

    def test_health_503_when_production_still_has_placeholder_key(
        self, client: TestClient, monkeypatch
    ):
        """In production the CI placeholder key is treated as missing, so a
        release that never wired in the real OpenAI key fails the gate."""
        monkeypatch.delenv("NODE_ENV", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "", raising=False)
        monkeypatch.setattr(settings, "OPENAI_AUTOAUTHOR_API_KEY", "test-key", raising=False)
        with patch("app.api.endpoints.router.get_database", return_value=_ok_db()):
            response = client.get("/api/v1/health")
        assert response.status_code == 503
        assert "OPENAI_API_KEY" in response.json()["checks"]["config"]

    def test_health_placeholder_key_allowed_outside_production(
        self, client: TestClient, monkeypatch
    ):
        """Outside production the placeholder key is fine — CI stays green."""
        monkeypatch.delenv("NODE_ENV", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "", raising=False)
        monkeypatch.setattr(settings, "OPENAI_AUTOAUTHOR_API_KEY", "test-key", raising=False)
        with patch("app.api.endpoints.router.get_database", return_value=_ok_db()):
            response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["checks"]["config"] == "ok"


@pytest.mark.asyncio
async def test_health_pings_real_mongo(async_client_factory):
    """Integration: the real `.command('ping')` against a live Mongo returns
    200 healthy — proves the ping call itself is correct (not just mocked)."""
    client = await async_client_factory(auth=False)
    try:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["checks"]["mongodb"] == "ok"
    finally:
        await client.aclose()


class TestStartupSecurityValidation:
    """Test startup validation for production security settings"""

    def test_startup_validation_blocks_production_bypass(self, monkeypatch):
        """Test that validate_production_security() blocks BYPASS_AUTH in production"""
        # Import after setting up environment
        monkeypatch.setenv("NODE_ENV", "production")

        # Create a mock settings object with BYPASS_AUTH=True
        mock_settings = MagicMock()
        mock_settings.BYPASS_AUTH = True

        with patch("app.main.settings", mock_settings):
            # Need to reimport the function to test it in isolation
            import importlib
            import app.main as main_module

            # Call the function directly
            with pytest.raises(RuntimeError) as exc_info:
                # Reload just the function logic
                from app.main import validate_production_security
                validate_production_security()

            assert "BYPASS_AUTH" in str(exc_info.value)
            assert "production" in str(exc_info.value).lower()

    def test_startup_validation_passes_production_secure(self, monkeypatch):
        """Test that validate_production_security() passes when BYPASS_AUTH=false in production"""
        monkeypatch.setenv("NODE_ENV", "production")

        # Create a mock settings object with BYPASS_AUTH=False
        mock_settings = MagicMock()
        mock_settings.BYPASS_AUTH = False

        with patch("app.main.settings", mock_settings):
            from app.main import validate_production_security
            # Should not raise
            validate_production_security()

    def test_startup_validation_allows_dev_bypass(self, monkeypatch):
        """validate_production_security() allows BYPASS_AUTH in development when the
        settings object carries it — the env-level gate (E2E_ALLOW_BYPASS=1 required)
        is applied at Settings construction, upstream of this function (#307)."""
        monkeypatch.setenv("NODE_ENV", "development")

        # Create a mock settings object with BYPASS_AUTH=True
        mock_settings = MagicMock()
        mock_settings.BYPASS_AUTH = True

        with patch("app.main.settings", mock_settings):
            from app.main import validate_production_security
            # Should not raise
            validate_production_security()

    def test_startup_validation_allows_test_bypass(self, monkeypatch):
        """validate_production_security() allows BYPASS_AUTH in test environment when
        the settings object carries it — env-level flag gate is at Settings
        construction (#307)."""
        monkeypatch.setenv("NODE_ENV", "test")

        # Create a mock settings object with BYPASS_AUTH=True
        mock_settings = MagicMock()
        mock_settings.BYPASS_AUTH = True

        with patch("app.main.settings", mock_settings):
            from app.main import validate_production_security
            # Should not raise
            validate_production_security()

    def test_startup_validation_allows_unset_env_bypass(self, monkeypatch):
        """validate_production_security() allows BYPASS_AUTH when NODE_ENV is unset
        and the settings object carries it — env-level flag gate is at Settings
        construction (#307)."""
        # Ensure NODE_ENV is not set
        monkeypatch.delenv("NODE_ENV", raising=False)

        # Create a mock settings object with BYPASS_AUTH=True
        mock_settings = MagicMock()
        mock_settings.BYPASS_AUTH = True

        with patch("app.main.settings", mock_settings):
            from app.main import validate_production_security
            # Should not raise
            validate_production_security()

    def test_startup_validation_blocks_bypass_when_environment_is_production(self, monkeypatch):
        """PM2 sets ENVIRONMENT (not NODE_ENV) on the backend, so startup must
        block BYPASS_AUTH on ENVIRONMENT=production too (issue #176)."""
        monkeypatch.delenv("NODE_ENV", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "production")

        mock_settings = MagicMock()
        mock_settings.BYPASS_AUTH = True

        with patch("app.main.settings", mock_settings):
            from app.main import validate_production_security
            with pytest.raises(RuntimeError) as exc_info:
                validate_production_security()

            assert "BYPASS_AUTH" in str(exc_info.value)
            assert "production" in str(exc_info.value).lower()

    def test_startup_validation_allows_bypass_when_environment_is_staging(self, monkeypatch):
        """ENVIRONMENT=staging allows BYPASS_AUTH when the settings object carries it —
        env-level flag gate (E2E_ALLOW_BYPASS=1) is at Settings construction (#307)."""
        monkeypatch.delenv("NODE_ENV", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "staging")

        mock_settings = MagicMock()
        mock_settings.BYPASS_AUTH = True

        with patch("app.main.settings", mock_settings):
            from app.main import validate_production_security
            # Should not raise
            validate_production_security()
