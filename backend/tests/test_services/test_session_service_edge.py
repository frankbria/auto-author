"""
Edge-case coverage for app/services/session_service.py — branches the main
service test file doesn't reach: metadata variants, validate_session early
returns and abnormal-request-rate flagging, refresh of an inactive session,
get_session_status miss, and cleanup_old_sessions.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
from fastapi import Request

from app.services.session_service import (
    validate_session,
    refresh_session,
    get_session_status,
    cleanup_old_sessions,
    extract_session_metadata,
    SUSPICIOUS_REQUEST_THRESHOLD,
)
from app.db.session import create_session, deactivate_session
from app.models.session import SessionCreate, SessionMetadata

pytestmark = pytest.mark.asyncio


def _request(user_agent="UA", host="1.2.3.4"):
    req = Mock(spec=Request)
    req.client = Mock()
    req.client.host = host
    req.headers = {"user-agent": user_agent}
    req.url = Mock()
    req.url.path = "/api/v1/books"
    return req


class TestMetadataVariants:
    async def test_tablet_edge_linux(self):
        md = extract_session_metadata(
            _request("Mozilla/5.0 (X11; Linux) Tablet Edge/18.0")
        )
        assert md.device_type == "tablet"
        assert md.browser == "Edge"
        assert md.os == "Linux"

    async def test_ipad_macos_fallback(self):
        # "iPad" -> tablet + iOS (checked before the Mac branch)
        md = extract_session_metadata(_request("Mozilla/5.0 (iPad; CPU OS 15_0)"))
        assert md.device_type == "tablet"
        assert md.os == "iOS"

    async def test_desktop_macos(self):
        # Plain Mac UA (no iOS/iPhone/iPad) -> MacOS branch
        md = extract_session_metadata(
            _request("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) Safari/605")
        )
        assert md.os == "MacOS"
        assert md.device_type == "desktop"

    async def test_no_client_host(self):
        req = _request()
        req.client = None
        md = extract_session_metadata(req)
        assert md.ip_address is None


class TestValidateSession:
    async def test_missing_session_returns_none(self, motor_reinit_db):
        assert await validate_session("sess_missing", _request()) is None

    async def test_inactive_session_returns_none(self, motor_reinit_db):
        s = await create_session(SessionCreate(user_id="u-inactive"))
        await deactivate_session(s.session_id)
        assert await validate_session(s.session_id, _request()) is None

    async def test_abnormal_request_rate_flagged(self, motor_reinit_db):
        # Session created "in the past" with a huge request_count -> high req/min.
        s = await create_session(
            SessionCreate(
                user_id="u-rate",
                metadata=SessionMetadata(fingerprint=None),
            )
        )
        # Backdate created_at and inflate request_count directly in the DB.
        from app.db import base
        await base.sessions_collection.update_one(
            {"session_id": s.session_id},
            {
                "$set": {
                    "created_at": datetime.now(timezone.utc) - timedelta(minutes=1),
                    "request_count": SUSPICIOUS_REQUEST_THRESHOLD * 10,
                }
            },
        )
        validated = await validate_session(s.session_id, _request())
        assert validated is not None
        assert validated.is_suspicious is True


class TestRefreshAndStatus:
    async def test_refresh_inactive_returns_none(self, motor_reinit_db):
        s = await create_session(SessionCreate(user_id="u-refresh"))
        await deactivate_session(s.session_id)
        assert await refresh_session(s.session_id) is None

    async def test_status_missing_returns_none(self, motor_reinit_db):
        assert await get_session_status("sess_missing") is None


class TestCleanup:
    async def test_cleanup_old_sessions(self, motor_reinit_db):
        await create_session(
            SessionCreate(
                user_id="u-old",
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            )
        )
        assert await cleanup_old_sessions() >= 1
