"""Stripe webhook: only the user's current subscription moves the plan (#768).

Same harness as test_stripe_webhook.py: genuine HMAC signatures through the real
endpoint, real local Mongo. A user can end up with more than one Stripe
subscription (two checkout tabs, a re-upgrade after a lapse), and an event for a
subscription that isn't the stored ``stripe_subscription_id`` must not downgrade
someone who is still paying on the current one.
"""

import pytest

from app.db.user import get_user_by_auth_id
from tests.test_api import test_stripe_webhook as base
from tests.test_api.test_stripe_webhook import _post_signed, _seed_user, subscription_event

webhook_client = base.webhook_client  # same fixture: bare webhook app, fresh Mongo

pytestmark = pytest.mark.asyncio


event = subscription_event


async def _seed_pro_on(sub_id: str = "sub_A", status: str = "active", plan: str = "pro"):
    return await _seed_user(
        stripe_customer_id="cus_test_1",
        stripe_subscription_id=sub_id,
        stripe_subscription_status=status,
        plan=plan,
    )


class TestNonCurrentSubscriptionIsIgnored:
    async def test_deleted_for_a_stale_subscription_keeps_pro(self, webhook_client):
        await _seed_pro_on("sub_A")
        resp = await _post_signed(
            webhook_client,
            event(event_id="evt_del_B", event_type="customer.subscription.deleted",
                  subscription_id="sub_B", status="canceled"),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "not_current_subscription"
        user = await get_user_by_auth_id("auth-stripe-1")
        assert user["plan"] == "pro"
        assert user["stripe_subscription_id"] == "sub_A"
        assert user["stripe_subscription_status"] == "active"

    async def test_deleted_for_another_subscription_is_ignored_even_without_a_current_one(
        self, webhook_client
    ):
        # Nothing is current, but a deletion establishes nothing either.
        await _seed_user(stripe_customer_id="cus_test_1", plan="free")
        resp = await _post_signed(
            webhook_client,
            event(event_type="customer.subscription.deleted", subscription_id="sub_B"),
        )
        assert resp.json()["status"] == "not_current_subscription"

    @pytest.mark.parametrize("status", ["canceled", "unpaid", "incomplete_expired"])
    async def test_stale_update_for_another_subscription_cannot_downgrade(
        self, webhook_client, status
    ):
        await _seed_pro_on("sub_A")
        resp = await _post_signed(
            webhook_client, event(event_id=f"evt_B_{status}", subscription_id="sub_B", status=status)
        )
        assert resp.json()["status"] == "not_current_subscription"
        user = await get_user_by_auth_id("auth-stripe-1")
        assert (user["plan"], user["stripe_subscription_id"]) == ("pro", "sub_A")

    async def test_past_due_current_subscription_still_counts_as_current(self, webhook_client):
        await _seed_pro_on("sub_A", status="past_due")
        resp = await _post_signed(
            webhook_client, event(subscription_id="sub_B", status="incomplete")
        )
        assert resp.json()["status"] == "not_current_subscription"
        assert (await get_user_by_auth_id("auth-stripe-1"))["stripe_subscription_id"] == "sub_A"

    async def test_pre_768_pro_document_counts_as_live(self, webhook_client):
        # Written before the status field existed: id + pro, no status. Treat
        # it as live, or a duplicate's cancellation downgrades on deploy day.
        await _seed_user(stripe_customer_id="cus_test_1", stripe_subscription_id="sub_A", plan="pro")
        resp = await _post_signed(webhook_client, event(subscription_id="sub_B", status="canceled"))
        assert resp.json()["status"] == "not_current_subscription"
        user = await get_user_by_auth_id("auth-stripe-1")
        assert (user["plan"], user["stripe_subscription_id"]) == ("pro", "sub_A")

    async def test_a_second_live_subscription_is_logged_as_an_error(self, webhook_client, caplog):
        # Two paid subscriptions = the user is being double-billed. Needs a human.
        await _seed_pro_on("sub_A")
        with caplog.at_level("ERROR", logger="app.api.endpoints.webhooks"):
            resp = await _post_signed(webhook_client, event(subscription_id="sub_B"))
        assert resp.json()["status"] == "not_current_subscription"
        errors = [r.getMessage() for r in caplog.records if r.levelname == "ERROR"]
        assert any("sub_A" in m and "sub_B" in m for m in errors), errors

    async def test_ignored_stale_cancellation_is_not_an_error(self, webhook_client, caplog):
        await _seed_pro_on("sub_A")
        with caplog.at_level("ERROR", logger="app.api.endpoints.webhooks"):
            await _post_signed(
                webhook_client,
                event(event_type="customer.subscription.deleted", subscription_id="sub_B",
                      price_id="price_unknown_9"),
            )
        assert not [r for r in caplog.records if r.levelname == "ERROR"]

    async def test_ignored_event_can_be_resent_once_its_subscription_is_current(
        self, webhook_client
    ):
        # Duplicate sub B is ignored while A is current. The user then cancels A;
        # an operator's dashboard Resend of B's event (same id) must apply now.
        await _seed_pro_on("sub_A")
        # B's event is newer than A's deletion but delivered first (Stripe does
        # not order deliveries). One older than the deletion would be
        # stale_event: the watermark is per user (see #768's known limits).
        b_active = event(event_id="evt_B_active", subscription_id="sub_B", created=3_000)
        assert (await _post_signed(webhook_client, b_active)).json()["status"] == (
            "not_current_subscription"
        )

        await _post_signed(
            webhook_client,
            event(event_id="evt_A_del", event_type="customer.subscription.deleted",
                  subscription_id="sub_A", status="canceled", created=2_000),
        )
        user = await get_user_by_auth_id("auth-stripe-1")
        assert (user["plan"], user["stripe_subscription_id"]) == ("free", None)
        assert user["stripe_subscription_status"] is None

        resend = await _post_signed(webhook_client, b_active)
        assert resend.json()["status"] == "processed"
        user = await get_user_by_auth_id("auth-stripe-1")
        assert (user["plan"], user["stripe_subscription_id"]) == ("pro", "sub_B")


class TestNewSubscriptionBecomesCurrent:
    @pytest.mark.parametrize(
        "stored_status,stored_plan",
        [
            ("unpaid", "restricted"),  # lapsed subscriber re-upgrades
            ("incomplete_expired", "free"),  # first card declined, retried checkout
            ("canceled", "free"),
            (None, "free"),  # pre-#768 document: no status recorded
        ],
    )
    async def test_replaces_a_subscription_that_is_not_live(
        self, webhook_client, stored_status, stored_plan
    ):
        await _seed_pro_on("sub_A", status=stored_status, plan=stored_plan)
        resp = await _post_signed(webhook_client, event(subscription_id="sub_B"))
        assert resp.json() == {"status": "processed", "plan": "pro"}
        user = await get_user_by_auth_id("auth-stripe-1")
        assert user["stripe_subscription_id"] == "sub_B"
        assert user["stripe_subscription_status"] == "active"

    async def test_old_subscription_deletion_after_replacement_is_ignored(self, webhook_client):
        await _seed_pro_on("sub_A", status="unpaid", plan="restricted")
        await _post_signed(webhook_client, event(event_id="evt_B", subscription_id="sub_B"))
        resp = await _post_signed(
            webhook_client,
            event(event_id="evt_A_del", event_type="customer.subscription.deleted",
                  subscription_id="sub_A"),
        )
        assert resp.json()["status"] == "not_current_subscription"
        assert (await get_user_by_auth_id("auth-stripe-1"))["plan"] == "pro"

    async def test_status_is_recorded_for_the_current_subscription(self, webhook_client):
        await _seed_user(stripe_customer_id="cus_test_1")
        await _post_signed(webhook_client, event(event_id="evt_1", status="trialing"))
        user = await get_user_by_auth_id("auth-stripe-1")
        assert user["stripe_subscription_status"] == "trialing"


class TestKeepDoesNotAdvanceTheWatermark:
    """A past_due write keeps the plan, so it must not block an older event that
    sets it (#902 GLM finding)."""

    async def test_resent_older_active_applies_after_past_due(self, webhook_client):
        # The original `active` delivery failed past Stripe's retry window; the
        # past_due one landed. The operator resends `active`: the user must get pro.
        await _seed_user(stripe_customer_id="cus_test_1", plan="free")
        past_due = event(event_id="evt_pd", status="past_due", created=2_000)
        assert (await _post_signed(webhook_client, past_due)).json()["plan"] == "free"

        resent_active = event(event_id="evt_active", status="active", created=1_000)
        resp = await _post_signed(webhook_client, resent_active)
        assert resp.json() == {"status": "processed", "plan": "pro"}
        assert (await get_user_by_auth_id("auth-stripe-1"))["plan"] == "pro"

    async def test_a_late_past_due_still_cannot_overwrite_newer_state(self, webhook_client):
        await _seed_user(stripe_customer_id="cus_test_1", plan="free")
        await _post_signed(webhook_client, event(event_id="evt_a", status="active", created=1_000))
        await _post_signed(webhook_client, event(event_id="evt_u", status="unpaid", created=3_000))

        resp = await _post_signed(
            webhook_client, event(event_id="evt_pd", status="past_due", created=2_000)
        )
        assert resp.json()["status"] == "stale_event"
        user = await get_user_by_auth_id("auth-stripe-1")
        assert (user["plan"], user["stripe_subscription_status"]) == ("restricted", "unpaid")
        assert user["stripe_event_created"] == 3_000

    async def test_plan_setting_events_still_advance_the_watermark(self, webhook_client):
        await _seed_user(stripe_customer_id="cus_test_1", plan="free")
        await _post_signed(webhook_client, event(event_id="evt_a", status="active", created=1_000))
        await _post_signed(webhook_client, event(event_id="evt_pd", status="past_due", created=2_000))
        user = await get_user_by_auth_id("auth-stripe-1")
        assert user["stripe_event_created"] == 1_000
        assert user["stripe_subscription_status"] == "past_due"

        resp = await _post_signed(
            webhook_client, event(event_id="evt_old", status="canceled", created=500)
        )
        assert resp.json()["status"] == "stale_event"
        assert (await get_user_by_auth_id("auth-stripe-1"))["plan"] == "pro"
