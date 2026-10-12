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

COMPOSE = Path(__file__).resolve().parents[3] / "docker-compose.yml"
# What nginx sends: the scheme it was reached on, and its peer's address added
# to whatever X-Forwarded-For the caller sent.
FROM_NGINX = {"X-Forwarded-Proto": "https", "X-Forwarded-For": "203.0.113.7, 198.51.100.9"}


def _allowed() -> str:
    found = re.search(r'^\s*FORWARDED_ALLOW_IPS: "([^"]+)"', COMPOSE.read_text(), re.M)
    assert found, "docker-compose.yml gives the backend no FORWARDED_ALLOW_IPS"
    return found.group(1)


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
