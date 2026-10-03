"""Account deletion cancels the Stripe subscription first (#764).

Stripe is stubbed at the HTTP boundary: a local server stands in for
api.stripe.com (``stripe.api_base`` points at it), so the real SDK builds and
sends the request. Users, books and the deletion itself run on real MongoDB.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import stripe
from bson.objectid import ObjectId

from app.core.config import settings
from app.db.base import get_collection

pytestmark = pytest.mark.asyncio

SUB_ID = "sub_test_764"
OWNER = "test-auth-id-123"  # the conftest test_user's auth_id
# (path, success status): /me answers 200 with a message, /{auth_id} 204.
ROUTES = [("/api/v1/users/me", 200), (f"/api/v1/users/{OWNER}", 204)]


@pytest.fixture
def stripe_stub(monkeypatch):
    """A fake Stripe API. ``stub["fail"] = True`` answers every call with a 400."""
    stub = {"requests": [], "fail": False}

    class Handler(BaseHTTPRequestHandler):
        def do_DELETE(self):
            stub["requests"].append(
                {
                    "method": "DELETE",
                    "path": self.path,
                    "idempotency_key": self.headers.get("Idempotency-Key"),
                }
            )
            if stub["fail"]:
                status, body = 400, {
                    "error": {"type": "invalid_request_error", "message": "boom"}
                }
            else:
                sub_id = self.path.rsplit("/", 1)[-1]
                status, body = 200, {
                    "id": sub_id, "object": "subscription", "status": "canceled"
                }
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(stripe, "api_base", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_dummy")
    yield stub
    server.shutdown()
    server.server_close()


async def _seed_book(owner_id: str) -> str:
    books = await get_collection("books")
    return str((await books.insert_one({"title": "Mine", "owner_id": owner_id})).inserted_id)


@pytest.mark.parametrize("path,ok_status", ROUTES)
async def test_delete_cancels_the_stored_subscription_once(
    auth_client_factory, stripe_stub, path, ok_status
):
    client = await auth_client_factory(
        overrides={"plan": "pro", "stripe_subscription_id": SUB_ID}
    )

    resp = await client.delete(path)

    assert resp.status_code == ok_status, resp.text
    assert len(stripe_stub["requests"]) == 1
    call = stripe_stub["requests"][0]
    assert call["path"] == f"/v1/subscriptions/{SUB_ID}"
    assert call["idempotency_key"] == f"account-delete-{SUB_ID}"
    users = await get_collection("users")
    doc = await users.find_one({"auth_id": OWNER})
    assert doc["is_active"] is False


@pytest.mark.parametrize("path", ["/api/v1/users/me", f"/api/v1/users/{OWNER}"])
async def test_stripe_failure_returns_502_and_leaves_account_intact(
    auth_client_factory, stripe_stub, path
):
    stripe_stub["fail"] = True
    client = await auth_client_factory(
        overrides={"plan": "pro", "stripe_subscription_id": SUB_ID, "is_active": True}
    )
    book_id = await _seed_book(OWNER)

    resp = await client.delete(path)

    assert resp.status_code == 502, resp.text
    assert "boom" not in resp.text  # Stripe's message stays in the server log
    assert len(stripe_stub["requests"]) == 1
    users = await get_collection("users")
    doc = await users.find_one({"auth_id": OWNER})
    assert doc["is_active"] is True
    assert doc["stripe_subscription_id"] == SUB_ID  # still retryable
    books = await get_collection("books")
    assert await books.find_one({"_id": ObjectId(book_id)}) is not None


async def test_retry_after_a_later_failure_does_not_cancel_twice(
    auth_client_factory, stripe_stub, monkeypatch
):
    """Cancel succeeded, then the cascade failed: the retry must not hit Stripe
    again (its idempotency key only lasts 24h; re-cancelling a cancelled
    subscription is an error that would block the deletion forever)."""
    import app.api.endpoints.users as users_endpoint

    client = await auth_client_factory(
        overrides={"plan": "pro", "stripe_subscription_id": SUB_ID}
    )
    real_cascade = users_endpoint.delete_all_user_books

    async def _boom(auth_id):
        raise RuntimeError("simulated mongo failure")

    monkeypatch.setattr(users_endpoint, "delete_all_user_books", _boom)
    assert (await client.delete("/api/v1/users/me")).status_code == 500

    monkeypatch.setattr(users_endpoint, "delete_all_user_books", real_cascade)
    assert (await client.delete("/api/v1/users/me")).status_code == 200
    assert len(stripe_stub["requests"]) == 1


@pytest.mark.parametrize("path,ok_status", ROUTES)
async def test_user_without_subscription_makes_no_stripe_call(
    auth_client_factory, stripe_stub, path, ok_status
):
    client = await auth_client_factory()

    resp = await client.delete(path)

    assert resp.status_code == ok_status, resp.text
    assert stripe_stub["requests"] == []
