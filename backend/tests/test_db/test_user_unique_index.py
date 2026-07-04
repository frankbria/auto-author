"""
Tests for the users unique-index + idempotent create guard (issue #178).

Reproduces the check-then-insert race that produced duplicate user records for a
single auth_id and verifies the fix: a unique index on users.auth_id/email plus
a create_user that catches DuplicateKeyError and re-fetches the winner.

Uses a real local MongoDB via motor_reinit_db (which does NOT build app indexes),
so each test calls ensure_user_indexes() itself.
"""

import asyncio

import pytest
from pymongo.errors import DuplicateKeyError

from app.db import base
from app.db.user import create_user, ensure_user_indexes

pytestmark = pytest.mark.asyncio


def _user(**overrides):
    data = {
        "auth_id": "auth-race",
        "email": "race@example.com",
        "first_name": "Race",
        "is_active": True,
    }
    data.update(overrides)
    return data


class TestEnsureUserIndexes:
    async def test_creates_unique_indexes(self, motor_reinit_db):
        await ensure_user_indexes()

        indexes = await base.users_collection.index_information()

        auth_idx = next(
            (v for v in indexes.values() if v["key"] == [("auth_id", 1)]), None
        )
        email_idx = next(
            (v for v in indexes.values() if v["key"] == [("email", 1)]), None
        )

        assert auth_idx is not None and auth_idx.get("unique") is True
        assert email_idx is not None and email_idx.get("unique") is True

    async def test_idempotent(self, motor_reinit_db):
        # Safe to run twice (mirrors startup re-runs / hot reload).
        await ensure_user_indexes()
        await ensure_user_indexes()


class TestConcurrentCreateIsIdempotent:
    async def test_concurrent_first_loads_produce_one_record(self, motor_reinit_db):
        await ensure_user_indexes()

        # Simulate an SPA's parallel first-load requests all auto-creating the
        # same user at once.
        results = await asyncio.gather(*[create_user(_user()) for _ in range(8)])

        count = await base.users_collection.count_documents({"auth_id": "auth-race"})
        assert count == 1

        # Every caller gets the one real record back (not None / not a crash).
        ids = {str(r["_id"]) for r in results}
        assert len(ids) == 1

    async def test_email_collision_on_different_auth_id_reraises(self, motor_reinit_db):
        # A duplicate on some OTHER key than auth_id (e.g. email taken by a
        # different auth_id) has no auth_id winner to return, so create_user
        # re-raises rather than silently returning None. The legacy endpoint
        # maps this to a 409.
        await ensure_user_indexes()

        await create_user(_user(auth_id="auth-a", email="taken@example.com"))
        with pytest.raises(DuplicateKeyError):
            await create_user(_user(auth_id="auth-b", email="taken@example.com"))
