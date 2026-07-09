"""Tests for POST /api/v1/billing/checkout (issue #221).

Real MongoDB via auth_client_factory; the Stripe SDK boundary
(stripe.Customer.create / stripe.checkout.Session.create) is stubbed — the
paid external API is the one thing we don't call for real. Everything else
(routing, auth dependency, persistence) is exercised end-to-end.
"""

import pytest
import stripe
from types import SimpleNamespace

from app.core.config import Settings, settings
from tests.conftest import _sync_users

pytestmark = pytest.mark.asyncio

SECRET_KEY = "sk_test_dummy"
PRICE_PRO = "price_pro_123"


@pytest.fixture
def stripe_configured(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", SECRET_KEY)
    monkeypatch.setattr(settings, "STRIPE_PRICE_ID_PRO", PRICE_PRO)


@pytest.fixture
def stripe_stub(monkeypatch):
    """Capture outbound Stripe SDK calls; return canned objects (v15 attribute API)."""
    calls = {"customer": [], "session": []}

    def fake_customer_create(**kwargs):
        calls["customer"].append(kwargs)
        return SimpleNamespace(id="cus_new_001")

    def fake_session_create(**kwargs):
        calls["session"].append(kwargs)
        return SimpleNamespace(
            id="cs_test_001", url="https://checkout.stripe.com/c/pay/cs_test_001"
        )

    monkeypatch.setattr(stripe.Customer, "create", fake_customer_create)
    monkeypatch.setattr(stripe.checkout.Session, "create", fake_session_create)
    return calls


async def test_checkout_creates_customer_and_session(
    auth_client_factory, stripe_configured, stripe_stub
):
    """Free user with no Stripe customer: customer created + persisted, session URL returned."""
    client = await auth_client_factory()
    resp = await client.post("/api/v1/billing/checkout", json={"plan": "pro"})

    assert resp.status_code == 200, resp.text
    assert resp.json()["url"] == "https://checkout.stripe.com/c/pay/cs_test_001"

    # Customer created with the linkage + idempotency the webhook/race-safety need
    assert len(stripe_stub["customer"]) == 1
    cust_kwargs = stripe_stub["customer"][0]
    user_doc = _sync_users.find_one({"stripe_customer_id": "cus_new_001"})
    assert user_doc is not None, "stripe_customer_id must be persisted on the user"
    auth_id = user_doc["auth_id"]
    assert cust_kwargs["email"] == user_doc["email"]
    assert cust_kwargs["metadata"] == {"auth_id": auth_id}
    assert auth_id in cust_kwargs["idempotency_key"]

    # Session carries everything the #220 webhook reconciles on
    assert len(stripe_stub["session"]) == 1
    sess = stripe_stub["session"][0]
    assert sess["mode"] == "subscription"
    assert sess["customer"] == "cus_new_001"
    assert sess["line_items"] == [{"price": PRICE_PRO, "quantity": 1}]
    assert sess["client_reference_id"] == auth_id
    assert sess["subscription_data"]["metadata"]["auth_id"] == auth_id
    assert "checkout=success" in sess["success_url"]
    assert "checkout=cancel" in sess["cancel_url"]

    # The plan must NOT flip here — reconciliation is webhook-only
    assert user_doc["plan"] == "free"


async def test_checkout_reuses_existing_customer(
    auth_client_factory, stripe_configured, stripe_stub
):
    client = await auth_client_factory(overrides={"stripe_customer_id": "cus_existing"})
    resp = await client.post("/api/v1/billing/checkout", json={"plan": "pro"})

    assert resp.status_code == 200, resp.text
    assert stripe_stub["customer"] == []  # no second Stripe customer
    assert stripe_stub["session"][0]["customer"] == "cus_existing"


async def test_checkout_rejects_already_paid_plan(
    auth_client_factory, stripe_configured, stripe_stub
):
    client = await auth_client_factory(overrides={"plan": "pro"})
    resp = await client.post("/api/v1/billing/checkout", json={"plan": "pro"})

    assert resp.status_code == 409
    assert stripe_stub["customer"] == [] and stripe_stub["session"] == []


async def test_checkout_fails_closed_when_unconfigured(
    auth_client_factory, stripe_stub, monkeypatch
):
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "")
    monkeypatch.setattr(settings, "STRIPE_PRICE_ID_PRO", PRICE_PRO)
    client = await auth_client_factory()
    resp = await client.post("/api/v1/billing/checkout", json={"plan": "pro"})

    assert resp.status_code == 503
    assert stripe_stub["customer"] == [] and stripe_stub["session"] == []


async def test_checkout_requires_auth(auth_client_factory, stripe_configured):
    client = await auth_client_factory(auth=False)
    resp = await client.post("/api/v1/billing/checkout", json={"plan": "pro"})
    assert resp.status_code == 401


async def test_checkout_rejects_unknown_plan(
    auth_client_factory, stripe_configured, stripe_stub
):
    client = await auth_client_factory()
    resp = await client.post("/api/v1/billing/checkout", json={"plan": "enterprise"})
    assert resp.status_code == 422
    assert stripe_stub["session"] == []


async def test_stripe_failure_returns_502_without_leaking(
    auth_client_factory, stripe_configured, stripe_stub, monkeypatch
):
    def boom(**kwargs):
        raise stripe.StripeError("secret internal detail sk_live_abc")

    monkeypatch.setattr(stripe.checkout.Session, "create", boom)
    client = await auth_client_factory()
    resp = await client.post("/api/v1/billing/checkout", json={"plan": "pro"})

    assert resp.status_code == 502
    assert "sk_live" not in resp.text
    assert "secret internal detail" not in resp.text
    # Customer creation succeeded before the failure; the id is retained so a
    # retry reuses it instead of minting another Stripe customer.
    assert _sync_users.find_one({"stripe_customer_id": "cus_new_001"}) is not None


async def test_stripe_secret_key_defaults_empty():
    """Checkout ships fail-closed: no key in the env means 503, never a crash."""
    assert Settings(_env_file=None).STRIPE_SECRET_KEY == ""
