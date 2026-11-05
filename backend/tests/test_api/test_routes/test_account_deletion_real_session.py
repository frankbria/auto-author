"""Account deletion against REAL better-auth session documents (#763).

No dependency override and no patched resolver: every request authenticates
through get_current_user_from_session, reading the better-auth `session` and
`users` collections exactly as production does (#1263). The documents are shaped
the way better-auth's MongoDB adapter writes them — `_id` and every `userId`
reference are ObjectIds.
"""

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from app.db.base import get_collection
from app.db.user import ensure_user_indexes
from tests.session_cookies import mint_session as _mint_session, real_session_client as _client


async def _seed_better_auth_user(
    email: str, sessions: int = 1, name: str = "Del Eted"
) -> dict:
    """Insert a better-auth user with a credential account, a twoFactor row and
    ``sessions`` live sessions. Returns the user id and the session tokens."""
    now = datetime.now(timezone.utc)
    user_oid = ObjectId()
    await (await get_collection("users")).insert_one(
        {
            "_id": user_oid,
            "email": email,
            "name": name,
            "emailVerified": True,
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


KEPT_KEYS = {"_id", "auth_id", "deleted_at", "purge_at", "retained"}
NONE_LEFT = {"session": 0, "account": 0, "twoFactor": 0, "users": 0}
ALL_THERE = {"session": 1, "account": 1, "twoFactor": 1, "users": 1}


async def _docs_mentioning(*needles: str) -> list:
    """"<collection>:<_id>" for every document in the test database that
    contains one of ``needles`` anywhere, nested values included."""
    db = (await get_collection("users")).database
    hits = []
    for name in await db.list_collection_names():
        async for doc in db[name].find():
            if any(needle in str(doc) for needle in needles):
                hits.append(f"{name}:{doc['_id']}")
    return hits


async def _better_auth_docs(user_oid: ObjectId) -> dict:
    return {
        name: await (await get_collection(name)).count_documents(
            {"userId": user_oid}
        )
        for name in ("session", "account", "twoFactor")
    } | {
        "users": await (await get_collection("users")).count_documents(
            {"_id": user_oid}
        )
    }


async def _kept(user_id: str):
    return await (await get_collection("deleted_users")).find_one({"auth_id": user_id})


async def _make_admin(seeded: dict) -> None:
    await (await get_collection("users")).update_one(
        {"_id": seeded["oid"]}, {"$set": {"role": "admin"}}
    )


@pytest.mark.asyncio
async def test_deleted_account_is_locked_out_and_its_better_auth_docs_are_gone(
    reinit_db,
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

    assert await _better_auth_docs(victim["oid"]) == NONE_LEFT, (
        "no session, credential account (old password), 2FA or users doc may survive"
    )

    # A session minted for the old id after deletion still cannot authenticate:
    # there is no user for it to resolve to.
    late = await _mint_session(victim["oid"])
    async with _client(late) as c:
        assert (await c.get("/api/v1/users/me")).status_code == 401

    assert set(await _kept(victim["user_id"])) == KEPT_KEYS

    assert await _better_auth_docs(bystander["oid"]) == ALL_THERE, (
        "another user's better-auth docs must not be touched"
    )
    async with _client(bystander["tokens"][0]) as c:
        assert (await c.get("/api/v1/users/me")).status_code == 200


@pytest.mark.asyncio
async def test_inactive_app_user_is_rejected_even_with_a_live_session(reinit_db):
    seeded = await _seed_better_auth_user("inactive@example.com")
    async with _client(seeded["tokens"][0]) as c:
        assert (await c.get("/api/v1/users/me")).status_code == 200
        await (await get_collection("users")).update_one(
            {"_id": seeded["oid"]}, {"$set": {"is_active": False}}
        )
        assert (await c.get("/api/v1/users/me")).status_code == 401


@pytest.mark.asyncio
async def test_session_whose_user_doc_is_gone_is_rejected(reinit_db):
    """With no auto-create (#1263), nothing can bring the account back."""
    seeded = await _seed_better_auth_user("orphan@example.com")
    async with _client(seeded["tokens"][0]) as c:
        assert (await c.get("/api/v1/users/me")).status_code == 200
        await (await get_collection("users")).delete_one({"_id": seeded["oid"]})
        assert (await c.get("/api/v1/users/me")).status_code == 401
        assert (await c.get("/api/v1/users/me")).status_code == 401
    assert await (await get_collection("users")).count_documents({}) == 0


@pytest.mark.asyncio
async def test_same_email_can_sign_up_again_after_deletion(reinit_db):
    first = await _seed_better_auth_user("again@example.com")
    users = await get_collection("users")
    async with _client(first["tokens"][0]) as c:
        assert (await c.get("/api/v1/users/me")).status_code == 200
        # The production unique index on users.email is what would make a
        # deleted account collide with the new sign-up. Build it after the
        # collection exists (see reinit_db's drop/index race).
        await ensure_user_indexes()
        indexes = await users.index_information()
        assert "email_unique_idx" in indexes
        await users.update_one(
            {"_id": first["oid"]}, {"$set": {"stripe_customer_id": "cus_first"}}
        )
        assert (await c.delete("/api/v1/users/me")).status_code == 200

    # better-auth issues a brand-new user id on the second sign-up.
    second = await _seed_better_auth_user("again@example.com")
    async with _client(second["tokens"][0]) as c:
        me = await c.get("/api/v1/users/me")
        assert me.status_code == 200, me.text
        assert me.json()["auth_id"] == second["user_id"]
        assert me.json()["email"] == "again@example.com"

    # #954: the kept record holds the email and billing identity, and none of
    # it is attached to the new account.
    kept = await _kept(first["user_id"])
    assert kept["retained"]["email"] == "again@example.com"
    assert kept["retained"]["stripe_customer_id"] == "cus_first"
    assert await users.count_documents({}) == 1
    fresh = await users.find_one({"_id": second["oid"]})
    assert "stripe_customer_id" not in fresh and "auth_id" not in fresh


@pytest.mark.asyncio
async def test_admin_user_list_serialises_the_users_better_auth_wrote(reinit_db):
    """The documents carry no auth_id; the listing derives it, and a deleted
    account is not listed."""
    gone = await _seed_better_auth_user("listed@example.com")
    async with _client(gone["tokens"][0]) as c:
        assert (await c.get("/api/v1/users/me")).status_code == 200
        assert (await c.delete("/api/v1/users/me")).status_code == 200

    admin = await _seed_better_auth_user("admin@example.com", name="Ada Min")
    await _make_admin(admin)
    async with _client(admin["tokens"][0]) as c:
        listed = await c.get("/api/v1/users/admin/users")
        assert listed.status_code == 200, listed.text
        assert [(u["auth_id"], u["email"], u["first_name"]) for u in listed.json()] == [
            (admin["user_id"], "admin@example.com", "Ada")
        ]


@pytest.mark.asyncio
async def test_delete_by_auth_id_revokes_better_auth_docs_too(reinit_db):
    seeded = await _seed_better_auth_user("byid@example.com")
    async with _client(seeded["tokens"][0]) as c:
        assert (await c.get("/api/v1/users/me")).status_code == 200
        resp = await c.delete(f"/api/v1/users/{seeded['user_id']}")
        assert resp.status_code == 204, resp.text
        assert (await c.get("/api/v1/users/me")).status_code == 401

    assert await _better_auth_docs(seeded["oid"]) == NONE_LEFT


@pytest.mark.asyncio
async def test_deletion_keeps_the_account_record_until_an_admin_erases_it(
    reinit_db,
):
    """#954: DELETE /users/me keeps the name, email and billing identity in
    deleted_users and nowhere else. An admin's DELETE then erases that record
    down to its id and deletion date, and nothing that identifies the person survives."""
    email = "erase.me@example.com"
    identifying = (email, "Zebedee", "Quillfeather", "cus_erase_me")
    seeded = await _seed_better_auth_user(email, name="Zebedee Quillfeather")
    users = await get_collection("users")

    async with _client(seeded["tokens"][0]) as c:
        assert (await c.get("/api/v1/users/me")).status_code == 200
        patched = await c.patch(
            "/api/v1/users/me",
            json={
                "display_name": "Zebedee Q.",
                "bio": "Quillfeather writes about owls",
            },
        )
        assert patched.status_code == 200, patched.text
        # Billing identity is webhook-written and the avatar URL upload-written;
        # neither is API-writable (#797).
        await users.update_one(
            {"_id": seeded["oid"]},
            {
                "$set": {
                    "stripe_customer_id": "cus_erase_me",
                    "avatar_url": "https://example.com/Zebedee.png",
                }
            },
        )
        before = await _docs_mentioning(*identifying)
        assert any(h.startswith("users:") for h in before), "scan must see the data"

        assert (await c.delete("/api/v1/users/me")).status_code == 200

    kept = await _kept(seeded["user_id"])
    assert set(kept) == KEPT_KEYS
    retained = kept["retained"]
    assert {k: v for k, v in retained.items() if k != "created_at"} == {
        "email": email,
        "first_name": "Zebedee",
        "last_name": "Quillfeather",
        "display_name": "Zebedee Q.",
        "plan": "free",
        "stripe_customer_id": "cus_erase_me",
    }
    assert isinstance(retained["created_at"], datetime)
    assert kept["purge_at"] - kept["deleted_at"] == timedelta(days=548)
    assert "owls" not in str(kept) and "Zebedee.png" not in str(kept)
    assert await _docs_mentioning(*identifying) == [f"deleted_users:{kept['_id']}"]

    support = await _seed_better_auth_user("support@example.com")
    await _make_admin(support)
    async with _client(support["tokens"][0]) as c:
        erase = await c.delete(f"/api/v1/users/{seeded['user_id']}")
        assert erase.status_code == 204, erase.text
        # Only the identifier and deletion date stay, as the privacy page says.
        assert set(await _kept(seeded["user_id"])) == {"_id", "auth_id", "deleted_at"}
        assert await _docs_mentioning(*identifying) == []

        again = await c.delete(f"/api/v1/users/{seeded['user_id']}")
        assert again.status_code == 404

    erased_by = await (await get_collection("audit_logs")).find_one(
        {"action": "user_erase"}
    )
    assert erased_by["actor_id"] == support["user_id"]


@pytest.mark.asyncio
async def test_an_account_whose_deletion_has_begun_is_rejected(reinit_db):
    """If the deletion stops after the users doc is marked, the surviving
    session must not authenticate, and nothing is written to the doc."""
    seeded = await _seed_better_auth_user("halfway@example.com")
    users = await get_collection("users")
    async with _client(seeded["tokens"][0]) as c:
        assert (await c.get("/api/v1/users/me")).status_code == 200
        await users.update_one(
            {"_id": seeded["oid"]}, {"$set": {"deleted_at": datetime.now(timezone.utc)}}
        )
        marked = await users.find_one({"_id": seeded["oid"]})
        assert (await c.get("/api/v1/users/me")).status_code == 401

    assert await users.find_one({"_id": seeded["oid"]}) == marked
