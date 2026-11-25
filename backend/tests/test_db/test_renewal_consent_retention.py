"""Renewal-consent rows are kept until the subscription ends + 4 years (#948).

Real MongoDB via reinit_db. A row whose subscription exists has no
expires_at; the stamp is set when the subscription ends, never shortened, and
cleared again if a subscription starts.
"""

from datetime import datetime, timedelta, timezone

import pytest

import app.db.audit_log as audit_log_dao
from app.db.audit_log import (
    RENEWAL_CONSENT_ACTION,
    create_audit_log,
    ensure_audit_log_indexes,
    renewal_consent_ended,
    renewal_consent_expiry,
    renewal_consent_live,
    sync_renewal_consent,
)
from app.db.base import get_collection
from tests.user_docs import insert_user

pytestmark = pytest.mark.asyncio

ENDED = datetime(2027, 3, 1, tzinfo=timezone.utc)
OLD = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


async def _rows(actor):
    coll = audit_log_dao.audit_logs_collection
    return [row async for row in coll.find({"actor_id": actor})]


async def _expiry(actor="u1"):
    value = (await _rows(actor))[0].get("expires_at")
    return _utc(value) if value is not None else None


async def _consent(actor="u1"):
    await create_audit_log(RENEWAL_CONSENT_ACTION, actor, actor, "billing")


async def test_the_period_is_four_calendar_years():
    assert renewal_consent_expiry(ENDED) == datetime(2031, 3, 1, tzinfo=timezone.utc)
    leap = datetime(2096, 2, 29, 12, tzinfo=timezone.utc)
    assert renewal_consent_expiry(leap) == datetime(2100, 3, 1, 12, tzinfo=timezone.utc)


async def test_consent_before_any_subscription_expires_four_years_after_it(reinit_db):
    # Recorded before Checkout: an abandoned checkout never makes a subscription.
    await _consent()
    [row] = await _rows("u1")
    assert row["expires_at"] == renewal_consent_expiry(row["timestamp"])


async def test_a_live_subscription_clears_the_stamp(reinit_db):
    await _consent()
    await renewal_consent_live("u1")
    assert await _expiry() is None


async def test_an_ended_subscription_stamps_end_plus_four_years(reinit_db):
    await _consent()
    await renewal_consent_live("u1")
    await renewal_consent_ended("u1", ENDED)
    assert await _expiry() == renewal_consent_expiry(ENDED)


async def test_a_restart_moves_the_stamp(reinit_db):
    await _consent()
    await renewal_consent_ended("u1", ENDED)
    await renewal_consent_live("u1")
    assert await _expiry() is None
    later = ENDED + timedelta(days=200)
    await renewal_consent_ended("u1", later)
    assert await _expiry() == renewal_consent_expiry(later)


async def test_an_earlier_end_never_shortens_the_stamp(reinit_db):
    await _consent()
    await renewal_consent_ended("u1", ENDED)
    await renewal_consent_ended("u1", ENDED - timedelta(days=30))
    assert await _expiry() == renewal_consent_expiry(ENDED)


async def test_only_the_users_consent_rows_move(reinit_db):
    await _consent("u1")
    await _consent("u2")
    await create_audit_log("book_create", "u1", "b1", "book")
    await renewal_consent_live("u1")

    by_action = {row["action"]: row for row in await _rows("u1")}
    assert "expires_at" not in by_action[RENEWAL_CONSENT_ACTION]
    assert "expires_at" in by_action["book_create"]
    assert "expires_at" in (await _rows("u2"))[0]


@pytest.mark.parametrize("status", ["active", "past_due", "unpaid", "paused", "incomplete"])
async def test_sync_keeps_rows_while_the_subscription_can_still_bill(reinit_db, status):
    await insert_user("u1", stripe_subscription_id="sub_1", stripe_subscription_status=status)
    await _consent()
    await sync_renewal_consent("u1", ENDED)
    assert await _expiry() is None


@pytest.mark.parametrize("fields", [
    {"stripe_subscription_id": "sub_1", "stripe_subscription_status": "canceled"},
    {"stripe_subscription_id": "sub_1", "stripe_subscription_status": "incomplete_expired"},
    {"stripe_subscription_id": None},
])
async def test_sync_stamps_rows_once_the_subscription_has_ended(reinit_db, fields):
    await insert_user("u1", **fields)
    await _consent()
    await renewal_consent_live("u1")
    await sync_renewal_consent("u1", ENDED)
    assert await _expiry() == renewal_consent_expiry(ENDED)


async def test_sync_puts_right_a_write_the_user_changed_under(reinit_db, monkeypatch):
    """A webhook read the user as live, then another one ended the subscription
    before the rows were written: the re-read after writing stamps them."""
    await insert_user("u1", stripe_subscription_id="sub_1", stripe_subscription_status="active")
    await _consent()
    real = audit_log_dao._stored_user
    reads = []

    async def read_then_end(auth_id):
        user = await real(auth_id)
        if not reads:
            await (await get_collection("users")).update_one(
                {"_id": "u1"}, {"$set": {"stripe_subscription_id": None}})
        reads.append(auth_id)
        return user

    monkeypatch.setattr(audit_log_dao, "_stored_user", read_then_end)
    await sync_renewal_consent("u1", ENDED)
    assert await _expiry() == renewal_consent_expiry(ENDED)


async def test_startup_dates_legacy_rows_from_the_best_known_end(reinit_db):
    """Rows written before #948 have no expires_at at all."""
    coll = audit_log_dao.audit_logs_collection
    ended_event = int(ENDED.timestamp())
    await insert_user("live", plan="pro", stripe_subscription_id="sub_1",
                      stripe_subscription_status="active")
    await insert_user("lapsed", plan="free", stripe_subscription_id=None,
                      stripe_event_created_by_subscription={"sub_0": ended_event - 99,
                                                            "sub_1": ended_event})
    await insert_user("never", plan="free")
    await (await get_collection("deleted_users")).insert_one(
        {"auth_id": "deleted", "deleted_at": ENDED})
    await coll.insert_many([
        {"actor_id": actor, "action": RENEWAL_CONSENT_ACTION, "timestamp": OLD}
        for actor in ("live", "lapsed", "never", "deleted", "unknown")
    ])

    await ensure_audit_log_indexes()

    assert await _expiry("live") is None
    assert await _expiry("lapsed") == renewal_consent_expiry(ENDED)
    assert await _expiry("never") == renewal_consent_expiry(OLD)
    assert await _expiry("deleted") == renewal_consent_expiry(ENDED)
    now = renewal_consent_expiry(datetime.now(timezone.utc))
    assert abs(await _expiry("unknown") - now) < timedelta(minutes=5)


async def test_an_older_event_finishing_last_cannot_date_the_rows_early(reinit_db):
    """An `active` event resumes after the deletion was applied: the rows are
    dated from the deletion recorded on the user, not from the older event."""
    deletion = int(ENDED.timestamp())
    await insert_user("u1", stripe_subscription_id=None,
                      stripe_event_created_by_subscription={"sub_1": deletion})
    await _consent()
    await renewal_consent_live("u1")
    await sync_renewal_consent("u1", ENDED - timedelta(days=60))
    assert await _expiry() == renewal_consent_expiry(ENDED)


async def test_legacy_abandoned_consents_each_keep_their_own_date(reinit_db):
    """Never subscribed: each abandoned checkout's consent expires 4 years
    after it was given, not after the latest one."""
    coll = audit_log_dao.audit_logs_collection
    later = OLD + timedelta(days=300)
    await insert_user("never", plan="free")
    await coll.insert_many([
        {"actor_id": "never", "action": RENEWAL_CONSENT_ACTION, "timestamp": when}
        for when in (OLD, later)
    ])

    await ensure_audit_log_indexes()

    rows = await coll.find({"actor_id": "never"}).sort("timestamp", 1).to_list()
    assert [_utc(r["expires_at"]) for r in rows] == [
        renewal_consent_expiry(OLD), renewal_consent_expiry(later)]
