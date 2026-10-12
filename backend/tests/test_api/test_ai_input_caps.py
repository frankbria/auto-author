"""Caps on what one request may put into a model prompt (#800).

The AI quota counts calls, not tokens, and these routes took free-form text of
any size, so a single call could carry a whole 128k context. Each field that
reaches a prompt now has a length cap, each list a count cap, and a list of
answers a total. An oversize request is answered 422 with nothing sent to the
provider and nothing left on the user's allowance.

Real routes, real MongoDB counters; the provider is stubbed at the wire.
"""

import logging

import pytest

from app.schemas.ai_input import (
    MAX_AI_CONTENT_CHARS,
    MAX_ANSWER_CHARS,
    MAX_QA_PAIRS,
    MAX_QA_TOTAL_CHARS,
    MAX_QUESTION_CHARS,
    MAX_WRITING_STYLE_CHARS,
)
from app.services.ai_service import ai_service
from tests.test_api.test_ai_quota_charging import _charged
from tests.test_api.test_rate_limit_routes import _create_book, _seed_toc, _small_toc
from tests.test_services.openai_autospec import autospec_openai_client

pytestmark = pytest.mark.asyncio

QA = {"question": "What is this chapter about?", "answer": "Getting started."}


def _pairs(count=1, question_chars=None, answer_chars=None):
    pair = dict(QA)
    if question_chars:
        pair["question"] = "q" * question_chars
    if answer_chars:
        pair["answer"] = "a" * answer_chars
    return [pair] * count


# Each list is over exactly one cap and inside the others.
OVERSIZE_ANSWER_LISTS = {
    "too many pairs": _pairs(count=MAX_QA_PAIRS + 1),
    "a question too long": _pairs(question_chars=MAX_QUESTION_CHARS + 1),
    "an answer too long": _pairs(answer_chars=MAX_ANSWER_CHARS + 1),
    "too long in total": _pairs(
        count=MAX_QA_TOTAL_CHARS // MAX_ANSWER_CHARS + 1, answer_chars=MAX_ANSWER_CHARS
    ),
}
TOO_LONG = "x" * (MAX_AI_CONTENT_CHARS + 1)

OVERSIZE_AI_REQUESTS = [
    *[("generate-toc", {"question_responses": v}, k) for k, v in OVERSIZE_ANSWER_LISTS.items()],
    *[
        ("chapters/ch1/generate-draft", {"question_responses": v}, k)
        for k, v in OVERSIZE_ANSWER_LISTS.items()
    ],
    (
        "chapters/ch1/generate-draft",
        {"question_responses": [QA], "writing_style": "s" * (MAX_WRITING_STYLE_CHARS + 1)},
        "a writing style too long",
    ),
    ("chapters/ch1/transform-style", {"content": TOO_LONG, "target_style": "professional"}, "content"),
    ("chapters/ch1/enhance-text", {"content": TOO_LONG, "enhancement_type": "clarity"}, "content"),
    ("chapters/ch1/enhance-transcription", {"content": TOO_LONG}, "content"),
]


@pytest.fixture
async def author(auth_client_factory, arm_real_ai_quota, monkeypatch):
    """A signed-in author with a book, a counted allowance and a stubbed provider."""
    arm_real_ai_quota(limit=5)
    api = await auth_client_factory(overrides={"plan": "pro"})
    book_id = await _create_book(api, with_summary=True)
    await _seed_toc(book_id, _small_toc())
    provider = autospec_openai_client()
    monkeypatch.setattr(ai_service, "client", provider)
    return api, f"/api/v1/books/{book_id}", provider.chat.completions.create


class TestAnOversizeAIRequestIsRefusedBeforeItCostsAnything:
    @pytest.mark.parametrize(
        "route, body",
        [(route, body) for route, body, _ in OVERSIZE_AI_REQUESTS],
        ids=[f"{route.split('/')[-1]}: {why}" for route, _, why in OVERSIZE_AI_REQUESTS],
    )
    async def test_it_is_answered_422_with_no_model_call_and_no_charge(self, author, route, body):
        api, book, model_call = author

        response = await api.post(f"{book}/{route}", json=body)

        assert response.status_code == 422, response.text
        assert not model_call.called
        assert await _charged() == 0

    async def test_the_refusal_neither_returns_nor_logs_the_text_it_refused(self, author, caplog):
        api, book, _ = author

        with caplog.at_level(logging.DEBUG):
            response = await api.post(
                f"{book}/chapters/ch1/transform-style",
                json={"content": TOO_LONG, "target_style": "professional"},
            )

        assert response.status_code == 422, response.text[:300]
        assert "content: String should have at most" in response.json()["error_summary"]
        assert "x" * 100 not in response.text
        assert "x" * 100 not in caplog.text

    async def test_content_exactly_at_the_cap_reaches_the_model(self, author):
        api, book, model_call = author

        response = await api.post(
            f"{book}/chapters/ch1/transform-style",
            json={"content": "x" * MAX_AI_CONTENT_CHARS, "target_style": "professional"},
        )

        assert response.status_code == 200, response.text
        assert model_call.called
        assert await _charged() == 1

    async def test_answers_exactly_at_every_cap_reach_the_model(self, author):
        api, book, model_call = author
        # 50 pairs whose questions and answers add up to the total exactly.
        per_answer = MAX_QA_TOTAL_CHARS // MAX_QA_PAIRS - len(QA["question"])
        full = _pairs(count=MAX_QA_PAIRS, answer_chars=per_answer)
        longest = _pairs(question_chars=MAX_QUESTION_CHARS, answer_chars=MAX_ANSWER_CHARS)

        for pairs in (full, longest):
            response = await api.post(
                f"{book}/chapters/ch1/generate-draft",
                json={
                    "question_responses": pairs,
                    "writing_style": "s" * MAX_WRITING_STYLE_CHARS,
                },
            )
            assert response.status_code == 200, response.text

        assert model_call.call_count == 2


class TestAnswersAreCappedWhereTheyAreSaved:
    """A saved answer comes back as model input, so it is capped at the door."""

    @pytest.mark.parametrize("pairs", OVERSIZE_ANSWER_LISTS.values(), ids=OVERSIZE_ANSWER_LISTS)
    async def test_the_toc_wizard_refuses_oversize_answers(self, author, pairs):
        api, book, _ = author

        response = await api.put(f"{book}/question-responses", json={"responses": pairs})

        assert response.status_code == 422, response.text
        saved = (await api.get(f"{book}/question-responses")).json()
        assert saved["responses"] == []

    async def test_the_toc_wizard_keeps_answers_at_the_cap(self, author):
        api, book, _ = author
        pairs = _pairs(question_chars=MAX_QUESTION_CHARS, answer_chars=MAX_ANSWER_CHARS)

        response = await api.put(f"{book}/question-responses", json={"responses": pairs})

        assert response.status_code == 200, response.text
        saved = (await api.get(f"{book}/question-responses")).json()
        assert saved["responses"] == pairs

    async def test_a_chapter_answer_over_the_cap_is_refused(self, author):
        api, book, _ = author

        response = await api.put(
            f"{book}/chapters/ch1/questions/q1/response",
            json={"response_text": "a" * (MAX_ANSWER_CHARS + 1)},
        )

        assert response.status_code == 422, response.text
        # The route answers 422 for an unknown question too; this one is about length.
        assert f"at most {MAX_ANSWER_CHARS} characters" in response.text

    async def test_a_batch_with_an_answer_over_the_cap_is_refused(self, author):
        api, book, _ = author

        response = await api.post(
            f"{book}/chapters/ch1/questions/responses/batch",
            json=[{"question_id": "q1", "response_text": "a" * (MAX_ANSWER_CHARS + 1)}],
        )

        assert response.status_code == 422, response.text
        assert f"limit of {MAX_ANSWER_CHARS} characters" in response.text
