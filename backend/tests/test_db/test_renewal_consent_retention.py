"""Renewal-consent rows are kept until the subscription ends + 4 years (#948).

Real MongoDB via reinit_db. A row whose subscription is live has no
expires_at; the stamp is set when the subscription ends, never shortened, and
cleared again if a subscription goes live.
"""

from datetime import datetime, timedelta, timezone

import pytest

import app.db.audit_log as audit_log_dao
from app.db.audit_log import (
    RENEWAL_CONSENT_ACTION,
    RENEWAL_CONSENT_RETENTION,
    create_audit_log,
    ensure_audit_log_indexes,
    renewal_consent_ended,
    renewal_consent_live,
)
from tests.user_docs import insert_user

pytestmark = pytest.mark.asyncio

ENDED = datetime(2027, 3, 1, tzinfo=timezone.utc)


def _utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


async def _rows(actor):
    coll = audit_log_dao.audit_logs_collection
    return [row async for row in coll.find({"actor_id": actor})]


async def _consent(actor="u1"):
    await create_audit_log(RENEWAL_CONSENT_ACTION, actor, actor, "billing")


async def test_the_period_is_four_years():
    assert RENEWAL_CONSENT_RETENTION == timedelta(days=4 * 365 + 1)


async def test_consent_before_any_subscription_expires_four_years_after_it(reinit_db):
    # Recorded before Checkout: an abandoned checkout never makes a subscription.
    await _consent()
    [row] = await _rows("u1")
    assert row["expires_at"] == row["timestamp"] + RENEWAL_CONSENT_RETENTION


async def test_a_live_subscription_clears_the_stamp(reinit_db):
    await _consent()
    await renewal_consent_live("u1")
    [row] = await _rows("u1")
    assert "expires_at" not in row


async def test_an_ended_subscription_stamps_end_plus_four_years(reinit_db):
    await _consent()
    await renewal_consent_live("u1")
    await renewal_consent_ended("u1", ENDED)
    [row] = await _rows("u1")
    assert _utc(row["expires_at"]) == ENDED + RENEWAL_CONSENT_RETENTION


async def test_a_restart_moves_the_stamp(reinit_db):
    await _consent()
    await renewal_consent_ended("u1", ENDED)
    await renewal_consent_live("u1")
    assert "expires_at" not in (await _rows("u1"))[0]
    later = ENDED + timedelta(days=200)
    await renewal_consent_ended("u1", later)
    assert _utc((await _rows("u1"))[0]["expires_at"]) == later + RENEWAL_CONSENT_RETENTION


async def test_an_earlier_end_never_shortens_the_stamp(reinit_db):
    await _consent()
    await renewal_consent_ended("u1", ENDED)
    await renewal_consent_ended("u1", ENDED - timedelta(days=30))
    assert _utc((await _rows("u1"))[0]["expires_at"]) == ENDED + RENEWAL_CONSENT_RETENTION


async def test_only_the_users_consent_rows_move(reinit_db):
    await _consent("u1")
    await _consent("u2")
    await create_audit_log("book_create", "u1", "b1", "book")
    await renewal_consent_live("u1")

    by_action = {row["action"]: row for row in await _rows("u1")}
    assert "expires_at" not in by_action[RENEWAL_CONSENT_ACTION]
    assert "expires_at" in by_action["book_create"]
    assert "expires_at" in (await _rows("u2"))[0]


async def test_startup_stamps_legacy_rows_unless_the_subscription_is_live(reinit_db):
    """Rows written before #948 have no expires_at at all."""
    coll = audit_log_dao.audit_logs_collection
    old = datetime(2026, 9, 1, tzinfo=timezone.utc)
    await insert_user("live", plan="pro", stripe_subscription_id="sub_1",
                      stripe_subscription_status="active")
    await insert_user("lapsed", plan="free", stripe_subscription_status="canceled")
    await coll.insert_many([
        {"actor_id": actor, "action": RENEWAL_CONSENT_ACTION, "timestamp": old}
        for actor in ("live", "lapsed", "gone")
    ])

    await ensure_audit_log_indexes()

    assert "expires_at" not in (await _rows("live"))[0]
    expected = datetime.now(timezone.utc) + RENEWAL_CONSENT_RETENTION
    for actor in ("lapsed", "gone"):
        stamped = _utc((await _rows(actor))[0]["expires_at"])
        assert abs(stamped - expected) < timedelta(minutes=5)
