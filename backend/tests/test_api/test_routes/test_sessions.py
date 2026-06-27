"""
HTTP-layer tests for app/api/endpoints/sessions.py.

Auth is mocked via auth_client_factory (overrides get_current_user_from_session).
request.state.session is populated by the registered SessionMiddleware, which
attaches a session when a valid `session_id` cookie is present (BYPASS_AUTH is
False by default in tests). So we create a real session in the test DB and set
that cookie to exercise the endpoints that read request.state.session.
"""

import pytest
from datetime import datetime, timezone, timedelta

from app.db.session import create_session
from app.models.session import SessionCreate, SessionMetadata

pytestmark = pytest.mark.asyncio

# auth_id seeded by the test_user fixture used inside auth_client_factory
TEST_AUTH_ID = "test-auth-id-123"


async def _make_session(user_id=TEST_AUTH_ID):
    """Create a real active session in the test DB and return it."""
    return await create_session(
        SessionCreate(
            user_id=user_id,
            metadata=SessionMetadata(fingerprint="seed-fp"),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=12),
        )
    )


class TestCurrentSession:
    async def test_get_current_status(self, auth_client_factory):
        client = await auth_client_factory()
        session = await _make_session()
        client.cookies.set("session_id", session.session_id)

        resp = await client.get("/api/v1/sessions/current")
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == session.session_id
        assert body["is_active"] is True

    async def test_get_current_no_session_404(self, auth_client_factory):
        client = await auth_client_factory()
        resp = await client.get("/api/v1/sessions/current")
        assert resp.status_code == 404
        assert "no active session" in resp.json()["detail"].lower()


class TestRefresh:
    async def test_refresh_extends_expiry(self, auth_client_factory):
        client = await auth_client_factory()
        session = await _make_session()
        client.cookies.set("session_id", session.session_id)

        resp = await client.post("/api/v1/sessions/refresh")
        assert resp.status_code == 200
        assert resp.json()["expires_at"] is not None

    async def test_refresh_no_session_404(self, auth_client_factory):
        client = await auth_client_factory()
        resp = await client.post("/api/v1/sessions/refresh")
        assert resp.status_code == 404


class TestLogout:
    async def test_logout_current(self, auth_client_factory):
        client = await auth_client_factory()
        session = await _make_session()
        client.cookies.set("session_id", session.session_id)

        resp = await client.post("/api/v1/sessions/logout")
        assert resp.status_code == 200
        assert "logged out" in resp.json()["message"].lower()

    async def test_logout_without_session(self, auth_client_factory):
        client = await auth_client_factory()
        resp = await client.post("/api/v1/sessions/logout")
        assert resp.status_code == 200
        assert "no active session" in resp.json()["message"].lower()


class TestLogoutAll:
    async def test_logout_all_keeps_current(self, auth_client_factory):
        client = await auth_client_factory()
        current = await _make_session()
        await _make_session()  # another session for the same user
        client.cookies.set("session_id", current.session_id)

        resp = await client.post("/api/v1/sessions/logout-all")
        assert resp.status_code == 200
        body = resp.json()
        assert body["current_session_kept"] is True
        assert body["sessions_ended"] >= 1

    async def test_logout_all_including_current(self, auth_client_factory):
        client = await auth_client_factory()
        await _make_session()
        await _make_session()

        resp = await client.post("/api/v1/sessions/logout-all?keep_current=false")
        assert resp.status_code == 200
        body = resp.json()
        assert body["current_session_kept"] is False
        assert body["sessions_ended"] >= 2


class TestListSessions:
    async def test_list_returns_sessions(self, auth_client_factory):
        client = await auth_client_factory()
        await _make_session()
        await _make_session()

        resp = await client.get("/api/v1/sessions/list")
        assert resp.status_code == 200
        sessions = resp.json()
        assert len(sessions) >= 2
        assert all(s["user_id"] == TEST_AUTH_ID for s in sessions)

    async def test_list_active_only(self, auth_client_factory):
        client = await auth_client_factory()
        await _make_session()
        resp = await client.get("/api/v1/sessions/list?active_only=true&limit=5")
        assert resp.status_code == 200
        assert all(s["is_active"] for s in resp.json())


class TestDeleteSession:
    async def test_delete_own_session(self, auth_client_factory):
        client = await auth_client_factory()
        session = await _make_session()

        resp = await client.delete(f"/api/v1/sessions/{session.session_id}")
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

    async def test_delete_unknown_session_404(self, auth_client_factory):
        client = await auth_client_factory()
        resp = await client.delete("/api/v1/sessions/sess_does_not_exist")
        assert resp.status_code == 404

    async def test_delete_other_users_session_403(self, auth_client_factory):
        client = await auth_client_factory()
        other = await _make_session(user_id="someone-else")

        resp = await client.delete(f"/api/v1/sessions/{other.session_id}")
        assert resp.status_code == 403
        assert "another user" in resp.json()["detail"].lower()
