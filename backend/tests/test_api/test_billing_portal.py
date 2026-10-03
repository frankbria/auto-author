"""Tests for POST /api/v1/billing/portal (issue #222).

Same harness as test_billing_checkout.py: real MongoDB via auth_client_factory,
only the Stripe SDK boundary (stripe.billing_portal.Session.create) is stubbed.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import pytest
import stripe

from app.api.endpoints import billing

from app.core.config import settings
from tests.conftest import _sync_users

pytestmark = pytest.mark.asyncio

SECRET_KEY = "sk_test_dummy"


@pytest.fixture
def stripe_configured(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", SECRET_KEY)


class _StripeWire(BaseHTTPRequestHandler):
    """Wire-level Stripe stub: the real SDK talks HTTP to it via stripe.api_base."""

    def _reply(self, body, status=200):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _record(self):
        n = int(self.headers.get("Content-Length") or 0)
        form = parse_qs(self.rfile.read(n).decode()) if n else {}
        query = parse_qs(urlparse(self.path).query)
        rec = {
            "method": self.command,
            "path": urlparse(self.path).path,
            "params": {k: v[0] for k, v in {**query, **form}.items()},
        }
        self.server.calls.append(rec)
        return rec

    def do_GET(self):
        self._record()
        self._reply({"object": "list", "data": list(self.server.configs), "has_more": False})

    def do_POST(self):
        rec = self._record()
        if rec["path"].endswith("/billing_portal/configurations"):
            if self.server.fail_config:
                return self._reply({"error": {"type": "api_error", "message": "boom sk_live_abc"}}, 500)
            cfg = {
                "id": "bpc_test_001",
                "object": "billing_portal.configuration",
                "active": True,
                "metadata": {
                    k[len("metadata["):-1]: v
                    for k, v in rec["params"].items()
                    if k.startswith("metadata[")
                },
            }
            self.server.configs.append(cfg)
            return self._reply(cfg)
        self._reply(
            {
                "id": "bps_test_001",
                "object": "billing_portal.session",
                "url": "https://billing.stripe.com/p/session/bps_test_001",
            }
        )

    def log_message(self, *a):
        pass


@pytest.fixture
def portal_stub(monkeypatch):
    """Serve a Stripe wire stub; returns the recorded HTTP calls."""
    server = HTTPServer(("127.0.0.1", 0), _StripeWire)
    server.calls, server.configs, server.fail_config = [], [], False
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(stripe, "api_base", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setattr(stripe, "max_network_retries", 0)
    monkeypatch.setattr(billing, "_portal_config_id", None)
    yield server
    server.shutdown()
    server.server_close()


def _session_calls(stub):
    return [c for c in stub.calls if c["path"].endswith("/billing_portal/sessions")]


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

    sessions = _session_calls(portal_stub)
    assert len(sessions) == 1
    kwargs = sessions[0]["params"]
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
    assert _session_calls(portal_stub)[0]["params"]["customer"] == "cus_lapsed_001"


async def test_portal_rejects_user_without_stripe_customer(
    auth_client_factory, stripe_configured, portal_stub
):
    """No stripe_customer_id → nothing to manage → 409, no Stripe call."""
    client = await auth_client_factory()
    resp = await client.post("/api/v1/billing/portal")

    assert resp.status_code == 409
    assert portal_stub.calls == []


async def test_portal_fails_closed_when_unconfigured(
    auth_client_factory, portal_stub, monkeypatch
):
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "")
    client = await auth_client_factory(
        overrides={"plan": "pro", "stripe_customer_id": "cus_paid_001"}
    )
    resp = await client.post("/api/v1/billing/portal")

    assert resp.status_code == 503
    assert portal_stub.calls == []


async def test_portal_requires_auth(auth_client_factory, stripe_configured):
    client = await auth_client_factory(auth=False)
    resp = await client.post("/api/v1/billing/portal")
    assert resp.status_code == 401


async def test_portal_stripe_failure_returns_502_without_leaking(
    auth_client_factory, stripe_configured, portal_stub
):
    portal_stub.fail_config = True  # Stripe 500s with a secret-looking message
    client = await auth_client_factory(
        overrides={"plan": "pro", "stripe_customer_id": "cus_paid_001"}
    )
    resp = await client.post("/api/v1/billing/portal")

    assert resp.status_code == 502
    assert "sk_live" not in resp.text
    assert "boom" not in resp.text


async def test_portal_session_pins_a_cancel_at_period_end_configuration(
    auth_client_factory, stripe_configured, portal_stub
):
    """#771: cancellation must not depend on unversioned dashboard settings.
    The Configuration is created in code (cancel enabled, at period end — what
    the #770 disclosure promises) and the session is bound to it."""
    client = await auth_client_factory(
        overrides={"plan": "pro", "stripe_customer_id": "cus_paid_001"}
    )
    resp = await client.post("/api/v1/billing/portal")
    assert resp.status_code == 200, resp.text

    creates = [
        c for c in portal_stub.calls
        if c["method"] == "POST" and c["path"].endswith("/billing_portal/configurations")
    ]
    assert len(creates) == 1
    p = creates[0]["params"]
    assert p["features[subscription_cancel][enabled]"] == "true"
    assert p["features[subscription_cancel][mode]"] == "at_period_end"
    assert _session_calls(portal_stub)[0]["params"]["configuration"] == "bpc_test_001"


async def test_portal_reuses_existing_configuration_across_processes(
    auth_client_factory, stripe_configured, portal_stub
):
    """Idempotent: with the config already in Stripe (found by metadata) and a
    cold cache, nothing new is created; the cache then avoids even the lookup."""
    portal_stub.configs.append(
        {"id": "bpc_existing", "object": "billing_portal.configuration",
         "active": True, "metadata": dict(billing.PORTAL_CONFIG_METADATA)}
    )
    client = await auth_client_factory(
        overrides={"plan": "pro", "stripe_customer_id": "cus_paid_001"}
    )
    for _ in range(2):
        assert (await client.post("/api/v1/billing/portal")).status_code == 200

    posts = [c for c in portal_stub.calls if c["method"] == "POST"
             and c["path"].endswith("/configurations")]
    lists = [c for c in portal_stub.calls if c["method"] == "GET"]
    assert posts == []
    assert len(lists) == 1
    assert {c["params"]["configuration"] for c in _session_calls(portal_stub)} == {"bpc_existing"}
