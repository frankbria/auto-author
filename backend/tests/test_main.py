import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """
    Test that the root endpoint returns a 200 status code and health check message.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "Auto Author" in response.json().get(
        "message", ""
    )  # Assuming the root returns a message field


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
