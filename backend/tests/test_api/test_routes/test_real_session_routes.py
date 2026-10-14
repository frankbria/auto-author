"""Routes reached with real better-auth session cookies, and nothing overridden (#838).

Almost every route test replaces ``get_current_user_from_session`` with a
stand-in that hands back a user it was told about. These do not: each request
is authenticated by the application itself, from a signed cookie and the
``session`` and ``user`` documents better-auth's MongoDB adapter writes. What a
valid, an expired, a revoked and another user's cookie get from a route is
therefore what production gives them.
"""

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from app.core.security import get_current_user_from_session
from app.db.base import get_collection
from app.main import app
from tests.session_cookies import mint_session, real_session_client, signed_session_cookie

BOOK = {"title": "Small Changes", "genre": "Self-help", "target_audience": "Managers"}


async def _a_better_auth_user(email: str) -> ObjectId:
    """A verified user as better-auth's MongoDB adapter stores one: keyed by an ObjectId."""
    now = datetime.now(timezone.utc)
    oid = ObjectId()
    await (await get_collection("user")).insert_one(
        {"_id": oid, "email": email, "name": "Ada Writer", "emailVerified": True, "createdAt": now, "updatedAt": now}
    )
    return oid


async def _signed_in(email: str, **session) -> tuple[AsyncClient, str]:
    token = await mint_session(await _a_better_auth_user(email), **session)
    return real_session_client(token), token


def _client_with(cookie_value: str | None) -> AsyncClient:
    cookies = {"better-auth.session_token": cookie_value} if cookie_value else {}
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies)


@pytest.fixture(autouse=True)
def nothing_stands_in_for_the_sign_in_check(motor_reinit_db):
    """These tests are worth nothing with an override in place: refuse to run with one."""
    assert get_current_user_from_session not in app.dependency_overrides
    yield
    assert get_current_user_from_session not in app.dependency_overrides


@pytest.mark.asyncio
async def test_a_valid_cookie_reaches_the_routes_as_its_own_user():
    ada, _ = await _signed_in("ada@example.com")
    async with ada:
        me = await ada.get("/api/v1/users/me")
        created = await ada.post("/api/v1/books/", json=BOOK)
        listed = await ada.get("/api/v1/books/")

    assert me.status_code == 200, me.text
    assert me.json()["email"] == "ada@example.com"
    assert created.status_code == 201, created.text
    assert [book["title"] for book in listed.json()] == ["Small Changes"]


@pytest.mark.asyncio
async def test_an_expired_cookie_is_refused_and_its_session_removed():
    ada, token = await _signed_in("ada@example.com", expires_in=timedelta(minutes=-1))
    async with ada:
        me = await ada.get("/api/v1/users/me")
        books = await ada.get("/api/v1/books/")

    assert (me.status_code, books.status_code) == (401, 401)
    assert await (await get_collection("session")).count_documents({"token": token}) == 0


@pytest.mark.asyncio
async def test_a_revoked_cookie_is_refused_on_the_very_next_request():
    ada, token = await _signed_in("ada@example.com")
    async with ada:
        before = await ada.get("/api/v1/books/")
        # What better-auth does when a session is revoked from Settings: the document goes.
        await (await get_collection("session")).delete_one({"token": token})
        after = await ada.get("/api/v1/books/")

    assert (before.status_code, after.status_code) == (200, 401)


@pytest.mark.asyncio
async def test_one_users_cookie_does_not_open_another_users_book():
    ada, _ = await _signed_in("ada@example.com")
    grace, _ = await _signed_in("grace@example.com")
    async with ada, grace:
        book_id = (await ada.post("/api/v1/books/", json=BOOK)).json()["id"]

        hers = await ada.get(f"/api/v1/books/{book_id}")
        not_hers = await grace.get(f"/api/v1/books/{book_id}")
        changed = await grace.patch(f"/api/v1/books/{book_id}", json={"title": "Mine Now"})
        deleted = await grace.delete(f"/api/v1/books/{book_id}")
        graces_list = await grace.get("/api/v1/books/")
        still_hers = await ada.get(f"/api/v1/books/{book_id}")

    assert hers.status_code == 200
    # Refused each time: 403 where the route says so, 404 where it will not say the book exists.
    assert not_hers.status_code == 403
    assert {changed.status_code, deleted.status_code} <= {403, 404}
    assert graces_list.json() == []
    assert still_hers.json()["title"] == "Small Changes"


@pytest.mark.asyncio
async def test_two_cookies_are_two_users_whatever_order_they_signed_in():
    ada, _ = await _signed_in("ada@example.com")
    grace, _ = await _signed_in("grace@example.com")
    async with ada, grace:
        emails = [(await who.get("/api/v1/users/me")).json()["email"] for who in (grace, ada, grace)]

    assert emails == ["grace@example.com", "ada@example.com", "grace@example.com"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cookie",
    ["none", "unsigned", "signed for a session that does not exist", "another token's signature"],
)
async def test_a_cookie_that_is_not_a_live_session_is_refused(cookie):
    _, token = await _signed_in("ada@example.com")
    value = {
        "none": None,
        "unsigned": token,
        "signed for a session that does not exist": signed_session_cookie("tok-no-such-session"),
        "another token's signature": token + "." + signed_session_cookie("tok-other").rpartition(".")[2],
    }[cookie]

    async with _client_with(value) as someone:
        me = await someone.get("/api/v1/users/me")
        books = await someone.get("/api/v1/books/")

    assert (me.status_code, books.status_code) == (401, 401)
