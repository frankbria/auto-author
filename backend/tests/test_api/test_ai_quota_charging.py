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

import pytest
from starlette.requests import Request

from app.api import dependencies as deps
from app.db import base
from tests.conftest import real_get_rate_limiter
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

    async def test_a_generation_that_fails_in_the_model_call_stays_charged(
        self, auth_client_factory, arm_real_ai_quota
    ):
        """The provider may have billed for it, so the allowance is not handed back."""
        arm_real_ai_quota(limit=5)
        api = await auth_client_factory(overrides={"plan": "free"})
        book_id = await _create_book(api, with_summary=True)

        with patch(ANALYZE, new=AsyncMock(side_effect=RuntimeError("model call blew up"))):
            response = await api.post(f"/api/v1/books/{book_id}/analyze-summary")

        assert response.status_code >= 500, response.text
        assert await _charged() == 1


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
        assert ":rl:/books/{book_id}/export/markdown:" in key
        assert not any(book_id in key for book_id in books)

    async def test_a_request_with_no_matched_route_falls_back_to_its_path(
        self, motor_reinit_db, monkeypatch
    ):
        monkeypatch.setattr(deps.settings, "BYPASS_AUTH", False)
        limiter = real_get_rate_limiter(limit=5, window=60)
        request = Request({"type": "http", "path": "/somewhere/odd", "headers": [], "query_string": b""})

        await limiter(request, current_user={"auth_id": "u1"})

        [key] = await _rate_limit_keys()
        assert ":rl:/somewhere/odd:" in key
