"""Test audit log functionality"""

import logging

import motor.motor_asyncio
import pytest
import app.db.audit_log as audit_log_dao
from app.api.endpoints.billing import RENEWAL_CONSENT_ACTION
from app.db.audit_log import (
    AUDIT_LOG_RETENTION,
    RETAINED_ACTIONS,
    create_audit_log,
    ensure_audit_log_indexes,
)
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta, timezone


@pytest.mark.asyncio
async def test_create_audit_log():
    """Test creating audit log entries"""
    # Mock the audit_logs_collection
    mock_collection = AsyncMock()
    mock_collection.insert_one = AsyncMock()

    with patch('app.db.audit_log.audit_logs_collection', mock_collection):
        # Test basic audit log
        log = await create_audit_log(
            action="test_action",
            actor_id="user123",
            target_id="resource456",
            resource_type="test_resource"
        )

        assert log["action"] == "test_action"
        assert log["actor_id"] == "user123"
        assert log["target_id"] == "resource456"
        assert log["resource_type"] == "test_resource"
        assert "timestamp" in log
        assert isinstance(log["timestamp"], datetime)
        assert log["details"] == {}

        # Verify insert_one was called
        mock_collection.insert_one.assert_called()

        # Test with details
        log_with_details = await create_audit_log(
            action="update_book",
            actor_id="user789",
            target_id="book123",
            resource_type="book",
            details={
                "fields_updated": ["title", "description"],
                "previous_title": "Old Title",
                "new_title": "New Title"
            }
        )

        assert log_with_details["details"]["fields_updated"] == ["title", "description"]
        assert log_with_details["details"]["new_title"] == "New Title"

        # Verify insert_one was called twice
        assert mock_collection.insert_one.call_count == 2


# ---------------------------------------------------------------------------
# Retention (issue #787) — real MongoDB via motor_reinit_db
# ---------------------------------------------------------------------------
NINETY_DAYS = timedelta(days=90)


@pytest.mark.asyncio
async def test_row_expires_ninety_days_after_timestamp(motor_reinit_db):
    await create_audit_log("book_create", "u1", "b1", "book")
    row = await audit_log_dao.audit_logs_collection.find_one({"actor_id": "u1"})
    assert AUDIT_LOG_RETENTION == NINETY_DAYS
    assert row["expires_at"] == row["timestamp"] + NINETY_DAYS


@pytest.mark.asyncio
async def test_renewal_consent_row_has_no_expiry(motor_reinit_db):
    await create_audit_log(RENEWAL_CONSENT_ACTION, "u1", "u1", "billing")
    row = await audit_log_dao.audit_logs_collection.find_one({"actor_id": "u1"})
    assert "expires_at" not in row


def test_retained_actions_track_the_billing_consent_action():
    assert RENEWAL_CONSENT_ACTION in RETAINED_ACTIONS


@pytest.mark.asyncio
async def test_backfill_stamps_legacy_rows_only(motor_reinit_db):
    coll = audit_log_dao.audit_logs_collection
    old = datetime(2026, 1, 1, tzinfo=timezone.utc)
    other = datetime(2030, 1, 1, tzinfo=timezone.utc)
    await coll.insert_many(
        [
            {"actor_id": "legacy", "action": "book_view", "timestamp": old},
            {"actor_id": "no-ts", "action": "book_view"},
            {"actor_id": "bad-ts", "action": "book_view", "timestamp": "2026-01-01"},
            {"actor_id": "consent", "action": RENEWAL_CONSENT_ACTION, "timestamp": old},
            {"actor_id": "set", "action": "book_view", "timestamp": old, "expires_at": other},
        ]
    )
    await ensure_audit_log_indexes()

    async def get(actor):
        return await coll.find_one({"actor_id": actor})

    legacy = await get("legacy")
    assert legacy["expires_at"].replace(tzinfo=timezone.utc) == old + NINETY_DAYS
    expected = datetime.now(timezone.utc) + NINETY_DAYS
    for actor in ("no-ts", "bad-ts"):
        stamped = (await get(actor))["expires_at"].replace(tzinfo=timezone.utc)
        assert abs(stamped - expected) < timedelta(minutes=5)
    assert "expires_at" not in await get("consent")
    assert (await get("set"))["expires_at"].replace(tzinfo=timezone.utc) == other


@pytest.mark.asyncio
async def test_unreachable_mongo_is_logged_and_never_fatal(monkeypatch, caplog):
    """Startup must survive: a real client pointed at a closed port fails all three steps."""
    dead = motor.motor_asyncio.AsyncIOMotorClient(
        "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=200"
    )
    monkeypatch.setattr(
        audit_log_dao, "audit_logs_collection", dead["unreachable"]["audit_logs"]
    )
    with caplog.at_level(logging.ERROR, logger="app.db.audit_log"):
        await ensure_audit_log_indexes()
    dead.close()

    assert [r.getMessage() for r in caplog.records] == [
        "Failed to create TTL index on audit_logs.expires_at",
        "Failed to create actor index on audit_logs",
        "Failed to backfill audit_logs.expires_at",
    ]
