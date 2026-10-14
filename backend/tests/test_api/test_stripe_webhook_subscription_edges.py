"""Stripe webhook edges left after #768 (#912).

Same harness as test_stripe_webhook.py: genuine HMAC signatures through the
real endpoint, real local Mongo.

1. The out-of-order watermark was one per user, so a new subscription's first
   event, created a moment before the old subscription's deletion landed, was
   refused as stale and the new subscriber stayed on free until their next
   event, possibly the renewal a month later.
2. Which subscription is current was read, then written: two first events for
   different subscriptions could both pass the check and either one be stored.
"""

import asyncio

import pytest

from app.api.endpoints import webhooks
from app.db.user import get_user_by_auth_id
from tests.test_api import test_stripe_webhook as base
from tests.test_api.test_stripe_webhook import _post_signed, _seed_user, subscription_event as event

webhook_client = base.webhook_client

pytestmark = pytest.mark.asyncio


async def _stored():
    user = await get_user_by_auth_id("auth-stripe-1")
    return user["plan"], user.get("stripe_subscription_id")


class TestEachSubscriptionHasItsOwnWatermark:
    async def test_a_new_subscription_older_than_the_last_deletion_is_applied(self, webhook_client):
        await _seed_user(stripe_customer_id="cus_test_1", stripe_subscription_id="sub_A",
                         stripe_subscription_status="active", plan="pro")
        deleted = await _post_signed(webhook_client, event(
            event_id="evt_A_del", event_type="customer.subscription.deleted",
            subscription_id="sub_A", status="canceled", created=2_000))
        assert deleted.json()["status"] == "processed"

        # Re-subscribed: sub_B's first event was created before sub_A's deletion landed.
        first_b = await _post_signed(webhook_client, event(
            event_id="evt_B_1", subscription_id="sub_B", status="active", created=1_990))

        assert first_b.json()["status"] == "processed"
        assert await _stored() == ("pro", "sub_B")

    async def test_a_late_event_for_the_deleted_subscription_still_cannot_revive_it(self, webhook_client):
        await _seed_user(stripe_customer_id="cus_test_1", stripe_subscription_id="sub_A",
                         stripe_subscription_status="active", plan="pro")
        await _post_signed(webhook_client, event(
            event_id="evt_A_del", event_type="customer.subscription.deleted",
            subscription_id="sub_A", status="canceled", created=2_000))

        late = await _post_signed(webhook_client, event(
            event_id="evt_A_old", subscription_id="sub_A", status="active", created=1_500))

        assert late.json()["status"] != "processed"
        assert await _stored() == ("free", None)

    async def test_an_older_event_for_the_same_subscription_is_still_stale(self, webhook_client):
        await _seed_user(stripe_customer_id="cus_test_1", plan="free")
        await _post_signed(webhook_client, event(
            event_id="evt_B_2", subscription_id="sub_B", status="canceled", created=3_000))
        older = await _post_signed(webhook_client, event(
            event_id="evt_B_1", subscription_id="sub_B", status="active", created=2_900))

        assert older.json()["status"] == "stale_event"
        assert (await _stored())[0] == "free"


class TestTheCurrentSubscriptionIsDecidedByTheWrite:
    async def test_two_first_events_for_different_subscriptions_do_not_both_land(
        self, webhook_client, monkeypatch
    ):
        await _seed_user(stripe_customer_id="cus_test_1", plan="free")
        both_have_read = asyncio.Barrier(2)
        real_lookup = webhooks.get_user_by_stripe_customer_id

        held = []

        async def lookup_then_wait(customer_id):
            user = await real_lookup(customer_id)
            if len(held) < 2:  # the two first reads; a second look goes straight through
                held.append(customer_id)
                await asyncio.wait_for(both_have_read.wait(), 5)
            return user

        monkeypatch.setattr(webhooks, "get_user_by_stripe_customer_id", lookup_then_wait)

        results = await asyncio.gather(
            _post_signed(webhook_client, event(event_id="evt_X", subscription_id="sub_X", status="active")),
            _post_signed(webhook_client, event(event_id="evt_Y", subscription_id="sub_Y", status="active")),
        )

        statuses = sorted(r.json()["status"] for r in results)
        assert statuses == ["not_current_subscription", "processed"]
        winner = next(r for r in results if r.json()["status"] == "processed")
        assert (await _stored())[1] == ("sub_X" if winner is results[0] else "sub_Y")
