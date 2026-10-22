"""Email ownership (#765): better-auth owns users' email, the backend mirrors it.

Runs the real session path end to end on real Mongo — a better-auth ``user`` and
``session`` document, a real cookie, no dependency overrides — because the bug
lived in the interaction between the unique email index and the auto-create
path, which no mock of either can show.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from app.core.security import get_current_user_from_session
from app.db import base
from app.db.user import ensure_user_indexes
from app.main import app
from tests.session_cookies import signed_session_cookie

pytestmark = pytest.mark.asyncio

VICTIM_EMAIL = "victim@example.com"


async def _seed_better_auth(email: str) -> tuple[str, str]:
    """Insert a better-auth user and a live session, as its MongoDB adapter writes
    them: the user under an ObjectId ``_id``, the session's ``userId`` that same
    ObjectId. Returns the user's id, as the application stores it, and the token."""
    oid = ObjectId()
    token = f"tok-{oid}"
    await base._db.get_collection("user").insert_one(
        {"_id": oid, "email": email, "name": "Some Body", "emailVerified": True}
    )
    await base._db.get_collection("session").insert_one(
        {
            "token": token,
            "userId": oid,
            "expiresAt": datetime.now(timezone.utc) + timedelta(hours=1),
        }
    )
    return str(oid), token


async def _indexed_users():
    # Warm the freshly dropped collection before building indexes, or the first
    # createIndexes can be silently lost (reinit/drop race).
    await base.users_collection.insert_one({"auth_id": "warmup"})
    await base.users_collection.delete_one({"auth_id": "warmup"})
    await ensure_user_indexes()


def _request(token: str) -> Request:
    cookie = f"better-auth.session_token={signed_session_cookie(token)}".encode()
    return Request({"type": "http", "headers": [(b"cookie", cookie)]})


async def test_stale_email_holder_no_longer_blocks_first_login(reinit_db):
    """The lockout: a backend doc already holds the victim's email (set through
    the old PATCH /users/me). The victim's first login must still succeed."""
    await _indexed_users()
    await base.users_collection.insert_one(
        {"auth_id": "attacker-id", "email": VICTIM_EMAIL, "first_name": "Mallory"}
    )
    victim_id, token = await _seed_better_auth(VICTIM_EMAIL)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies={"better-auth.session_token": signed_session_cookie(token)},
    ) as client:
        resp = await client.get("/api/v1/users/me")

    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == VICTIM_EMAIL
    victim = await base.users_collection.find_one({"auth_id": victim_id})
    assert victim["email"] == VICTIM_EMAIL
    attacker = await base.users_collection.find_one({"auth_id": "attacker-id"})
    assert attacker is not None and "email" not in attacker


async def test_concurrent_first_loads_share_one_record(reinit_db):
    """The auth_id race (#178) still resolves to the one winning record."""
    await _indexed_users()
    racer_id, token = await _seed_better_auth("racer@example.com")

    results = await asyncio.gather(
        *(get_current_user_from_session(_request(token)) for _ in range(5))
    )

    assert {str(r["_id"]) for r in results} == {str(results[0]["_id"])}
    assert await base.users_collection.count_documents({"auth_id": racer_id}) == 1


async def test_existing_record_mirrors_better_auth_email(reinit_db):
    """A doc whose email diverged from better-auth is brought back in line on
    the owner's next request, which also frees the address it was squatting."""
    await _indexed_users()
    attacker_id, token = await _seed_better_auth("mallory@example.com")
    await base.users_collection.insert_one(
        {"auth_id": attacker_id, "email": VICTIM_EMAIL, "first_name": "Mallory"}
    )

    user = await get_current_user_from_session(_request(token))

    assert user["email"] == "mallory@example.com"
    stored = await base.users_collection.find_one({"auth_id": attacker_id})
    assert stored["email"] == "mallory@example.com"
    assert await base.users_collection.count_documents({"email": VICTIM_EMAIL}) == 0
    # An email change is security-relevant: the mirror leaves an audit trail.
    assert await base.audit_logs_collection.count_documents(
        {"action": "user_update", "target_id": attacker_id}
    ) == 1


async def test_mirror_releases_email_held_by_another_record(reinit_db):
    """Mirroring onto an address a stale doc holds must not 500 on the index."""
    await _indexed_users()
    owner_id, token = await _seed_better_auth("new@example.com")
    await base.users_collection.insert_many(
        [
            {"auth_id": owner_id, "email": "old@example.com"},
            {"auth_id": "squatter-id", "email": "new@example.com"},
        ]
    )

    user = await get_current_user_from_session(_request(token))

    assert user["email"] == "new@example.com"
    squatter = await base.users_collection.find_one({"auth_id": "squatter-id"})
    assert "email" not in squatter
