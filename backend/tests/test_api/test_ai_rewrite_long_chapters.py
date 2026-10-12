"""Transform, enhance and transcription cleanup work on a chapter of ordinary length (#801).

The three rewrite flows ran on the default model class (gpt-4, an 8,192-token
context shared between prompt and completion) with a fixed 4,000-token
completion budget, so a chapter over about 3,000 words could not come back
whole. They now run on the long-output class with a budget taken from the
length of the text.

Sizes are measured, not guessed: 5,000 words of English prose as the editor
stores it (HTML paragraphs) is about 33,000 characters and 5,900 gpt-4o tokens.
The sample chapter here has the same density.

Real routes, real MongoDB counters; the provider is stubbed at the wire.
"""

import pytest

from app.core.config import settings
from app.schemas.ai_input import MAX_AI_CONTENT_CHARS
from app.services.ai_service import ai_service
from tests.test_api.test_ai_quota_charging import _charged
from tests.test_services.openai_autospec import autospec_openai_client

pytestmark = pytest.mark.asyncio

# A sentence with the density that was measured: 6.4 characters a word.
SENTENCE = (
    "A useful chapter states its argument early, supports it with concrete examples, "
    "and leaves the reader with something practical to try."
)
PARAGRAPH = "<p>" + " ".join([SENTENCE] * 4) + "</p>"  # 84 words
FIVE_THOUSAND_WORDS = PARAGRAPH * 60

REWRITES = [
    ("transform-style", {"target_style": "professional"}),
    ("enhance-text", {"enhancement_type": "clarity"}),
    ("enhance-transcription", {}),
]
ROUTE_IDS = [route for route, _ in REWRITES]


async def test_the_sample_chapter_is_the_size_that_was_measured():
    assert len(FIVE_THOUSAND_WORDS.replace("</p><p>", " ").split()) == 5040
    assert 32_000 <= len(FIVE_THOUSAND_WORDS) <= MAX_AI_CONTENT_CHARS


class TestAChapterOfOrdinaryLengthCanBeRewritten:
    @pytest.mark.parametrize("route, options", REWRITES, ids=ROUTE_IDS)
    async def test_five_thousand_words_go_to_the_long_output_model_with_its_whole_budget(
        self, author, route, options
    ):
        api, book, model_call = author

        response = await api.post(
            f"{book}/chapters/ch1/{route}", json={"content": FIVE_THOUSAND_WORDS, **options}
        )

        assert response.status_code == 200, response.text
        sent = model_call.call_args.kwargs
        assert sent["model"] == settings.AI_MODEL_LONG_OUTPUT
        assert sent["max_tokens"] == settings.AI_MAX_OUTPUT_TOKENS_LONG
        assert response.json()["metadata"]["model_used"] == settings.AI_MODEL_LONG_OUTPUT

    @pytest.mark.parametrize(
        "characters, budget",
        [(300, 4000), (15_000, 5000), (21_000, 7000)],
        ids=["a paragraph keeps the old budget", "15,000 characters", "21,000 characters"],
    )
    async def test_the_completion_budget_follows_the_length_of_the_text(
        self, author, characters, budget
    ):
        api, book, model_call = author

        response = await api.post(
            f"{book}/chapters/ch1/enhance-text",
            json={"content": "x" * characters, "enhancement_type": "clarity"},
        )

        assert response.status_code == 200, response.text
        assert model_call.call_args.kwargs["max_tokens"] == budget


class TestARewriteTheModelCouldNotFinishIsAFixedRefusal:
    @pytest.mark.parametrize("route, options", REWRITES, ids=ROUTE_IDS)
    async def test_a_cut_off_rewrite_is_answered_413_not_503(
        self, author, monkeypatch, route, options
    ):
        """503 says wait and retry, and the retry would be cut off at the same place."""
        api, book, _ = author
        monkeypatch.setattr(
            ai_service, "client", autospec_openai_client(content="half a", finish_reason="length")
        )

        response = await api.post(
            f"{book}/chapters/ch1/{route}", json={"content": "Some text.", **options}
        )

        assert response.status_code == 413, response.text
        detail = response.json()["detail"]
        assert detail["error_code"] == "REWRITE_TRUNCATED"
        assert "too long" in detail["message"]
        assert "half a" not in response.text
        # The provider was called, so the generation stays charged (#798).
        assert await _charged() == 1
