"""What the AI quota charges for, and what a rate limit is keyed on (#798).

The quota used to be charged before validation, ownership and the rate
limiter ran, so a request that was refused for any of those still spent the
user's daily allowance. It now charges only a request that may have reached
the model. The rate limiter keyed on the concrete URL, so every book id was a
fresh bucket.

Real routes, real MongoDB counters; only the model call is stubbed.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import httpx
import openai
import pytest
from starlette.requests import Request

from app.api import dependencies as deps
from app.core import entitlements
from app.db import base
from app.services.ai_service import ai_service
from tests.conftest import real_get_rate_limiter
from tests.test_services.openai_autospec import autospec_openai_client
from tests.test_api.test_rate_limit_routes import (
    ANALYSIS_OK,
    _create_book,
    _seed_toc,
    _small_toc,
)

pytestmark = pytest.mark.asyncio

ANALYZE = "app.services.ai_service.ai_service.analyze_summary_for_toc"


async def _charged() -> int:
    """Generations charged today, across every user in this test's database."""
    counters = base._db.get_collection("usage_counters")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    docs = await counters.find({"_id": {"$regex": f":day:{today}$"}}).to_list(None)
    return sum(doc["count"] for doc in docs)


async def _rate_limit_keys() -> list:
    counters = base._db.get_collection("usage_counters")
    return [doc["_id"] async for doc in counters.find({"_id": {"$regex": ":rl:"}})]


class TestQuotaIsChargedOnlyForARequestThatMayHaveReachedTheModel:
    async def test_a_successful_generation_is_charged_once(
        self, auth_client_factory, arm_real_ai_quota
    ):
        arm_real_ai_quota(limit=5)
        api = await auth_client_factory(overrides={"plan": "free"})
        book_id = await _create_book(api, with_summary=True)

        with patch(ANALYZE, new=AsyncMock(return_value=dict(ANALYSIS_OK))):
            response = await api.post(f"/api/v1/books/{book_id}/analyze-summary")

        assert response.status_code == 200, response.text
        assert await _charged() == 1

    async def test_a_book_that_does_not_exist_costs_nothing(
        self, auth_client_factory, arm_real_ai_quota
    ):
        arm_real_ai_quota(limit=5)
        api = await auth_client_factory(overrides={"plan": "free"})

        response = await api.post("/api/v1/books/000000000000000000000000/analyze-summary")

        assert response.status_code == 404, response.text
        assert await _charged() == 0

    async def test_another_users_book_costs_nothing(self, auth_client_factory, arm_real_ai_quota):
        arm_real_ai_quota(limit=5)
        owner = await auth_client_factory(overrides={"plan": "free", "auth_id": "owner"})
        book_id = await _create_book(owner, with_summary=True)
        stranger = await auth_client_factory(
            overrides={"plan": "free", "auth_id": "stranger", "email": "stranger@example.com"}
        )

        response = await stranger.post(f"/api/v1/books/{book_id}/analyze-summary")

        assert response.status_code in (403, 404), response.text
        assert await _charged() == 0

    async def test_a_request_that_fails_validation_costs_nothing(
        self, auth_client_factory, arm_real_ai_quota
    ):
        arm_real_ai_quota(limit=5)
        api = await auth_client_factory(overrides={"plan": "free"})
        book_id = await _create_book(api)

        response = await api.post(
            f"/api/v1/books/{book_id}/chapters/ch1/generate-questions", json={"count": "many"}
        )

        assert response.status_code == 422, response.text
        assert await _charged() == 0

    async def test_a_request_the_rate_limiter_refuses_costs_nothing(
        self, auth_client_factory, arm_real_ai_quota, arm_real_rate_limiter
    ):
        arm_real_ai_quota(limit=5)
        arm_real_rate_limiter(1)
        api = await auth_client_factory(overrides={"plan": "free"})
        book_id = await _create_book(api, with_summary=True)
        url = f"/api/v1/books/{book_id}/analyze-summary"

        with patch(ANALYZE, new=AsyncMock(return_value=dict(ANALYSIS_OK))):
            assert (await api.post(url)).status_code == 200
            refused = await api.post(url)

        assert refused.status_code == 429, refused.text
        assert "X-RateLimit-Limit" in refused.headers
        assert await _charged() == 1

    async def test_many_requests_the_rate_limiter_refuses_cost_nothing(
        self, auth_client_factory, arm_real_ai_quota, arm_real_rate_limiter
    ):
        """A user retrying through a rate-limit window keeps the day's allowance (#883)."""
        arm_real_ai_quota(limit=10)
        arm_real_rate_limiter(1)
        api = await auth_client_factory(overrides={"plan": "free"})
        book_id = await _create_book(api, with_summary=True)
        url = f"/api/v1/books/{book_id}/analyze-summary"

        with patch(ANALYZE, new=AsyncMock(return_value=dict(ANALYSIS_OK))):
            statuses = [(await api.post(url)).status_code for _ in range(6)]

        assert statuses == [200] + [429] * 5
        assert await _charged() == 1

    async def test_a_request_the_entitlement_gate_refuses_costs_nothing(
        self, auth_client_factory, arm_real_ai_quota, monkeypatch
    ):
        """The quota charges before the gate runs, so the gate's 402 must refund (#883)."""
        arm_real_ai_quota(limit=5)
        monkeypatch.setattr(deps.settings, "PLAN_ENFORCEMENT_ENABLED", True)
        # The free plan keeps its quota but loses this one feature.
        monkeypatch.setitem(entitlements.PLAN_ENTITLEMENTS, "free", frozenset())
        api = await auth_client_factory(overrides={"plan": "free"})
        book_id = await _create_book(api, with_summary=True)

        with patch(ANALYZE, new=AsyncMock(return_value=dict(ANALYSIS_OK))) as analyze:
            response = await api.post(f"/api/v1/books/{book_id}/analyze-summary")

        assert response.status_code == 402, response.text
        assert "analyze_summary" in response.text
        analyze.assert_not_called()
        assert await _charged() == 0

    async def test_a_request_past_the_cap_is_refused_and_not_counted(
        self, auth_client_factory, arm_real_ai_quota
    ):
        """The counter used to climb with every refused attempt."""
        arm_real_ai_quota(limit=1)
        api = await auth_client_factory(overrides={"plan": "free"})
        book_id = await _create_book(api, with_summary=True)
        url = f"/api/v1/books/{book_id}/analyze-summary"

        with patch(ANALYZE, new=AsyncMock(return_value=dict(ANALYSIS_OK))):
            assert (await api.post(url)).status_code == 200
            second = await api.post(url)
            third = await api.post(url)

        assert second.status_code == third.status_code == 429
        assert second.headers["X-AI-Quota-Limit"] == "1"
        assert await _charged() == 1

    @pytest.mark.parametrize(
        "provider_error, route, expected_status",
        [
            (openai.InternalServerError, "analyze-summary", 503),
            # A 4xx too: the provider was called, whatever it answered. The same
            # holds for a draft the model truncated, which is answered 422.
            (openai.RateLimitError, "generate-questions", 429),
        ],
        ids=["provider 500", "provider rate limit"],
    )
    async def test_a_request_handed_to_the_provider_stays_charged_when_it_fails(
        self,
        auth_client_factory,
        arm_real_ai_quota,
        monkeypatch,
        provider_error,
        route,
        expected_status,
    ):
        """The provider may have billed for it, so the allowance is not handed back."""
        arm_real_ai_quota(limit=5)
        api = await auth_client_factory(overrides={"plan": "free"})
        book_id = await _create_book(api, with_summary=True)
        # Stubbed at the wire, so the service's own request path runs.
        status = 500 if provider_error is openai.InternalServerError else 429
        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        client = autospec_openai_client()
        client.chat.completions.create.side_effect = provider_error(
            "stub", response=httpx.Response(status, request=request), body={"code": "stub"}
        )
        monkeypatch.setattr(ai_service, "client", client)
        monkeypatch.setattr(ai_service, "base_delay", 0)

        response = await api.post(f"/api/v1/books/{book_id}/{route}")

        assert response.status_code == expected_status, response.text
        assert client.chat.completions.create.called
        assert await _charged() == 1

    async def test_a_refused_request_is_refunded_even_right_after_one_that_reached_the_provider(
        self, auth_client_factory, arm_real_ai_quota, monkeypatch
    ):
        """The mark belongs to one request: each runs in its own context, so
        the first one's does not carry over to the second."""
        arm_real_ai_quota(limit=5)
        api = await auth_client_factory(overrides={"plan": "free"})
        book_id = await _create_book(api, with_summary=True)
        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        client = autospec_openai_client()
        client.chat.completions.create.side_effect = openai.InternalServerError(
            "stub", response=httpx.Response(500, request=request), body={"code": "stub"}
        )
        monkeypatch.setattr(ai_service, "client", client)
        monkeypatch.setattr(ai_service, "base_delay", 0)

        reached = await api.post(f"/api/v1/books/{book_id}/analyze-summary")
        refused = await api.post("/api/v1/books/000000000000000000000000/analyze-summary")

        assert (reached.status_code, refused.status_code) == (503, 404)
        assert await _charged() == 1

    async def test_a_failure_before_any_model_call_costs_nothing_even_as_a_500(
        self, auth_client_factory, arm_real_ai_quota
    ):
        arm_real_ai_quota(limit=5)
        api = await auth_client_factory(overrides={"plan": "free"})
        book_id = await _create_book(api, with_summary=True)

        # The service method itself is replaced, so nothing is sent to a provider.
        with patch(ANALYZE, new=AsyncMock(side_effect=RuntimeError("broke before the call"))):
            response = await api.post(f"/api/v1/books/{book_id}/analyze-summary")

        assert response.status_code >= 500, response.text
        assert await _charged() == 0


class TestRateLimitsAreKeyedOnTheRouteNotTheResource:
    async def test_the_eleventh_export_across_two_books_is_refused(
        self, auth_client_factory, arm_real_rate_limiter
    ):
        api = await auth_client_factory()
        books = [await _create_book(api, title=f"Book {n}") for n in (1, 2)]
        for book_id in books:
            await _seed_toc(book_id, _small_toc())
        arm_real_rate_limiter(10)

        statuses = [
            (await api.get(f"/api/v1/books/{books[n % 2]}/export/markdown")).status_code
            for n in range(11)
        ]

        assert statuses == [200] * 10 + [429]
        # One bucket, named for the route; no book id in the key.
        [key] = await _rate_limit_keys()
        assert ":rl:GET /books/{book_id}/export/markdown:" in key
        assert not any(book_id in key for book_id in books)

    async def test_two_methods_on_one_path_have_their_own_buckets(
        self, auth_client_factory, arm_real_rate_limiter
    ):
        """GET, PATCH and DELETE /users/me shared one bucket, so loading the
        profile page a few times refused the account deletion with a 429 (#886)."""
        api = await auth_client_factory()
        arm_real_rate_limiter(2)

        reads = [(await api.get("/api/v1/users/me")).status_code for _ in range(2)]
        update = await api.patch("/api/v1/users/me", json={"bio": "Writes about small changes."})

        assert reads == [200, 200]
        assert update.status_code == 200, update.text

    async def test_a_request_with_no_matched_route_falls_back_to_its_path(
        self, motor_reinit_db, monkeypatch
    ):
        monkeypatch.setattr(deps.settings, "BYPASS_AUTH", False)
        limiter = real_get_rate_limiter(limit=5, window=60)
        request = Request({"type": "http", "method": "GET", "path": "/somewhere/odd", "headers": [], "query_string": b""})

        await limiter(request, current_user={"auth_id": "u1"})

        [key] = await _rate_limit_keys()
        assert ":rl:GET /somewhere/odd:" in key
