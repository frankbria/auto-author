"""Tax at checkout (#783): Stripe Tax, billing address and tax-ID collection.

Same Stripe SDK boundary stubs as test_billing_checkout.py; real Mongo and routing.
"""

import pytest

from app.api.endpoints import billing
from app.core.config import Settings, settings
from tests.test_api import test_billing_checkout as checkout

# Reuse the checkout module's Stripe boundary stubs as this module's fixtures.
stripe_configured = checkout.stripe_configured
stripe_stub = checkout.stripe_stub
consenting = checkout.consenting

pytestmark = pytest.mark.asyncio


async def _checkout_kwargs(client, stripe_stub):
    resp = await client.post("/api/v1/billing/checkout", json=await consenting(client))
    assert resp.status_code == 200, resp.text
    return stripe_stub["session"][0]


async def test_checkout_always_collects_billing_address_and_tax_ids(
    auth_client_factory, stripe_configured, stripe_stub
):
    client = await auth_client_factory(overrides={"stripe_customer_id": "cus_existing"})
    sess = await _checkout_kwargs(client, stripe_stub)

    assert sess["billing_address_collection"] == "required"
    assert sess["tax_id_collection"] == {"enabled": True}
    # The session always passes an existing Customer, and Stripe refuses tax-ID
    # collection and automatic tax on one unless Checkout may write the
    # collected name and address back to it.
    assert sess["customer_update"] == {"address": "auto", "name": "auto"}


async def test_automatic_tax_is_off_until_the_operator_enables_it(
    auth_client_factory, stripe_configured, stripe_stub
):
    """Stripe rejects every checkout with automatic_tax on an account where
    Stripe Tax isn't activated, so the default must not turn it on."""
    assert Settings.model_fields["STRIPE_AUTOMATIC_TAX"].default is False
    client = await auth_client_factory()
    sess = await _checkout_kwargs(client, stripe_stub)

    assert sess["automatic_tax"] == {"enabled": False}


async def test_automatic_tax_enabled_by_setting(
    auth_client_factory, stripe_configured, stripe_stub, monkeypatch
):
    monkeypatch.setattr(settings, "STRIPE_AUTOMATIC_TAX", True)
    client = await auth_client_factory()
    sess = await _checkout_kwargs(client, stripe_stub)

    assert sess["automatic_tax"] == {"enabled": True}


async def test_disclosure_says_the_price_excludes_tax(
    auth_client_factory, stripe_configured, stripe_stub
):
    client = await auth_client_factory()
    body = (await client.get("/api/v1/billing/disclosure")).json()

    assert "$12.00 per month plus any applicable tax" in body["text"]
    assert billing.RENEWAL_DISCLOSURE_VERSION != "2026-10-02"
