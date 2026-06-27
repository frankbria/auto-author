"""
Direct DB-layer tests for app/db/user.py (user CRUD + book deletion).

Uses a real local MongoDB via the motor_reinit_db fixture. The conftest rebinds
users_dao.users_collection per test but NOT users_dao.books_collection, so the
delete_user_books tests rebind it explicitly to the fresh per-test collection.
"""

import pytest
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
)

pytestmark = pytest.mark.asyncio


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
    async def test_soft_delete_marks_inactive(self, motor_reinit_db):
        await _make_user(auth_id="auth-soft")
        ok = await delete_user("auth-soft", actor_id="admin")
        assert ok is True
        doc = await get_user_by_auth_id("auth-soft")
        assert doc["is_active"] is False
        log = await base.audit_logs_collection.find_one({"action": "user_delete"})
        assert log["details"]["soft_delete"] is True

    async def test_soft_delete_missing_returns_false(self, motor_reinit_db):
        assert await delete_user("absent") is False

    async def test_hard_delete_removes_document(self, motor_reinit_db):
        await _make_user(auth_id="auth-hard")
        ok = await delete_user("auth-hard", soft_delete=False)
        assert ok is True
        assert await get_user_by_auth_id("auth-hard") is None

    async def test_hard_delete_missing_returns_false(self, motor_reinit_db):
        assert await delete_user("absent", soft_delete=False) is False

    async def test_delete_defaults_actor_to_self(self, motor_reinit_db):
        await _make_user(auth_id="auth-self")
        await delete_user("auth-self")  # no actor_id -> actor defaults to auth_id
        log = await base.audit_logs_collection.find_one({"action": "user_delete"})
        assert log["actor_id"] == "auth-self"


class TestDeleteUserBooks:
    async def test_delete_all_user_books(self, bind_books):
        uid = "owner-1"
        await base.books_collection.insert_many(
            [{"user_id": uid, "title": "A"}, {"user_id": uid, "title": "B"}]
        )
        ok = await delete_user_books(uid)
        assert ok is True
        assert await base.books_collection.count_documents({"user_id": uid}) == 0

    async def test_delete_specific_books(self, bind_books):
        uid = "owner-2"
        keep = ObjectId()
        drop = ObjectId()
        await base.books_collection.insert_many(
            [
                {"_id": keep, "user_id": uid, "title": "keep"},
                {"_id": drop, "user_id": uid, "title": "drop"},
            ]
        )
        ok = await delete_user_books(uid, book_ids=[str(drop)])
        assert ok is True
        remaining = await base.books_collection.find({"user_id": uid}).to_list(None)
        assert {b["_id"] for b in remaining} == {keep}

    async def test_delete_no_books_returns_false(self, bind_books):
        assert await delete_user_books("owner-empty") is False

    async def test_invalid_book_id_is_handled(self, bind_books):
        # Non-hex book id raises inside the try -> returns False, no crash
        assert await delete_user_books("owner-x", book_ids=["not-an-objectid"]) is False
