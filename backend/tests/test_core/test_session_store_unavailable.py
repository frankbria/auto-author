"""A session that cannot be checked is our outage, not a signed-out user (#1007).

When the database was away the session lookup failed, the failure was treated
like a session that does not exist, and the request was answered 401 "Please
sign in" after the driver's thirty seconds. The frontend ends the session in
the browser on a 401 from the API, so a database blip logged out everyone who
made a request during it.

The database here is a real driver pointed at an address nothing listens on.
"""

import time
from unittest.mock import AsyncMock, patch

import pytest
import sentry_sdk
from bson import ObjectId
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError
from starlette.requests import Request

from app import main
from app.core import better_auth_session as sessions
from app.core import reporting
from app.core.config import settings
from app.main import app
from tests.session_cookies import session_collection, signed_session_cookie

pytestmark = pytest.mark.asyncio

TOKEN = "TOKEN-SENTINEL-of-a-signed-in-user"
COOKIE = f"better-auth.session_token={signed_session_cookie(TOKEN)}"
ORIGIN = {"Origin": settings.BACKEND_CORS_ORIGINS[0]}


def _request() -> Request:
    return Request({"type": "http", "method": "GET", "path": "/", "headers": [(b"cookie", COOKIE.encode())]})


@pytest.fixture
def database_is_away(monkeypatch):
    """The session collections on a driver whose server is not there. The driver would
    wait its usual thirty seconds; the lookup's own limit is shortened to keep the test quick."""
    away = AsyncIOMotorClient("mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=30000")
    monkeypatch.setattr(sessions, "get_collection", AsyncMock(side_effect=lambda name: away["nowhere"][name]))
    monkeypatch.setattr(sessions, "SESSION_LOOKUP_TIMEOUT_SECONDS", 0.3)
    yield
    away.close()


class TestTheLookupSaysItCouldNotLook:
    async def test_a_session_lookup_that_cannot_reach_the_database_is_not_a_missing_session(self, database_is_away):
        started = time.monotonic()
        with pytest.raises(sessions.SessionStoreUnavailable):
            await sessions.validate_better_auth_session(_request())

        assert time.monotonic() - started < 5, "it gave up on its own limit, not the driver's thirty seconds"

    async def test_nor_is_a_user_lookup(self, database_is_away):
        with pytest.raises(sessions.SessionStoreUnavailable):
            await sessions.get_better_auth_user(str(ObjectId()))

    async def test_an_error_the_database_reports_counts_too(self):
        collection = session_collection(error=ServerSelectionTimeoutError("no primary"))
        with patch.object(sessions, "get_collection", AsyncMock(return_value=collection)):
            with pytest.raises(sessions.SessionStoreUnavailable):
                await sessions.validate_better_auth_session(_request())

    async def test_nor_is_the_user_lookup_when_the_database_reports_an_error(self):
        """Its failure used to be swallowed as "that id is not an ObjectId", which is a 401."""
        collection = AsyncMock()
        collection.find_one.side_effect = ServerSelectionTimeoutError("no primary")
        with patch.object(sessions, "get_collection", AsyncMock(return_value=collection)):
            with pytest.raises(sessions.SessionStoreUnavailable):
                await sessions.get_better_auth_user(str(ObjectId()))

    async def test_an_id_that_is_not_an_object_id_is_still_just_a_user_who_is_not_there(self):
        collection = AsyncMock()
        collection.find_one.return_value = None
        with patch.object(sessions, "get_collection", AsyncMock(return_value=collection)):
            assert await sessions.get_better_auth_user("not-an-object-id") is None

        assert collection.find_one.await_count == 1

    async def test_a_session_that_is_not_there_is_still_just_not_there(self):
        collection = session_collection()
        with patch.object(sessions, "get_collection", AsyncMock(return_value=collection)):
            assert await sessions.validate_better_auth_session(_request()) is None

        collection.aggregate.return_value.to_list.assert_awaited_once()

    async def test_a_session_record_that_makes_no_sense_is_still_refused_not_an_outage(self):
        collection = session_collection({"_id": "s1", "userId": "u1", "expiresAt": "not a date"})
        with patch.object(sessions, "get_collection", AsyncMock(return_value=collection)):
            assert await sessions.validate_better_auth_session(_request()) is None


class TestTheRequestIsToldToComeBackNotToSignIn:
    @pytest.fixture
    async def api(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client

    @pytest.fixture
    def reports(self, monkeypatch):
        sent: list = []
        real_init = sentry_sdk.init
        monkeypatch.setattr(settings, "SENTRY_DSN", "https://key@sentry.invalid/1")
        monkeypatch.setattr(sentry_sdk, "init", lambda **options: real_init(**options, transport=sent.append))
        monkeypatch.setattr(reporting, "_last_reported", {})
        main._init_sentry()
        # The SDK wraps an app's exception handlers when the app's middleware is
        # built, which for this shared app happened before the SDK was started
        # here. Build it again, or the SDK's own reporting of a 5xx is not in
        # play and this test could not see a report per request.
        app.middleware_stack = None
        yield sent
        real_init()
        app.middleware_stack = None

    async def test_a_signed_in_request_is_answered_503_with_when_to_retry(self, api, database_is_away):
        response = await api.get("/api/v1/books/", headers={"Cookie": COOKIE, **ORIGIN})

        assert response.status_code == 503
        assert response.status_code != 401, "a 401 ends the session in the browser"
        assert int(response.headers["retry-after"]) > 0
        assert "sign in" not in response.json()["detail"].lower()

    async def test_the_page_can_read_that_answer(self, api, database_is_away):
        response = await api.get("/api/v1/books/", headers={"Cookie": COOKIE, **ORIGIN})

        assert response.headers["access-control-allow-origin"] == ORIGIN["Origin"]
        assert response.headers["x-request-id"]

    async def test_it_is_reported_once_and_not_once_per_request(self, api, database_is_away, reports):
        for _ in range(3):
            await api.get("/api/v1/books/", headers={"Cookie": COOKIE})

        assert [r["fingerprint"] for r in reports] == [["handled", "session-validation"]]
        assert "TOKEN-SENTINEL" not in str(reports)

    async def test_the_same_when_the_database_goes_after_the_session_was_found(self, api, monkeypatch):
        """The sign-in check makes a third lookup, of the app's own record of the user."""
        from app.core import security

        monkeypatch.setattr(security, "validate_better_auth_session", AsyncMock(return_value={"userId": ObjectId()}))
        monkeypatch.setattr(security, "get_better_auth_user", AsyncMock(return_value={"email": "writer@example.com"}))
        with patch("app.db.user.get_user_by_auth_id", AsyncMock(side_effect=ServerSelectionTimeoutError("no primary"))):
            response = await api.get("/api/v1/books/", headers={"Cookie": COOKIE})

        assert response.status_code == 503
        assert int(response.headers["retry-after"]) > 0

    async def test_a_request_with_no_session_is_still_asked_to_sign_in(self, api):
        response = await api.get("/api/v1/books/")

        assert response.status_code in (401, 403)
