"""
Comprehensive tests for core security module

Tests JWT verification, password hashing, authentication, and authorization.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, PropertyMock
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError
import time
from datetime import datetime, timedelta

from app.core.security import (
    hash_password,
    verify_password,
    verify_jwt_token,
    RoleChecker,
    get_current_user,
    optional_security,
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
class TestJWTVerification:
    """Test JWT token verification for better-auth (HS256)"""

    @patch("app.core.security.jwt.decode")
    @patch("app.core.security.settings")
    async def test_verify_jwt_token_success(self, mock_settings, mock_decode):
        """Test JWT verification with valid HS256 token"""
        mock_settings.BETTER_AUTH_SECRET = "test-secret-key-minimum-32-chars-long"
        mock_decode.return_value = {
            "sub": "user_123",
            "email": "test@example.com"
        }

        token = "test_token"
        result = await verify_jwt_token(token)

        assert result["sub"] == "user_123"
        assert result["email"] == "test@example.com"
        mock_decode.assert_called_once()

    @patch("app.core.security.jwt.decode")
    @patch("app.core.security.settings")
    async def test_verify_jwt_token_expired(self, mock_settings, mock_decode):
        """Test JWT verification with expired token"""
        mock_settings.BETTER_AUTH_SECRET = "test-secret-key-minimum-32-chars-long"
        mock_decode.side_effect = ExpiredSignatureError("Token has expired")

        token = "expired_token"

        with pytest.raises(HTTPException) as exc_info:
            await verify_jwt_token(token)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    @patch("app.core.security.jwt.decode")
    @patch("app.core.security.settings")
    async def test_verify_jwt_token_invalid(self, mock_settings, mock_decode):
        """Test JWT verification with invalid token"""
        mock_settings.BETTER_AUTH_SECRET = "test-secret-key-minimum-32-chars-long"
        mock_decode.side_effect = JWTError("Invalid signature")

        token = "invalid_token"

        with pytest.raises(HTTPException) as exc_info:
            await verify_jwt_token(token)

        assert exc_info.value.status_code == 401
        assert "Invalid authentication token" in exc_info.value.detail


@pytest.mark.asyncio
class TestRoleChecker:
    """Test role-based access control"""

    @patch("app.core.security.verify_jwt_token")
    @patch("app.db.user.get_user_by_auth_id")
    async def test_role_checker_allowed(self, mock_get_user, mock_verify):
        """Test RoleChecker allows authorized role"""
        mock_verify.return_value = {"sub": "user_123"}
        mock_get_user.return_value = {
            "auth_id": "user_123",
            "role": "admin",
            "email": "admin@example.com"
        }

        checker = RoleChecker(allowed_roles=["admin", "moderator"])
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test_token")

        result = await checker(credentials)

        assert result["role"] == "admin"

    @patch("app.core.security.verify_jwt_token")
    @patch("app.db.user.get_user_by_auth_id")
    async def test_role_checker_forbidden(self, mock_get_user, mock_verify):
        """Test RoleChecker denies unauthorized role"""
        mock_verify.return_value = {"sub": "user_123"}
        mock_get_user.return_value = {
            "auth_id": "user_123",
            "role": "user",
            "email": "user@example.com"
        }

        checker = RoleChecker(allowed_roles=["admin", "moderator"])
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test_token")

        with pytest.raises(HTTPException) as exc_info:
            await checker(credentials)

        assert exc_info.value.status_code == 403
        assert "Not enough permissions" in exc_info.value.detail

    @patch("app.core.security.verify_jwt_token")
    @patch("app.db.user.get_user_by_auth_id")
    async def test_role_checker_user_not_found(self, mock_get_user, mock_verify):
        """Test RoleChecker when user not in database"""
        mock_verify.return_value = {"sub": "user_123"}
        mock_get_user.return_value = None

        checker = RoleChecker(allowed_roles=["admin"])
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test_token")

        with pytest.raises(HTTPException) as exc_info:
            await checker(credentials)

        assert exc_info.value.status_code == 401
        assert "User not found" in exc_info.value.detail

    @patch("app.core.security.verify_jwt_token")
    async def test_role_checker_no_user_id(self, mock_verify):
        """Test RoleChecker when token has no user ID"""
        mock_verify.return_value = {}  # No 'sub' field

        checker = RoleChecker(allowed_roles=["admin"])
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test_token")

        with pytest.raises(HTTPException) as exc_info:
            await checker(credentials)

        assert exc_info.value.status_code == 401
        assert "Invalid user ID" in exc_info.value.detail


@pytest.mark.asyncio
class TestGetCurrentUser:
    """Test get_current_user authentication function"""

    @patch("app.core.config.settings")
    async def test_get_current_user_bypass_auth(self, mock_settings):
        """Test get_current_user with BYPASS_AUTH enabled"""
        # Mock BYPASS_AUTH as a property
        type(mock_settings).BYPASS_AUTH = PropertyMock(return_value=True)

        result = await get_current_user(credentials=None)

        assert result["auth_id"] == "test-auth-id"
        assert result["email"] == "test@example.com"
        assert result["role"] == "user"

    @patch("app.core.security.verify_jwt_token")
    @patch("app.db.user.get_user_by_auth_id")
    @patch("app.core.config.settings")
    async def test_get_current_user_valid_token(self, mock_settings, mock_get_user, mock_verify):
        """Test get_current_user with valid token"""
        type(mock_settings).BYPASS_AUTH = PropertyMock(return_value=False)
        mock_verify.return_value = {"sub": "user_123"}
        mock_get_user.return_value = {
            "auth_id": "user_123",
            "email": "test@example.com",
            "role": "user"
        }

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")

        result = await get_current_user(credentials)

        assert result["auth_id"] == "user_123"
        assert result["email"] == "test@example.com"

    @patch("app.core.security.settings")
    async def test_get_current_user_missing_credentials(self, mock_settings):
        """Test get_current_user without credentials"""
        mock_settings.BYPASS_AUTH = False

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=None)

        assert exc_info.value.status_code == 401
        assert "Missing authentication credentials" in exc_info.value.detail

    @patch("app.core.security.verify_jwt_token")
    @patch("app.core.security.settings")
    async def test_get_current_user_invalid_token(self, mock_settings, mock_verify):
        """Test get_current_user with invalid token"""
        mock_settings.BYPASS_AUTH = False
        mock_verify.return_value = {}  # No 'sub' field

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid_token")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert "Invalid user ID" in exc_info.value.detail

    @patch("app.core.security.verify_jwt_token")
    @patch("app.db.user.get_user_by_auth_id")
    @patch("app.core.security.settings")
    async def test_get_current_user_not_found(self, mock_settings, mock_get_user, mock_verify):
        """Test get_current_user when user not in database - should return 403"""
        mock_settings.BYPASS_AUTH = False
        mock_verify.return_value = {"sub": "user_123"}
        mock_get_user.return_value = None

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 403
        assert "not found" in exc_info.value.detail.lower()

    @patch("app.core.security.verify_jwt_token")
    @patch("app.db.user.get_user_by_auth_id")
    @patch("app.core.security.settings")
    async def test_get_current_user_database_error(self, mock_settings, mock_get_user, mock_verify):
        """Test get_current_user with database error"""
        mock_settings.BYPASS_AUTH = False
        mock_verify.return_value = {"sub": "user_123"}
        mock_get_user.side_effect = Exception("Database connection error")

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 500
        assert "Error fetching user" in exc_info.value.detail


@pytest.mark.asyncio
class TestOptionalSecurity:
    """Test optional security dependency"""

    @patch("app.core.security.settings")
    async def test_optional_security_bypass_auth(self, mock_settings):
        """Test optional_security with BYPASS_AUTH enabled"""
        type(mock_settings).BYPASS_AUTH = PropertyMock(return_value=True)
        mock_request = Mock(spec=Request)
        mock_request.headers = {}

        result = await optional_security(mock_request)

        assert result is None

    @patch("app.core.security.HTTPBearer")
    @patch("app.core.security.settings")
    async def test_optional_security_with_token(self, mock_settings, mock_bearer_class):
        """Test optional_security with valid token"""
        mock_settings.BYPASS_AUTH = False
        mock_request = Mock(spec=Request)
        mock_bearer_instance = AsyncMock()
        mock_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test_token")
        mock_bearer_instance.return_value = mock_credentials
        mock_bearer_class.return_value = mock_bearer_instance

        result = await optional_security(mock_request)

        assert result == mock_credentials

    @patch("app.core.security.HTTPBearer")
    @patch("app.core.security.settings")
    async def test_optional_security_without_token(self, mock_settings, mock_bearer_class):
        """Test optional_security without token (auto_error=False)"""
        mock_settings.BYPASS_AUTH = False
        mock_request = Mock(spec=Request)
        mock_bearer_instance = AsyncMock()
        mock_bearer_instance.return_value = None
        mock_bearer_class.return_value = mock_bearer_instance

        result = await optional_security(mock_request)

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
