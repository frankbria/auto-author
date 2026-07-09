"""Tests for POST /api/v1/billing/portal (issue #222).

Same harness as test_billing_checkout.py: real MongoDB via auth_client_factory,
only the Stripe SDK boundary (stripe.billing_portal.Session.create) is stubbed.
"""

import pytest
import stripe
from types import SimpleNamespace

from app.core.config import settings
from tests.conftest import _sync_users

pytestmark = pytest.mark.asyncio

SECRET_KEY = "sk_test_dummy"


@pytest.fixture
def stripe_configured(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", SECRET_KEY)


@pytest.fixture
def portal_stub(monkeypatch):
    """Capture outbound billing-portal SDK calls; return a canned session."""
    calls = []

    def fake_portal_create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            id="bps_test_001", url="https://billing.stripe.com/p/session/bps_test_001"
        )

    monkeypatch.setattr(stripe.billing_portal.Session, "create", fake_portal_create)
    return calls


async def test_portal_returns_session_url(
    auth_client_factory, stripe_configured, portal_stub
):
    """Paid user with a Stripe customer gets a portal URL; return_url deep-links the billing tab."""
    client = await auth_client_factory(
        overrides={"plan": "pro", "stripe_customer_id": "cus_paid_001"}
    )
    resp = await client.post("/api/v1/billing/portal")

    assert resp.status_code == 200, resp.text
    assert resp.json()["url"] == "https://billing.stripe.com/p/session/bps_test_001"

    assert len(portal_stub) == 1
    kwargs = portal_stub[0]
    assert kwargs["customer"] == "cus_paid_001"
    assert (
        kwargs["return_url"]
        == f"{settings.BETTER_AUTH_URL.rstrip('/')}/dashboard/settings?tab=billing"
    )

    # Plan is never mutated here — reconciliation stays webhook-only (#220).
    user_doc = _sync_users.find_one({"stripe_customer_id": "cus_paid_001"})
    assert user_doc["plan"] == "pro"


async def test_portal_allows_lapsed_restricted_user(
    auth_client_factory, stripe_configured, portal_stub
):
    """The gate is the Stripe customer, not the plan — a lapsed ('restricted')
    user must reach the portal to fix their payment method."""
    client = await auth_client_factory(
        overrides={"plan": "restricted", "stripe_customer_id": "cus_lapsed_001"}
    )
    resp = await client.post("/api/v1/billing/portal")

    assert resp.status_code == 200, resp.text
    assert portal_stub[0]["customer"] == "cus_lapsed_001"


async def test_portal_rejects_user_without_stripe_customer(
    auth_client_factory, stripe_configured, portal_stub
):
    """No stripe_customer_id → nothing to manage → 409, no Stripe call."""
    client = await auth_client_factory()
    resp = await client.post("/api/v1/billing/portal")

    assert resp.status_code == 409
    assert portal_stub == []


async def test_portal_fails_closed_when_unconfigured(
    auth_client_factory, portal_stub, monkeypatch
):
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "")
    client = await auth_client_factory(
        overrides={"plan": "pro", "stripe_customer_id": "cus_paid_001"}
    )
    resp = await client.post("/api/v1/billing/portal")

    assert resp.status_code == 503
    assert portal_stub == []


async def test_portal_requires_auth(auth_client_factory, stripe_configured):
    client = await auth_client_factory(auth=False)
    resp = await client.post("/api/v1/billing/portal")
    assert resp.status_code == 401


async def test_portal_stripe_failure_returns_502_without_leaking(
    auth_client_factory, stripe_configured, monkeypatch
):
    def boom(**kwargs):
        raise stripe.StripeError("secret internal detail sk_live_abc")

    monkeypatch.setattr(stripe.billing_portal.Session, "create", boom)
    client = await auth_client_factory(
        overrides={"plan": "pro", "stripe_customer_id": "cus_paid_001"}
    )
    resp = await client.post("/api/v1/billing/portal")

    assert resp.status_code == 502
    assert "sk_live" not in resp.text
    assert "secret internal detail" not in resp.text
