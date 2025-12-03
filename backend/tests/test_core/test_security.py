"""
Comprehensive tests for core security module

Tests JWT verification, password hashing, authentication, and authorization.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, PropertyMock
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError
import time
from datetime import datetime, timedelta

from app.core.security import (
    hash_password,
    verify_password,
    verify_jwt_token,
    get_clerk_jwks,
    get_clerk_user,
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

    @patch("app.core.security.jwt.get_unverified_header")
    @patch("app.core.security.settings")
    async def test_verify_jwt_token_missing_kid(self, mock_settings, mock_get_header):
        """Test JWT verification when kid is missing from header"""
        mock_settings.clerk_jwt_public_key_pem = None
        mock_get_header.return_value = {}  # No kid in header

        token = "test_token"

        # Should raise when trying to find key without kid
        with patch("app.core.security.get_clerk_jwks") as mock_get_jwks:
            mock_get_jwks.return_value = {"keys": [{"kid": "some_kid"}]}

            with pytest.raises(HTTPException) as exc_info:
                await verify_jwt_token(token)

            assert exc_info.value.status_code == 401

    @patch("app.core.security.jwt.decode")
    @patch("app.core.security.jwt.get_unverified_header")
    @patch("app.core.security.settings")
    async def test_verify_jwt_token_debug_output(self, mock_settings, mock_get_header, mock_decode):
        """Test that JWT debug output handles decode errors gracefully"""
        mock_settings.clerk_jwt_public_key_pem = "test_key"
        mock_settings.CLERK_JWT_ALGORITHM = "RS256"
        mock_get_header.return_value = {"kid": "test_kid"}

        # First call (debug decode) raises error, second call (real decode) succeeds
        mock_decode.side_effect = [
            Exception("Debug decode failed"),  # Debug call
            {"sub": "user_123"}  # Actual verification call
        ]

        token = "test_token"
        result = await verify_jwt_token(token)

        assert result["sub"] == "user_123"
        # Verify debug decode was attempted
        assert mock_decode.call_count == 2


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

    @patch("app.core.config.settings")
    async def test_get_current_user_missing_credentials(self, mock_settings):
        """Test get_current_user without credentials"""
        type(mock_settings).BYPASS_AUTH = PropertyMock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=None)

        assert exc_info.value.status_code == 401
        assert "Missing authentication credentials" in exc_info.value.detail

    @patch("app.core.security.verify_jwt_token")
    @patch("app.core.config.settings")
    async def test_get_current_user_invalid_token(self, mock_settings, mock_verify):
        """Test get_current_user with invalid token"""
        type(mock_settings).BYPASS_AUTH = PropertyMock(return_value=False)
        mock_verify.return_value = {}  # No 'sub' field

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid_token")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert "Invalid user ID" in exc_info.value.detail

    @patch("app.core.security.get_clerk_user")
    @patch("app.core.security.verify_jwt_token")
    @patch("app.core.security.get_user_by_clerk_id")
    @patch("app.core.config.settings")
    async def test_get_current_user_auto_create_success(self, mock_settings, mock_get_user, mock_verify, mock_get_clerk_user):
        """Test get_current_user auto-creates user from Clerk"""
        type(mock_settings).BYPASS_AUTH = PropertyMock(return_value=False)
        mock_verify.return_value = {"sub": "user_123"}
        mock_get_user.return_value = None  # User not in DB
        mock_get_clerk_user.return_value = {
            "id": "user_123",
            "email_addresses": [{"email_address": "newuser@example.com"}],
            "first_name": "New",
            "last_name": "User",
            "image_url": "https://example.com/avatar.jpg",
            "public_metadata": {"custom": "data"}
        }

        # Mock the create_user function (imported inside get_current_user)
        with patch("app.db.database.create_user") as mock_create_user:
            mock_create_user.return_value = {
                "clerk_id": "user_123",
                "email": "newuser@example.com",
                "first_name": "New",
                "last_name": "User",
                "role": "user"
            }

            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")
            result = await get_current_user(credentials)

            assert result["clerk_id"] == "user_123"
            assert result["email"] == "newuser@example.com"
            mock_create_user.assert_called_once()

    @patch("app.core.security.verify_jwt_token")
    @patch("app.core.security.get_user_by_clerk_id")
    @patch("app.core.config.settings")
    async def test_get_current_user_database_error(self, mock_settings, mock_get_user, mock_verify):
        """Test get_current_user with database error"""
        type(mock_settings).BYPASS_AUTH = PropertyMock(return_value=False)
        mock_verify.return_value = {"sub": "user_123"}
        mock_get_user.side_effect = Exception("Database connection error")

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 500
        assert "Error fetching user" in exc_info.value.detail

    @patch("app.core.security.get_clerk_user")
    @patch("app.core.security.verify_jwt_token")
    @patch("app.core.security.get_user_by_clerk_id")
    @patch("app.core.config.settings")
    async def test_get_current_user_auto_create_clerk_not_found(self, mock_settings, mock_get_user, mock_verify, mock_get_clerk_user):
        """Test get_current_user when user not in DB and not in Clerk"""
        type(mock_settings).BYPASS_AUTH = PropertyMock(return_value=False)
        mock_verify.return_value = {"sub": "user_123"}
        mock_get_user.return_value = None  # User not in DB
        mock_get_clerk_user.return_value = None  # User not in Clerk either

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert "User not found in Clerk" in exc_info.value.detail

    @patch("app.core.security.get_clerk_user")
    @patch("app.core.security.verify_jwt_token")
    @patch("app.core.security.get_user_by_clerk_id")
    @patch("app.core.config.settings")
    async def test_get_current_user_auto_create_create_fails(self, mock_settings, mock_get_user, mock_verify, mock_get_clerk_user):
        """Test get_current_user when auto-create fails"""
        type(mock_settings).BYPASS_AUTH = PropertyMock(return_value=False)
        mock_verify.return_value = {"sub": "user_123"}
        mock_get_user.return_value = None  # User not in DB
        mock_get_clerk_user.return_value = {
            "id": "user_123",
            "email_addresses": [{"email_address": "newuser@example.com"}],
            "first_name": "New",
            "last_name": "User"
        }

        # Mock create_user to fail
        with patch("app.db.database.create_user") as mock_create_user:
            mock_create_user.side_effect = Exception("Database insert failed")

            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials)

            assert exc_info.value.status_code == 401
            assert "Failed to create user" in exc_info.value.detail

    @patch("app.core.security.get_clerk_user")
    @patch("app.core.security.verify_jwt_token")
    @patch("app.core.security.get_user_by_clerk_id")
    @patch("app.core.config.settings")
    async def test_get_current_user_auto_create_http_exception_reraised(self, mock_settings, mock_get_user, mock_verify, mock_get_clerk_user):
        """Test that HTTPExceptions are re-raised during auto-create"""
        type(mock_settings).BYPASS_AUTH = PropertyMock(return_value=False)
        mock_verify.return_value = {"sub": "user_123"}
        mock_get_user.return_value = None  # User not in DB
        mock_get_clerk_user.return_value = {
            "id": "user_123",
            "email_addresses": [{"email_address": "newuser@example.com"}],
            "first_name": "New",
            "last_name": "User"
        }

        # Mock create_user to raise HTTPException
        with patch("app.db.database.create_user") as mock_create_user:
            mock_create_user.side_effect = HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User creation forbidden"
            )

            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials)

            assert exc_info.value.status_code == 403
            assert "User creation forbidden" in exc_info.value.detail

    @patch("app.core.security.get_clerk_user")
    @patch("app.core.security.verify_jwt_token")
    @patch("app.core.security.get_user_by_clerk_id")
    @patch("app.core.config.settings")
    async def test_get_current_user_auto_create_minimal_clerk_data(self, mock_settings, mock_get_user, mock_verify, mock_get_clerk_user):
        """Test auto-create with minimal Clerk data (missing optional fields)"""
        type(mock_settings).BYPASS_AUTH = PropertyMock(return_value=False)
        mock_verify.return_value = {"sub": "user_123"}
        mock_get_user.return_value = None  # User not in DB
        mock_get_clerk_user.return_value = {
            "id": "user_123",
            # No email_addresses, first_name, last_name, image_url, public_metadata
        }

        # Mock the create_user function (imported inside get_current_user)
        with patch("app.db.database.create_user") as mock_create_user:
            mock_create_user.return_value = {
                "clerk_id": "user_123",
                "email": None,
                "first_name": None,
                "last_name": None,
                "role": "user"
            }

            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")
            result = await get_current_user(credentials)

            assert result["clerk_id"] == "user_123"
            mock_create_user.assert_called_once()
            # Verify UserCreate was called with None for missing fields
            call_args = mock_create_user.call_args[0][0]
            assert call_args["email"] is None
            assert call_args["first_name"] is None
            assert call_args["last_name"] is None


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

    @patch("app.core.security.HTTPBearer.__call__", new_callable=AsyncMock)
    @patch("app.core.config.settings")
    async def test_optional_security_with_token(self, mock_settings, mock_bearer_call):
        """Test optional_security with valid token"""
        type(mock_settings).BYPASS_AUTH = PropertyMock(return_value=False)
        mock_request = Mock(spec=Request)
        mock_request.headers = {"authorization": "Bearer test_token"}

        mock_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test_token")
        mock_bearer_call.return_value = mock_credentials

        result = await optional_security(mock_request)

        # The function should return credentials when present
        assert result == mock_credentials

    @patch("app.core.security.HTTPBearer.__call__", new_callable=AsyncMock)
    @patch("app.core.config.settings")
    async def test_optional_security_without_token(self, mock_settings, mock_bearer_call):
        """Test optional_security without token (auto_error=False)"""
        type(mock_settings).BYPASS_AUTH = PropertyMock(return_value=False)
        mock_request = Mock(spec=Request)
        mock_request.headers = {}
        mock_bearer_call.return_value = None

        result = await optional_security(mock_request)

        assert result is None