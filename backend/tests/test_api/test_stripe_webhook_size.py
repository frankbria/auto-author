"""The Stripe webhook checks its signature header and size before reading (#1005).

Real ASGI requests through httpx; the body is a generator that records how much
of it the server pulled, so "never read" is observed, not assumed.
"""

import pytest
import sentry_sdk

from tests.test_api import test_stripe_webhook as base
from tests.test_api.test_stripe_webhook import WEBHOOK_URL, _post_signed, sign, subscription_event

webhook_client = base.webhook_client

pytestmark = pytest.mark.asyncio

LIMIT = 1024 * 1024
CHUNK = 64 * 1024


@pytest.fixture(autouse=True)
def _no_sentry():
    # An SDK left initialised by another module's test reads small-declared
    # bodies in full to attach them to events (production sets this to never), which would mask what the app reads.
    sentry_sdk.init(max_request_body_size="never")


class RecordingBody:
    """An async body of ``chunks`` x ``size`` bytes that counts bytes the server consumed."""

    def __init__(self, chunks: int, size: int = CHUNK):
        self.chunks, self.size, self.read = chunks, size, 0

    async def __aiter__(self):
        for _ in range(self.chunks):
            self.read += self.size
            yield b"x" * self.size


async def test_missing_signature_is_rejected_without_reading_the_body(webhook_client):
    body = RecordingBody(chunks=4)
    r = await webhook_client.post(WEBHOOK_URL, content=body)
    assert r.status_code == 400
    assert r.json() == {"detail": "Missing Stripe-Signature header"}
    assert body.read == 0


async def test_oversized_content_length_is_413_without_reading_the_body(webhook_client):
    body = RecordingBody(chunks=4)
    r = await webhook_client.post(
        WEBHOOK_URL,
        content=body,
        headers={"stripe-signature": sign(b"x"), "content-length": str(LIMIT + 1)},
    )
    assert r.status_code == 413
    assert body.read == 0


async def test_lying_content_length_is_cut_off_at_the_limit(webhook_client):
    body = RecordingBody(chunks=64)  # 4 MiB actually sent
    r = await webhook_client.post(
        WEBHOOK_URL,
        content=body,
        headers={"stripe-signature": sign(b"x"), "content-length": "10"},
    )
    assert r.status_code == 413
    assert body.read <= LIMIT + CHUNK


async def test_chunked_oversize_body_is_cut_off_at_the_limit(webhook_client):
    body = RecordingBody(chunks=64)
    r = await webhook_client.post(
        WEBHOOK_URL, content=body, headers={"stripe-signature": sign(b"x")}
    )
    assert r.status_code == 413
    assert body.read <= LIMIT + CHUNK


async def test_a_normal_delivery_still_verifies_on_the_exact_bytes(webhook_client):
    r = await _post_signed(webhook_client, subscription_event(event_id="evt_size_ok"))
    assert r.status_code == 200
