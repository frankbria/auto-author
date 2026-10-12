"""A Stripe webhook that cannot do its job says so (#812).

Three failures left no trace an operator would see. A delivery whose signature
does not verify (a rotated ``whsec_``) was a 400 with no log line: Stripe
retries for days and then disables the endpoint. A webhook with no secret
configured was a 503 with no log line. An event for a customer that matches no
user was a warning. Each now logs an error and sends one report to Sentry,
with nothing from the payload in either.

Real HMAC signatures and the real Sentry SDK (its transport is a list).
"""

import json
import logging

import pytest
import pytest_asyncio
import sentry_sdk
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app import main
from app.api.endpoints import webhooks
from app.core import reporting
from app.core.config import settings
from tests.test_api.test_stripe_webhook import (
    TEST_PRO_PRICE_ID,
    TEST_WEBHOOK_SECRET,
    WEBHOOK_URL,
    sign,
    subscription_event,
)

pytestmark = pytest.mark.asyncio

CUSTOMER = "cus_SENTINEL_customer"
EMAIL = "sentinel-payer@example.com"
LOGGER = "app.api.endpoints.webhooks"


@pytest_asyncio.fixture
async def webhook(motor_reinit_db, monkeypatch):
    """The webhook router alone, with Stripe test settings and a fresh database."""
    import app.db.stripe_events as stripe_events_dao

    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)
    monkeypatch.setattr(settings, "STRIPE_PRICE_ID_PRO", TEST_PRO_PRICE_ID)
    monkeypatch.setattr(stripe_events_dao, "_ttl_index_ensured", False)
    monkeypatch.setattr(reporting, "_last_reported", {})
    app = FastAPI()
    app.include_router(webhooks.router, prefix="/api/v1/webhooks")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def reports(monkeypatch):
    """The SDK as the app starts it, sending to a list. Inert again afterwards."""
    sent: list = []
    real_init = sentry_sdk.init
    monkeypatch.setattr(settings, "SENTRY_DSN", "https://key@sentry.invalid/1")
    monkeypatch.setattr(sentry_sdk, "init", lambda **options: real_init(**options, transport=sent.append))
    main._init_sentry()
    yield sent
    real_init()


def _errors(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == LOGGER and r.levelno >= logging.ERROR]


def _unknown_customer_event() -> bytes:
    return subscription_event(event_id="evt_unmatched_1", customer=CUSTOMER, metadata={"email": EMAIL})


class TestASignatureThatDoesNotVerify:
    async def test_is_logged_and_reported(self, webhook, reports, caplog):
        payload = _unknown_customer_event()
        with caplog.at_level(logging.INFO, logger=LOGGER):
            response = await webhook.post(
                WEBHOOK_URL, content=payload, headers={"stripe-signature": sign(payload, secret="whsec_rotated")}
            )

        assert response.status_code == 400
        assert len(_errors(caplog)) == 1
        assert [(r["level"], r["fingerprint"]) for r in reports] == [("error", ["stripe-webhook", "signature"])]

    async def test_says_nothing_from_the_delivery(self, webhook, reports, caplog):
        payload = _unknown_customer_event()
        signature = sign(payload, secret="whsec_rotated")
        with caplog.at_level(logging.INFO, logger=LOGGER):
            await webhook.post(WEBHOOK_URL, content=payload, headers={"stripe-signature": signature})

        said = caplog.text + json.dumps(reports, default=str)
        assert reports, "nothing was reported, so nothing was checked"
        for secret in (CUSTOMER, EMAIL, signature.split("v1=")[1], TEST_WEBHOOK_SECRET):
            assert secret not in said

    async def test_a_flood_of_them_is_logged_each_time_and_reported_once(self, webhook, reports, caplog):
        """Anyone can post a bad signature here; the log is ours, the Sentry quota is not."""
        payload = _unknown_customer_event()
        with caplog.at_level(logging.INFO, logger=LOGGER):
            for _ in range(3):
                await webhook.post(WEBHOOK_URL, content=payload, headers={"stripe-signature": "t=1,v1=forged"})

        assert len(_errors(caplog)) == 3
        assert len(reports) == 1

    async def test_a_request_with_no_signature_at_all_is_not_a_report(self, webhook, reports, caplog):
        """Stripe always signs. This is a scanner, and it is answered and no more."""
        with caplog.at_level(logging.INFO, logger=LOGGER):
            response = await webhook.post(WEBHOOK_URL, content=b"{}")

        assert response.status_code == 400
        assert (_errors(caplog), reports) == ([], [])


class TestAWebhookWithNoSecretConfigured:
    async def test_is_logged_and_reported_once_however_many_deliveries_arrive(
        self, webhook, reports, caplog, monkeypatch
    ):
        """Anyone can post here while it is unconfigured, so it is throttled like a bad signature.
        Raised as an exception, the 503 was reported by the SDK itself on every request."""
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "")
        payload = _unknown_customer_event()
        with caplog.at_level(logging.INFO, logger=LOGGER):
            responses = [
                await webhook.post(WEBHOOK_URL, content=payload, headers={"stripe-signature": sign(payload)})
                for _ in range(3)
            ]

        assert [(r.status_code, r.json()) for r in responses] == [(503, {"detail": "Stripe webhook is not configured"})] * 3
        assert len(_errors(caplog)) == 3 and "STRIPE_WEBHOOK_SECRET" in _errors(caplog)[0]
        assert [r.get("fingerprint") for r in reports] == [["stripe-webhook", "not-configured"]]
        said = caplog.text + json.dumps(reports, default=str)
        assert CUSTOMER not in said and EMAIL not in said and sign(payload).split("v1=")[1] not in said


class TestAnEventForACustomerNobodyHas:
    async def test_is_acknowledged_logged_and_reported(self, webhook, reports, caplog):
        payload = _unknown_customer_event()
        with caplog.at_level(logging.INFO, logger=LOGGER):
            response = await webhook.post(WEBHOOK_URL, content=payload, headers={"stripe-signature": sign(payload)})

        assert (response.status_code, response.json()) == (200, {"status": "no_matching_user"})
        assert len(_errors(caplog)) == 1
        assert [r["fingerprint"] for r in reports] == [["stripe-webhook", "no-matching-user"]]

    async def test_names_the_event_to_resend_and_not_the_customer(self, webhook, reports, caplog):
        payload = _unknown_customer_event()
        with caplog.at_level(logging.INFO, logger=LOGGER):
            await webhook.post(WEBHOOK_URL, content=payload, headers={"stripe-signature": sign(payload)})

        said = caplog.text + json.dumps(reports, default=str)
        assert "evt_unmatched_1" in _errors(caplog)[0]
        assert "evt_unmatched_1" in reports[0]["message"]
        assert CUSTOMER not in said and EMAIL not in said

    async def test_each_one_is_reported_because_each_names_a_different_event(self, webhook, reports):
        """Only Stripe can cause this one, so it is not held to one report in five minutes."""
        for event_id in ("evt_unmatched_1", "evt_unmatched_2"):
            payload = subscription_event(event_id=event_id, customer=CUSTOMER)
            await webhook.post(WEBHOOK_URL, content=payload, headers={"stripe-signature": sign(payload)})

        assert ["evt_unmatched_1" in reports[0]["message"], "evt_unmatched_2" in reports[1]["message"]] == [True, True]
        assert len(reports) == 2

    async def test_different_kinds_of_failure_are_reported_separately(self, webhook, reports):
        payload = _unknown_customer_event()
        await webhook.post(WEBHOOK_URL, content=payload, headers={"stripe-signature": "t=1,v1=forged"})
        await webhook.post(WEBHOOK_URL, content=payload, headers={"stripe-signature": sign(payload)})

        assert [r["fingerprint"][1] for r in reports] == ["signature", "no-matching-user"]
