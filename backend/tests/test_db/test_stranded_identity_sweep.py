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


async def test_a_deletion_that_died_after_the_tombstone_is_finished_by_the_sweep(motor_reinit_db, monkeypatch):
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


async def test_the_sweep_is_idempotent(motor_reinit_db, monkeypatch):
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


async def test_a_password_left_without_its_user_is_found_too(motor_reinit_db):
    """The erasure deletes the better-auth user last; a strand may still hold
    only the account (the password hash) if that order ever changes."""
    from app.db.base import get_collection

    victim = await _account("account-only@example.com")
    await delete_user(victim["user_id"])
    await (await get_collection("account")).insert_one({"userId": victim["oid"], "password": "hash"})

    assert await erase_stranded_identities() == 1
    assert await _better_auth_docs(victim["oid"]) == NONE_LEFT
