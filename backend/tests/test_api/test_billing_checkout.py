"""Tests for POST /api/v1/billing/checkout (issue #221).

Real MongoDB via auth_client_factory; the Stripe SDK boundary
(stripe.Customer.create / stripe.checkout.Session.create / stripe.Price.retrieve)
is stubbed — the paid external API is the one thing we don't call for real.
Everything else (routing, auth dependency, persistence) is exercised end-to-end.
"""

import hashlib

import pytest
import stripe
from types import SimpleNamespace

from app.api.endpoints import billing
from app.core.config import Settings, settings
from tests.conftest import _sync_logs, _sync_users

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

    def fake_price_retrieve(price_id, **kwargs):
        calls["price"].append(price_id)
        return SimpleNamespace(
            id=price_id,
            unit_amount=1200,
            currency="usd",
            recurring=SimpleNamespace(interval="month", interval_count=1),
        )

    calls["price"] = []
    monkeypatch.setattr(billing, "_PRICE_CACHE", {})
    monkeypatch.setattr(stripe.Customer, "create", fake_customer_create)
    monkeypatch.setattr(stripe.checkout.Session, "create", fake_session_create)
    monkeypatch.setattr(stripe.Price, "retrieve", fake_price_retrieve)
    return calls


async def consenting(client):
    """A checkout body that agrees to the disclosure the API currently shows (#770)."""
    disclosure = (await client.get("/api/v1/billing/disclosure")).json()
    return {
        "plan": "pro",
        "accept_renewal_terms": True,
        "disclosure_sha256": disclosure["sha256"],
    }


async def test_checkout_creates_customer_and_session(
    auth_client_factory, stripe_configured, stripe_stub
):
    """Free user with no Stripe customer: customer created + persisted, session URL returned."""
    client = await auth_client_factory()
    resp = await client.post("/api/v1/billing/checkout", json=await consenting(client))

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
    resp = await client.post("/api/v1/billing/checkout", json=await consenting(client))

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
    resp = await client.post("/api/v1/billing/checkout", json=await consenting(client))

    assert resp.status_code == 502
    assert "sk_live" not in resp.text
    assert "secret internal detail" not in resp.text
    # Customer creation succeeded before the failure; the id is retained so a
    # retry reuses it instead of minting another Stripe customer.
    assert _sync_users.find_one({"stripe_customer_id": "cus_new_001"}) is not None


async def test_customer_create_failure_returns_502_without_leaking(
    auth_client_factory, stripe_configured, stripe_stub, monkeypatch
):
    """Pins that the Customer.create call is inside the sanitizing try-block too."""

    def boom(**kwargs):
        raise stripe.StripeError("secret internal detail sk_live_abc")

    monkeypatch.setattr(stripe.Customer, "create", boom)
    client = await auth_client_factory()
    resp = await client.post("/api/v1/billing/checkout", json=await consenting(client))

    assert resp.status_code == 502
    assert "sk_live" not in resp.text
    assert stripe_stub["session"] == []
    assert _sync_users.find_one({"stripe_customer_id": {"$ne": None}}) is None


async def test_users_me_surfaces_stripe_linkage(auth_client_factory):
    """Regression (#220 drift found during the #221 demo): read_users_me built
    UserResponse field-by-field and silently dropped the stripe ids."""
    client = await auth_client_factory(
        overrides={
            "plan": "pro",
            "stripe_customer_id": "cus_visible",
            "stripe_subscription_id": "sub_visible",
        }
    )
    resp = await client.get("/api/v1/users/me")

    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "pro"
    assert body["stripe_customer_id"] == "cus_visible"
    assert body["stripe_subscription_id"] == "sub_visible"


async def test_stripe_secret_key_defaults_empty():
    """Checkout ships fail-closed: no key in the env means 503, never a crash."""
    assert Settings(_env_file=None).STRIPE_SECRET_KEY == ""


async def test_quotas_endpoint_reports_each_plans_caps(auth_client_factory):
    """The billing UI reads the per-plan caps from the same settings the quota enforces (#766)."""
    client = await auth_client_factory()
    resp = await client.get("/api/v1/billing/quotas")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "free": {"daily": settings.AI_QUOTA_FREE_DAILY, "monthly": settings.AI_QUOTA_FREE_MONTHLY},
        "pro": {"daily": settings.AI_QUOTA_PRO_DAILY, "monthly": settings.AI_QUOTA_PRO_MONTHLY},
    }


async def test_quotas_endpoint_reports_disabled_windows_as_unlimited(
    auth_client_factory, monkeypatch
):
    """A <=0 window is 'disabled' to the enforcer; never advertise it as 0 (#766)."""
    monkeypatch.setattr(settings, "AI_QUOTA_FREE_DAILY", 0)
    client = await auth_client_factory()
    body = (await client.get("/api/v1/billing/quotas")).json()
    assert body["free"] == {"daily": None, "monthly": settings.AI_QUOTA_FREE_MONTHLY}


async def test_quotas_endpoint_all_unlimited_when_quota_disabled(
    auth_client_factory, monkeypatch
):
    monkeypatch.setattr(settings, "AI_QUOTA_ENABLED", False)
    client = await auth_client_factory()
    body = (await client.get("/api/v1/billing/quotas")).json()
    assert body == {
        "free": {"daily": None, "monthly": None},
        "pro": {"daily": None, "monthly": None},
    }


# --- Auto-renewal disclosure + recorded consent (issue #770, CA ARL / ROSCA) ---


def _price(unit_amount=1200, currency="usd", interval_count=1, recurring=True):
    return lambda price_id, **kw: SimpleNamespace(
        id=price_id,
        unit_amount=unit_amount,
        currency=currency,
        recurring=(
            SimpleNamespace(interval="month", interval_count=interval_count)
            if recurring
            else None
        ),
    )


async def test_disclosure_states_price_period_renewal_and_cancel_path(
    auth_client_factory, stripe_configured, stripe_stub
):
    """The price comes from the Stripe Price itself, so the copy can't drift from the charge."""
    client = await auth_client_factory()
    resp = await client.get("/api/v1/billing/disclosure")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    text = body["text"]
    assert "$12.00 per month" in text
    assert "renews automatically until you cancel" in text
    assert "Settings → Billing → Manage billing" in text
    assert body["version"] == billing.RENEWAL_DISCLOSURE_VERSION
    assert body["sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert stripe_stub["price"] == [PRICE_PRO]


async def test_disclosure_names_a_multi_interval_period(
    auth_client_factory, stripe_configured, stripe_stub, monkeypatch
):
    monkeypatch.setattr(
        stripe.Price, "retrieve", _price(unit_amount=3000, currency="eur", interval_count=3)
    )
    client = await auth_client_factory()
    text = (await client.get("/api/v1/billing/disclosure")).json()["text"]
    assert "30.00 EUR per 3 months" in text


async def test_disclosure_fails_closed_when_unconfigured(
    auth_client_factory, stripe_stub, monkeypatch
):
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "")
    client = await auth_client_factory()
    resp = await client.get("/api/v1/billing/disclosure")
    assert resp.status_code == 503
    assert stripe_stub["price"] == []


async def test_disclosure_price_lookup_failure_is_502_without_leaking(
    auth_client_factory, stripe_configured, stripe_stub, monkeypatch
):
    def boom(price_id, **kwargs):
        raise stripe.StripeError("secret internal detail sk_live_abc")

    monkeypatch.setattr(stripe.Price, "retrieve", boom)
    client = await auth_client_factory()
    resp = await client.get("/api/v1/billing/disclosure")
    assert resp.status_code == 502
    assert "sk_live" not in resp.text


async def test_disclosure_rejects_a_non_recurring_price(
    auth_client_factory, stripe_configured, stripe_stub, monkeypatch
):
    """A one-time price can't back a subscription; never render a renewal promise for it."""
    monkeypatch.setattr(stripe.Price, "retrieve", _price(recurring=False))
    client = await auth_client_factory()
    assert (await client.get("/api/v1/billing/disclosure")).status_code == 503


@pytest.mark.parametrize(
    "consent",
    [
        {},
        # The real, current hash: only the missing agreement can refuse this one.
        {"accept_renewal_terms": False, "disclosure_sha256": "CURRENT"},
        {"accept_renewal_terms": True},
    ],
    ids=["missing", "declined", "agreed-without-hash"],
)
async def test_checkout_refused_without_affirmative_consent(
    auth_client_factory, stripe_configured, stripe_stub, consent
):
    client = await auth_client_factory()
    if consent.get("disclosure_sha256") == "CURRENT":
        consent = {**consent, "disclosure_sha256": (await consenting(client))["disclosure_sha256"]}
    resp = await client.post("/api/v1/billing/checkout", json={"plan": "pro", **consent})

    assert resp.status_code == 400, resp.text
    assert "renewal" in resp.json()["detail"].lower()
    assert stripe_stub["customer"] == [] and stripe_stub["session"] == []
    assert _sync_logs.count_documents({"action": billing.RENEWAL_CONSENT_ACTION}) == 0


async def test_checkout_refused_when_the_shown_disclosure_is_stale(
    auth_client_factory, stripe_configured, stripe_stub
):
    """Agreeing to yesterday's price is not consent to today's (409, nothing recorded)."""
    client = await auth_client_factory()
    resp = await client.post(
        "/api/v1/billing/checkout",
        json={"plan": "pro", "accept_renewal_terms": True, "disclosure_sha256": "0" * 64},
    )

    assert resp.status_code == 409, resp.text
    assert stripe_stub["customer"] == [] and stripe_stub["session"] == []
    assert _sync_logs.count_documents({"action": billing.RENEWAL_CONSENT_ACTION}) == 0


async def test_checkout_records_consent_and_carries_it_to_stripe(
    auth_client_factory, stripe_configured, stripe_stub
):
    client = await auth_client_factory()
    disclosure = (await client.get("/api/v1/billing/disclosure")).json()
    resp = await client.post(
        "/api/v1/billing/checkout",
        json=await consenting(client),
        headers={"User-Agent": "consent-test-agent/1.0"},
    )
    assert resp.status_code == 200, resp.text

    # The consent record: who, when, from where, and exactly what they agreed to.
    user = _sync_users.find_one({"stripe_customer_id": "cus_new_001"})
    record = _sync_logs.find_one({"action": billing.RENEWAL_CONSENT_ACTION})
    assert record is not None, "consent must be recorded before checkout is created"
    assert record["actor_id"] == user["auth_id"]
    assert record["timestamp"] is not None
    details = record["details"]
    assert details["user_agent"] == "consent-test-agent/1.0"
    assert details["ip_address"]
    assert details["disclosure_version"] == billing.RENEWAL_DISCLOSURE_VERSION
    assert details["disclosure_sha256"] == disclosure["sha256"]
    assert details["disclosure_text"] == disclosure["text"]
    assert details["price_id"] == PRICE_PRO

    # Stripe's hosted page repeats the renewal terms and requires ToS consent.
    sess = stripe_stub["session"][0]
    assert sess["consent_collection"] == {"terms_of_service": "required"}
    assert sess["custom_text"]["submit"]["message"] == disclosure["text"]
    assert "/terms" in sess["custom_text"]["terms_of_service_acceptance"]["message"]
