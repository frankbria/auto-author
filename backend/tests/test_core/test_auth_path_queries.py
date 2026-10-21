"""What one signed-in request asks the database (#826).

It used to ask five things: the session by its token, with no index on the
token; a write to the session; the better-auth user by a field, ``id``, that
better-auth's MongoDB adapter does not write, which scanned the collection and
found nothing; the same user by ``_id``; and the application's record of the
user, with every book id the user has ever had.

The data here is in the shape better-auth writes it, and the database is asked
what it was asked: its profiler records each command and the plan it ran.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from fastapi import HTTPException
from starlette.requests import Request

import app.db.base as base
from app.core import better_auth_session as bas
from app.core.security import get_current_user_from_session
from app.db.user import ensure_user_indexes
from app.schemas.user import UserResponse
from tests.session_cookies import signed_session_cookie

pytestmark = pytest.mark.asyncio

READS = {"query", "command", "getmore"}
WRITES = {"insert", "update", "remove"}


async def _signed_in(*, last_active: timedelta = timedelta(0)) -> tuple[Request, ObjectId]:
    """A user as better-auth stores one, a live session, the application's record, and the indexes."""
    oid = ObjectId()
    now = datetime.now(timezone.utc)
    await base._db["user"].insert_many([
        {"_id": oid, "email": "writer@example.com", "name": "A Writer", "emailVerified": True},
        *({"_id": ObjectId(), "email": f"other{n}@example.com"} for n in range(5)),
    ])
    await base._db["session"].insert_many([
        {"token": f"tok-{oid}", "userId": oid, "expiresAt": now + timedelta(hours=1),
         "createdAt": now - timedelta(days=1), "updatedAt": now - last_active},
        *({"token": f"tok-{ObjectId()}", "userId": ObjectId(), "expiresAt": now} for _ in range(5)),
    ])
    await base.users_collection.insert_one({
        "auth_id": str(oid), "email": "writer@example.com", "is_active": True,
        "book_ids": [str(ObjectId()) for _ in range(40)],
    })
    await ensure_user_indexes()
    cookie = f"better-auth.session_token={signed_session_cookie(f'tok-{oid}')}".encode()
    return Request({"type": "http", "headers": [(b"cookie", cookie)]}), oid


@asynccontextmanager
async def _asked():
    """What the database is asked inside the block, about the three collections sign-in uses."""
    asked = []
    await base._db.command("profile", 2)
    try:
        yield asked
    finally:
        await base._db.command("profile", 0)
        name = base._db.name
        asked.extend(await base._db["system.profile"].find(
            {"ns": {"$in": [f"{name}.session", f"{name}.user", f"{name}.users"]}}
        ).to_list(None))


def _values(explained, key):
    """Every value under ``key`` anywhere in an explain document."""
    if isinstance(explained, dict):
        return [v for k, v in explained.items() if k == key] + [f for v in explained.values() for f in _values(v, key)]
    if isinstance(explained, list):
        return [f for v in explained for f in _values(v, key)]
    return []


async def test_a_signed_in_request_reads_twice_and_writes_nothing(reinit_db):
    request, oid = await _signed_in()

    async with _asked() as asked:
        user = await get_current_user_from_session(request)

    assert user["auth_id"] == str(oid)
    what = [(entry["op"], entry["ns"].split(".", 1)[1]) for entry in asked]
    assert [op for op, _ in what if op in WRITES] == [], what
    assert len([op for op, _ in what if op in READS]) <= 2, what
    assert len(what) >= 2, f"the profiler recorded too little to count: {what}"


async def test_nothing_it_asks_scans_a_collection(reinit_db):
    request, _ = await _signed_in()

    async with _asked() as asked:
        await get_current_user_from_session(request)

    plans = [(entry["ns"].split(".", 1)[1], entry.get("planSummary", "")) for entry in asked]
    assert not [plan for _, plan in plans if "COLLSCAN" in plan], plans
    assert [plan for collection, plan in plans if collection == "session" and "token" in plan], plans
    assert [plan for collection, plan in plans if collection == "users" and "auth_id" in plan], plans


async def test_the_user_is_found_through_the_index_on_its_id(reinit_db):
    """The session's user is joined to it in the same read. explain() says how."""
    _, oid = await _signed_in()

    explained = await base._db.command(
        "explain",
        {"aggregate": "session", "pipeline": bas._session_and_its_user(f"tok-{oid}"), "cursor": {}},
        verbosity="executionStats",
    )

    # The classic engine reports the indexes a $lookup used; the newer one names the join's index.
    used = [name for names in _values(explained, "indexesUsed") for name in names] + _values(explained, "indexName")
    assert "_id_" in used, used
    assert "COLLSCAN" not in str(explained)
    assert "NestedLoopJoin" not in _values(explained, "strategy")


async def test_a_lookup_of_the_user_on_its_own_goes_by_id_too(reinit_db):
    """The fallback, for a session that holds its user id as text."""
    _, oid = await _signed_in()

    async with _asked() as asked:
        found = await bas.get_better_auth_user(str(oid))

    assert found["email"] == "writer@example.com"
    assert [(entry["op"], entry.get("planSummary", "")) for entry in asked if "COLLSCAN" in entry.get("planSummary", "")] == []
    assert len(asked) == 1, asked


async def test_the_user_it_returns_does_not_carry_every_book_id(reinit_db):
    request, _ = await _signed_in()

    user = await get_current_user_from_session(request)

    assert "book_ids" not in user
    assert user["email"] == "writer@example.com" and user["is_active"] is True
    # Nothing reads it from the signed-in user, and the API no longer claims to return it.
    assert "book_ids" not in UserResponse.model_fields


async def test_last_active_is_written_once_it_is_out_of_date(reinit_db):
    """Settings shows a session's updatedAt as "Last active"."""
    request, oid = await _signed_in(last_active=timedelta(minutes=30))
    before = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=5)

    async with _asked() as asked:
        await get_current_user_from_session(request)

    assert [entry["op"] for entry in asked if entry["op"] in WRITES] == ["update"]
    assert (await base._db["session"].find_one({"token": f"tok-{oid}"}))["updatedAt"] >= before


async def test_a_session_whose_user_is_gone_is_refused(reinit_db):
    """A session that outlives its better-auth user is not a credential (#763)."""
    request, oid = await _signed_in()
    await base._db["user"].delete_one({"_id": oid})

    with pytest.raises(HTTPException) as refused:
        await get_current_user_from_session(request)

    assert refused.value.status_code == 401


async def test_a_session_holding_its_user_id_as_text_still_signs_in(reinit_db):
    """Not how better-auth writes it now. The join finds nothing; the user is looked up on its own."""
    request, oid = await _signed_in()
    await base._db["session"].update_one({"token": f"tok-{oid}"}, {"$set": {"userId": str(oid)}})

    user = await get_current_user_from_session(request)

    assert user["auth_id"] == str(oid)


async def test_the_better_auth_email_is_still_mirrored(reinit_db):
    """The joined user is the one whose email the application's record follows (#765)."""
    request, oid = await _signed_in()
    await base._db["user"].update_one({"_id": oid}, {"$set": {"email": "renamed@example.com"}})

    user = await get_current_user_from_session(request)

    assert user["email"] == "renamed@example.com"
    assert (await base.users_collection.find_one({"auth_id": str(oid)}))["email"] == "renamed@example.com"


async def test_sessions_are_indexed_by_token(reinit_db):
    await _signed_in()

    indexes = await base._db["session"].index_information()

    assert [("token", 1)] in [index["key"] for index in indexes.values()], indexes
