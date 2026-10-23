"""Indexes for the lookups better-auth makes itself (#1034).

Its Mongo adapter creates none. The filters below are the ones a profiled
sign-up, sign-in, password reset and session list actually issued.
"""
import logging
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.db import base
from app.db.user import ensure_user_indexes
from app.main import app

EXPECTED = {
    "user": {"email": 1},
    "account": {"userId": 1},
    "session": {"userId": 1},
    "verification": {"identifier": 1},
}


async def _keys(name):
    indexes = await (await base._db.get_collection(name).list_indexes()).to_list(None)
    return [idx["key"] for idx in indexes]


async def _warm():
    """First createIndexes after a drop can be lost: do a real write first."""
    for name in EXPECTED:
        await base._db.get_collection(name).insert_one({"warm": True, "email": f"{name}@warm.test"})


@pytest.mark.asyncio
async def test_ensure_user_indexes_indexes_the_filters_better_auth_uses(reinit_db):
    await _warm()
    await ensure_user_indexes()
    await ensure_user_indexes()  # twice is harmless

    for name, key in EXPECTED.items():
        assert key in await _keys(name), name


@pytest.mark.asyncio
async def test_user_email_is_unique_when_the_data_allows(reinit_db):
    await _warm()
    await ensure_user_indexes()
    indexes = await (await base._db.user.list_indexes()).to_list(None)
    email = next(i for i in indexes if i["key"] == {"email": 1})
    assert email.get("unique") is True


@pytest.mark.asyncio
async def test_duplicate_emails_do_not_block_startup(reinit_db, caplog):
    users = base._db.user
    await users.insert_many([{"email": "dup@example.com"}, {"email": "dup@example.com"}])
    with caplog.at_level(logging.ERROR):
        await ensure_user_indexes()
        await ensure_user_indexes()

    indexes = await (await users.list_indexes()).to_list(None)
    email = next(i for i in indexes if i["key"] == {"email": 1})
    assert not email.get("unique")
    assert "duplicate" in caplog.text.lower()
    # the rest still got built
    assert {"userId": 1} in await _keys("account")


@pytest.mark.asyncio
async def test_lifespan_creates_them(reinit_db, monkeypatch):
    # Shutdown closes the export pool; hand it one no other test uses.
    monkeypatch.setattr("app.services.export_service.export_executor", ThreadPoolExecutor(1))
    await _warm()
    async with app.router.lifespan_context(app):
        await app.state.database_prepared
    assert {"identifier": 1} in await _keys("verification")
    assert {"userId": 1} in await _keys("session")
