"""The stand-in for the sign-in check in ``conftest.py`` is as strict as the real one (#838).

Both client factories replace ``get_current_user_from_session``. The stand-in
used to answer a missing or unknown cookie with the first user any client had
been made for, so a test that forgot its cookie, or sent the wrong one, was
quietly signed in as someone. And it answered with the dictionary the user was
seeded from, so a test could change the user in the database and never see it.
"""

import pytest

from tests.conftest import _sync_sessions, _sync_users

FACTORIES = ["auth_client_factory", "async_client_factory"]


@pytest.fixture(params=FACTORIES)
def make_client(request):
    return request.getfixturevalue(request.param)


@pytest.mark.asyncio
async def test_a_client_made_without_sign_in_is_not_signed_in_as_the_first_user(make_client):
    await make_client()
    anonymous = await make_client(auth=False)

    assert (await anonymous.get("/api/v1/users/me")).status_code == 401


@pytest.mark.asyncio
async def test_a_cookie_no_client_was_given_is_not_signed_in_as_the_first_user(make_client):
    client = await make_client()
    client.cookies.set("better-auth.session_token", "test-session-nobody")

    assert (await client.get("/api/v1/users/me")).status_code == 401


@pytest.mark.asyncio
async def test_each_client_is_its_own_user(make_client):
    first = await make_client(overrides={"auth_id": "auth-first", "email": "first@example.com"})
    second = await make_client(overrides={"auth_id": "auth-second", "email": "second@example.com"})

    emails = [(await who.get("/api/v1/users/me")).json()["email"] for who in (second, first)]

    assert emails == ["second@example.com", "first@example.com"]


@pytest.mark.asyncio
async def test_the_user_is_read_again_on_every_request(make_client):
    client = await make_client()
    before = (await client.get("/api/v1/users/me")).json()

    _sync_users.update_one({"auth_id": before["auth_id"]}, {"$set": {"first_name": "Renamed"}})

    assert (await client.get("/api/v1/users/me")).json()["first_name"] == "Renamed"


@pytest.mark.asyncio
async def test_a_user_who_is_no_longer_in_the_database_is_not_signed_in(make_client):
    client = await make_client()
    me = (await client.get("/api/v1/users/me")).json()

    _sync_users.delete_one({"auth_id": me["auth_id"]})

    assert (await client.get("/api/v1/users/me")).status_code == 401


def test_the_sessions_handle_is_better_auths_collection():
    # better-auth's collection is `session`; `sessions` is a collection nothing writes.
    assert _sync_sessions.name == "session"
