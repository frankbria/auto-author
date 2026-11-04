"""
Direct DB-layer tests for app/db/user.py: one users collection (#1263).

better-auth creates the users document; the backend reads it by ``_id`` and
derives ``auth_id`` from it. A deletion keeps its record in deleted_users.

Uses a real local MongoDB via the reinit_db fixture.
"""

import pytest
from bson import ObjectId
from datetime import datetime, timedelta, timezone

import app.db.user as user_dao
from app.db import base
from app.db.base import get_collection
from app.db.user import (
    as_app_user,
    get_user_by_auth_id,
    get_user_by_email,
    update_user,
    delete_user,
    erase_deactivated_user,
    erase_stranded_identities,
    purge_expired_users,
)
from tests.user_docs import insert_user

pytestmark = pytest.mark.asyncio


async def _make_user(auth_id="auth-1", **overrides):
    data = {"email": "user1@example.com", "first_name": "Jane", "is_active": True}
    data.update(overrides)
    return await insert_user(auth_id, **data)


async def _stored(auth_id):
    return await base.users_collection.find_one(user_dao.user_key(auth_id))


async def _deleted(auth_id):
    return await (await get_collection("deleted_users")).find_one({"auth_id": auth_id})


class TestReadingABetterAuthUser:
    """The document better-auth writes at sign-up is the app's user."""

    async def test_it_is_found_by_its_id_and_gets_its_auth_id_from_it(self, reinit_db):
        signed_up = datetime(2026, 11, 1, 9, 0)
        oid = ObjectId()
        await base.users_collection.insert_one({
            "_id": oid, "email": "ada@example.com", "name": "Ada King Lovelace",
            "emailVerified": True, "createdAt": signed_up, "updatedAt": signed_up,
            "termsVersion": "2026-10-10", "termsAcceptedAt": signed_up,
        })

        user = await get_user_by_auth_id(str(oid))

        assert user["auth_id"] == str(oid)
        assert (user["first_name"], user["last_name"]) == ("Ada", "King Lovelace")
        assert (user["created_at"], user["updated_at"]) == (signed_up, signed_up)
        assert (user["terms_version"], user["terms_accepted_at"]) == ("2026-10-10", signed_up)
        assert (user["role"], user["plan"], user["is_active"], user["metadata"]) == (
            "user", "free", True, {},
        )
        assert "auth_id" not in await base.users_collection.find_one({"_id": oid})

    async def test_a_user_with_no_name_is_named_from_the_email(self):
        user = as_app_user({"_id": "u1", "email": "jo.bloggs@example.com"})
        assert (user["first_name"], user["last_name"]) == ("jo.bloggs", "")

    async def test_a_name_the_user_set_is_kept(self):
        user = as_app_user({"_id": "u1", "name": "A B", "first_name": "Al", "plan": "pro"})
        assert (user["first_name"], user["plan"]) == ("Al", "pro")
        assert "last_name" not in user

    async def test_a_missing_document_is_none(self, reinit_db):
        assert await get_user_by_auth_id(str(ObjectId())) is None
        assert await get_user_by_auth_id("nope") is None
        assert as_app_user(None) is None

    async def test_get_by_email(self, reinit_db):
        auth_id = await _make_user(email="hit@example.com")
        found = await get_user_by_email("hit@example.com")
        assert found["auth_id"] == auth_id
        assert await get_user_by_email("ghost@example.com") is None


class TestUpdateUser:
    async def test_update_sets_fields_and_better_auths_timestamp(self, reinit_db):
        await _make_user("auth-upd")
        updated = await update_user(
            "auth-upd", {"first_name": "Janet", "updated_at": datetime(2020, 1, 1)}
        )
        assert updated["first_name"] == "Janet"
        assert updated["updated_at"] > datetime(2026, 1, 1)
        stored = await _stored("auth-upd")
        assert "updated_at" not in stored and "auth_id" not in stored
        assert stored["updatedAt"] == updated["updated_at"]

    async def test_update_missing_user_returns_none(self, reinit_db):
        assert await update_user("absent", {"first_name": "X"}) is None

    async def test_update_with_actor_writes_audit_log(self, reinit_db):
        await _make_user("auth-audit")
        await update_user("auth-audit", {"bio": "new"}, actor_id="admin-1")
        log = await base.audit_logs_collection.find_one({"action": "user_update"})
        assert log is not None
        assert log["actor_id"] == "admin-1"
        assert "bio" in log["details"]["updated_fields"]


class TestDeleteUser:
    async def test_delete_keeps_only_the_account_and_billing_record(self, reinit_db):
        """#954: the users document goes; an allowlist is kept for 18 months."""
        await _make_user(
            "auth-soft", last_name="Doe", display_name="JD", plan="pro",
            bio="about me", stripe_customer_id="cus_1", preferences={"theme": "dark"},
            cancelled_subscription={"id": "sub_1", "plan": "pro", "status": "active"},
            termsVersion="2026-10-10", termsAcceptedAt=datetime(2026, 10, 11, 12, 0),
        )
        assert await delete_user("auth-soft", actor_id="admin") is True

        assert await _stored("auth-soft") is None
        kept = await _deleted("auth-soft")
        assert set(kept) == {"_id", "auth_id", "deleted_at", "purge_at", "retained"}
        assert kept["retained"] == {
            "email": "user1@example.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "display_name": "JD",
            "plan": "pro",
            "stripe_customer_id": "cus_1",
            "cancelled_subscription": {"id": "sub_1", "plan": "pro", "status": "active"},
            "terms_version": "2026-10-10",
            "terms_accepted_at": datetime(2026, 10, 11, 12, 0),
        }
        assert kept["purge_at"] - kept["deleted_at"] == timedelta(days=548)
        assert await base.audit_logs_collection.find_one({"action": "user_delete", "target_id": "auth-soft"})

    async def test_deleting_again_reports_not_found(self, reinit_db):
        await _make_user("auth-twice")
        assert await delete_user("auth-twice") is True
        first = await _deleted("auth-twice")
        assert await delete_user("auth-twice") is False
        assert await _deleted("auth-twice") == first

    async def test_update_cannot_write_onto_an_account_being_deleted(self, reinit_db):
        await _make_user("auth-gone")
        await base.users_collection.update_one(
            user_dao.user_key("auth-gone"), {"$set": {"deleted_at": datetime.now(timezone.utc)}}
        )
        assert await update_user("auth-gone", {"bio": "back again"}) is None
        assert "bio" not in await _stored("auth-gone")

    async def test_delete_missing_returns_false(self, reinit_db):
        assert await delete_user("absent") is False
        assert await (await get_collection("deleted_users")).count_documents({}) == 0

    async def test_in_flight_book_create_fails_once_the_account_is_deleted(self, reinit_db):
        """A create_book that authenticated before the delete lands after it:
        its book is removed again and it fails (#945)."""
        from app.db.book import create_book

        await _make_user("auth-race")
        await delete_user("auth-race")
        with pytest.raises(ValueError):
            await create_book({"title": "Late"}, "auth-race")
        assert await base.books_collection.count_documents({"owner_id": "auth-race"}) == 0

    async def test_in_flight_book_create_fails_while_the_account_is_being_deleted(self, reinit_db):
        from app.db.book import create_book

        await _make_user("auth-midway")
        await base.users_collection.update_one(
            user_dao.user_key("auth-midway"), {"$set": {"deleted_at": datetime.now(timezone.utc)}}
        )
        with pytest.raises(ValueError):
            await create_book({"title": "Late"}, "auth-midway")
        assert await base.books_collection.count_documents({"owner_id": "auth-midway"}) == 0
        assert "book_ids" not in await _stored("auth-midway")

    async def test_delete_defaults_actor_to_self(self, reinit_db):
        await _make_user("auth-self")
        await delete_user("auth-self")  # no actor_id -> actor defaults to auth_id
        log = await base.audit_logs_collection.find_one({"action": "user_delete"})
        assert log["actor_id"] == "auth-self"


class TestAStoppedDeletionIsFinished:
    """#935: a crash after the mark leaves the document; the sweep finishes it."""

    async def _stopped(self, monkeypatch, auth_id):
        async def dies(_):
            raise RuntimeError("the process died here")

        with monkeypatch.context() as patched:
            patched.setattr(user_dao, "delete_usage", dies)
            with pytest.raises(RuntimeError):
                await delete_user(auth_id)
        assert (await _stored(auth_id))["deleted_at"]

    async def test_the_sweep_finishes_it_and_keeps_the_record(self, reinit_db, monkeypatch):
        await _make_user("auth-stopped")
        await _make_user("auth-active", email="active@example.com")
        await self._stopped(monkeypatch, "auth-stopped")
        kept = await _deleted("auth-stopped")

        assert await erase_stranded_identities() == 1

        assert await _stored("auth-stopped") is None
        assert await _deleted("auth-stopped") == kept
        assert await _stored("auth-active") is not None
        assert await erase_stranded_identities() == 0

    async def test_a_second_delete_finishes_it_too(self, reinit_db, monkeypatch):
        await _make_user("auth-stopped")
        await self._stopped(monkeypatch, "auth-stopped")
        deleted_at = (await _stored("auth-stopped"))["deleted_at"]

        assert await delete_user("auth-stopped") is True

        assert await _stored("auth-stopped") is None
        assert (await _deleted("auth-stopped"))["deleted_at"] == deleted_at


class TestEraseAndPurge:
    """#954: a deleted account's record goes early on request, or on time."""

    async def test_erase_removes_the_kept_record(self, reinit_db):
        await _make_user("auth-erase")
        await delete_user("auth-erase")

        assert await erase_deactivated_user("auth-erase", actor_id="admin-1") is True

        assert await _deleted("auth-erase") is None
        log = await base.audit_logs_collection.find_one({"action": "user_erase"})
        assert (log["actor_id"], log["target_id"]) == ("admin-1", "auth-erase")

    async def test_erase_matches_only_a_kept_record(self, reinit_db):
        await _make_user("auth-active")

        for auth_id in ("auth-active", "absent"):
            assert await erase_deactivated_user(auth_id, actor_id="admin-1") is False

        assert (await get_user_by_auth_id("auth-active"))["email"] == "user1@example.com"

    async def test_purge_erases_only_records_whose_purge_date_has_passed(self, reinit_db):
        records = await get_collection("deleted_users")
        now = datetime.now(timezone.utc)
        await _make_user("auth-due", email="due@example.com")
        await _make_user("auth-waiting", email="waiting@example.com")
        await _make_user("auth-active", email="active@example.com")
        await delete_user("auth-due")
        await delete_user("auth-waiting")
        # 18 months and a day ago.
        long_ago = now - timedelta(days=549)
        await records.update_one(
            {"auth_id": "auth-due"},
            {"$set": {"deleted_at": long_ago, "purge_at": long_ago + timedelta(days=548)}},
        )
        waiting = await _deleted("auth-waiting")

        assert await purge_expired_users() == 1

        assert await _deleted("auth-due") is None
        assert await _deleted("auth-waiting") == waiting
        assert await get_user_by_auth_id("auth-active") is not None
        assert await purge_expired_users() == 0
