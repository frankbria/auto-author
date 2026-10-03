"""Stripe webhook delivery semantics: crash recovery and ordering (#769).

Same harness as test_stripe_webhook.py: genuine HMAC signatures through the real
endpoint, real local Mongo. Stripe delivers at least once and in no particular
order, so the handler must (a) let a retry re-apply an event whose first attempt
died part-way, (b) still treat a duplicate of an applied event as a no-op, and
(c) refuse an older event that lands after a newer one.
"""

import pytest

from app.api.endpoints import webhooks as webhooks_module
from app.db import base as db_base
from app.db.user import get_user_by_auth_id
from tests.test_api import test_stripe_webhook as base
from tests.test_api.test_stripe_webhook import _post_signed, _seed_user, subscription_event

webhook_client = base.webhook_client  # same fixture: bare webhook app, fresh Mongo

pytestmark = pytest.mark.asyncio


class SimulatedCrash(BaseException):
    """A worker dying mid-request: a redeploy's CancelledError or a killed
    process. A BaseException, so the handler's ``except Exception`` never sees it."""


def crash_once(monkeypatch, name: str):
    """Make ``webhooks.<name>`` die on its next call, then behave normally."""
    real = getattr(webhooks_module, name)
    calls = {"n": 0}

    async def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise SimulatedCrash()
        return await real(*args, **kwargs)

    monkeypatch.setattr(webhooks_module, name, flaky)


async def _post_crashing(client, payload: bytes):
    with pytest.raises(SimulatedCrash):
        await _post_signed(client, payload)


class TestCrashRecovery:
    async def test_crash_before_the_plan_write_lets_the_retry_apply_it(
        self, webhook_client, monkeypatch
    ):
        await _seed_user(stripe_customer_id="cus_test_1")
        payload = subscription_event(event_id="evt_crash_1")
        crash_once(monkeypatch, "update_user")

        await _post_crashing(webhook_client, payload)
        assert (await get_user_by_auth_id("auth-stripe-1"))["plan"] == "free"

        # Stripe retries the same event id. It must not be swallowed as a replay.
        retry = await _post_signed(webhook_client, payload)
        assert retry.json()["status"] == "processed"
        assert (await get_user_by_auth_id("auth-stripe-1"))["plan"] == "pro"

    async def test_crash_after_the_write_but_before_the_marker_reapplies_safely(
        self, webhook_client, monkeypatch
    ):
        await _seed_user(stripe_customer_id="cus_test_1")
        payload = subscription_event(event_id="evt_crash_2")
        crash_once(monkeypatch, "mark_event_processed")

        await _post_crashing(webhook_client, payload)
        assert (await get_user_by_auth_id("auth-stripe-1"))["plan"] == "pro"

        retry = await _post_signed(webhook_client, payload)
        assert retry.json() == {"status": "processed", "plan": "pro"}

        # Now recorded: a further duplicate is a no-op again.
        dup = await _post_signed(webhook_client, payload)
        assert dup.json()["status"] == "replay"

    async def test_duplicate_of_an_applied_event_is_a_noop(self, webhook_client):
        from app.db.user import update_user

        await _seed_user(stripe_customer_id="cus_test_1")
        payload = subscription_event(event_id="evt_dup_1")
        assert (await _post_signed(webhook_client, payload)).json()["status"] == "processed"

        await update_user("auth-stripe-1", {"plan": "free"})  # out-of-band change
        dup = await _post_signed(webhook_client, payload)
        assert dup.json()["status"] == "replay"
        assert (await get_user_by_auth_id("auth-stripe-1"))["plan"] == "free"

    async def test_ignored_events_record_no_marker(self, webhook_client):
        # no_matching_user: nothing applied, so a later Resend must reprocess.
        payload = subscription_event(event_id="evt_nobody", customer="cus_nobody")
        assert (await _post_signed(webhook_client, payload)).json()["status"] == (
            "no_matching_user"
        )
        coll = await db_base.get_collection("processed_stripe_events")
        assert await coll.find_one({"_id": "evt_nobody"}) is None


class TestOutOfOrderDelivery:
    async def test_older_event_after_newer_is_stale_and_changes_nothing(self, webhook_client):
        await _seed_user(stripe_customer_id="cus_test_1")
        new = subscription_event(event_id="evt_new", status="active", created=2_000)
        old = subscription_event(event_id="evt_old", status="canceled", created=1_000)

        assert (await _post_signed(webhook_client, new)).json()["status"] == "processed"
        resp = await _post_signed(webhook_client, old)

        assert resp.json() == {"status": "stale_event", "event_id": "evt_old"}
        user = await get_user_by_auth_id("auth-stripe-1")
        assert (user["plan"], user["stripe_event_created"]) == ("pro", 2_000)
        # Stale is final (the watermark only rises), so it is recorded.
        assert (await _post_signed(webhook_client, old)).json()["status"] == "replay"

    async def test_same_second_event_still_applies(self, webhook_client):
        # `created` has one-second granularity: two updates in the same second
        # are last-write-wins, never dropped.
        await _seed_user(stripe_customer_id="cus_test_1")
        first = subscription_event(event_id="evt_s1", status="active", created=3_000)
        second = subscription_event(event_id="evt_s2", status="canceled", created=3_000)

        await _post_signed(webhook_client, first)
        resp = await _post_signed(webhook_client, second)

        assert resp.json()["status"] == "processed"
        assert (await get_user_by_auth_id("auth-stripe-1"))["plan"] == "free"

    async def test_newer_event_landing_between_lookup_and_write_wins(
        self, webhook_client, monkeypatch
    ):
        # The guard must be in the write's query, not a read before it: two
        # deliveries carry different event ids, so nothing else serializes them.
        await _seed_user(stripe_customer_id="cus_test_1", plan="pro")
        real_lookup = webhooks_module.get_user_by_stripe_customer_id

        async def lookup_then_newer_event_lands(customer_id):
            snapshot = await real_lookup(customer_id)
            await db_base.users_collection.update_one(
                {"auth_id": "auth-stripe-1"}, {"$set": {"stripe_event_created": 9_000}}
            )
            return snapshot  # the handler now holds a stale read

        monkeypatch.setattr(
            webhooks_module, "get_user_by_stripe_customer_id", lookup_then_newer_event_lands
        )
        old = subscription_event(event_id="evt_raced", status="canceled", created=5_000)
        resp = await _post_signed(webhook_client, old)

        assert resp.json()["status"] == "stale_event"
        assert (await get_user_by_auth_id("auth-stripe-1"))["plan"] == "pro"
