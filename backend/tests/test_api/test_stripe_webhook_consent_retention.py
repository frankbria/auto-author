"""The Stripe webhook moves the renewal-consent expiry with the subscription (#948).

Same harness as test_stripe_webhook.py: genuine HMAC signatures through the
real endpoint, real local Mongo.
"""

import json
from datetime import datetime, timezone

import pytest

import app.db.audit_log as audit_log_dao
from app.db.audit_log import (
    RENEWAL_CONSENT_ACTION,
    RENEWAL_CONSENT_RETENTION,
    create_audit_log,
)
from tests.test_api import test_stripe_webhook as base
from tests.test_api.test_stripe_webhook import _post_signed, _seed_user, subscription_event

webhook_client = base.webhook_client

pytestmark = pytest.mark.asyncio

AUTH_ID = "auth-stripe-1"
ENDED_AT = 1_800_000_000


def event(ended_at=None, **kwargs) -> bytes:
    payload = json.loads(subscription_event(**kwargs))
    if ended_at is not None:
        payload["data"]["object"]["ended_at"] = ended_at
    return json.dumps(payload).encode()


def _at(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc) + RENEWAL_CONSENT_RETENTION


async def _expiry():
    row = await audit_log_dao.audit_logs_collection.find_one(
        {"actor_id": AUTH_ID, "action": RENEWAL_CONSENT_ACTION}
    )
    value = row.get("expires_at")
    return value.replace(tzinfo=timezone.utc) if value is not None else None


async def _subscribed(webhook_client):
    await _seed_user(stripe_customer_id="cus_test_1", plan="free")
    await create_audit_log(RENEWAL_CONSENT_ACTION, AUTH_ID, AUTH_ID, "billing")
    live = await _post_signed(webhook_client, event(event_id="evt_1", subscription_id="sub_A"))
    assert live.json()["status"] == "processed"


async def test_a_live_subscription_keeps_the_consent_without_expiry(webhook_client):
    await _subscribed(webhook_client)
    assert await _expiry() is None


async def test_deletion_stamps_ended_at_plus_four_years(webhook_client):
    await _subscribed(webhook_client)
    resp = await _post_signed(webhook_client, event(
        event_id="evt_2", event_type="customer.subscription.deleted",
        subscription_id="sub_A", status="canceled", ended_at=ENDED_AT))
    assert resp.json()["status"] == "processed"
    assert await _expiry() == _at(ENDED_AT)


async def test_without_ended_at_the_event_time_is_the_end(webhook_client):
    await _subscribed(webhook_client)
    await _post_signed(webhook_client, event(
        event_id="evt_2", subscription_id="sub_A", status="unpaid", created=1_850_000_000))
    assert await _expiry() == _at(1_850_000_000)


async def test_a_restart_clears_the_stamp_again(webhook_client):
    await _subscribed(webhook_client)
    await _post_signed(webhook_client, event(
        event_id="evt_2", subscription_id="sub_A", status="unpaid"))
    assert await _expiry() is not None
    await _post_signed(webhook_client, event(
        event_id="evt_3", subscription_id="sub_A", status="active"))
    assert await _expiry() is None


async def test_a_stale_event_does_not_move_the_stamp(webhook_client):
    await _subscribed(webhook_client)
    await _post_signed(webhook_client, event(
        event_id="evt_2", event_type="customer.subscription.deleted",
        subscription_id="sub_A", status="canceled", ended_at=ENDED_AT, created=1_900_000_000))
    stale = await _post_signed(webhook_client, event(
        event_id="evt_old", subscription_id="sub_A", status="active", created=1_800_000_500))
    assert stale.json()["status"] != "processed"
    assert await _expiry() == _at(ENDED_AT)
