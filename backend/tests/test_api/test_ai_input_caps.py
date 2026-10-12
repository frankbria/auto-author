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

from bson import ObjectId

from app.db import base
from app.schemas.ai_input import (
    MAX_AI_CONTENT_CHARS,
    MAX_ANSWER_CHARS,
    MAX_CHAPTER_DESCRIPTION_CHARS,
    MAX_CHAPTER_TITLE_CHARS,
    MAX_PROMPT_CHARS,
    MAX_QA_PAIRS,
    MAX_QA_TOTAL_CHARS,
    MAX_QUESTION_CHARS,
    MAX_WRITING_STYLE_CHARS,
)
from app.services.ai_errors import AIInvalidRequestError
from app.services.ai_service import ai_service, model_call_attempted
from tests.test_api.test_ai_quota_charging import _charged
from tests.test_api.test_rate_limit_routes import _seed_toc, _small_toc
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


def _prompt(model_call) -> str:
    """Everything the provider was sent in its one call."""
    return "".join(m["content"] for m in model_call.call_args.kwargs["messages"])


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

    async def test_content_exactly_at_the_cap_reaches_the_model(self, author, monkeypatch):
        api, book, _ = author
        # A rewrite as long as its source; a much shorter one is refused (#983).
        provider = autospec_openai_client(content="y" * MAX_AI_CONTENT_CHARS)
        monkeypatch.setattr(ai_service, "client", provider)
        model_call = provider.chat.completions.create

        response = await api.post(
            f"{book}/chapters/ch1/transform-style",
            json={"content": "x" * MAX_AI_CONTENT_CHARS, "target_style": "professional"},
        )

        assert response.status_code == 200, response.text
        assert model_call.called
        assert await _charged() == 1

    async def test_answers_exactly_at_every_cap_reach_the_model(self, author):
        api, book, model_call = author
        # A full list whose questions and answers add up to the total exactly.
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


    async def test_a_chapter_filled_by_one_batch_save_can_be_drafted(self, author):
        """The page sends every answered question, and one batch save takes 100."""
        api, book, model_call = author

        response = await api.post(
            f"{book}/chapters/ch1/generate-draft", json={"question_responses": _pairs(count=100)}
        )

        assert response.status_code == 200, response.text
        assert model_call.called


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


class TestStoredTextIsBoundedOnItsWayIntoAPrompt:
    """A request body is not the only road to the model: the book's own stored
    text goes into prompts too, and some of it was stored without a limit."""

    async def _store_chapter(self, book: str, **fields) -> None:
        toc = _small_toc()
        toc["chapters"][0].update(fields)
        await _seed_toc(book.rsplit("/", 1)[-1], toc)

    async def test_a_draft_uses_the_start_of_an_oversize_chapter_title_and_description(
        self, author
    ):
        api, book, model_call = author
        await self._store_chapter(book, title="t" * 5_000, description="d" * 300_000)

        response = await api.post(
            f"{book}/chapters/ch1/generate-draft", json={"question_responses": [QA]}
        )

        assert response.status_code == 200, response.text
        prompt = _prompt(model_call)
        assert "t" * MAX_CHAPTER_TITLE_CHARS in prompt
        assert "t" * (MAX_CHAPTER_TITLE_CHARS + 1) not in prompt
        assert "d" * MAX_CHAPTER_DESCRIPTION_CHARS in prompt
        assert "d" * (MAX_CHAPTER_DESCRIPTION_CHARS + 1) not in prompt

    async def test_chapter_questions_use_the_start_of_an_oversize_chapter_title(self, author):
        api, book, model_call = author
        await self._store_chapter(book, title="t" * 5_000)

        await api.post(f"{book}/chapters/ch1/generate-questions", json={"count": 3})

        prompt = _prompt(model_call)
        assert "t" * MAX_CHAPTER_TITLE_CHARS in prompt
        assert "t" * (MAX_CHAPTER_TITLE_CHARS + 1) not in prompt

    async def test_a_chapter_stored_without_a_description_can_still_be_drafted(self, author):
        """``description: null`` is a stored shape: nothing on the write path checks it."""
        api, book, model_call = author
        await self._store_chapter(book, description=None)

        response = await api.post(
            f"{book}/chapters/ch1/generate-draft", json={"question_responses": [QA]}
        )

        assert response.status_code == 200, response.text
        assert "Chapter Description: \n" in _prompt(model_call)

    async def test_a_chapter_stored_without_a_title_can_still_be_asked_questions(self, author):
        api, book, model_call = author
        await self._store_chapter(book, title=None)

        await api.post(f"{book}/chapters/ch1/generate-questions", json={"count": 3})

        assert 'the chapter titled "Chapter"' in _prompt(model_call)

    async def test_a_chapter_whose_stored_content_is_not_text_can_still_be_asked_questions(
        self, author
    ):
        """``PUT /toc`` passes ``content`` through unchecked, so a number can be stored."""
        api, book, model_call = author
        await self._store_chapter(book, content=123)

        await api.post(f"{book}/chapters/ch1/generate-questions", json={"count": 3})

        assert "123" in _prompt(model_call)

    async def test_answers_saved_before_the_caps_are_checked_when_the_contents_fall_back_to_them(
        self, author
    ):
        api, book, model_call = author
        await base.books_collection.update_one(
            {"_id": ObjectId(book.rsplit("/", 1)[-1])},
            {"$set": {"question_responses": {"responses": _pairs(60, answer_chars=10_000)}}},
        )

        response = await api.post(f"{book}/generate-toc", json={})

        assert response.status_code == 422, response.text
        assert not model_call.called
        assert await _charged() == 0

    async def test_a_generated_question_longer_than_an_answer_list_accepts_is_cut_when_stored(
        self, author, monkeypatch
    ):
        api, book, _ = author
        long_question = "Why " + "w" * (MAX_QUESTION_CHARS + 500) + "?"
        provider = autospec_openai_client(
            content=f"1. {long_question}\n2. Who is the reader?\n3. What should they do next?"
        )
        monkeypatch.setattr(ai_service, "client", provider)

        response = await api.post(f"{book}/generate-questions", json={})

        assert response.status_code == 200, response.text
        questions = response.json()["questions"]
        assert len(questions) == 3
        assert max(len(q) for q in questions) == MAX_QUESTION_CHARS
        # What the wizard sends back with an answer is accepted.
        saved = await api.put(
            f"{book}/question-responses",
            json={"responses": [{"question": q, "answer": "An answer."} for q in questions]},
        )
        assert saved.status_code == 200, saved.text

    async def test_no_prompt_over_the_ceiling_is_sent_whatever_road_it_came_by(self, author):
        _, _, model_call = author
        model_call_attempted.set(False)

        with pytest.raises(AIInvalidRequestError, match=str(MAX_PROMPT_CHARS)):
            await ai_service._make_openai_request(
                messages=[
                    {"role": "system", "content": "s"},
                    {"role": "user", "content": "x" * MAX_PROMPT_CHARS},
                ]
            )

        assert not model_call.called
        assert not model_call_attempted.get()

    async def test_a_prompt_at_the_ceiling_is_sent(self, author):
        _, _, model_call = author

        await ai_service._make_openai_request(
            messages=[{"role": "user", "content": "x" * MAX_PROMPT_CHARS}]
        )

        assert model_call.called
