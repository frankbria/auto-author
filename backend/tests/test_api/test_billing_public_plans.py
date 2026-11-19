"""GET /api/v1/billing/plans: the public pricing page's numbers.

No sign-in, the same per-plan caps as GET /billing/quotas (#766), and the Pro
price read from the Stripe Price the checkout charges. The Stripe SDK boundary
(stripe.Price.retrieve) is stubbed; routing and settings are real.
"""

import pytest
import stripe
from httpx import ASGITransport, AsyncClient
from types import SimpleNamespace

from app.api.endpoints import billing
from app.core.config import settings
from app.main import app

pytestmark = pytest.mark.asyncio

PRICE_PRO = "price_pro_123"


@pytest.fixture
async def anon_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def price_calls(monkeypatch):
    """Configure Stripe and count Price lookups; each test sets what they return."""
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setattr(settings, "STRIPE_PRICE_ID_PRO", PRICE_PRO)
    monkeypatch.setattr(billing, "_PRICE_CACHE", {})
    monkeypatch.setattr(billing, "_PRICE_FAILED_AT", {})
    calls = []

    def retrieve(price_id, **kwargs):
        calls.append(price_id)
        return SimpleNamespace(
            id=price_id,
            unit_amount=4900,
            currency="usd",
            recurring=SimpleNamespace(interval="month", interval_count=1),
        )

    monkeypatch.setattr(stripe.Price, "retrieve", retrieve)
    return calls


async def test_plans_need_no_sign_in_and_match_the_quotas_endpoint(
    anon_client, auth_client_factory, price_calls
):
    public = await anon_client.get("/api/v1/billing/plans")
    assert public.status_code == 200, public.text

    signed_in = await auth_client_factory()
    quotas = (await signed_in.get("/api/v1/billing/quotas")).json()
    # One source: the pricing page and Settings → Billing can't disagree.
    assert public.json()["plans"] == quotas
    assert public.json()["plans"]["free"] == {
        "daily": None,
        "monthly": None,
        "total": settings.AI_QUOTA_FREE_TOTAL,
        "draft_chapters": settings.AI_QUOTA_FREE_DRAFT_CHAPTERS,
        "export": False,
    }


async def test_plans_carry_the_live_stripe_price(anon_client, price_calls):
    body = (await anon_client.get("/api/v1/billing/plans")).json()
    assert body["pro_price"] == {"amount": "$49.00", "period": "month"}

    await anon_client.get("/api/v1/billing/plans")
    assert price_calls == [PRICE_PRO], "a Price is immutable; one lookup per id"


async def test_no_price_when_stripe_is_not_configured(anon_client, price_calls, monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_PRICE_ID_PRO", "")
    body = (await anon_client.get("/api/v1/billing/plans")).json()
    assert body["pro_price"] is None
    assert body["plans"]["pro"]["export"] is True
    assert price_calls == []


async def test_a_failed_price_lookup_hides_the_price_and_backs_off(
    anon_client, price_calls, monkeypatch
):
    attempts = []

    def failing(price_id, **kwargs):
        attempts.append(price_id)
        raise stripe.APIConnectionError("down")

    monkeypatch.setattr(stripe.Price, "retrieve", failing)
    for _ in range(3):
        resp = await anon_client.get("/api/v1/billing/plans")
        assert resp.status_code == 200, "the page still gets the plans"
        assert resp.json()["pro_price"] is None

    # Anonymous page views must not each become a Stripe call during an outage.
    assert attempts == [PRICE_PRO]


async def test_lookup_retries_once_the_backoff_has_passed(
    anon_client, price_calls, monkeypatch
):
    monkeypatch.setattr(
        billing, "_PRICE_FAILED_AT",
        {PRICE_PRO: -billing.PRICE_FAILURE_BACKOFF_SECONDS - 1},
    )
    body = (await anon_client.get("/api/v1/billing/plans")).json()
    assert body["pro_price"] == {"amount": "$49.00", "period": "month"}


async def test_a_one_off_price_is_not_advertised_as_a_subscription(
    anon_client, price_calls, monkeypatch
):
    monkeypatch.setattr(
        stripe.Price, "retrieve",
        lambda price_id, **kw: SimpleNamespace(
            id=price_id, unit_amount=4900, currency="usd", recurring=None
        ),
    )
    body = (await anon_client.get("/api/v1/billing/plans")).json()
    assert body["pro_price"] is None
