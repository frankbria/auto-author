"""
Comprehensive tests for core security module

Tests password hashing, session-based authentication, and authorization.
JWT-based authentication has been removed - all auth is now cookie/session-based.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, PropertyMock
from fastapi import HTTPException, Request

from app.core.security import (
    hash_password,
    verify_password,
    SessionRoleChecker,
    get_current_user_from_session,
    optional_session_security,
)


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password_creates_hash(self):
        """Test that hash_password creates a bcrypt hash"""
        password = "test_password_123"
        hashed = hash_password(password)

        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix
        assert len(hashed) == 60  # standard bcrypt hash length

    def test_hash_password_different_each_time(self):
        """Test that hashing the same password twice gives different hashes (salt)"""
        password = "test_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2  # Different salts

    def test_verify_password_correct(self):
        """Test that verify_password accepts correct password"""
        password = "test_password_123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test that verify_password rejects incorrect password"""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty(self):
        """Test verify_password with empty password"""
        password = "test_password_123"
        hashed = hash_password(password)

        assert verify_password("", hashed) is False


@pytest.mark.asyncio
class TestSessionRoleChecker:
    """Test session-based role access control"""

    @patch("app.core.security.get_current_user_from_session")
    async def test_session_role_checker_allowed(self, mock_get_user):
        """Test SessionRoleChecker allows authorized role"""
        mock_get_user.return_value = {
            "auth_id": "user_123",
            "role": "admin",
            "email": "admin@example.com"
        }

        checker = SessionRoleChecker(allowed_roles=["admin", "moderator"])
        mock_request = Mock(spec=Request)

        result = await checker(mock_request)

        assert result["role"] == "admin"

    @patch("app.core.security.get_current_user_from_session")
    async def test_session_role_checker_forbidden(self, mock_get_user):
        """Test SessionRoleChecker denies unauthorized role"""
        mock_get_user.return_value = {
            "auth_id": "user_123",
            "role": "user",
            "email": "user@example.com"
        }

        checker = SessionRoleChecker(allowed_roles=["admin", "moderator"])
        mock_request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await checker(mock_request)

        assert exc_info.value.status_code == 403
        assert "Not enough permissions" in exc_info.value.detail

    @patch("app.core.config.settings")
    async def test_session_role_checker_bypass_auth(self, mock_settings):
        """Test SessionRoleChecker with BYPASS_AUTH enabled returns admin"""
        type(mock_settings).BYPASS_AUTH = PropertyMock(return_value=True)

        checker = SessionRoleChecker(allowed_roles=["admin"])
        mock_request = Mock(spec=Request)

        result = await checker(mock_request)

        assert result["role"] == "admin"
        assert result["auth_id"] == "test-auth-id"


@pytest.mark.asyncio
class TestGetCurrentUserFromSession:
    """Test get_current_user_from_session authentication function"""

    @patch("app.core.config.settings")
    async def test_get_current_user_from_session_bypass_auth(self, mock_settings):
        """Test get_current_user_from_session with BYPASS_AUTH enabled"""
        type(mock_settings).BYPASS_AUTH = PropertyMock(return_value=True)

        mock_request = Mock(spec=Request)
        result = await get_current_user_from_session(mock_request)

        assert result["auth_id"] == "test-auth-id"
        assert result["email"] == "test@example.com"
        assert result["role"] == "user"

    @patch("app.core.security.validate_better_auth_session")
    @patch("app.core.config.settings")
    async def test_get_current_user_from_session_no_session(self, mock_settings, mock_validate):
        """Test get_current_user_from_session without valid session"""
        mock_settings.BYPASS_AUTH = False
        mock_validate.return_value = None

        mock_request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_from_session(mock_request)

        assert exc_info.value.status_code == 401
        assert "Not authenticated" in exc_info.value.detail

    @patch("app.core.security.validate_better_auth_session")
    @patch("app.core.security.get_better_auth_user")
    @patch("app.db.user.get_user_by_auth_id")
    @patch("app.core.config.settings")
    async def test_get_current_user_from_session_valid_session(
        self, mock_settings, mock_get_user, mock_get_auth_user, mock_validate
    ):
        """Test get_current_user_from_session with valid session"""
        mock_settings.BYPASS_AUTH = False
        mock_validate.return_value = {"userId": "user_123"}
        mock_get_auth_user.return_value = {"id": "user_123", "email": "test@example.com"}
        mock_get_user.return_value = {
            "auth_id": "user_123",
            "email": "test@example.com",
            "role": "user"
        }

        mock_request = Mock(spec=Request)

        result = await get_current_user_from_session(mock_request)

        assert result["auth_id"] == "user_123"
        assert result["email"] == "test@example.com"

    @patch("app.core.security.validate_better_auth_session")
    @patch("app.core.config.settings")
    async def test_get_current_user_from_session_no_user_id_in_session(
        self, mock_settings, mock_validate
    ):
        """Test get_current_user_from_session when session has no userId"""
        mock_settings.BYPASS_AUTH = False
        # Return a truthy session dict but without userId
        mock_validate.return_value = {"token": "some-token", "expiresAt": "2025-12-25"}

        mock_request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_from_session(mock_request)

        assert exc_info.value.status_code == 401
        assert "Invalid session" in exc_info.value.detail

    @patch("app.core.security.validate_better_auth_session")
    @patch("app.core.security.get_better_auth_user")
    @patch("app.db.user.get_user_by_auth_id")
    @patch("app.db.user.create_user")
    @patch("app.core.config.settings")
    async def test_get_current_user_from_session_auto_creates_user(
        self, mock_settings, mock_create_user, mock_get_user, mock_get_auth_user, mock_validate
    ):
        """Test get_current_user_from_session auto-creates user when not in database"""
        mock_settings.BYPASS_AUTH = False
        mock_validate.return_value = {"userId": "user_123"}
        mock_get_auth_user.return_value = {
            "id": "user_123",
            "email": "test@example.com",
            "name": "Test User"
        }
        mock_get_user.return_value = None  # User not in backend database
        created_user = {
            "id": "new_user_id",
            "auth_id": "user_123",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User"
        }
        mock_create_user.return_value = created_user

        mock_request = Mock(spec=Request)

        result = await get_current_user_from_session(mock_request)

        assert result == created_user
        mock_create_user.assert_called_once()


@pytest.mark.asyncio
class TestOptionalSessionSecurity:
    """Test optional session security dependency"""

    @patch("app.core.config.settings")
    async def test_optional_session_security_bypass_auth(self, mock_settings):
        """Test optional_session_security with BYPASS_AUTH enabled returns None"""
        type(mock_settings).BYPASS_AUTH = PropertyMock(return_value=True)

        mock_request = Mock(spec=Request)
        result = await optional_session_security(mock_request)

        assert result is None

    @patch("app.core.security.get_current_user_from_session")
    @patch("app.core.config.settings")
    async def test_optional_session_security_authenticated(self, mock_settings, mock_get_user):
        """Test optional_session_security with valid session"""
        mock_settings.BYPASS_AUTH = False
        mock_get_user.return_value = {
            "auth_id": "user_123",
            "email": "test@example.com",
            "role": "user"
        }

        mock_request = Mock(spec=Request)
        result = await optional_session_security(mock_request)

        assert result["auth_id"] == "user_123"

    @patch("app.core.security.get_current_user_from_session")
    @patch("app.core.config.settings")
    async def test_optional_session_security_not_authenticated(self, mock_settings, mock_get_user):
        """Test optional_session_security without valid session returns None"""
        mock_settings.BYPASS_AUTH = False
        mock_get_user.side_effect = HTTPException(status_code=401, detail="Not authenticated")

        mock_request = Mock(spec=Request)
        result = await optional_session_security(mock_request)

        assert result is None


class TestProductionSecurityValidation:
    """Test production environment security validation for BYPASS_AUTH"""

    def test_bypass_auth_blocked_in_production(self, monkeypatch):
        """Test that BYPASS_AUTH=true is blocked when NODE_ENV=production"""
        from pydantic import ValidationError as PydanticValidationError
        from app.core.config import Settings

        # Set production environment with a valid secret (not the test secret)
        # to ensure we're testing BYPASS_AUTH validation, not secret validation
        monkeypatch.setenv("NODE_ENV", "production")
        monkeypatch.setenv("BYPASS_AUTH", "true")
        monkeypatch.setenv("BETTER_AUTH_SECRET", "production-secret-that-is-at-least-32-characters-long")

        with pytest.raises(PydanticValidationError) as exc_info:
            Settings()

        # Verify the error message mentions BYPASS_AUTH security issue
        error_str = str(exc_info.value)
        assert "BYPASS_AUTH" in error_str

    def test_bypass_auth_allowed_in_development(self, monkeypatch):
        """Test that BYPASS_AUTH=true is allowed when NODE_ENV=development"""
        from app.core.config import Settings

        # Set development environment
        monkeypatch.setenv("NODE_ENV", "development")
        monkeypatch.setenv("BYPASS_AUTH", "true")

        # Should not raise - just verify it doesn't error
        settings = Settings()
        assert settings.BYPASS_AUTH is True

    def test_bypass_auth_allowed_in_test(self, monkeypatch):
        """Test that BYPASS_AUTH=true is allowed when NODE_ENV=test"""
        from app.core.config import Settings

        # Set test environment
        monkeypatch.setenv("NODE_ENV", "test")
        monkeypatch.setenv("BYPASS_AUTH", "true")

        # Should not raise - just verify it doesn't error
        settings = Settings()
        assert settings.BYPASS_AUTH is True

    def test_bypass_auth_allowed_in_staging(self, monkeypatch):
        """Test that BYPASS_AUTH=true is allowed when NODE_ENV=staging (for E2E tests)"""
        from app.core.config import Settings

        # Set staging environment
        monkeypatch.setenv("NODE_ENV", "staging")
        monkeypatch.setenv("BYPASS_AUTH", "true")

        # Should not raise - staging may need E2E testing capability
        settings = Settings()
        assert settings.BYPASS_AUTH is True

    def test_bypass_auth_allowed_when_env_not_set(self, monkeypatch):
        """Test that BYPASS_AUTH=true is allowed when NODE_ENV is not set (backward compatibility)"""
        from app.core.config import Settings

        # Ensure NODE_ENV is not set
        monkeypatch.delenv("NODE_ENV", raising=False)
        monkeypatch.setenv("BYPASS_AUTH", "true")

        # Should not raise - default/unset environment should allow testing
        settings = Settings()
        assert settings.BYPASS_AUTH is True

    def test_bypass_auth_false_allowed_in_production(self, monkeypatch):
        """Test that BYPASS_AUTH=false is allowed in production (normal secure operation)"""
        from app.core.config import Settings

        # Set production environment with auth bypass disabled
        # Also need a production-valid secret (not the test secret)
        monkeypatch.setenv("NODE_ENV", "production")
        monkeypatch.setenv("BYPASS_AUTH", "false")
        monkeypatch.setenv("BETTER_AUTH_SECRET", "production-secret-that-is-at-least-32-characters-long")

        # Should not raise - this is the expected secure configuration
        settings = Settings()
        assert settings.BYPASS_AUTH is False
