"""The API knows it is served over https, and who is calling (#814).

nginx ends TLS and reaches the backend container through a port published on
the host's loopback, so the peer uvicorn sees is the Docker network's gateway.
uvicorn believes X-Forwarded-Proto and X-Forwarded-For only from the peers in
FORWARDED_ALLOW_IPS, which is loopback unless told otherwise: the redirect to
a trailing slash was built as http://, and the log named the gateway as the
client.

uvicorn's own middleware runs here with the list docker-compose.yml gives it.
"""

import re
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.main import app

pytestmark = pytest.mark.asyncio

REPO = Path(__file__).resolve().parents[3]
# What nginx sends: the scheme it was reached on, and its peer's address added
# to whatever X-Forwarded-For the caller sent.
FROM_NGINX = {"X-Forwarded-Proto": "https", "X-Forwarded-For": "203.0.113.7, 198.51.100.9"}


def _allowed() -> str:
    """The one list the compose files give uvicorn. An overlay that set another would be
    what runs, and these tests would go on checking the base file's."""
    found = [
        value
        for compose in sorted(REPO.glob("docker-compose*.yml"))
        for value in re.findall(r'^[^#\n]*FORWARDED_ALLOW_IPS[:=]\s*"?([^"\s]+)', compose.read_text(), re.M)
    ]
    assert len(found) == 1, f"expected one FORWARDED_ALLOW_IPS in the compose files, found {found}"
    return found[0]


async def _get_books_from(peer: str):
    """GET /api/v1/books as uvicorn would serve it to `peer`: the answer, and the client the app saw."""
    seen = {}

    async def spy(scope, receive, send):
        seen["client"] = scope.get("client")
        await app(scope, receive, send)

    served = ProxyHeadersMiddleware(spy, trusted_hosts=_allowed())
    transport = ASGITransport(app=served, client=(peer, 40000))
    async with AsyncClient(transport=transport, base_url="http://api.example.test") as client:
        response = await client.get("/api/v1/books", headers=FROM_NGINX)
    return response, seen["client"][0]


# The gateway of a Docker network: the first address of whichever range Docker gave it.
@pytest.mark.parametrize("gateway", ["172.17.0.1", "172.22.0.1", "172.31.0.1", "192.168.0.1"])
async def test_the_redirect_to_the_trailing_slash_stays_on_https(gateway):
    response, _ = await _get_books_from(gateway)

    assert response.status_code == 307
    assert response.headers["location"] == "https://api.example.test/api/v1/books/"


async def test_the_client_is_the_address_nginx_added_not_one_the_caller_sent():
    _, client = await _get_books_from("172.22.0.1")

    assert client == "198.51.100.9"


async def test_a_peer_that_is_not_the_proxy_is_not_believed():
    response, client = await _get_books_from("203.0.113.50")

    assert response.headers["location"].startswith("http://")
    assert client == "203.0.113.50"


async def test_every_answer_tells_the_browser_to_keep_using_https():
    response, _ = await _get_books_from("172.22.0.1")

    assert response.headers["strict-transport-security"] == "max-age=31536000"


@pytest.mark.parametrize(
    "peer, recorded",
    [("172.22.0.1", "198.51.100.9"), ("203.0.113.50", "203.0.113.50")],
    ids=["through the proxy", "straight from an untrusted peer"],
)
async def test_the_audit_row_records_the_client_the_proxy_named(
    auth_client_factory, monkeypatch, peer, recorded
):
    """The audit trail is evidence (#770's renewal consent among it): it must
    name the client, not the proxy, and only believe the proxy (#907)."""
    from app.api import dependencies
    from app.api.endpoints import users as users_endpoint
    from app.db import base

    api = await auth_client_factory()
    # The factory stands in for the audit; this test is about the real one.
    monkeypatch.setattr(users_endpoint, "audit_after_commit", dependencies.audit_after_commit)
    served = ProxyHeadersMiddleware(app, trusted_hosts=_allowed())
    transport = ASGITransport(app=served, client=(peer, 40000))
    async with AsyncClient(transport=transport, base_url="http://api.example.test", cookies=api.cookies) as client:
        response = await client.patch("/api/v1/users/me", json={"bio": "Small changes."}, headers=FROM_NGINX)

    assert response.status_code == 200, response.text
    row = await base._db.audit_logs.find_one({"action": "profile_update"})
    assert row["details"]["ip_address"] == recorded
    assert "ip_address" not in row  # one place for it, not a top-level null beside it
