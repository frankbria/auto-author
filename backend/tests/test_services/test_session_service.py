"""
Tests for session management service
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi import Request
from unittest.mock import Mock, AsyncMock

from app.services.session_service import (
    create_user_session,
    validate_session,
    refresh_session,
    end_session,
    end_all_user_sessions,
    get_session_status,
    extract_session_metadata,
    generate_fingerprint,
    MAX_CONCURRENT_SESSIONS,
)
from app.models.session import SessionCreate, SessionMetadata
from app.db.session import cleanup_expired_sessions


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request"""
    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "192.168.1.1"
    request.headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "accept-language": "en-US,en;q=0.9",
        "accept-encoding": "gzip, deflate, br",
    }
    request.url = Mock()
    request.url.path = "/api/v1/books"
    return request


@pytest.mark.asyncio
class TestSessionService:
    """Test session service functions"""

    async def test_create_user_session(self, motor_reinit_db, mock_request):
        """Test creating a new session for a user"""
        user_id = "test_user_123"

        session = await create_user_session(user_id, mock_request)

        assert session.user_id == user_id
        assert session.is_active is True
        assert session.is_suspicious is False
        assert session.session_id.startswith("sess_")
        assert session.csrf_token.startswith("csrf_")
        assert session.metadata.ip_address == "192.168.1.1"
        assert session.metadata.device_type == "desktop"
        assert session.metadata.browser == "Chrome"
        assert session.metadata.os == "Windows"

    async def test_create_session_with_max_concurrent_limit(self, motor_reinit_db, mock_request):
        """Test that old sessions are deactivated when limit is reached"""
        user_id = "test_user_max_sessions"

        # Create MAX_CONCURRENT_SESSIONS sessions
        sessions = []
        for i in range(MAX_CONCURRENT_SESSIONS + 1):
            session = await create_user_session(user_id, mock_request)
            sessions.append(session)

        # Verify that at most MAX_CONCURRENT_SESSIONS are active
        from app.db.session import get_concurrent_sessions_count
        active_count = await get_concurrent_sessions_count(user_id)
        assert active_count <= MAX_CONCURRENT_SESSIONS

    async def test_validate_session(self, motor_reinit_db, mock_request):
        """Test validating an active session"""
        user_id = "test_user_validate"
        session = await create_user_session(user_id, mock_request)

        # Validate the session
        validated = await validate_session(session.session_id, mock_request)

        assert validated is not None
        assert validated.session_id == session.session_id
        assert validated.is_active is True
        assert validated.request_count > 0  # Should increment

    async def test_validate_expired_session(self, motor_reinit_db, mock_request):
        """Test validating an expired session"""
        user_id = "test_user_expired"

        # Create session that expired 1 hour ago (use large window to avoid timing flakiness)
        from app.db.session import create_session
        from app.models.session import SessionCreate

        metadata = extract_session_metadata(mock_request)
        session_data = SessionCreate(
            user_id=user_id,
            metadata=metadata,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)  # Expired 1 hour ago
        )
        session = await create_session(session_data)

        # Validate should return None for expired session
        validated = await validate_session(session.session_id, mock_request)
        assert validated is None

    async def test_validate_session_fingerprint_mismatch(self, motor_reinit_db, mock_request):
        """Test session validation flags fingerprint mismatch as suspicious"""
        user_id = "test_user_fingerprint"
        session = await create_user_session(user_id, mock_request)

        # Change the request fingerprint
        mock_request.headers["user-agent"] = "Different User Agent"

        # Validate should flag as suspicious but still return session
        validated = await validate_session(session.session_id, mock_request)

        assert validated is not None
        assert validated.is_suspicious is True

    async def test_refresh_session(self, motor_reinit_db, mock_request):
        """Test refreshing a session's expiry time"""
        user_id = "test_user_refresh"
        session = await create_user_session(user_id, mock_request)

        original_expiry = session.expires_at

        # Wait a moment
        import asyncio
        await asyncio.sleep(0.1)

        # Refresh the session
        refreshed = await refresh_session(session.session_id)

        assert refreshed is not None
        assert refreshed.expires_at > original_expiry

    async def test_end_session(self, motor_reinit_db, mock_request):
        """Test ending a session"""
        user_id = "test_user_end"
        session = await create_user_session(user_id, mock_request)

        # End the session
        success = await end_session(session.session_id)
        assert success is True

        # Verify session is inactive
        from app.db.session import get_session_by_id
        ended_session = await get_session_by_id(session.session_id)
        assert ended_session.is_active is False

    async def test_end_all_user_sessions(self, motor_reinit_db, mock_request):
        """Test ending all sessions for a user"""
        user_id = "test_user_end_all"

        # Create multiple sessions
        session1 = await create_user_session(user_id, mock_request)
        session2 = await create_user_session(user_id, mock_request)
        session3 = await create_user_session(user_id, mock_request)

        # End all except session3
        count = await end_all_user_sessions(user_id, except_session_id=session3.session_id)

        assert count >= 2

        # Verify session3 is still active
        from app.db.session import get_session_by_id
        active_session = await get_session_by_id(session3.session_id)
        assert active_session.is_active is True

    async def test_get_session_status(self, motor_reinit_db, mock_request):
        """Test getting session status information"""
        user_id = "test_user_status"
        session = await create_user_session(user_id, mock_request)

        status = await get_session_status(session.session_id)

        assert status is not None
        assert status["session_id"] == session.session_id
        assert status["is_active"] is True
        assert "idle_seconds" in status
        assert "time_until_expiry_seconds" in status
        assert "device_type" in status

    async def test_extract_session_metadata_mobile(self):
        """Test extracting metadata from mobile request"""
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "10.0.0.1"
        request.headers = {
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
        }

        metadata = extract_session_metadata(request)

        assert metadata.ip_address == "10.0.0.1"
        assert metadata.device_type == "mobile"
        assert metadata.os == "iOS"
        assert metadata.browser == "Safari"

    async def test_generate_fingerprint(self, motor_reinit_db, mock_request):
        """Test generating browser fingerprint"""
        fingerprint1 = generate_fingerprint(mock_request)

        # Same request should generate same fingerprint
        fingerprint2 = generate_fingerprint(mock_request)
        assert fingerprint1 == fingerprint2

        # Different request should generate different fingerprint
        mock_request.headers["user-agent"] = "Different Browser"
        fingerprint3 = generate_fingerprint(mock_request)
        assert fingerprint1 != fingerprint3

    async def test_cleanup_expired_sessions(self, motor_reinit_db, mock_request):
        """Test cleanup of expired sessions"""
        user_id = "test_user_cleanup"

        # Create an expired session
        from app.db.session import create_session
        metadata = extract_session_metadata(mock_request)
        session_data = SessionCreate(
            user_id=user_id,
            metadata=metadata,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        await create_session(session_data)

        # Cleanup expired sessions
        deleted_count = await cleanup_expired_sessions()

        assert deleted_count >= 1


@pytest.mark.asyncio
class TestSessionMetadata:
    """Test session metadata extraction"""

    async def test_metadata_for_desktop_chrome(self):
        """Test metadata extraction for desktop Chrome"""
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "192.168.1.1"
        request.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        metadata = extract_session_metadata(request)

        assert metadata.device_type == "desktop"
        assert metadata.browser == "Chrome"
        assert metadata.os == "Windows"

    async def test_metadata_for_mobile_safari(self):
        """Test metadata extraction for mobile Safari"""
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "10.0.0.1"
        request.headers = {
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15"
        }

        metadata = extract_session_metadata(request)

        assert metadata.device_type == "mobile"
        assert metadata.os == "iOS"

    async def test_metadata_for_android_firefox(self):
        """Test metadata extraction for Android Firefox"""
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "10.0.0.2"
        request.headers = {
            "user-agent": "Mozilla/5.0 (Android 12; Mobile; rv:95.0) Gecko/95.0 Firefox/95.0"
        }

        metadata = extract_session_metadata(request)

        assert metadata.device_type == "mobile"
        assert metadata.browser == "Firefox"
        assert metadata.os == "Android"
