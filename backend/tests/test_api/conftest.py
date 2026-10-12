"""Fixtures shared by the route tests in this directory."""

import pytest

from app.services.ai_service import ai_service
from tests.test_api.test_rate_limit_routes import _create_book, _seed_toc, _small_toc
from tests.test_services.openai_autospec import autospec_openai_client


@pytest.fixture
async def author(auth_client_factory, arm_real_ai_quota, monkeypatch):
    """A signed-in author with a book, a counted allowance and a stubbed provider.

    Yields the client, the book's URL and the provider's ``create`` mock.
    """
    arm_real_ai_quota(limit=5)
    api = await auth_client_factory(overrides={"plan": "pro"})
    book_id = await _create_book(api, with_summary=True)
    await _seed_toc(book_id, _small_toc())
    provider = autospec_openai_client()
    monkeypatch.setattr(ai_service, "client", provider)
    return api, f"/api/v1/books/{book_id}", provider.chat.completions.create
