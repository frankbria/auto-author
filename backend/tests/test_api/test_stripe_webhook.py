"""Stripe webhook endpoint tests (issue #220).

Real HMAC signatures (stdlib hmac, the exact scheme Stripe uses:
``t=<ts>,v1=HMAC-SHA256(f"{t}.{payload}")``) so ``stripe.Webhook.construct_event``
genuinely verifies — the signature seam is NOT mocked. User persistence and
replay tracking run against real local Mongo via ``motor_reinit_db``.

Bare-router pattern (mount only webhooks.router): the webhook is deliberately
unauthenticated — the signature is the auth.
"""

import hashlib
import hmac
import json
import time

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.endpoints import webhooks
from app.core.config import settings
from app.db.user import create_user, get_user_by_auth_id

pytestmark = pytest.mark.asyncio

TEST_WEBHOOK_SECRET = "whsec_test_secret_for_issue_220"
TEST_PRO_PRICE_ID = "price_test_pro_123"
WEBHOOK_URL = "/api/v1/webhooks/stripe"


def sign(payload: bytes, secret: str = TEST_WEBHOOK_SECRET, timestamp: int = None) -> str:
    """Build a genuine Stripe-Signature header for ``payload``."""
    t = timestamp if timestamp is not None else int(time.time())
    signed = f"{t}.".encode() + payload
    v1 = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={t},v1={v1}"


def subscription_event(
    event_id: str = "evt_test_1",
    event_type: str = "customer.subscription.updated",
    customer: str = "cus_test_1",
    subscription_id: str = "sub_test_1",
    price_id: str = TEST_PRO_PRICE_ID,
    metadata: dict = None,
) -> bytes:
    return json.dumps(
        {
            "id": event_id,
            "object": "event",
            "type": event_type,
            "data": {
                "object": {
                    "id": subscription_id,
                    "object": "subscription",
                    "customer": customer,
                    "status": "active",
                    "metadata": metadata or {},
                    "items": {
                        "object": "list",
                        "data": [{"price": {"id": price_id}}],
                    },
                }
            },
        }
    ).encode()


@pytest_asyncio.fixture
async def webhook_client(motor_reinit_db, monkeypatch):
    """Bare app with only the webhook router, Stripe test config, fresh Mongo."""
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)
    monkeypatch.setattr(settings, "STRIPE_PRICE_ID_PRO", TEST_PRO_PRICE_ID)
    app = FastAPI()
    app.include_router(webhooks.router, prefix="/api/v1/webhooks")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def _seed_user(**overrides):
    data = {
        "auth_id": "auth-stripe-1",
        "email": "stripe-user@example.com",
        "plan": "free",
        "is_active": True,
    }
    data.update(overrides)
    return await create_user(data)


class TestSignatureVerification:
    async def test_valid_signed_event_updates_plan(self, webhook_client):
        await _seed_user(stripe_customer_id="cus_test_1")
        payload = subscription_event()
        resp = await webhook_client.post(
            WEBHOOK_URL, content=payload, headers={"stripe-signature": sign(payload)}
        )
        assert resp.status_code == 200
        user = await get_user_by_auth_id("auth-stripe-1")
        assert user["plan"] == "pro"
        assert user["stripe_customer_id"] == "cus_test_1"
        assert user["stripe_subscription_id"] == "sub_test_1"

    async def test_tampered_payload_rejected_400(self, webhook_client):
        await _seed_user(stripe_customer_id="cus_test_1")
        payload = subscription_event()
        header = sign(payload)
        tampered = payload.replace(b"cus_test_1", b"cus_evil_9")
        resp = await webhook_client.post(
            WEBHOOK_URL, content=tampered, headers={"stripe-signature": header}
        )
        assert resp.status_code == 400
        user = await get_user_by_auth_id("auth-stripe-1")
        assert user["plan"] == "free"

    async def test_wrong_secret_rejected_400(self, webhook_client):
        payload = subscription_event()
        resp = await webhook_client.post(
            WEBHOOK_URL,
            content=payload,
            headers={"stripe-signature": sign(payload, secret="whsec_wrong")},
        )
        assert resp.status_code == 400

    async def test_missing_signature_header_400(self, webhook_client):
        resp = await webhook_client.post(WEBHOOK_URL, content=subscription_event())
        assert resp.status_code == 400

    async def test_validly_signed_garbage_payload_400(self, webhook_client):
        payload = b"not json at all"
        resp = await webhook_client.post(
            WEBHOOK_URL, content=payload, headers={"stripe-signature": sign(payload)}
        )
        assert resp.status_code == 400

    async def test_unconfigured_secret_fails_closed_503(self, webhook_client, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "")
        payload = subscription_event()
        resp = await webhook_client.post(
            WEBHOOK_URL, content=payload, headers={"stripe-signature": sign(payload)}
        )
        assert resp.status_code == 503


class TestEventRouting:
    async def test_subscription_deleted_reverts_to_free(self, webhook_client):
        await _seed_user(stripe_customer_id="cus_test_1", plan="pro")
        payload = subscription_event(
            event_id="evt_del_1", event_type="customer.subscription.deleted"
        )
        resp = await webhook_client.post(
            WEBHOOK_URL, content=payload, headers={"stripe-signature": sign(payload)}
        )
        assert resp.status_code == 200
        user = await get_user_by_auth_id("auth-stripe-1")
        assert user["plan"] == "free"

    async def test_unknown_price_maps_to_free(self, webhook_client):
        await _seed_user(stripe_customer_id="cus_test_1", plan="pro")
        payload = subscription_event(price_id="price_unknown_999")
        resp = await webhook_client.post(
            WEBHOOK_URL, content=payload, headers={"stripe-signature": sign(payload)}
        )
        assert resp.status_code == 200
        user = await get_user_by_auth_id("auth-stripe-1")
        assert user["plan"] == "free"

    async def test_unrelated_event_type_ignored_no_write(self, webhook_client):
        await _seed_user(stripe_customer_id="cus_test_1")
        payload = json.dumps(
            {"id": "evt_inv_1", "object": "event", "type": "invoice.paid", "data": {"object": {}}}
        ).encode()
        resp = await webhook_client.post(
            WEBHOOK_URL, content=payload, headers={"stripe-signature": sign(payload)}
        )
        assert resp.status_code == 200
        user = await get_user_by_auth_id("auth-stripe-1")
        assert user["plan"] == "free"
        assert "stripe_subscription_id" not in user

    async def test_unknown_customer_acked_200(self, webhook_client):
        # No user matches — Stripe must still get a 200 so it stops retrying.
        payload = subscription_event(customer="cus_nobody")
        resp = await webhook_client.post(
            WEBHOOK_URL, content=payload, headers={"stripe-signature": sign(payload)}
        )
        assert resp.status_code == 200

    async def test_metadata_auth_id_fallback_links_customer(self, webhook_client):
        # User not yet linked to a Stripe customer (checkout #221 will set
        # metadata.auth_id) — the webhook links and updates in one pass.
        await _seed_user()
        payload = subscription_event(metadata={"auth_id": "auth-stripe-1"})
        resp = await webhook_client.post(
            WEBHOOK_URL, content=payload, headers={"stripe-signature": sign(payload)}
        )
        assert resp.status_code == 200
        user = await get_user_by_auth_id("auth-stripe-1")
        assert user["plan"] == "pro"
        assert user["stripe_customer_id"] == "cus_test_1"


class TestReplayIdempotency:
    async def test_replayed_event_id_is_noop(self, webhook_client):
        from app.db.user import update_user

        await _seed_user(stripe_customer_id="cus_test_1")
        payload = subscription_event(event_id="evt_replay_1")
        headers = {"stripe-signature": sign(payload)}

        first = await webhook_client.post(WEBHOOK_URL, content=payload, headers=headers)
        assert first.status_code == 200
        assert (await get_user_by_auth_id("auth-stripe-1"))["plan"] == "pro"

        # Flip the plan out-of-band; a replay must NOT re-apply the event.
        await update_user("auth-stripe-1", {"plan": "free"})

        replay = await webhook_client.post(WEBHOOK_URL, content=payload, headers=headers)
        assert replay.status_code == 200
        assert (await get_user_by_auth_id("auth-stripe-1"))["plan"] == "free"

    async def test_mark_event_processed_dao(self, motor_reinit_db):
        from app.db.stripe_events import mark_event_processed, unmark_event

        assert await mark_event_processed("evt_dao_1") is True
        assert await mark_event_processed("evt_dao_1") is False  # replay
        assert await mark_event_processed("evt_dao_2") is True  # independent id
        # Unmark releases the id (used when processing fails, so Stripe's retry
        # isn't misclassified as a replay).
        await unmark_event("evt_dao_1")
        assert await mark_event_processed("evt_dao_1") is True
