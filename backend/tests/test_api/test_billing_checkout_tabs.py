"""Checkout edges left after #768 (#912).

3. Two checkout tabs opened before any webhook lands created two Stripe
   Checkout sessions, both payable: the customer could be billed twice.
4. A paused subscription did not count, so a paused subscriber could start a
   second one that would double-bill once the first resumed.

The Stripe SDK calls are stubbed, as in test_billing_checkout.py; the user
record is real MongoDB.
"""

from types import SimpleNamespace

import pytest
import stripe

from tests.test_api.test_billing_checkout import consenting, stripe_configured, stripe_stub  # noqa: F401

pytestmark = pytest.mark.asyncio


@pytest.fixture
def sessions(monkeypatch, stripe_stub):  # noqa: F811
    """Each checkout gets its own session id; their Stripe status is ours to set."""
    state = {"status": {}, "expired": [], "made": 0}

    def create(**kwargs):
        stripe_stub["session"].append(kwargs)
        state["made"] += 1
        sid = f"cs_test_{state['made']}"
        state["status"][sid] = "open"
        return SimpleNamespace(id=sid, url=f"https://checkout.stripe.com/c/pay/{sid}")

    def retrieve(sid, **kwargs):
        return SimpleNamespace(id=sid, status=state["status"][sid])

    def expire(sid, **kwargs):
        state["expired"].append(sid)
        state["status"][sid] = "expired"
        return SimpleNamespace(id=sid, status="expired")

    monkeypatch.setattr(stripe.checkout.Session, "create", create)
    monkeypatch.setattr(stripe.checkout.Session, "retrieve", retrieve)
    monkeypatch.setattr(stripe.checkout.Session, "expire", expire)
    return state


async def test_a_second_checkout_closes_the_first(auth_client_factory, stripe_configured, sessions):  # noqa: F811
    api = await auth_client_factory()
    first = await api.post("/api/v1/billing/checkout", json=await consenting(api))
    second = await api.post("/api/v1/billing/checkout", json=await consenting(api))

    assert (first.status_code, second.status_code) == (200, 200), second.text
    assert sessions["expired"] == ["cs_test_1"]
    assert sessions["status"] == {"cs_test_1": "expired", "cs_test_2": "open"}


async def test_a_checkout_after_one_already_paid_is_refused(auth_client_factory, stripe_configured, sessions):  # noqa: F811
    api = await auth_client_factory()
    await api.post("/api/v1/billing/checkout", json=await consenting(api))
    sessions["status"]["cs_test_1"] = "complete"  # paid; its webhook has not landed yet

    again = await api.post("/api/v1/billing/checkout", json=await consenting(api))

    assert again.status_code == 409, again.text
    assert "already" in again.json()["detail"].lower()
    assert sessions["expired"] == ["cs_test_2"]  # the new one cannot be paid either


async def test_a_first_checkout_closes_nothing(auth_client_factory, stripe_configured, sessions):  # noqa: F811
    api = await auth_client_factory()
    response = await api.post("/api/v1/billing/checkout", json=await consenting(api))

    assert response.status_code == 200
    assert sessions["expired"] == []


async def test_a_paused_subscriber_is_sent_to_resume_it(auth_client_factory, stripe_configured, sessions):  # noqa: F811
    api = await auth_client_factory(overrides={
        "stripe_customer_id": "cus_paused", "stripe_subscription_id": "sub_paused",
        "stripe_subscription_status": "paused", "plan": "free",
    })
    response = await api.post("/api/v1/billing/checkout", json=await consenting(api))

    assert response.status_code == 409
    assert "paused" in response.json()["detail"].lower()
    assert sessions["made"] == 0


async def test_a_paid_checkout_from_before_a_cancellation_does_not_block_a_new_one(
    auth_client_factory, stripe_configured, sessions, monkeypatch  # noqa: F811
):
    """Found in review: the paid session stayed recorded, and every later
    checkout was refused as 'already subscribed'."""
    from tests.test_api.test_stripe_webhook import TEST_PRO_PRICE_ID, subscription_event
    from app.api.endpoints import webhooks
    import json

    api = await auth_client_factory(overrides={"stripe_customer_id": "cus_back"})
    await api.post("/api/v1/billing/checkout", json=await consenting(api))
    sessions["status"]["cs_test_1"] = "complete"
    monkeypatch.setattr(webhooks.settings, "STRIPE_PRICE_ID_PRO", TEST_PRO_PRICE_ID)
    auth_id = (await api.get("/api/v1/users/me")).json()["auth_id"]
    for payload in (
        subscription_event(event_id="evt_on", customer="cus_back", subscription_id="sub_1",
                           metadata={"auth_id": auth_id}),
        subscription_event(event_id="evt_off", customer="cus_back", subscription_id="sub_1",
                           event_type="customer.subscription.deleted", status="canceled"),
    ):
        event = json.loads(payload)
        result = await webhooks._apply_subscription_event(
            event["type"], event["data"]["object"], event["id"], event["created"])
        assert result["status"] == "processed"

    again = await api.post("/api/v1/billing/checkout", json=await consenting(api))

    assert again.status_code == 200, again.text


async def test_a_stripe_error_after_the_swap_keeps_the_earlier_checkout_recorded(
    auth_client_factory, stripe_configured, sessions, monkeypatch  # noqa: F811
):
    """Found in review: the earlier, still payable session was dropped from the
    record, so a retry could not close it."""
    api = await auth_client_factory()
    await api.post("/api/v1/billing/checkout", json=await consenting(api))
    real_retrieve = stripe.checkout.Session.retrieve

    def unreachable(sid, **kwargs):
        raise stripe.APIConnectionError("Stripe is unreachable")

    monkeypatch.setattr(stripe.checkout.Session, "retrieve", unreachable)
    failed = await api.post("/api/v1/billing/checkout", json=await consenting(api))
    assert failed.status_code == 502
    assert sessions["expired"] == ["cs_test_2"]  # the new one cannot be paid

    monkeypatch.setattr(stripe.checkout.Session, "retrieve", real_retrieve)
    retried = await api.post("/api/v1/billing/checkout", json=await consenting(api))
    assert retried.status_code == 200
    assert "cs_test_1" in sessions["expired"]  # the retry closed the earlier one
