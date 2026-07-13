"""Regression tests: legacy /sessions/* subsystem removed (issue #196).

The advertised "Session Management" feature was dead code: SessionMiddleware
only acted when request.state.user was set, but nothing ever set it, so the
/api/v1/sessions/* endpoints never worked (current/refresh/logout always 404,
list always empty). Real session management is better-auth's native APIs
(ActiveSessionsList in the frontend). The legacy router, middleware, service,
DAO, and model were deleted rather than wired up.
"""
import pytest

from app.main import app

pytestmark = pytest.mark.asyncio


async def test_sessions_list_route_is_gone(auth_client_factory):
    # RED on the old code: /sessions/list was the one endpoint that "worked"
    # (returned 200 with an empty list). After removal it must 404.
    client = await auth_client_factory()
    resp = await client.get("/api/v1/sessions/list")
    assert resp.status_code in (404, 405)


async def test_no_sessions_routes_registered():
    session_paths = [
        path
        for r in app.routes
        if (path := getattr(r, "path", "")).startswith("/api/v1/sessions")
    ]
    assert session_paths == []
