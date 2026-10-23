"""A deletion that dies between the tombstone and the identity erasure is
finished automatically (#935).

`delete_user` writes the tombstone, then erases the better-auth session,
account, twoFactor and user documents one collection at a time. A crash or a
failover in between left the email, name and password hash behind, and the
user could not retry: the tombstone refuses their session. A start-up sweep
now erases whatever a tombstone left behind.

Against a real MongoDB.
"""

import pytest

from app.db import user as users_dao
from app.db.user import create_user, delete_user, erase_stranded_identities
from tests.test_api.test_routes.test_account_deletion_real_session import (
    _better_auth_docs,
    _seed_better_auth_user,
)

pytestmark = pytest.mark.asyncio

NONE_LEFT = {"session": 0, "account": 0, "twoFactor": 0, "user": 0}
ALL_THERE = {"session": 1, "account": 1, "twoFactor": 1, "user": 1}


async def _account(email: str) -> dict:
    seeded = await _seed_better_auth_user(email)
    await create_user({"auth_id": seeded["user_id"], "email": email, "plan": "free", "is_active": True})
    return seeded


async def test_a_deletion_that_died_after_the_tombstone_is_finished_by_the_sweep(reinit_db, monkeypatch):
    victim = await _account("stranded@example.com")
    bystander = await _account("stays@example.com")

    async def dies(auth_id):
        raise RuntimeError("the process died here")

    with monkeypatch.context() as patched:
        patched.setattr(users_dao, "delete_better_auth_identity", dies)
        with pytest.raises(RuntimeError):
            await delete_user(victim["user_id"])
    assert await _better_auth_docs(victim["oid"]) == ALL_THERE  # the strand #935 describes

    assert await erase_stranded_identities() == 1

    assert await _better_auth_docs(victim["oid"]) == NONE_LEFT
    assert await _better_auth_docs(bystander["oid"]) == ALL_THERE


async def test_the_sweep_is_idempotent(reinit_db, monkeypatch):
    victim = await _account("twice@example.com")

    async def dies(auth_id):
        raise RuntimeError("the process died here")

    with monkeypatch.context() as patched:
        patched.setattr(users_dao, "delete_better_auth_identity", dies)
        with pytest.raises(RuntimeError):
            await delete_user(victim["user_id"])

    assert await erase_stranded_identities() == 1
    assert await erase_stranded_identities() == 0
    assert await _better_auth_docs(victim["oid"]) == NONE_LEFT


async def test_a_password_left_without_its_user_is_found_too(reinit_db):
    """The erasure deletes the better-auth user last; a strand may still hold
    only the account (the password hash) if that order ever changes."""
    from app.db.base import get_collection

    victim = await _account("account-only@example.com")
    await delete_user(victim["user_id"])
    await (await get_collection("account")).insert_one({"userId": victim["oid"], "password": "hash"})

    assert await erase_stranded_identities() == 1
    assert await _better_auth_docs(victim["oid"]) == NONE_LEFT


# #956: a deactivation (#954) keeps a retained record, and finishing its
# identity removal must not cost that record.


async def _deactivate_with_identity_removal_failing_once(monkeypatch, victim: dict) -> None:
    """Deactivate ``victim`` while the database drops the connection once, part
    way through the identity removal: the sessions go, the rest stays."""
    from pymongo.errors import AutoReconnect

    real_get_collection = users_dao.get_collection
    failed = []

    async def drops_once(name):
        if name == "account" and not failed:
            failed.append(name)
            raise AutoReconnect("connection reset by peer")
        return await real_get_collection(name)

    monkeypatch.setattr(users_dao, "get_collection", drops_once)
    with pytest.raises(AutoReconnect):
        await delete_user(victim["user_id"])
    assert failed and await _better_auth_docs(victim["oid"]) == {**ALL_THERE, "session": 0}


async def _retained(auth_id: str) -> dict:
    from app.db.base import get_collection

    doc = await (await get_collection("users")).find_one({"auth_id": auth_id})
    return {key: doc.get(key) for key in ("purge_at", "retained")}


async def test_the_sweep_finishes_a_failed_removal_and_keeps_the_retained_record(reinit_db, monkeypatch):
    victim = await _account("sweep-keeps@example.com")
    await _deactivate_with_identity_removal_failing_once(monkeypatch, victim)
    kept = await _retained(victim["user_id"])
    assert kept["retained"]["email"] == "sweep-keeps@example.com"

    assert await erase_stranded_identities() == 1

    assert await _better_auth_docs(victim["oid"]) == NONE_LEFT
    assert await _retained(victim["user_id"]) == kept


async def test_an_admin_finishes_a_failed_removal_without_erasing_the_retained_record(reinit_db, monkeypatch):
    from app.db.base import get_collection
    from tests.session_cookies import real_session_client

    victim = await _account("admin-repair@example.com")
    await _deactivate_with_identity_removal_failing_once(monkeypatch, victim)
    kept = await _retained(victim["user_id"])

    admin = await _seed_better_auth_user("repairer@example.com")
    async with real_session_client(admin["tokens"][0]) as c:
        assert (await c.get("/api/v1/users/me")).status_code == 200
        await (await get_collection("users")).update_one(
            {"auth_id": admin["user_id"]}, {"$set": {"role": "admin"}}
        )
        assert (await c.delete(f"/api/v1/users/{victim['user_id']}")).status_code == 204

        assert await _better_auth_docs(victim["oid"]) == NONE_LEFT
        assert await _retained(victim["user_id"]) == kept

        # With the identity gone, the next admin DELETE is the erasure #954 offers.
        assert (await c.delete(f"/api/v1/users/{victim['user_id']}")).status_code == 204
    assert await _retained(victim["user_id"]) == {"purge_at": None, "retained": None}
