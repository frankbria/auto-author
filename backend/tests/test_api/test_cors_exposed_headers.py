"""The headers a page needs to read on a refusal are exposed to it (#803).

The frontend is served from another origin than the API. A browser lets its
script read only a short list of response headers across origins unless the
server names more in ``Access-Control-Expose-Headers``. Without that the page
cannot tell a quota refusal (``X-AI-Quota-Period``) from a rate limit, or read
``Retry-After``, however the client code is written.
"""

import pytest

from app.core.config import settings

pytestmark = pytest.mark.asyncio

NEEDED_BY_THE_PAGE = ["Retry-After", "X-AI-Quota-Limit", "X-AI-Quota-Period"]


async def test_a_cross_origin_response_exposes_the_refusal_headers(auth_client_factory):
    api = await auth_client_factory()
    origin = settings.BACKEND_CORS_ORIGINS[0]

    response = await api.get("/api/v1/health", headers={"Origin": origin})

    assert response.headers["access-control-allow-origin"] == origin
    exposed = [h.strip() for h in response.headers["access-control-expose-headers"].split(",")]
    assert [header for header in NEEDED_BY_THE_PAGE if header not in exposed] == []
