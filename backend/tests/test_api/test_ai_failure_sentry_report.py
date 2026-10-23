"""One refused AI request is one Sentry event, and it carries no prompt (#994).

Two reporters used to see the same failure: the SDK's own model-client
integration, once per attempt, and the Starlette integration, for the 503 the
route answers. The model-client integration exists to record prompts, so it is
off; the AI transport reports the failure once, after its retries, and the 503
it caused is not reported again.

The real SDK sends to a list, and the real model client calls a port nothing
listens on.
"""

import json

import openai
import pytest
import sentry_sdk
from bson import ObjectId

from app.db import base
from app.services.ai_service import ai_service
from tests.test_handled_failure_reporting import reports  # noqa: F401 - the SDK as the app starts it
from tests.test_services.openai_autospec import asyncio_without_retry_waits

pytestmark = pytest.mark.asyncio

PROMPT = "PROMPT-SENTINEL the paragraph the author asked to rewrite"
SUMMARY = "SUMMARY-SENTINEL " + "a summary of the book that is long enough to analyse. " * 6


@pytest.fixture
def provider_down(monkeypatch):
    monkeypatch.setattr(
        ai_service, "client", openai.OpenAI(api_key="k", base_url="http://127.0.0.1:1/v1", max_retries=0)
    )
    monkeypatch.setattr("app.services.ai.transport.asyncio", asyncio_without_retry_waits())


async def _transform(api, book):
    return await api.post(
        f"{book}/chapters/ch1/transform-style", json={"content": PROMPT, "target_style": "professional"}
    )


async def _analyze(api, book):
    await base.books_collection.update_one({"_id": ObjectId(book.rsplit("/", 1)[-1])}, {"$set": {"summary": SUMMARY}})
    return await api.post(f"{book}/analyze-summary")


REFUSED = [_transform, _analyze]
IDS = ["rewrite", "summary analysis"]


class TestARefusedAIRequestIsOneEvent:
    @pytest.mark.parametrize("refuse", REFUSED, ids=IDS)
    async def test_one_event_after_every_retry(self, reports, author, provider_down, refuse):  # noqa: F811
        api, book, _ = author

        response = await refuse(api, book)

        assert response.status_code == 503, response.text
        assert len(reports) == 1, [e["exception"]["values"][-1]["type"] for e in reports]
        failures = [value["type"] for value in reports[0]["exception"]["values"]]
        assert failures[-1] == "AINetworkError" and "APIConnectionError" in failures

    @pytest.mark.parametrize("refuse", REFUSED, ids=IDS)
    async def test_the_event_carries_no_prompt(self, reports, author, provider_down, refuse):  # noqa: F811
        api, book, _ = author

        await refuse(api, book)

        assert reports, "nothing was reported, so nothing was checked"
        sent = json.dumps(reports, default=str)
        assert "PROMPT-SENTINEL" not in sent and "SUMMARY-SENTINEL" not in sent


async def test_the_model_client_integration_is_off(reports):  # noqa: F811
    assert "openai" not in sentry_sdk.get_client().integrations
