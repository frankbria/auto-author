"""Managed Payments at checkout (#1234): Stripe, as Link, is merchant of record.

The setting is always sent, so the account's Dashboard default never decides it
(that default broke checkout once). Same Stripe SDK boundary stubs as
test_billing_checkout.py; real Mongo and routing.
"""

import pytest

from app.api.endpoints import billing
from app.core.config import Settings, settings
from tests.conftest import _sync_logs
from tests.test_api import test_billing_checkout as checkout

stripe_configured = checkout.stripe_configured
stripe_stub = checkout.stripe_stub
consenting = checkout.consenting

pytestmark = pytest.mark.asyncio

# Params Stripe refuses on a Managed Payments session: custom_text (seen live,
# "custom_text cannot be used with Managed Payments") and the tax and
# customer_update params (Stripe's docs). The last two are left out because the
# docs' list proved incomplete and Stripe collects the address itself.
REFUSED_UNDER_MANAGED_PAYMENTS = {
    "custom_text",
    "automatic_tax",
    "tax_id_collection",
    "customer_update",
    "consent_collection",
    "billing_address_collection",
}


async def _checkout_kwargs(client, stripe_stub):
    resp = await client.post("/api/v1/billing/checkout", json=await consenting(client))
    assert resp.status_code == 200, resp.text
    return stripe_stub["session"][0]


async def test_managed_payments_is_off_by_default_and_always_sent(
    auth_client_factory, stripe_configured, stripe_stub
):
    assert Settings.model_fields["STRIPE_MANAGED_PAYMENTS"].default is False
    client = await auth_client_factory()
    sess = await _checkout_kwargs(client, stripe_stub)

    # Explicitly off, not absent: absent lets the Dashboard default decide.
    assert sess["managed_payments"] == {"enabled": False}
    assert sess["custom_text"]["submit"]["message"]
    assert sess["consent_collection"] == {"terms_of_service": "required"}


async def test_managed_payments_on_sends_no_param_stripe_refuses(
    auth_client_factory, stripe_configured, stripe_stub, monkeypatch
):
    monkeypatch.setattr(settings, "STRIPE_MANAGED_PAYMENTS", True)
    client = await auth_client_factory(overrides={"stripe_customer_id": "cus_existing"})
    sess = await _checkout_kwargs(client, stripe_stub)

    assert sess["managed_payments"] == {"enabled": True}
    assert REFUSED_UNDER_MANAGED_PAYMENTS.isdisjoint(sess)
    # Everything the webhook and the consent record rely on is unchanged.
    assert sess["mode"] == "subscription"
    assert sess["customer"] == "cus_existing"
    assert sess["client_reference_id"]
    metadata = sess["subscription_data"]["metadata"]
    assert set(metadata) == {
        "auth_id", "renewal_disclosure_version", "renewal_disclosure_sha256"
    }


async def test_managed_payments_supersedes_automatic_tax(
    auth_client_factory, stripe_configured, stripe_stub, monkeypatch
):
    monkeypatch.setattr(settings, "STRIPE_MANAGED_PAYMENTS", True)
    monkeypatch.setattr(settings, "STRIPE_AUTOMATIC_TAX", True)
    client = await auth_client_factory()
    sess = await _checkout_kwargs(client, stripe_stub)

    assert "automatic_tax" not in sess


async def test_managed_payments_still_requires_and_records_in_app_consent(
    auth_client_factory, stripe_configured, stripe_stub, monkeypatch
):
    """With Stripe's page no longer repeating the renewal terms, the in-app
    disclosure and consent record (#770) are the whole of it: no consent, no
    checkout; consent, a record of the exact text first."""
    monkeypatch.setattr(settings, "STRIPE_MANAGED_PAYMENTS", True)
    client = await auth_client_factory()

    refused = await client.post("/api/v1/billing/checkout", json={"plan": "pro"})
    assert refused.status_code == 400
    assert stripe_stub["session"] == []

    body = await consenting(client)
    resp = await client.post("/api/v1/billing/checkout", json=body)
    assert resp.status_code == 200, resp.text
    assert _sync_logs.count_documents({"action": billing.RENEWAL_CONSENT_ACTION}) == 1
    record = _sync_logs.find_one({"action": billing.RENEWAL_CONSENT_ACTION})
    assert record["details"]["disclosure_sha256"] == body["disclosure_sha256"]
