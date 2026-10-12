"""Transform, enhance and transcription cleanup work on a chapter of ordinary length (#801).

The three rewrite flows ran on the default model class (gpt-4, an 8,192-token
context shared between prompt and completion) with a fixed 4,000-token
completion budget, so a chapter over about 3,000 words could not come back
whole. They now run on the long-output class with a budget taken from the
length of the text.

Sizes are measured, not guessed: 5,000 words of English prose with its
punctuation, as the editor stores it (HTML paragraphs), is about 31,000
characters and 6,200 gpt-4o tokens. The sample chapter here has about that many
characters; it repeats one sentence, so its token count means nothing.

Real routes, real MongoDB counters; the provider is stubbed at the wire.
"""

import pytest

from app.core.config import settings
from app.schemas.ai_input import MAX_AI_CONTENT_CHARS
from app.services.ai_service import ai_service
from tests.test_api.test_ai_quota_charging import _charged
from tests.test_services.openai_autospec import autospec_openai_client

pytestmark = pytest.mark.asyncio

# A sentence with about the density that was measured: 6 characters a word.
SENTENCE = (
    "A useful chapter states its argument early, supports it with a few concrete examples, "
    "and then leaves the reader with something practical to try."
)
PARAGRAPH = "<p>" + " ".join([SENTENCE] * 4) + "</p>"  # 96 words
FIVE_THOUSAND_WORDS = PARAGRAPH * 53

REWRITES = [
    ("transform-style", {"target_style": "professional"}),
    ("enhance-text", {"enhancement_type": "clarity"}),
    ("enhance-transcription", {}),
]
ROUTE_IDS = [route for route, _ in REWRITES]


async def test_the_sample_chapter_is_the_size_that_was_measured():
    assert len(FIVE_THOUSAND_WORDS.replace("</p><p>", " ").split()) == 5088
    assert 30_000 <= len(FIVE_THOUSAND_WORDS) <= MAX_AI_CONTENT_CHARS


class TestAChapterOfOrdinaryLengthCanBeRewritten:
    @pytest.mark.parametrize("route, options", REWRITES, ids=ROUTE_IDS)
    async def test_five_thousand_words_go_to_the_long_output_model_with_its_whole_budget(
        self, author, monkeypatch, route, options
    ):
        api, book, _ = author
        # A provider that returns the chapter at its own length, as a rewrite should.
        provider = autospec_openai_client(content=FIVE_THOUSAND_WORDS)
        monkeypatch.setattr(ai_service, "client", provider)
        model_call = provider.chat.completions.create

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
        self, author, monkeypatch, characters, budget
    ):
        api, book, _ = author
        provider = autospec_openai_client(content="y" * characters)
        monkeypatch.setattr(ai_service, "client", provider)
        model_call = provider.chat.completions.create

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


def _words(count: int, word: str = "word") -> str:
    return " ".join([word] * count)


# route, options, the fewest words a rewrite of 1,000 equal words may keep
SHARES = [
    ("transform-style", {"target_style": "professional"}, 600),
    ("enhance-text", {"enhancement_type": "clarity"}, 600),
    # Cleanup removes filler, so it is allowed to lose more.
    ("enhance-transcription", {}, 400),
]


class TestARewriteThatLostMostOfTheTextIsRefused:
    """A model can condense a chapter and report a normal finish (#983). In live
    runs a 5,000-word chapter came back at 28% to 49% of its length, as a 200,
    and the page would have offered it as the finished rewrite."""

    @pytest.mark.parametrize("route, options, fewest", SHARES, ids=ROUTE_IDS)
    async def test_a_rewrite_under_the_share_is_a_413_that_says_how_much_was_lost(
        self, author, monkeypatch, route, options, fewest
    ):
        api, book, _ = author
        monkeypatch.setattr(
            ai_service, "client", autospec_openai_client(content=_words(fewest - 1, "kept"))
        )

        response = await api.post(
            f"{book}/chapters/ch1/{route}", json={"content": _words(1000), **options}
        )

        assert response.status_code == 413, response.text
        detail = response.json()["detail"]
        assert detail["error_code"] == "REWRITE_SHORTENED"
        assert f"at {fewest // 10 - 1}% of the length" in detail["message"]
        assert "kept kept" not in response.text
        # The provider was called, so the generation stays charged (#798).
        assert await _charged() == 1

    @pytest.mark.parametrize("route, options, fewest", SHARES, ids=ROUTE_IDS)
    async def test_a_rewrite_at_the_share_is_returned_with_both_word_counts(
        self, author, monkeypatch, route, options, fewest
    ):
        api, book, _ = author
        monkeypatch.setattr(
            ai_service, "client", autospec_openai_client(content=_words(fewest, "kept"))
        )

        response = await api.post(
            f"{book}/chapters/ch1/{route}", json={"content": _words(1000), **options}
        )

        assert response.status_code == 200, response.text
        counts = [v for k, v in response.json()["metadata"].items() if k.endswith("_word_count")]
        assert sorted(counts) == [fewest, 1000]

    async def test_a_short_text_may_shrink_by_any_amount(self, author, monkeypatch):
        """Under 1,000 characters the share says little: tightening a paragraph can halve it."""
        api, book, _ = author
        monkeypatch.setattr(ai_service, "client", autospec_openai_client(content=_words(20)))

        response = await api.post(
            f"{book}/chapters/ch1/enhance-text",
            json={"content": _words(249), "enhancement_type": "clarity"},  # 996 characters
        )

        assert response.status_code == 200, response.text

    async def test_markup_and_spacing_do_not_count_as_lost_text(self, author, monkeypatch):
        """The same text with its paragraphs marked up differently is not a shorter text."""
        api, book, _ = author
        lines = [_words(8)] * 250
        monkeypatch.setattr(
            ai_service, "client", autospec_openai_client(content="".join(lines).replace(" ", ""))
        )

        response = await api.post(
            f"{book}/chapters/ch1/transform-style",
            json={
                "content": "".join(f'<p class="lead">{line}</p>\n' for line in lines),
                "target_style": "professional",
            },
        )

        assert response.status_code == 200, response.text

    async def test_a_text_written_without_spaces_is_measured_too(self, author, monkeypatch):
        """Chinese, Japanese and Thai have no spaces between words, so words cannot be the measure."""
        api, book, _ = author
        chapter = "".join(f"<p>{'写' * 60}</p>" for _ in range(50))  # 3,000 characters, 1 "word"
        monkeypatch.setattr(ai_service, "client", autospec_openai_client(content="写" * 1000))

        response = await api.post(
            f"{book}/chapters/ch1/transform-style",
            json={"content": chapter, "target_style": "professional"},
        )

        assert response.status_code == 413, response.text
        assert "at 33% of the length" in response.json()["detail"]["message"]
