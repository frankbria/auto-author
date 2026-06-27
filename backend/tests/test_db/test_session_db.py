"""
Residual coverage for app/db/session.py — paths not hit by the service tests:
get_session_by_id miss, get_active_session_by_user, update_session field
branches / no-op / not-found, and update_session_activity not-found.
"""

import pytest
from datetime import datetime, timezone, timedelta

from app.db.session import (
    create_session,
    get_session_by_id,
    get_active_session_by_user,
    update_session,
    update_session_activity,
    deactivate_session,
)
from app.models.session import SessionCreate, SessionUpdate, SessionMetadata

pytestmark = pytest.mark.asyncio


async def _new(user_id="u1", **kw):
    return await create_session(SessionCreate(user_id=user_id, **kw))


class TestLookups:
    async def test_get_by_id_missing(self, motor_reinit_db):
        assert await get_session_by_id("sess_missing") is None

    async def test_active_session_for_user(self, motor_reinit_db):
        created = await _new(user_id="active-user")
        found = await get_active_session_by_user("active-user")
        assert found is not None
        assert found.session_id == created.session_id

    async def test_active_session_none_when_expired(self, motor_reinit_db):
        await _new(
            user_id="expired-user",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert await get_active_session_by_user("expired-user") is None

    async def test_active_session_none_when_deactivated(self, motor_reinit_db):
        s = await _new(user_id="off-user")
        await deactivate_session(s.session_id)
        assert await get_active_session_by_user("off-user") is None


class TestUpdateSession:
    async def test_update_all_optional_fields(self, motor_reinit_db):
        s = await _new()
        upd = SessionUpdate(
            last_activity=datetime.now(timezone.utc),
            is_active=False,
            is_suspicious=True,
            metadata=SessionMetadata(browser="Firefox"),
            request_count=7,
            last_endpoint="/api/v1/books",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        result = await update_session(s.session_id, upd)
        assert result.is_active is False
        assert result.is_suspicious is True
        assert result.request_count == 7
        assert result.last_endpoint == "/api/v1/books"
        assert result.metadata.browser == "Firefox"

    async def test_update_noop_returns_current(self, motor_reinit_db):
        s = await _new()
        # All-None update -> no fields to set -> returns current session
        result = await update_session(s.session_id, SessionUpdate())
        assert result.session_id == s.session_id

    async def test_update_missing_session_returns_none(self, motor_reinit_db):
        result = await update_session("sess_missing", SessionUpdate(request_count=1))
        assert result is None


class TestUpdateActivity:
    async def test_activity_missing_session_returns_none(self, motor_reinit_db):
        assert await update_session_activity("sess_missing", "/x") is None
