"""
Comprehensive tests for core security module

Tests password hashing, session-based authentication, and authorization.
JWT-based authentication has been removed - all auth is now cookie/session-based.
"""

import pytest
from unittest.mock import Mock, patch, PropertyMock
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

    @patch("app.core.security.validate_better_auth_session")
    @patch("app.core.security.get_better_auth_user")
    @patch("app.db.user.get_user_by_auth_id")
    @patch("app.core.config.settings")
    async def test_get_current_user_from_session_db_error(
        self, mock_settings, mock_get_user, mock_get_auth_user, mock_validate
    ):
        """DB error while fetching the application user surfaces as a 500."""
        mock_settings.BYPASS_AUTH = False
        mock_validate.return_value = {"userId": "user_123"}
        mock_get_auth_user.return_value = {"id": "user_123", "email": "test@example.com"}
        mock_get_user.side_effect = Exception("connection lost")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_from_session(Mock(spec=Request))

        assert exc_info.value.status_code == 500
        assert "Error fetching user" in exc_info.value.detail

    @patch("app.core.security.validate_better_auth_session")
    @patch("app.core.security.get_better_auth_user")
    @patch("app.db.user.get_user_by_auth_id")
    @patch("app.core.config.settings")
    async def test_get_current_user_from_session_unknown_user(
        self, mock_settings, mock_get_user, mock_get_auth_user, mock_validate
    ):
        """Valid session but user missing from both backend and better-auth -> 401."""
        mock_settings.BYPASS_AUTH = False
        mock_validate.return_value = {"userId": "user_123"}
        mock_get_user.return_value = None
        mock_get_auth_user.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_from_session(Mock(spec=Request))

        assert exc_info.value.status_code == 401
        assert "User not found" in exc_info.value.detail

    @patch("app.core.security.validate_better_auth_session")
    @patch("app.core.security.get_better_auth_user")
    @patch("app.db.user.get_user_by_auth_id")
    @patch("app.core.config.settings")
    async def test_get_current_user_from_session_auto_create_missing_email(
        self, mock_settings, mock_get_user, mock_get_auth_user, mock_validate
    ):
        """Auto-create aborts with 400 when better-auth user has no email."""
        mock_settings.BYPASS_AUTH = False
        mock_validate.return_value = {"userId": "user_123"}
        mock_get_user.return_value = None
        mock_get_auth_user.return_value = {"id": "user_123", "name": "No Email"}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_from_session(Mock(spec=Request))

        assert exc_info.value.status_code == 400
        assert "missing email" in exc_info.value.detail

    @patch("app.core.security.validate_better_auth_session")
    @patch("app.core.security.get_better_auth_user")
    @patch("app.db.user.get_user_by_auth_id")
    @patch("app.db.user.create_user")
    @patch("app.core.config.settings")
    async def test_get_current_user_from_session_auto_create_failure(
        self, mock_settings, mock_create_user, mock_get_user, mock_get_auth_user, mock_validate
    ):
        """A failure during auto-create surfaces as a 500."""
        mock_settings.BYPASS_AUTH = False
        mock_validate.return_value = {"userId": "user_123"}
        mock_get_user.return_value = None
        mock_get_auth_user.return_value = {
            "id": "user_123",
            "email": "test@example.com",
            "name": "Test User",
        }
        mock_create_user.side_effect = Exception("insert failed")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_from_session(Mock(spec=Request))

        assert exc_info.value.status_code == 500
        assert "Failed to create user account" in exc_info.value.detail

    @patch("app.core.security.validate_better_auth_session")
    @patch("app.core.security.get_better_auth_user")
    @patch("app.db.user.get_user_by_auth_id")
    @patch("app.db.user.create_user")
    @patch("app.core.config.settings")
    async def test_get_current_user_from_session_auto_create_race_reuses_winner(
        self, mock_settings, mock_create_user, mock_get_user, mock_get_auth_user, mock_validate
    ):
        """Concurrent first-load race (issue #178): create_user raises
        DuplicateKeyError because a parallel request already inserted; the path
        re-fetches and returns that winning record instead of erroring."""
        from pymongo.errors import DuplicateKeyError

        winner = {
            "id": "winner_id",
            "auth_id": "user_123",
            "email": "test@example.com",
            "first_name": "Test",
        }
        mock_settings.BYPASS_AUTH = False
        mock_validate.return_value = {"userId": "user_123"}
        mock_get_auth_user.return_value = {
            "id": "user_123",
            "email": "test@example.com",
            "name": "Test User",
        }
        # First call (pre-check) finds nothing; re-fetch after the race returns the winner.
        mock_get_user.side_effect = [None, winner]
        mock_create_user.side_effect = DuplicateKeyError("dup auth_id")

        result = await get_current_user_from_session(Mock(spec=Request))

        assert result == winner

    @patch("app.core.security.validate_better_auth_session")
    @patch("app.core.security.get_better_auth_user")
    @patch("app.db.user.get_user_by_auth_id")
    @patch("app.db.user.create_user")
    @patch("app.core.config.settings")
    async def test_get_current_user_from_session_auto_create_race_missing_winner(
        self, mock_settings, mock_create_user, mock_get_user, mock_get_auth_user, mock_validate
    ):
        """If the duplicate was on some other key (no auth_id winner to re-fetch),
        the race handler surfaces a 500 rather than returning None."""
        from pymongo.errors import DuplicateKeyError

        mock_settings.BYPASS_AUTH = False
        mock_validate.return_value = {"userId": "user_123"}
        mock_get_auth_user.return_value = {
            "id": "user_123",
            "email": "test@example.com",
            "name": "Test User",
        }
        mock_get_user.side_effect = [None, None]  # pre-check + re-fetch both empty
        mock_create_user.side_effect = DuplicateKeyError("dup email")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_from_session(Mock(spec=Request))

        assert exc_info.value.status_code == 500
        assert "Failed to create user account" in exc_info.value.detail


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

    def test_bypass_auth_ignored_in_development_without_flag(self, monkeypatch):
        """BYPASS_AUTH=true alone no longer bypasses when NODE_ENV=development —
        coerced off unless E2E_ALLOW_BYPASS=1 is also set (#307)."""
        from app.core.config import Settings

        monkeypatch.setenv("NODE_ENV", "development")
        monkeypatch.setenv("BYPASS_AUTH", "true")
        monkeypatch.delenv("E2E_ALLOW_BYPASS", raising=False)

        settings = Settings()
        assert settings.BYPASS_AUTH is False

    def test_bypass_auth_ignored_in_test_without_flag(self, monkeypatch):
        """BYPASS_AUTH=true alone no longer bypasses when NODE_ENV=test —
        coerced off unless E2E_ALLOW_BYPASS=1 is also set (#307)."""
        from app.core.config import Settings

        monkeypatch.setenv("NODE_ENV", "test")
        monkeypatch.setenv("BYPASS_AUTH", "true")
        monkeypatch.delenv("E2E_ALLOW_BYPASS", raising=False)

        settings = Settings()
        assert settings.BYPASS_AUTH is False

    def test_bypass_auth_ignored_in_staging_without_flag(self, monkeypatch):
        """BYPASS_AUTH=true alone no longer bypasses when NODE_ENV=staging —
        coerced off unless E2E_ALLOW_BYPASS=1 is also set (#307)."""
        from app.core.config import Settings

        monkeypatch.setenv("NODE_ENV", "staging")
        monkeypatch.setenv("BYPASS_AUTH", "true")
        monkeypatch.delenv("E2E_ALLOW_BYPASS", raising=False)

        settings = Settings()
        assert settings.BYPASS_AUTH is False

    def test_bypass_auth_ignored_when_env_not_set_without_flag(self, monkeypatch):
        """BYPASS_AUTH=true alone no longer bypasses when NODE_ENV is unset —
        coerced off unless E2E_ALLOW_BYPASS=1 is also set (#307)."""
        from app.core.config import Settings

        monkeypatch.delenv("NODE_ENV", raising=False)
        monkeypatch.setenv("BYPASS_AUTH", "true")
        monkeypatch.delenv("E2E_ALLOW_BYPASS", raising=False)

        settings = Settings()
        assert settings.BYPASS_AUTH is False

    def test_bypass_auth_ignored_warns_about_missing_flag(self, monkeypatch, caplog):
        """The coercion logs a warning naming E2E_ALLOW_BYPASS (#307)."""
        import logging
        from app.core.config import Settings

        monkeypatch.setenv("NODE_ENV", "development")
        monkeypatch.setenv("BYPASS_AUTH", "true")
        monkeypatch.delenv("E2E_ALLOW_BYPASS", raising=False)

        with caplog.at_level(logging.WARNING, logger="app.core.config"):
            settings = Settings()

        assert settings.BYPASS_AUTH is False
        assert any("E2E_ALLOW_BYPASS" in r.message for r in caplog.records)

    @pytest.mark.parametrize("env_var,env_value", [
        ("NODE_ENV", "development"),
        ("NODE_ENV", "test"),
        ("NODE_ENV", "staging"),
        ("ENVIRONMENT", "staging"),
    ])
    def test_bypass_auth_allowed_with_e2e_flag(self, monkeypatch, env_var, env_value):
        """With E2E_ALLOW_BYPASS=1 the bypass stays allowed outside production (#307)."""
        from app.core.config import Settings

        monkeypatch.delenv("NODE_ENV", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.setenv(env_var, env_value)
        monkeypatch.setenv("BYPASS_AUTH", "true")
        monkeypatch.setenv("E2E_ALLOW_BYPASS", "1")

        settings = Settings()
        assert settings.BYPASS_AUTH is True

    def test_bypass_auth_allowed_with_e2e_flag_when_env_not_set(self, monkeypatch):
        """With E2E_ALLOW_BYPASS=1 the bypass stays allowed when no env marker is set (#307)."""
        from app.core.config import Settings

        monkeypatch.delenv("NODE_ENV", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.setenv("BYPASS_AUTH", "true")
        monkeypatch.setenv("E2E_ALLOW_BYPASS", "1")

        settings = Settings()
        assert settings.BYPASS_AUTH is True

    def test_bypass_auth_loose_flag_value_does_not_allow(self, monkeypatch):
        """Only the exact value '1' enables the bypass — 'true' is inert (#307)."""
        from app.core.config import Settings

        monkeypatch.setenv("NODE_ENV", "development")
        monkeypatch.setenv("BYPASS_AUTH", "true")
        monkeypatch.setenv("E2E_ALLOW_BYPASS", "true")

        settings = Settings()
        assert settings.BYPASS_AUTH is False

    def test_bypass_auth_blocked_in_production_even_with_flag(self, monkeypatch):
        """Production stays hard-blocked even with E2E_ALLOW_BYPASS=1 (#307) —
        deliberately stricter than the frontend: no backend E2E path runs
        production-marked (staging E2E uses real auth), so no flag exemption."""
        from pydantic import ValidationError as PydanticValidationError
        from app.core.config import Settings

        monkeypatch.setenv("NODE_ENV", "production")
        monkeypatch.setenv("BYPASS_AUTH", "true")
        monkeypatch.setenv("E2E_ALLOW_BYPASS", "1")
        monkeypatch.setenv("BETTER_AUTH_SECRET", "production-secret-that-is-at-least-32-characters-long")

        with pytest.raises(PydanticValidationError) as exc_info:
            Settings()

        assert "BYPASS_AUTH" in str(exc_info.value)

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

    def test_bypass_auth_blocked_when_environment_is_production(self, monkeypatch):
        """PM2 sets ENVIRONMENT (not NODE_ENV) on the backend, so the guard must
        fire on ENVIRONMENT=production too (issue #176)."""
        from pydantic import ValidationError as PydanticValidationError
        from app.core.config import Settings

        monkeypatch.delenv("NODE_ENV", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("BYPASS_AUTH", "true")
        monkeypatch.setenv("BETTER_AUTH_SECRET", "production-secret-that-is-at-least-32-characters-long")

        with pytest.raises(PydanticValidationError) as exc_info:
            Settings()

        assert "BYPASS_AUTH" in str(exc_info.value)

    def test_ci_test_secret_rejected_when_environment_is_production(self, monkeypatch):
        """The built-in CI test secret must be rejected on the real deployment,
        where ENVIRONMENT=production is the only marker set (issue #176)."""
        from pydantic import ValidationError as PydanticValidationError
        from app.core.config import Settings

        monkeypatch.delenv("NODE_ENV", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("BYPASS_AUTH", "false")
        monkeypatch.setenv(
            "BETTER_AUTH_SECRET",
            "test-secret-for-ci-minimum-32-characters-long-safe-for-testing",
        )

        with pytest.raises(PydanticValidationError) as exc_info:
            Settings()

        assert "test secret" in str(exc_info.value).lower()

    def test_bypass_auth_ignored_when_environment_is_staging_without_flag(self, monkeypatch):
        """ENVIRONMENT=staging no longer allows a bare BYPASS_AUTH — coerced off
        unless E2E_ALLOW_BYPASS=1 is also set (#307)."""
        from app.core.config import Settings

        monkeypatch.delenv("NODE_ENV", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.setenv("BYPASS_AUTH", "true")
        monkeypatch.delenv("E2E_ALLOW_BYPASS", raising=False)

        settings = Settings()
        assert settings.BYPASS_AUTH is False

    def test_bypass_auth_blocked_when_environment_is_production_even_with_flag(self, monkeypatch):
        """PM2 sets ENVIRONMENT (not NODE_ENV) on the real deployment (#176) —
        the no-exemption rule must hold on that marker too (#307)."""
        from pydantic import ValidationError as PydanticValidationError
        from app.core.config import Settings

        monkeypatch.delenv("NODE_ENV", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("BYPASS_AUTH", "true")
        monkeypatch.setenv("E2E_ALLOW_BYPASS", "1")
        monkeypatch.setenv("BETTER_AUTH_SECRET", "production-secret-that-is-at-least-32-characters-long")

        with pytest.raises(PydanticValidationError) as exc_info:
            Settings()

        assert "BYPASS_AUTH" in str(exc_info.value)

    def test_e2e_allow_bypass_alone_is_not_a_bypass(self, monkeypatch):
        """The flag by itself does nothing — BYPASS_AUTH stays off (#307,
        mirroring the frontend's defense-in-depth pin from #272)."""
        from app.core.config import Settings

        monkeypatch.setenv("NODE_ENV", "test")
        # explicit 'false', not delenv: a local .env may carry BYPASS_AUTH=true
        monkeypatch.setenv("BYPASS_AUTH", "false")
        monkeypatch.setenv("E2E_ALLOW_BYPASS", "1")

        settings = Settings()
        assert settings.BYPASS_AUTH is False

    @pytest.mark.parametrize("marker", ["ENVIRONMENT", "NODE_ENV"])
    @pytest.mark.parametrize("value", ["PRODUCTION", "Production", "pRoDuCtIoN"])
    def test_is_production_env_case_insensitive(self, monkeypatch, marker, value):
        """is_production_env() must match production case-insensitively so a
        marker set as PRODUCTION/Production doesn't fail open (#309)."""
        from app.core.config import is_production_env

        monkeypatch.delenv("NODE_ENV", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.setenv(marker, value)

        assert is_production_env() is True

    def test_is_production_env_false_for_non_production(self, monkeypatch):
        """Non-production markers (and unset) still return False (#309)."""
        from app.core.config import is_production_env

        monkeypatch.delenv("NODE_ENV", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        assert is_production_env() is False

        monkeypatch.setenv("ENVIRONMENT", "Staging")
        assert is_production_env() is False

    def test_bypass_auth_blocked_when_environment_is_uppercase_production(self, monkeypatch):
        """The BYPASS_AUTH guard fires on ENVIRONMENT=PRODUCTION, not just the
        exact-case 'production' (#309 — was fail-open)."""
        from pydantic import ValidationError as PydanticValidationError
        from app.core.config import Settings

        monkeypatch.delenv("NODE_ENV", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "PRODUCTION")
        monkeypatch.setenv("BYPASS_AUTH", "true")
        monkeypatch.setenv("BETTER_AUTH_SECRET", "production-secret-that-is-at-least-32-characters-long")

        with pytest.raises(PydanticValidationError) as exc_info:
            Settings()

        assert "BYPASS_AUTH" in str(exc_info.value)

    def test_ci_test_secret_rejected_when_node_env_is_titlecase_production(self, monkeypatch):
        """The weak-secret fail-safe fires on NODE_ENV=Production too (#309)."""
        from pydantic import ValidationError as PydanticValidationError
        from app.core.config import Settings

        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.setenv("NODE_ENV", "Production")
        monkeypatch.setenv("BYPASS_AUTH", "false")
        monkeypatch.setenv(
            "BETTER_AUTH_SECRET",
            "test-secret-for-ci-minimum-32-characters-long-safe-for-testing",
        )

        with pytest.raises(PydanticValidationError) as exc_info:
            Settings()

        assert "test secret" in str(exc_info.value).lower()
