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
        """Test that validate_production_security() allows BYPASS_AUTH in development"""
        monkeypatch.setenv("NODE_ENV", "development")

        # Create a mock settings object with BYPASS_AUTH=True
        mock_settings = MagicMock()
        mock_settings.BYPASS_AUTH = True

        with patch("app.main.settings", mock_settings):
            from app.main import validate_production_security
            # Should not raise
            validate_production_security()

    def test_startup_validation_allows_test_bypass(self, monkeypatch):
        """Test that validate_production_security() allows BYPASS_AUTH in test environment"""
        monkeypatch.setenv("NODE_ENV", "test")

        # Create a mock settings object with BYPASS_AUTH=True
        mock_settings = MagicMock()
        mock_settings.BYPASS_AUTH = True

        with patch("app.main.settings", mock_settings):
            from app.main import validate_production_security
            # Should not raise
            validate_production_security()

    def test_startup_validation_allows_unset_env_bypass(self, monkeypatch):
        """Test that validate_production_security() allows BYPASS_AUTH when NODE_ENV is unset"""
        # Ensure NODE_ENV is not set
        monkeypatch.delenv("NODE_ENV", raising=False)

        # Create a mock settings object with BYPASS_AUTH=True
        mock_settings = MagicMock()
        mock_settings.BYPASS_AUTH = True

        with patch("app.main.settings", mock_settings):
            from app.main import validate_production_security
            # Should not raise - backward compatibility
            validate_production_security()
