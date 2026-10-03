"""Account deletion against REAL better-auth session documents (#763).

No dependency override and no patched resolver: every request authenticates
through get_current_user_from_session, reading the better-auth `session` and
`user` collections exactly as production does. The documents are shaped the way
better-auth's MongoDB adapter writes them — `_id` and every `userId` reference
are ObjectIds.
"""

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from app.db.base import get_collection
from app.db.user import ensure_user_indexes
from app.main import app


async def _seed_better_auth_user(email: str, sessions: int = 1) -> dict:
    """Insert a better-auth user with a credential account, a twoFactor row and
    ``sessions`` live sessions. Returns the user id and the session tokens."""
    now = datetime.now(timezone.utc)
    user_oid = ObjectId()
    await (await get_collection("user")).insert_one(
        {
            "_id": user_oid,
            "email": email,
            "name": "Del Eted",
            "emailVerified": False,
            "twoFactorEnabled": True,
            "createdAt": now,
            "updatedAt": now,
        }
    )
    await (await get_collection("account")).insert_one(
        {
            "userId": user_oid,
            "accountId": str(user_oid),
            "providerId": "credential",
            "password": "hash",  # the old password lives here
            "createdAt": now,
            "updatedAt": now,
        }
    )
    await (await get_collection("twoFactor")).insert_one(
        {"userId": user_oid, "secret": "totp-secret", "backupCodes": "codes"}
    )
    tokens = [await _mint_session(user_oid) for _ in range(sessions)]
    return {"user_id": str(user_oid), "oid": user_oid, "tokens": tokens}


async def _mint_session(user_oid: ObjectId) -> str:
    token = f"tok-{ObjectId()}"
    now = datetime.now(timezone.utc)
    await (await get_collection("session")).insert_one(
        {
            "token": token,
            "userId": user_oid,
            "expiresAt": now + timedelta(days=7),
            "createdAt": now,
            "updatedAt": now,
        }
    )
    return token


def _client(token: str) -> AsyncClient:
    # better-auth signs the cookie as "<token>.<signature>"; the backend strips
    # the signature before the lookup, so send it in that shape.
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies={"better-auth.session_token": f"{token}.signature"},
    )


async def _better_auth_docs(user_oid: ObjectId) -> dict:
    return {
        name: await (await get_collection(name)).count_documents(
            {"userId": user_oid}
        )
        for name in ("session", "account", "twoFactor")
    } | {
        "user": await (await get_collection("user")).count_documents(
            {"_id": user_oid}
        )
    }


@pytest.mark.asyncio
async def test_deleted_account_is_locked_out_and_its_better_auth_docs_are_gone(
    motor_reinit_db,
):
    victim = await _seed_better_auth_user("gone@example.com", sessions=2)
    bystander = await _seed_better_auth_user("stays@example.com")
    this_device, other_device = victim["tokens"]

    async with _client(this_device) as c, _client(other_device) as c2:
        assert (await c.get("/api/v1/users/me")).status_code == 200
        created = await c.post("/api/v1/books/", json={"title": "Before"})
        assert created.status_code == 201, created.text

        deleted = await c.delete("/api/v1/users/me")
        assert deleted.status_code == 200, deleted.text

        for client in (c, c2):
            assert (await client.get("/api/v1/users/me")).status_code == 401
            after = await client.post("/api/v1/books/", json={"title": "After"})
            assert after.status_code == 401

    assert await _better_auth_docs(victim["oid"]) == {
        "session": 0,
        "account": 0,
        "twoFactor": 0,
        "user": 0,
    }, "no session, credential account (old password), 2FA or user doc may survive"

    # A session minted for the old id after deletion still cannot authenticate:
    # the better-auth user is gone and the app record is inactive.
    late = await _mint_session(victim["oid"])
    async with _client(late) as c:
        assert (await c.get("/api/v1/users/me")).status_code == 401

    app_user = await (await get_collection("users")).find_one(
        {"auth_id": victim["user_id"]}
    )
    assert app_user["is_active"] is False
    assert "email" not in app_user, "email released so the address can sign up again"

    assert await _better_auth_docs(bystander["oid"]) == {
        "session": 1,
        "account": 1,
        "twoFactor": 1,
        "user": 1,
    }, "another user's better-auth docs must not be touched"
    async with _client(bystander["tokens"][0]) as c:
        assert (await c.get("/api/v1/users/me")).status_code == 200


@pytest.mark.asyncio
async def test_inactive_app_user_is_rejected_even_with_a_live_session(motor_reinit_db):
    seeded = await _seed_better_auth_user("inactive@example.com")
    async with _client(seeded["tokens"][0]) as c:
        assert (await c.get("/api/v1/users/me")).status_code == 200
        await (await get_collection("users")).update_one(
            {"auth_id": seeded["user_id"]}, {"$set": {"is_active": False}}
        )
        assert (await c.get("/api/v1/users/me")).status_code == 401


@pytest.mark.asyncio
async def test_session_whose_better_auth_user_was_deleted_is_rejected(motor_reinit_db):
    seeded = await _seed_better_auth_user("orphan@example.com")
    async with _client(seeded["tokens"][0]) as c:
        assert (await c.get("/api/v1/users/me")).status_code == 200
        # App user still exists and is active; only the better-auth row is gone.
        await (await get_collection("user")).delete_one({"_id": seeded["oid"]})
        assert (await c.get("/api/v1/users/me")).status_code == 401


@pytest.mark.asyncio
async def test_same_email_can_sign_up_again_after_deletion(motor_reinit_db):
    first = await _seed_better_auth_user("again@example.com")
    async with _client(first["tokens"][0]) as c:
        assert (await c.get("/api/v1/users/me")).status_code == 200
        # The production unique index on users.email is what makes a retained
        # soft-deleted record collide with the new sign-up. Build it after the
        # collection exists (see motor_reinit_db's drop/index race).
        await ensure_user_indexes()
        indexes = await (await get_collection("users")).index_information()
        assert "email_unique_idx" in indexes
        assert (await c.delete("/api/v1/users/me")).status_code == 200

    # better-auth issues a brand-new user id on the second sign-up.
    second = await _seed_better_auth_user("again@example.com")
    async with _client(second["tokens"][0]) as c:
        me = await c.get("/api/v1/users/me")
        assert me.status_code == 200, me.text
        assert me.json()["auth_id"] == second["user_id"]
        assert me.json()["email"] == "again@example.com"


@pytest.mark.asyncio
async def test_admin_user_list_still_serialises_a_deleted_account(motor_reinit_db):
    """The deleted record keeps no email, so the admin listing must not 500 on it."""
    gone = await _seed_better_auth_user("listed@example.com")
    async with _client(gone["tokens"][0]) as c:
        assert (await c.get("/api/v1/users/me")).status_code == 200
        assert (await c.delete("/api/v1/users/me")).status_code == 200

    admin = await _seed_better_auth_user("admin@example.com")
    async with _client(admin["tokens"][0]) as c:
        assert (await c.get("/api/v1/users/me")).status_code == 200
        await (await get_collection("users")).update_one(
            {"auth_id": admin["user_id"]}, {"$set": {"role": "admin"}}
        )
        listed = await c.get("/api/v1/users/admin/users")
        assert listed.status_code == 200, listed.text
        deleted = next(u for u in listed.json() if u["auth_id"] == gone["user_id"])
        assert deleted["email"] is None


@pytest.mark.asyncio
async def test_delete_by_auth_id_revokes_better_auth_docs_too(motor_reinit_db):
    seeded = await _seed_better_auth_user("byid@example.com")
    async with _client(seeded["tokens"][0]) as c:
        assert (await c.get("/api/v1/users/me")).status_code == 200
        resp = await c.delete(f"/api/v1/users/{seeded['user_id']}")
        assert resp.status_code == 204, resp.text
        assert (await c.get("/api/v1/users/me")).status_code == 401

    assert await _better_auth_docs(seeded["oid"]) == {
        "session": 0,
        "account": 0,
        "twoFactor": 0,
        "user": 0,
    }
