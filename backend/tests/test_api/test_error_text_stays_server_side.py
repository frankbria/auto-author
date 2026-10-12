"""What an error tells the client, and what it keeps for the log (#802).

A provider's error body and a database driver's error text name things a client
has no business seeing: hostnames, index and collection names, organisation
ids, whatever the upstream chose to say. They reached clients by two roads. The
three rewrite routes flattened every AI failure into ``str(e)`` inside a 503,
which also lost the rate limit's status. And the shared handlers in
``app/utils/error_handlers.py`` put ``str(error)`` into the response.

A response now carries a fixed message and an id to quote; the text is logged.
"""

import json
import logging
from unittest.mock import AsyncMock

import httpx
import openai
import pytest
from pymongo.errors import OperationFailure

from app.services.ai_service import ai_service
from app.utils.error_handlers import (
    handle_generic_error,
    handle_question_generation_error,
    handle_rating_save_error,
    handle_response_save_error,
)
from tests.test_services.openai_autospec import autospec_openai_client

pytestmark = pytest.mark.asyncio

MONGO_TEXT = (
    "E11000 duplicate key error collection: auto_author.books index: owner_id_1_title_1 "
    "dup key: { owner_id: \"a1\" }, full error: {'host': 'db1.internal.example:27017'}"
)
SECRETS_IN_MONGO_TEXT = ["E11000", "owner_id_1_title_1", "internal.example", "auto_author.books"]

PROVIDER_TEXT = (
    "This model's maximum context length is 8192 tokens, requested by organization "
    "org-Zx81kQp on tokens per min. Contact support with request req_7f3a."
)
SECRETS_IN_PROVIDER_TEXT = ["org-Zx81kQp", "req_7f3a", "maximum context length"]

REWRITES = [
    ("transform-style", {"target_style": "professional"}),
    ("enhance-text", {"enhancement_type": "clarity"}),
    ("enhance-transcription", {}),
]
ROUTE_IDS = [route for route, _ in REWRITES]


def _provider_error(kind, status):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    return kind(
        f"Error code: {status} - {{'error': {{'message': \"{PROVIDER_TEXT}\"}}}}",
        response=httpx.Response(status, request=request),
        body={"message": PROVIDER_TEXT, "code": "stub"},
    )


@pytest.fixture
def provider_fails(monkeypatch):
    """Make the provider answer every call with the given error, without the retry waits."""

    def install(error):
        client = autospec_openai_client()
        client.chat.completions.create.side_effect = error
        monkeypatch.setattr(ai_service, "client", client)
        monkeypatch.setattr("app.services.ai_service.asyncio.sleep", AsyncMock())
        return client.chat.completions.create

    return install


class TestASharedHandlerKeepsTheDriversTextOutOfTheResponse:
    @pytest.mark.parametrize(
        "build",
        [
            lambda e: handle_generic_error(e, "saving the chapter", request_id="req_1"),
            lambda e: handle_question_generation_error(e, "b1", "c1", request_id="req_1"),
            lambda e: handle_response_save_error(e, "q1", "u1", request_id="req_1"),
            lambda e: handle_rating_save_error(e, "q1", 4, request_id="req_1"),
        ],
        ids=["generic", "question generation", "response save", "rating save"],
    )
    async def test_a_database_error_becomes_a_fixed_message_with_an_id_to_quote(
        self, build, caplog
    ):
        with caplog.at_level(logging.ERROR):
            answer = build(OperationFailure(MONGO_TEXT))

        body = json.dumps(answer.detail)
        assert answer.status_code == 500
        assert [secret for secret in SECRETS_IN_MONGO_TEXT if secret in body] == []
        assert answer.detail["request_id"] == "req_1"
        # The text is not lost: it is in the log, next to the same id.
        assert "db1.internal.example" in caplog.text
        assert "req_1" in caplog.text


class TestARewriteReportsAnAIFailureLikeTheOtherAIRoutes:
    @pytest.mark.parametrize("route, options", REWRITES, ids=ROUTE_IDS)
    async def test_a_provider_rate_limit_is_a_429_with_retry_after(
        self, author, provider_fails, route, options
    ):
        api, book, _ = author
        provider_fails(_provider_error(openai.RateLimitError, 429))

        response = await api.post(
            f"{book}/chapters/ch1/{route}", json={"content": "Some text.", **options}
        )

        assert response.status_code == 429, response.text
        assert int(response.headers["Retry-After"]) > 0
        detail = response.json()["detail"]
        assert detail["error_code"] == "AI_RATE_LIMIT"
        assert detail["retry_after"] == int(response.headers["Retry-After"])
        assert [s for s in SECRETS_IN_PROVIDER_TEXT if s in response.text] == []

    @pytest.mark.parametrize("route, options", REWRITES, ids=ROUTE_IDS)
    async def test_a_provider_outage_is_a_503_without_the_providers_text(
        self, author, provider_fails, route, options
    ):
        api, book, _ = author
        provider_fails(_provider_error(openai.InternalServerError, 500))

        response = await api.post(
            f"{book}/chapters/ch1/{route}", json={"content": "Some text.", **options}
        )

        assert response.status_code == 503, response.text
        assert response.json()["detail"]["error_code"] == "AI_SERVICE_UNAVAILABLE"
        assert [s for s in SECRETS_IN_PROVIDER_TEXT if s in response.text] == []

    @pytest.mark.parametrize("route, options", REWRITES, ids=ROUTE_IDS)
    async def test_an_unexpected_failure_is_a_fixed_message(
        self, author, provider_fails, route, options, caplog
    ):
        api, book, _ = author
        provider_fails(RuntimeError(MONGO_TEXT))

        with caplog.at_level(logging.ERROR):
            response = await api.post(
                f"{book}/chapters/ch1/{route}", json={"content": "Some text.", **options}
            )

        assert response.status_code >= 500, response.text
        assert [s for s in SECRETS_IN_MONGO_TEXT if s in response.text] == []
        assert "internal.example" in caplog.text


class TestNoAIRoutePassesOnWhatTheProviderSaid:
    """The routes that already re-raised sent ``e.message`` to the client, and
    two kinds of error built that message from the provider's own text."""

    AI_ROUTES = [
        ("chapters/ch1/transform-style", {"content": "Some text.", "target_style": "professional"}),
        ("chapters/ch1/generate-draft", {"question_responses": [{"question": "Q?", "answer": "A."}]}),
        ("generate-questions", {}),
        ("generate-toc", {"question_responses": [{"question": "Q?", "answer": "A."}]}),
    ]

    @pytest.mark.parametrize("route, body", AI_ROUTES, ids=[r.split("/")[-1] for r, _ in AI_ROUTES])
    async def test_a_request_the_provider_rejects_is_a_400_with_a_fixed_message(
        self, author, provider_fails, route, body, caplog
    ):
        api, book, _ = author
        provider_fails(_provider_error(openai.BadRequestError, 400))

        with caplog.at_level(logging.ERROR):
            response = await api.post(f"{book}/{route}", json=body)

        assert response.status_code == 400, response.text
        assert response.json()["detail"]["error_code"] == "AI_INVALID_REQUEST"
        assert [s for s in SECRETS_IN_PROVIDER_TEXT if s in response.text] == []
        assert "org-Zx81kQp" in caplog.text

    @pytest.mark.parametrize(
        "kind, status",
        [(openai.BadRequestError, 400), (openai.RateLimitError, 429), (RuntimeError, None)],
        ids=["rejected request", "rate limit", "unexpected"],
    )
    async def test_summary_analysis_fails_as_its_own_503_whatever_the_provider_said(
        self, author, provider_fails, kind, status
    ):
        """The contents wizard treats a failed analysis as "no analysis" and
        carries on, so this route answers every failure the same way."""
        api, book, _ = author
        provider_fails(_provider_error(kind, status) if status else kind(PROVIDER_TEXT))

        response = await api.post(f"{book}/analyze-summary")

        assert response.status_code == 503, response.text
        assert response.json()["detail"]["error_code"] == "AI_ANALYSIS_FAILED"
        assert [s for s in SECRETS_IN_PROVIDER_TEXT if s in response.text] == []

    @pytest.mark.parametrize("route, body", AI_ROUTES, ids=[r.split("/")[-1] for r, _ in AI_ROUTES])
    async def test_a_rate_limit_carries_the_retry_after_header_on_every_ai_route(
        self, author, provider_fails, route, body
    ):
        api, book, _ = author
        provider_fails(_provider_error(openai.RateLimitError, 429))

        response = await api.post(f"{book}/{route}", json=body)

        assert response.status_code == 429, response.text
        assert int(response.headers["Retry-After"]) > 0
        assert [s for s in SECRETS_IN_PROVIDER_TEXT if s in response.text] == []
