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
    create_audit_log,
    renewal_consent_expiry,
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
    return renewal_consent_expiry(datetime.fromtimestamp(epoch, timezone.utc))


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
        event_id="evt_2", subscription_id="sub_A", status="incomplete_expired",
        created=1_850_000_000))
    assert await _expiry() == _at(1_850_000_000)


@pytest.mark.parametrize("status", ["paused", "unpaid", "past_due"])
async def test_a_subscription_that_can_resume_has_not_ended(webhook_client, status):
    await _subscribed(webhook_client)
    await _post_signed(webhook_client, event(
        event_id="evt_2", subscription_id="sub_A", status=status))
    assert await _expiry() is None


async def test_a_new_subscription_clears_the_stamp_again(webhook_client):
    await _subscribed(webhook_client)
    await _post_signed(webhook_client, event(
        event_id="evt_2", event_type="customer.subscription.deleted",
        subscription_id="sub_A", status="canceled", ended_at=ENDED_AT))
    assert await _expiry() == _at(ENDED_AT)
    resp = await _post_signed(webhook_client, event(
        event_id="evt_3", subscription_id="sub_B", status="active"))
    assert resp.json()["status"] == "processed"
    assert await _expiry() is None


async def test_a_stale_event_does_not_move_the_stamp(webhook_client):
    await _subscribed(webhook_client)
    await _post_signed(webhook_client, event(
        event_id="evt_2", event_type="customer.subscription.deleted",
        subscription_id="sub_A", status="canceled", ended_at=ENDED_AT, created=ENDED_AT))
    stale = await _post_signed(webhook_client, event(
        event_id="evt_old", subscription_id="sub_A", status="active", created=ENDED_AT - 500))
    assert stale.json()["status"] != "processed"
    assert await _expiry() == _at(ENDED_AT)


async def test_cancelling_a_duplicate_keeps_the_live_ones_consent(webhook_client):
    await _subscribed(webhook_client)
    resp = await _post_signed(webhook_client, event(
        event_id="evt_2", event_type="customer.subscription.deleted",
        subscription_id="sub_DUP", status="canceled", ended_at=ENDED_AT))
    assert resp.json()["status"] == "not_current_subscription"
    assert await _expiry() is None


async def test_an_event_for_a_closed_account_does_not_move_the_stamp(webhook_client):
    from app.db.base import get_collection

    await _subscribed(webhook_client)
    await (await get_collection("users")).update_one(
        {"_id": AUTH_ID}, {"$set": {"deleted_at": datetime.now(timezone.utc)}})
    resp = await _post_signed(webhook_client, event(
        event_id="evt_2", event_type="customer.subscription.deleted",
        subscription_id="sub_A", status="canceled", ended_at=ENDED_AT))
    assert resp.json()["status"] == "account_closed"
    assert await _expiry() is None


async def test_a_retried_deletion_stamps_rows_its_first_delivery_could_not(
    webhook_client, monkeypatch
):
    """The user write cleared the subscription id, then the consent write failed:
    Stripe's retry finds the id gone, and must still stamp the rows."""
    from app.api.endpoints import webhooks

    await _subscribed(webhook_client)
    real_sync = webhooks.sync_renewal_consent

    async def fail(*args):
        raise RuntimeError("simulated mongo failure")

    monkeypatch.setattr(webhooks, "sync_renewal_consent", fail)
    deletion = event(event_id="evt_2", event_type="customer.subscription.deleted",
                     subscription_id="sub_A", status="canceled", ended_at=ENDED_AT)
    assert (await _post_signed(webhook_client, deletion)).status_code == 500
    assert await _expiry() is None

    monkeypatch.setattr(webhooks, "sync_renewal_consent", real_sync)
    retry = await _post_signed(webhook_client, deletion)
    assert retry.json()["status"] == "not_current_subscription"
    assert await _expiry() == _at(ENDED_AT)
