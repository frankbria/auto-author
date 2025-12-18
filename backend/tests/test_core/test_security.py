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
class TestClerkUser:
    """Test Clerk API user fetching"""

    @patch("app.core.security.requests.get")
    async def test_get_clerk_user_success(self, mock_get):
        """Test successful Clerk user fetch"""
        clerk_id = "test_clerk_id_123"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": clerk_id,
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User"
        }
        mock_get.return_value = mock_response

        result = await get_clerk_user(clerk_id)

        assert result is not None
        assert result["id"] == clerk_id
        assert result["email"] == "test@example.com"

    @patch("app.core.security.requests.get")
    async def test_get_clerk_user_not_found(self, mock_get):
        """Test Clerk user not found"""
        clerk_id = "nonexistent_id"
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = await get_clerk_user(clerk_id)

        assert result is None

    @patch("app.core.security.requests.get")
    async def test_get_clerk_user_api_error(self, mock_get):
        """Test Clerk API error"""
        clerk_id = "test_id"
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = await get_clerk_user(clerk_id)

        assert result is None


class TestClerkJWKS:
    """Test JWKS fetching and caching"""

    @patch("app.core.security.requests.get")
    def test_get_clerk_jwks_success(self, mock_get):
        """Test successful JWKS fetch"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "keys": [
                {
                    "kid": "test_key_id",
                    "kty": "RSA",
                    "use": "sig",
                    "alg": "RS256",
                    "n": "test_modulus",
                    "e": "AQAB"
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Clear cache before test
        get_clerk_jwks.cache_clear()

        result = get_clerk_jwks()

        assert result is not None
        assert "keys" in result
        assert len(result["keys"]) == 1

    @patch("app.core.security.requests.get")
    def test_get_clerk_jwks_caching(self, mock_get):
        """Test that JWKS is cached"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"keys": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Clear cache
        get_clerk_jwks.cache_clear()

        # First call
        get_clerk_jwks()
        # Second call
        get_clerk_jwks()

        # Should only call API once due to caching
        assert mock_get.call_count == 1

    @patch("app.core.security.requests.get")
    def test_get_clerk_jwks_network_error(self, mock_get):
        """Test JWKS fetch with network error"""
        mock_get.side_effect = Exception("Network error")

        # Clear cache
        get_clerk_jwks.cache_clear()

        with pytest.raises(Exception, match="Network error"):
            get_clerk_jwks()


@pytest.mark.asyncio
class TestJWTVerification:
    """Test JWT token verification"""

    @patch("app.core.security.jwt.decode")
    @patch("app.core.security.jwt.get_unverified_header")
    @patch("app.core.security.settings")
    async def test_verify_jwt_token_with_pem_key(self, mock_settings, mock_get_header, mock_decode):
        """Test JWT verification with PEM key"""
        mock_settings.clerk_jwt_public_key_pem = "-----BEGIN PUBLIC KEY-----\ntest_key\n-----END PUBLIC KEY-----"
        mock_settings.CLERK_JWT_ALGORITHM = "RS256"
        mock_get_header.return_value = {"kid": "test_kid"}
        mock_decode.return_value = {
            "sub": "user_123",
            "email": "test@example.com"
        }

        token = "test_token"
        result = await verify_jwt_token(token)

        assert result["sub"] == "user_123"
        assert result["email"] == "test@example.com"

    @patch("app.core.security.jwk.construct")
    @patch("app.core.security.get_clerk_jwks")
    @patch("app.core.security.jwt.decode")
    @patch("app.core.security.jwt.get_unverified_header")
    @patch("app.core.security.settings")
    async def test_verify_jwt_token_with_jwks(self, mock_settings, mock_get_header, mock_decode, mock_get_jwks, mock_jwk_construct):
        """Test JWT verification with JWKS"""
        mock_settings.clerk_jwt_public_key_pem = None
        mock_settings.CLERK_JWT_ALGORITHM = "RS256"
        mock_get_header.return_value = {"kid": "test_kid"}
        mock_get_jwks.return_value = {
            "keys": [
                {"kid": "test_kid", "kty": "RSA", "use": "sig"}
            ]
        }
        mock_jwk_construct.return_value = "constructed_key"
        mock_decode.return_value = {
            "sub": "user_123",
            "email": "test@example.com"
        }

        token = "test_token"
        result = await verify_jwt_token(token)

        assert result["sub"] == "user_123"

    @patch("app.core.security.get_clerk_jwks")
    @patch("app.core.security.jwt.get_unverified_header")
    @patch("app.core.security.settings")
    async def test_verify_jwt_token_key_not_found(self, mock_settings, mock_get_header, mock_get_jwks):
        """Test JWT verification when kid not in JWKS"""
        mock_settings.clerk_jwt_public_key_pem = None
        mock_get_header.return_value = {"kid": "missing_kid"}
        mock_get_jwks.return_value = {
            "keys": [
                {"kid": "different_kid", "kty": "RSA"}
            ]
        }

        token = "test_token"

        with pytest.raises(HTTPException) as exc_info:
            await verify_jwt_token(token)

        assert exc_info.value.status_code == 401
        assert "Unable to find appropriate key" in exc_info.value.detail

    @patch("app.core.security.jwt.decode")
    @patch("app.core.security.jwt.get_unverified_header")
    @patch("app.core.security.settings")
    async def test_verify_jwt_token_expired(self, mock_settings, mock_get_header, mock_decode):
        """Test JWT verification with expired token"""
        mock_settings.clerk_jwt_public_key_pem = "test_key"
        mock_settings.CLERK_JWT_ALGORITHM = "RS256"
        mock_get_header.return_value = {"kid": "test_kid"}
        mock_decode.side_effect = ExpiredSignatureError("Token has expired")

        token = "expired_token"

        with pytest.raises(HTTPException) as exc_info:
            await verify_jwt_token(token)

        assert exc_info.value.status_code == 401
        assert "Invalid authentication credentials" in exc_info.value.detail

    @patch("app.core.security.jwt.decode")
    @patch("app.core.security.jwt.get_unverified_header")
    @patch("app.core.security.settings")
    async def test_verify_jwt_token_invalid(self, mock_settings, mock_get_header, mock_decode):
        """Test JWT verification with invalid token"""
        mock_settings.clerk_jwt_public_key_pem = "test_key"
        mock_settings.CLERK_JWT_ALGORITHM = "RS256"
        mock_get_header.return_value = {"kid": "test_kid"}
        mock_decode.side_effect = JWTError("Invalid signature")

        token = "invalid_token"

        with pytest.raises(HTTPException) as exc_info:
            await verify_jwt_token(token)

        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
class TestRoleChecker:
    """Test role-based access control"""

    @patch("app.core.security.verify_jwt_token")
    @patch("app.core.security.get_user_by_clerk_id")
    async def test_role_checker_allowed(self, mock_get_user, mock_verify):
        """Test RoleChecker allows authorized role"""
        mock_verify.return_value = {"sub": "user_123"}
        mock_get_user.return_value = {
            "clerk_id": "user_123",
            "role": "admin",
            "email": "admin@example.com"
        }

        checker = RoleChecker(allowed_roles=["admin", "moderator"])
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test_token")

        result = await checker(credentials)

        assert result["role"] == "admin"

    @patch("app.core.security.verify_jwt_token")
    @patch("app.core.security.get_user_by_clerk_id")
    async def test_role_checker_forbidden(self, mock_get_user, mock_verify):
        """Test RoleChecker denies unauthorized role"""
        mock_verify.return_value = {"sub": "user_123"}
        mock_get_user.return_value = {
            "clerk_id": "user_123",
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
    @patch("app.core.security.get_user_by_clerk_id")
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

        assert result["clerk_id"] == "test-clerk-id"
        assert result["email"] == "test@example.com"
        assert result["role"] == "user"

    @patch("app.core.security.verify_jwt_token")
    @patch("app.core.security.get_user_by_clerk_id")
    @patch("app.core.config.settings")
    async def test_get_current_user_valid_token(self, mock_settings, mock_get_user, mock_verify):
        """Test get_current_user with valid token"""
        type(mock_settings).BYPASS_AUTH = PropertyMock(return_value=False)
        mock_verify.return_value = {"sub": "user_123"}
        mock_get_user.return_value = {
            "clerk_id": "user_123",
            "email": "test@example.com",
            "role": "user"
        }

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")

        result = await get_current_user(credentials)

        assert result["clerk_id"] == "user_123"
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
    @patch("app.core.security.get_user_by_clerk_id")
    @patch("app.core.security.settings")
    async def test_get_current_user_not_found(self, mock_settings, mock_get_user, mock_verify):
        """Test get_current_user when user not in database"""
        mock_settings.BYPASS_AUTH = False
        mock_verify.return_value = {"sub": "user_123"}
        mock_get_user.return_value = None

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert "User not found" in exc_info.value.detail

    @patch("app.core.security.verify_jwt_token")
    @patch("app.core.security.get_user_by_clerk_id")
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
