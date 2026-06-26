"""
Tests for SessionMiddleware (app/api/middleware/session_middleware.py).

Drives dispatch() directly with mocked session_service calls to cover the
skip-path, bypass, cookie-session, user-session, and error branches.
"""

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from starlette.responses import Response

from app.api.middleware import session_middleware as sm
from app.api.middleware.session_middleware import SessionMiddleware


def _request(path="/api/v1/books", cookies=None, headers=None, user=None):
    req = Mock()
    req.url.path = path
    req.cookies = cookies or {}
    req.headers = headers or {}
    req.state = SimpleNamespace()
    if user is not None:
        req.state.user = user
    return req


def _call_next_returning(response=None):
    return AsyncMock(return_value=response or Response("ok"))


def _session(active=True, suspicious=False, sid="sess_1", uid="u1"):
    return SimpleNamespace(
        session_id=sid, user_id=uid, is_active=active, is_suspicious=suspicious
    )


@pytest.fixture
def mw():
    return SessionMiddleware(app=Mock())


@pytest.mark.asyncio
class TestSessionMiddleware:
    async def test_skip_path_bypasses_session_logic(self, mw):
        req = _request(path="/docs")
        call_next = _call_next_returning()
        with patch.object(sm.settings, "BYPASS_AUTH", False):
            resp = await mw.dispatch(req, call_next)
        call_next.assert_awaited_once()
        assert "X-Session-ID" not in resp.headers

    async def test_bypass_auth_skips(self, mw):
        req = _request()
        call_next = _call_next_returning()
        with patch.object(sm.settings, "BYPASS_AUTH", True):
            resp = await mw.dispatch(req, call_next)
        call_next.assert_awaited_once()
        assert "X-Session-ID" not in resp.headers

    async def test_valid_cookie_session_sets_cookie_and_header(self, mw):
        req = _request(cookies={"session_id": "sess_1"})
        call_next = _call_next_returning()
        session = _session()
        with patch.object(sm.settings, "BYPASS_AUTH", False), \
             patch.object(sm, "validate_session", AsyncMock(return_value=session)):
            resp = await mw.dispatch(req, call_next)
        assert resp.headers["X-Session-ID"] == "sess_1"
        assert "session_id=sess_1" in resp.headers.get("set-cookie", "")
        assert req.state.session is session

    async def test_suspicious_session_logs_warning(self, mw):
        req = _request(headers={"X-Session-ID": "sess_1"})
        call_next = _call_next_returning()
        session = _session(suspicious=True)
        with patch.object(sm.settings, "BYPASS_AUTH", False), \
             patch.object(sm, "validate_session", AsyncMock(return_value=session)), \
             patch.object(sm.logger, "warning") as mock_warn:
            await mw.dispatch(req, call_next)
        mock_warn.assert_called_once()

    async def test_validate_session_error_is_swallowed(self, mw):
        req = _request(cookies={"session_id": "sess_1"})
        call_next = _call_next_returning()
        with patch.object(sm.settings, "BYPASS_AUTH", False), \
             patch.object(sm, "validate_session", AsyncMock(side_effect=RuntimeError("boom"))), \
             patch.object(sm.logger, "error") as mock_err:
            resp = await mw.dispatch(req, call_next)
        mock_err.assert_called_once()
        assert "X-Session-ID" not in resp.headers  # no session attached

    async def test_authenticated_user_reuses_existing_session(self, mw):
        req = _request(user={"auth_id": "u1"})
        call_next = _call_next_returning()
        session = _session()
        with patch.object(sm.settings, "BYPASS_AUTH", False), \
             patch.object(sm, "get_active_session_by_user", AsyncMock(return_value=session)), \
             patch.object(sm, "create_user_session", AsyncMock()) as mock_create:
            resp = await mw.dispatch(req, call_next)
        mock_create.assert_not_awaited()
        assert resp.headers["X-Session-ID"] == "sess_1"

    async def test_authenticated_user_creates_new_session(self, mw):
        req = _request(user={"auth_id": "u1"}, headers={"X-Auth-Session-ID": "auth_99"})
        call_next = _call_next_returning()
        new_session = _session(sid="sess_new")
        with patch.object(sm.settings, "BYPASS_AUTH", False), \
             patch.object(sm, "get_active_session_by_user", AsyncMock(return_value=None)), \
             patch.object(sm, "create_user_session", AsyncMock(return_value=new_session)) as mock_create:
            resp = await mw.dispatch(req, call_next)
        mock_create.assert_awaited_once()
        assert resp.headers["X-Session-ID"] == "sess_new"

    async def test_create_session_error_is_swallowed(self, mw):
        req = _request(user={"auth_id": "u1"})
        call_next = _call_next_returning()
        with patch.object(sm.settings, "BYPASS_AUTH", False), \
             patch.object(sm, "get_active_session_by_user", AsyncMock(side_effect=RuntimeError("boom"))), \
             patch.object(sm.logger, "error") as mock_err:
            resp = await mw.dispatch(req, call_next)
        mock_err.assert_called_once()
        assert "X-Session-ID" not in resp.headers

    async def test_no_session_no_user_passes_through(self, mw):
        req = _request()  # no cookie, no user on state
        call_next = _call_next_returning()
        with patch.object(sm.settings, "BYPASS_AUTH", False):
            resp = await mw.dispatch(req, call_next)
        call_next.assert_awaited_once()
        assert "X-Session-ID" not in resp.headers

    async def test_inactive_session_not_written_to_response(self, mw):
        req = _request(cookies={"session_id": "sess_1"})
        call_next = _call_next_returning()
        session = _session(active=False)
        with patch.object(sm.settings, "BYPASS_AUTH", False), \
             patch.object(sm, "validate_session", AsyncMock(return_value=session)):
            resp = await mw.dispatch(req, call_next)
        assert "X-Session-ID" not in resp.headers
