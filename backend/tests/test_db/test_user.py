"""
Direct DB-layer tests for app/db/user.py (user CRUD + book deletion).

Uses a real local MongoDB via the motor_reinit_db fixture. The conftest rebinds
users_dao.users_collection per test but NOT users_dao.books_collection, so the
delete_user_books tests rebind it explicitly to the fresh per-test collection.
"""

import pytest
from datetime import datetime, timedelta, timezone

from bson import ObjectId

import app.db.user as user_dao
from app.db import base
from app.db.user import (
    get_user_by_auth_id,
    get_user_by_id,
    get_user_by_email,
    create_user,
    update_user,
    delete_user,
    delete_user_books,
    erase_deactivated_user,
    purge_expired_users,
)

pytestmark = pytest.mark.asyncio

TOMBSTONE_KEYS = {"_id", "auth_id", "deleted_at"}
DEACTIVATED_KEYS = TOMBSTONE_KEYS | {"purge_at", "retained"}


@pytest.fixture
def bind_books(motor_reinit_db, monkeypatch):
    """Rebind the books_collection captured by user.py at import time to the
    fresh per-test collection (conftest only rebinds users_collection there)."""
    monkeypatch.setattr(user_dao, "books_collection", base.books_collection)


async def _make_user(**overrides):
    data = {
        "auth_id": "auth-1",
        "email": "user1@example.com",
        "first_name": "Jane",
        "is_active": True,
    }
    data.update(overrides)
    return await create_user(data)


class TestUserLookups:
    async def test_create_and_get_by_id(self, motor_reinit_db):
        created = await _make_user()
        assert created["_id"]
        fetched = await get_user_by_id(str(created["_id"]))
        assert fetched["email"] == "user1@example.com"

    async def test_get_by_auth_id(self, motor_reinit_db):
        await _make_user(auth_id="auth-xyz")
        found = await get_user_by_auth_id("auth-xyz")
        assert found is not None
        assert found["auth_id"] == "auth-xyz"

    async def test_get_by_auth_id_missing(self, motor_reinit_db):
        assert await get_user_by_auth_id("nope") is None

    async def test_get_by_email(self, motor_reinit_db):
        await _make_user(email="hit@example.com")
        found = await get_user_by_email("hit@example.com")
        assert found["email"] == "hit@example.com"

    async def test_get_by_email_missing(self, motor_reinit_db):
        assert await get_user_by_email("ghost@example.com") is None


class TestUpdateUser:
    async def test_update_sets_fields_and_timestamp(self, motor_reinit_db):
        await _make_user(auth_id="auth-upd")
        updated = await update_user("auth-upd", {"first_name": "Janet"})
        assert updated["first_name"] == "Janet"
        assert "updated_at" in updated

    async def test_update_missing_user_returns_none(self, motor_reinit_db):
        assert await update_user("absent", {"first_name": "X"}) is None

    async def test_update_with_actor_writes_audit_log(self, motor_reinit_db):
        await _make_user(auth_id="auth-audit")
        await update_user("auth-audit", {"bio": "new"}, actor_id="admin-1")
        log = await base.audit_logs_collection.find_one({"action": "user_update"})
        assert log is not None
        assert log["actor_id"] == "admin-1"
        assert "bio" in log["details"]["updated_fields"]


class TestDeleteUser:
    async def test_soft_delete_keeps_only_the_account_and_billing_record(
        self, motor_reinit_db
    ):
        """#954: deactivation keeps an allowlist under ``retained`` for 18 months."""
        await _make_user(
            auth_id="auth-soft", last_name="Doe", display_name="JD", plan="pro",
            bio="about me", stripe_customer_id="cus_1", preferences={"theme": "dark"},
            cancelled_subscription={"id": "sub_1", "plan": "pro", "status": "active"},
        )
        ok = await delete_user("auth-soft", actor_id="admin")
        assert ok is True
        doc = await get_user_by_auth_id("auth-soft")
        assert set(doc) == DEACTIVATED_KEYS
        assert doc["retained"] == {
            "email": "user1@example.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "display_name": "JD",
            "plan": "pro",
            "stripe_customer_id": "cus_1",
            "cancelled_subscription": {"id": "sub_1", "plan": "pro", "status": "active"},
        }
        assert doc["purge_at"] - doc["deleted_at"] == timedelta(days=548)
        log = await base.audit_logs_collection.find_one({"action": "user_delete"})
        assert log["details"]["soft_delete"] is True

    async def test_deleting_a_tombstone_again_reports_not_found(self, motor_reinit_db):
        await _make_user(auth_id="auth-twice")
        assert await delete_user("auth-twice") is True
        first = await get_user_by_auth_id("auth-twice")
        assert await delete_user("auth-twice") is False
        assert await get_user_by_auth_id("auth-twice") == first

    async def test_update_cannot_write_onto_a_tombstone(self, motor_reinit_db):
        await _make_user(auth_id="auth-gone")
        await delete_user("auth-gone")
        assert await update_user("auth-gone", {"bio": "back again"}) is None
        assert set(await get_user_by_auth_id("auth-gone")) == DEACTIVATED_KEYS

    async def test_soft_delete_missing_returns_false(self, motor_reinit_db):
        assert await delete_user("absent") is False

    async def test_hard_delete_removes_document(self, motor_reinit_db):
        await _make_user(auth_id="auth-hard")
        ok = await delete_user("auth-hard", soft_delete=False)
        assert ok is True
        assert await get_user_by_auth_id("auth-hard") is None

    async def test_hard_delete_missing_returns_false(self, motor_reinit_db):
        assert await delete_user("absent", soft_delete=False) is False

    async def test_in_flight_book_create_adds_nothing_to_a_tombstone(
        self, motor_reinit_db
    ):
        """A create_book that authenticated before the delete lands after it:
        its book_ids $push must not grow the tombstone."""
        from app.db.book import create_book

        await _make_user(auth_id="auth-race")
        await delete_user("auth-race")
        await create_book({"title": "Late"}, "auth-race")
        assert set(await get_user_by_auth_id("auth-race")) == DEACTIVATED_KEYS

    async def test_delete_defaults_actor_to_self(self, motor_reinit_db):
        await _make_user(auth_id="auth-self")
        await delete_user("auth-self")  # no actor_id -> actor defaults to auth_id
        log = await base.audit_logs_collection.find_one({"action": "user_delete"})
        assert log["actor_id"] == "auth-self"


class TestEraseAndPurge:
    """#954: a deactivated record ends as the #784 tombstone, early or on time."""

    async def test_erase_turns_a_deactivated_record_into_a_tombstone(
        self, motor_reinit_db
    ):
        await _make_user(auth_id="auth-erase")
        await delete_user("auth-erase")
        deleted_at = (await get_user_by_auth_id("auth-erase"))["deleted_at"]

        assert await erase_deactivated_user("auth-erase", actor_id="admin-1") is True

        doc = await get_user_by_auth_id("auth-erase")
        assert set(doc) == TOMBSTONE_KEYS
        assert doc["deleted_at"] == deleted_at
        log = await base.audit_logs_collection.find_one({"action": "user_erase"})
        assert (log["actor_id"], log["target_id"]) == ("admin-1", "auth-erase")

    async def test_erase_matches_only_a_deactivated_record(self, motor_reinit_db):
        await _make_user(auth_id="auth-active")
        tombstone = {"auth_id": "auth-old", "deleted_at": datetime(2026, 9, 1)}
        await user_dao.users_collection.insert_one(dict(tombstone))

        for auth_id in ("auth-active", "auth-old", "absent"):
            assert await erase_deactivated_user(auth_id, actor_id="admin-1") is False

        assert (await get_user_by_auth_id("auth-active"))["email"] == "user1@example.com"
        old = await get_user_by_auth_id("auth-old")
        assert {k: old[k] for k in tombstone} == tombstone and set(old) == TOMBSTONE_KEYS

    async def test_purge_erases_only_records_whose_purge_date_has_passed(
        self, motor_reinit_db
    ):
        users = user_dao.users_collection
        now = datetime.now(timezone.utc)
        await _make_user(auth_id="auth-due", email="due@example.com")
        await _make_user(auth_id="auth-waiting", email="waiting@example.com")
        await _make_user(auth_id="auth-active", email="active@example.com")
        await delete_user("auth-due")
        await delete_user("auth-waiting")
        # 18 months and a day ago.
        long_ago = now - timedelta(days=549)
        await users.update_one(
            {"auth_id": "auth-due"},
            {"$set": {"deleted_at": long_ago, "purge_at": long_ago + timedelta(days=548)}},
        )
        # An account erased before #954: a tombstone with no purge date.
        await users.insert_one({"auth_id": "auth-old", "deleted_at": long_ago})
        untouched = {
            auth_id: await get_user_by_auth_id(auth_id)
            for auth_id in ("auth-waiting", "auth-active", "auth-old")
        }

        assert await purge_expired_users() == 1

        due = await get_user_by_auth_id("auth-due")
        assert set(due) == TOMBSTONE_KEYS
        assert abs(due["deleted_at"] - long_ago.replace(tzinfo=None)) < timedelta(seconds=1)
        for auth_id, before in untouched.items():
            assert await get_user_by_auth_id(auth_id) == before
        assert await purge_expired_users() == 0


class TestDeleteUserBooks:
    async def test_delete_all_user_books(self, bind_books):
        # Books are stored with owner_id (see create_book); seeding user_id here
        # used to mask the #179 wrong-field bug.
        uid = "owner-1"
        await base.books_collection.insert_many(
            [{"owner_id": uid, "title": "A"}, {"owner_id": uid, "title": "B"}]
        )
        ok = await delete_user_books(uid)
        assert ok is True
        assert await base.books_collection.count_documents({"owner_id": uid}) == 0

    async def test_delete_specific_books(self, bind_books):
        uid = "owner-2"
        keep = ObjectId()
        drop = ObjectId()
        await base.books_collection.insert_many(
            [
                {"_id": keep, "owner_id": uid, "title": "keep"},
                {"_id": drop, "owner_id": uid, "title": "drop"},
            ]
        )
        ok = await delete_user_books(uid, book_ids=[str(drop)])
        assert ok is True
        remaining = await base.books_collection.find({"owner_id": uid}).to_list(None)
        assert {b["_id"] for b in remaining} == {keep}

    async def test_delete_no_books_returns_false(self, bind_books):
        assert await delete_user_books("owner-empty") is False

    async def test_invalid_book_id_is_handled(self, bind_books):
        # Non-hex book id raises inside the try -> returns False, no crash
        assert await delete_user_books("owner-x", book_ids=["not-an-objectid"]) is False
