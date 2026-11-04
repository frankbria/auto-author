"""
The users collection's indexes (#178, #1263).

better-auth creates users documents with no ``auth_id`` field, so the old
unique index on it would make every sign-up after the first collide on null:
ensure_user_indexes drops it.

Uses a real local MongoDB via reinit_db (which does NOT build app indexes),
so each test calls ensure_user_indexes() itself.
"""

import pytest
from pymongo.errors import DuplicateKeyError

from app.db import base
from app.db.base import get_collection
from app.db.user import ensure_user_indexes
from tests.user_docs import insert_user

pytestmark = pytest.mark.asyncio


async def _warm():
    # reinit_db drops the DB immediately before this test; a real
    # round-trip drains that async drop so the first createIndexes below
    # can't be lost to it (a drop-then-index test artifact, not a prod path).
    await base.users_collection.insert_one({"warmup": True})
    await base.users_collection.delete_many({})


async def test_creates_the_unique_indexes(reinit_db):
    await _warm()
    await ensure_user_indexes()

    indexes = (await base.users_collection.index_information()).values()
    email_idx = next((v for v in indexes if v["key"] == [("email", 1)]), None)
    assert email_idx is not None and email_idx.get("unique") is True
    assert not [v for v in indexes if v["key"] == [("auth_id", 1)]]

    deleted = (await (await get_collection("deleted_users")).index_information()).values()
    assert [v for v in deleted if v["key"] == [("auth_id", 1)] and v.get("unique")]


async def test_drops_the_old_auth_id_index_so_sign_ups_do_not_collide(reinit_db):
    await _warm()
    await base.users_collection.create_index("auth_id", name="auth_id_unique_idx", unique=True)

    await ensure_user_indexes()

    assert "auth_id_unique_idx" not in await base.users_collection.index_information()
    await insert_user(email="first@example.com")
    await insert_user(email="second@example.com")
    assert await base.users_collection.count_documents({}) == 2


async def test_an_email_is_still_one_account(reinit_db):
    await _warm()
    await ensure_user_indexes()

    await insert_user(email="taken@example.com")
    with pytest.raises(DuplicateKeyError):
        await insert_user(email="taken@example.com")


async def test_idempotent(reinit_db):
    # Safe to run twice (mirrors startup re-runs / hot reload).
    await ensure_user_indexes()
    await ensure_user_indexes()
