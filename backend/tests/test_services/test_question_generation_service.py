"""Unit tests for QuestionGenerationService.

Covers the generation, adaptive, prompt-building, fallback, and error-handling
paths of ``app/services/question_generation_service.py``. The AI service is
injected as a mock and the ``app.db.database`` functions the service imports are
patched at the module boundary, so these are fast, deterministic unit tests with
no real AI calls or database access.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_errors import AIRateLimitError, AIServiceError
from app.services.question_generation_service import (
    QuestionGenerationService,
    get_question_generation_service,
    RegenerationLimitError,
    QuestionNotFoundError,
)
from app.schemas.book import (
    QuestionType,
    QuestionDifficulty,
    ResponseStatus,
    QuestionResponseCreate,
    QuestionRating,
    QuestionCreate,
    Question,
    QuestionListResponse,
    QuestionProgressResponse,
    GenerateQuestionsResponse,
)

MODULE = "app.services.question_generation_service"


@pytest.fixture
def mock_ai_service():
    ai = MagicMock()
    ai.generate_chapter_questions = AsyncMock()
    return ai


@pytest.fixture
def service(mock_ai_service):
    return QuestionGenerationService(mock_ai_service)


def _saved_question_dict(qid="q1", order=1, qtype="character"):
    """A dict shaped like what create_questions_batch returns (a valid Question)."""
    return {
        "id": qid,
        "book_id": "book-1",
        "chapter_id": "ch-1",
        "question_text": "What motivates the protagonist in this chapter?",
        "question_type": qtype,
        "difficulty": "medium",
        "category": "development",
        "order": order,
        "metadata": {"suggested_response_length": "200-300 words"},
    }


# --------------------------------------------------------------------------- #
# Pure helpers
# --------------------------------------------------------------------------- #
class TestSuggestedLength:
    def test_easy_medium_hard(self, service):
        assert service._get_suggested_length(QuestionDifficulty.EASY) == "100-200 words"
        assert service._get_suggested_length(QuestionDifficulty.MEDIUM) == "200-300 words"
        # HARD branch (line 754)
        assert service._get_suggested_length(QuestionDifficulty.HARD) == "300-500 words"


class TestGetQuestionProgress:
    async def test_mixed_statuses(self, service):
        questions = [
            {"response_status": ResponseStatus.COMPLETED},
            {"response_status": ResponseStatus.DRAFT},
            {"response_status": None},
        ]
        result = await service.get_question_progress(questions)
        assert isinstance(result, QuestionProgressResponse)
        assert result.total == 3
        assert result.completed == 1
        # Regression: in_progress must survive serialization (schema field exists)
        assert result.in_progress == 1
        assert result.progress == pytest.approx(1 / 3)
        assert result.status == "in-progress"

    async def test_all_completed(self, service):
        questions = [{"response_status": ResponseStatus.COMPLETED} for _ in range(2)]
        result = await service.get_question_progress(questions)
        assert result.completed == 2
        assert result.progress == 1.0
        assert result.status == "completed"

    async def test_all_unanswered_not_started(self, service):
        questions = [{"response_status": None}, {"response_status": "not_answered"}]
        result = await service.get_question_progress(questions)
        assert result.total == 2
        assert result.completed == 0
        assert result.in_progress == 0
        assert result.progress == 0.0
        assert result.status == "not-started"

    async def test_empty_is_vacuously_complete(self, service):
        # Pre-existing behavior (mirrored in app/db/questions.py): with no questions
        # ``completed == total == 0`` so status is "completed". Documented, not asserted
        # as desired — changing it is out of scope for a coverage task.
        result = await service.get_question_progress([])
        assert result.total == 0
        assert result.progress == 0.0
        assert result.status == "completed"


class TestFallbackQuestions:
    def test_defaults_difficulty_and_focus(self, service):
        # difficulty None -> MEDIUM, focus_types empty -> all types
        questions = service._generate_fallback_questions(
            book_id="book-1",
            chapter_id="ch-1",
            chapter_title="My Chapter",
            count=5,
            difficulty=None,
            focus_types=None,
        )
        assert len(questions) == 5
        for q in questions:
            assert isinstance(q, QuestionCreate)
            assert q.difficulty == QuestionDifficulty.MEDIUM
            assert q.metadata.suggested_response_length == "200-300 words"

    def test_respects_focus_types(self, service):
        questions = service._generate_fallback_questions(
            book_id="book-1",
            chapter_id="ch-1",
            chapter_title="My Chapter",
            count=4,
            difficulty=QuestionDifficulty.HARD,
            focus_types=[QuestionType.CHARACTER, QuestionType.PLOT],
        )
        assert len(questions) == 4
        assert {q.question_type for q in questions} <= {
            QuestionType.CHARACTER,
            QuestionType.PLOT,
        }


class TestBuildPrompt:
    def test_no_content_no_context(self, service):
        prompt = service._build_question_generation_prompt(
            chapter_title="Intro",
            chapter_content="",
            book_metadata={},
            count=5,
        )
        assert "Intro" in prompt
        assert "does not have any content yet" in prompt

    def test_long_content_is_truncated(self, service):
        long_content = "x" * 6000
        prompt = service._build_question_generation_prompt(
            chapter_title="Big",
            chapter_content=long_content,
            book_metadata={},
            count=5,
        )
        assert "..." in prompt
        # the raw 6000-char block should not appear in full
        assert "x" * 6000 not in prompt

    def test_genre_audience_difficulty_focus(self, service):
        prompt = service._build_question_generation_prompt(
            chapter_title="Ch",
            chapter_content="some content",
            book_metadata={"genre": "Fantasy", "audience": "Young Adult", "title": "Bk"},
            count=5,
            difficulty=QuestionDifficulty.HARD,
            focus_types=[
                QuestionType.CHARACTER,
                QuestionType.PLOT,
                QuestionType.SETTING,
                QuestionType.THEME,
                QuestionType.RESEARCH,
            ],
        )
        assert "Fantasy" in prompt
        assert "Young Adult" in prompt  # audience branch (line 466)
        assert "challenging" in prompt  # HARD difficulty guidance (470-475)
        # focus guidance for all five types (479-494)
        assert "character development" in prompt
        assert "plot structure" in prompt
        assert "setting details" in prompt
        assert "themes" in prompt
        assert "research needs" in prompt


# --------------------------------------------------------------------------- #
# _process_generated_questions
# --------------------------------------------------------------------------- #
class TestProcessGeneratedQuestions:
    def test_empty_raw_returns_fallback(self, service):
        result = service._process_generated_questions(
            raw_questions=[],
            book_id="book-1",
            chapter_id="ch-1",
            count=5,
        )
        assert len(result) == 5  # fallback questions (line 528)
        assert all(isinstance(q, QuestionCreate) for q in result)
        assert all(q.is_fallback is True for q in result)  # tagged templates (#182)

    def test_fallback_renders_real_chapter_title(self, service):
        # N5 (#234): the PLOT template must interpolate the actual chapter title,
        # not the hardcoded "Chapter" placeholder.
        # Force the PLOT template (the only one that interpolates the title) so the
        # assertion is deterministic regardless of the default type-cycling order.
        result = service._process_generated_questions(
            raw_questions=[],
            book_id="book-1",
            chapter_id="ch-1",
            count=5,
            chapter_title="The Great Escape",
            requested_focus_types=[QuestionType.PLOT],
        )
        texts = [q.question_text for q in result]
        assert any("The Great Escape" in t for t in texts)
        assert not any("conflict in Chapter?" in t for t in texts)

    def test_mixed_ai_and_fallback_tagging(self, service):
        # One valid AI question + count=3 -> template fill; only the fill is
        # tagged, so a mixed response gives clients per-question provenance (#182).
        raw = [
            {"question_text": "A single valid AI question about the plot here?", "question_type": "plot", "difficulty": "medium"}
        ]
        result = service._process_generated_questions(
            raw_questions=raw,
            book_id="book-1",
            chapter_id="ch-1",
            count=3,
        )
        assert len(result) == 3
        assert result[0].is_fallback is False
        assert all(q.is_fallback is True for q in result[1:])

    def test_skips_short_and_unsafe_then_fills_fallback(self, service):
        raw = [
            {"question_text": "short"},  # < 10 chars -> skip (545)
            {"question_text": "This is an unsafe question text here"},  # unsafe -> skip (549)
        ]

        def fake_safety(text):
            return "unsafe" not in text

        with patch(f"{MODULE}.validate_text_safety", side_effect=fake_safety):
            result = service._process_generated_questions(
                raw_questions=raw,
                book_id="book-1",
                chapter_id="ch-1",
                count=5,
            )
        # both inputs dropped; fallback fills to >= min(3, count)
        assert len(result) >= 3

    def test_parses_all_types_and_difficulties(self, service):
        raw = [
            {"question_text": "A character question about motivation?", "question_type": "character", "difficulty": "easy"},
            {"question_text": "A plot question about the conflict here?", "question_type": "plot", "difficulty": "medium"},
            {"question_text": "A setting question about the world here?", "question_type": "setting", "difficulty": "hard"},
            {"question_text": "A theme question about the meaning here?", "question_type": "theme", "difficulty": "weird"},
            {"question_text": "A research question requiring some facts?", "question_type": "research", "difficulty": ""},
            {"question_text": "An unspecified-type question goes here?", "question_type": "bogus", "difficulty": "medium"},
        ]
        result = service._process_generated_questions(
            raw_questions=raw,
            book_id="book-1",
            chapter_id="ch-1",
            count=10,
            requested_difficulty=QuestionDifficulty.EASY,
        )
        assert len(result) == 6
        types = [q.question_type for q in result]
        assert QuestionType.CHARACTER in types
        assert QuestionType.RESEARCH in types  # research branch (561-566)
        # hard difficulty parsed (574-575); invalid -> requested EASY (577-578)
        assert result[2].difficulty == QuestionDifficulty.HARD
        assert result[3].difficulty == QuestionDifficulty.EASY

    def test_examples_non_list_becomes_empty(self, service):
        raw = [
            {
                "question_text": "A valid question about the chapter content?",
                "question_type": "character",
                "difficulty": "medium",
                "examples": "not-a-list",  # non-list -> [] (line 586)
            }
        ]
        result = service._process_generated_questions(
            raw_questions=raw,
            book_id="book-1",
            chapter_id="ch-1",
            count=3,
        )
        # first processed question has no examples
        assert result[0].metadata.examples is None

    def test_exception_during_processing_is_skipped(self, service):
        # A non-dict element makes q.get(...) raise -> caught -> continue (609-611)
        raw = ["not-a-dict", {"question_text": "A valid fallback-safe question here?", "question_type": "plot", "difficulty": "easy"}]
        result = service._process_generated_questions(
            raw_questions=raw,
            book_id="book-1",
            chapter_id="ch-1",
            count=3,
        )
        # processing didn't crash; fallback fills to >= 3
        assert len(result) >= 3


# --------------------------------------------------------------------------- #
# generate_chapter_questions (AI orchestration + fallback)
# --------------------------------------------------------------------------- #
class TestGenerateChapterQuestions:
    async def test_happy_path(self, service, mock_ai_service):
        mock_ai_service.generate_chapter_questions.return_value = [
            {"question_text": "A solid character question for testing?", "question_type": "character", "difficulty": "medium"}
        ]
        result = await service.generate_chapter_questions(
            book_id="book-1",
            chapter_id="ch-1",
            chapter_title="Ch",
            chapter_content="content",
            book_metadata={"genre": "SciFi"},
            count=3,
        )
        mock_ai_service.generate_chapter_questions.assert_awaited_once()
        assert len(result) >= 3
        assert all(isinstance(q, QuestionCreate) for q in result)

    async def test_ai_failure_falls_back(self, service, mock_ai_service):
        mock_ai_service.generate_chapter_questions.side_effect = RuntimeError("AI down")
        result = await service.generate_chapter_questions(
            book_id="book-1",
            chapter_id="ch-1",
            chapter_title="Ch",
            chapter_content="",
            book_metadata={},
            count=4,
        )
        # fallback path (404-407) — templates must be tagged so they can't
        # masquerade as AI output (#182)
        assert len(result) == 4
        assert all(isinstance(q, QuestionCreate) for q in result)
        assert all(q.is_fallback is True for q in result)

    async def test_ai_service_error_propagates(self, service, mock_ai_service):
        """A structured AI outage must raise, not silently become templates (#182)."""
        mock_ai_service.generate_chapter_questions.side_effect = AIRateLimitError("outage")
        with pytest.raises(AIServiceError):
            await service.generate_chapter_questions(
                book_id="book-1",
                chapter_id="ch-1",
                chapter_title="Ch",
                chapter_content="",
                book_metadata={},
                count=4,
            )

    async def test_ai_path_questions_not_tagged_fallback(self, service, mock_ai_service):
        mock_ai_service.generate_chapter_questions.return_value = [
            {"question_text": f"A solid AI question number {i} for testing?", "question_type": "plot", "difficulty": "medium"}
            for i in range(3)
        ]
        result = await service.generate_chapter_questions(
            book_id="book-1",
            chapter_id="ch-1",
            chapter_title="Ch",
            chapter_content="content",
            book_metadata={},
            count=3,
        )
        assert all(q.is_fallback is False for q in result)


# --------------------------------------------------------------------------- #
# generate_questions_for_chapter (full async orchestration)
# --------------------------------------------------------------------------- #
class TestGenerateQuestionsForChapter:
    async def test_ai_service_error_propagates_to_caller(self, service, mock_ai_service):
        """The orchestration layer must not re-swallow structured AI errors (#182)."""
        book = {"title": "Bk", "table_of_contents": {"chapters": []}}
        mock_ai_service.generate_chapter_questions.side_effect = AIRateLimitError("outage")
        with patch(f"{MODULE}.get_book_by_id", AsyncMock(return_value=book)):
            with pytest.raises(AIServiceError):
                await service.generate_questions_for_chapter(
                    book_id="book-1", chapter_id="ch-1", user_id="u1"
                )

    async def test_book_not_found_raises(self, service):
        with patch(f"{MODULE}.get_book_by_id", AsyncMock(return_value=None)):
            with pytest.raises(ValueError, match="Book not found"):
                await service.generate_questions_for_chapter(
                    book_id="missing", chapter_id="ch-1", user_id="u1"
                )

    async def test_happy_path_finds_subchapter_and_saves(self, service, mock_ai_service):
        book = {
            "title": "Bk",
            "genre": "Fantasy",
            "target_audience": "Adults",
            "table_of_contents": {
                "chapters": [
                    {
                        "id": "parent",
                        "title": "Parent",
                        "subchapters": [
                            {"id": "ch-1", "title": "Target", "content": "c", "description": "d"}
                        ],
                    }
                ]
            },
        }
        mock_ai_service.generate_chapter_questions.return_value = [
            {"question_text": "A good question for the saved path here?", "question_type": "plot", "difficulty": "medium"}
        ]
        saved = [_saved_question_dict("q1", 1), _saved_question_dict("q2", 2)]
        verify = QuestionListResponse(questions=[], total=2, page=1, pages=1)

        with patch(f"{MODULE}.get_book_by_id", AsyncMock(return_value=book)), \
             patch(f"{MODULE}.create_questions_batch", AsyncMock(return_value=saved)), \
             patch(f"{MODULE}.db_get_questions_for_chapter", AsyncMock(return_value=verify)):
            result = await service.generate_questions_for_chapter(
                book_id="book-1",
                chapter_id="ch-1",  # only reachable via subchapter recursion (86-89)
                count=2,
                difficulty="invalid-level",  # invalid -> MEDIUM (113-114)
                focus=["character", "bogus"],  # bogus skipped (121-122)
                current_user={"auth_id": "u1"},
            )
        assert isinstance(result, GenerateQuestionsResponse)
        assert result.total == 2

    async def test_question_conversion_error_raises(self, service, mock_ai_service):
        book = {"title": "Bk", "table_of_contents": {"chapters": []}}
        mock_ai_service.generate_chapter_questions.return_value = [
            {"question_text": "A question to drive the save path here?", "question_type": "plot", "difficulty": "easy"}
        ]
        bad_saved = [{"id": "q1"}]  # missing required Question fields -> conversion error (153-157)

        with patch(f"{MODULE}.get_book_by_id", AsyncMock(return_value=book)), \
             patch(f"{MODULE}.create_questions_batch", AsyncMock(return_value=bad_saved)):
            with pytest.raises(Exception):
                await service.generate_questions_for_chapter(
                    book_id="book-1", chapter_id="ch-1", user_id="u1"
                )

    async def test_batch_save_failure_raises(self, service, mock_ai_service):
        book = {"title": "Bk", "table_of_contents": {"chapters": []}}
        mock_ai_service.generate_chapter_questions.return_value = [
            {"question_text": "A question to drive the save path here?", "question_type": "plot", "difficulty": "easy"}
        ]
        with patch(f"{MODULE}.get_book_by_id", AsyncMock(return_value=book)), \
             patch(f"{MODULE}.create_questions_batch", AsyncMock(side_effect=RuntimeError("db boom"))):
            with pytest.raises(Exception, match="Failed to save questions"):
                await service.generate_questions_for_chapter(
                    book_id="book-1", chapter_id="ch-1", user_id="u1"
                )

    async def test_persistence_verification_mismatch_raises(self, service, mock_ai_service):
        book = {"title": "Bk", "table_of_contents": {"chapters": []}}
        mock_ai_service.generate_chapter_questions.return_value = [
            {"question_text": "A question to drive the save path here?", "question_type": "plot", "difficulty": "easy"}
        ]
        saved = [_saved_question_dict("q1", 1), _saved_question_dict("q2", 2)]
        # verification reports fewer than saved -> discrepancy (174-181)
        verify = QuestionListResponse(questions=[], total=1, page=1, pages=1)
        with patch(f"{MODULE}.get_book_by_id", AsyncMock(return_value=book)), \
             patch(f"{MODULE}.create_questions_batch", AsyncMock(return_value=saved)), \
             patch(f"{MODULE}.db_get_questions_for_chapter", AsyncMock(return_value=verify)):
            with pytest.raises(Exception, match="Failed to save questions"):
                await service.generate_questions_for_chapter(
                    book_id="book-1", chapter_id="ch-1", user_id="u1"
                )


# --------------------------------------------------------------------------- #
# regenerate_chapter_questions
# --------------------------------------------------------------------------- #
class TestRegenerate:
    async def test_generates_and_persists_before_deleting(self, service):
        """Generate-then-swap: the new batch is generated + persisted FIRST, then the
        old questions are deleted, excluding the just-created ids. new_count is the
        up-front count of unanswered questions, not the delete's return value (#234)."""
        gen_result = GenerateQuestionsResponse(
            questions=[
                Question(**_saved_question_dict("new1", order=1)),
                Question(**_saved_question_dict("new2", order=2)),
            ],
            generation_id="g",
            total=2,
        )
        ctx = {"previous_questions": ["old q"], "feedback_guidance": None}
        call_order = []

        async def fake_gen(*a, **k):
            call_order.append("generate")
            return gen_result

        async def fake_delete(*a, **k):
            call_order.append("delete")
            return 2

        with patch(f"{MODULE}.count_questions_without_responses", AsyncMock(return_value=2)), \
             patch.object(service, "_gather_regeneration_context", AsyncMock(return_value=ctx)), \
             patch.object(service, "generate_questions_for_chapter", side_effect=fake_gen) as mock_gen, \
             patch(f"{MODULE}.delete_questions_for_chapter", side_effect=fake_delete) as mock_delete:
            result = await service.regenerate_chapter_questions(
                book_id="book-1",
                chapter_id="ch-1",
                count=5,
                user_id="u1",
                preserve_responses=True,
            )

        # Generation completed before the destructive delete -> no empty-chapter window.
        assert call_order == ["generate", "delete"]
        # The freshly-created question ids are excluded from the delete.
        assert set(mock_delete.await_args.kwargs["exclude_ids"]) == {"new1", "new2"}
        # new_count is the up-front unanswered count; prior context still threaded in.
        assert mock_gen.await_args.kwargs["count"] == 2
        assert mock_gen.await_args.kwargs["previous_questions"] == ["old q"]
        assert result.new_count == 2
        assert result.preserved_count == 5 - 2

    async def test_ai_outage_leaves_existing_questions_intact(self, service):
        """The core reliability guarantee (#234): an AI outage during bulk regenerate
        must NOT reach the delete, so the chapter keeps its questions until retry."""
        ctx = {"previous_questions": [], "feedback_guidance": None}
        with patch(f"{MODULE}.count_questions_without_responses", AsyncMock(return_value=3)), \
             patch.object(service, "_gather_regeneration_context", AsyncMock(return_value=ctx)), \
             patch.object(service, "generate_questions_for_chapter",
                          AsyncMock(side_effect=AIServiceError("outage", error_code="AI_UNAVAILABLE", retryable=True))), \
             patch(f"{MODULE}.delete_questions_for_chapter", AsyncMock(return_value=0)) as mock_delete:
            with pytest.raises(AIServiceError):
                await service.regenerate_chapter_questions(
                    book_id="book-1",
                    chapter_id="ch-1",
                    count=5,
                    user_id="u1",
                    preserve_responses=True,
                )
        mock_delete.assert_not_awaited()

    async def test_nothing_to_replace_returns_empty_without_side_effects(self, service):
        """preserve_responses True with zero unanswered questions -> neither generate
        nor delete runs, empty result returned."""
        ctx = {"previous_questions": [], "feedback_guidance": None}
        with patch(f"{MODULE}.count_questions_without_responses", AsyncMock(return_value=0)), \
             patch.object(service, "_gather_regeneration_context", AsyncMock(return_value=ctx)), \
             patch.object(service, "generate_questions_for_chapter", AsyncMock()) as mock_gen, \
             patch(f"{MODULE}.delete_questions_for_chapter", AsyncMock()) as mock_delete:
            result = await service.regenerate_chapter_questions(
                book_id="book-1",
                chapter_id="ch-1",
                count=5,
                current_user={"auth_id": "u1"},
                preserve_responses=True,
            )
        assert isinstance(result, GenerateQuestionsResponse)
        assert result.total == 0
        assert result.questions == []
        mock_gen.assert_not_awaited()
        mock_delete.assert_not_awaited()

    async def test_preserve_false_replaces_full_set(self, service):
        """preserve_responses False regenerates `count` questions and deletes the whole
        old set (excluding new ids); the unanswered count is irrelevant on this path."""
        gen_result = GenerateQuestionsResponse(
            questions=[Question(**_saved_question_dict("n1", order=1))],
            generation_id="g",
            total=1,
        )
        ctx = {"previous_questions": [], "feedback_guidance": None}
        with patch(f"{MODULE}.count_questions_without_responses", AsyncMock(return_value=99)) as mock_count, \
             patch.object(service, "_gather_regeneration_context", AsyncMock(return_value=ctx)), \
             patch.object(service, "generate_questions_for_chapter", AsyncMock(return_value=gen_result)) as mock_gen, \
             patch(f"{MODULE}.delete_questions_for_chapter", AsyncMock(return_value=4)) as mock_delete:
            result = await service.regenerate_chapter_questions(
                book_id="book-1",
                chapter_id="ch-1",
                count=7,
                user_id="u1",
                preserve_responses=False,
            )
        mock_count.assert_not_awaited()  # unanswered count not consulted when discarding all
        assert mock_gen.await_args.kwargs["count"] == 7
        assert mock_delete.await_args.kwargs["preserve_with_responses"] is False
        assert set(mock_delete.await_args.kwargs["exclude_ids"]) == {"n1"}
        assert result.preserved_count == 0


# --------------------------------------------------------------------------- #
# Regeneration improvements: prompt context, feedback guidance, single-question
# --------------------------------------------------------------------------- #
class TestRegenerationImprovements:
    def test_prompt_includes_previous_questions(self, service):
        prompt = service._build_question_generation_prompt(
            chapter_title="Ch",
            chapter_content="content",
            book_metadata={},
            count=3,
            previous_questions=["What is the theme?", "Who is the villain?"],
        )
        assert "meaningfully different" in prompt
        assert "What is the theme?" in prompt
        assert "Who is the villain?" in prompt

    def test_prompt_includes_feedback_guidance(self, service):
        prompt = service._build_question_generation_prompt(
            chapter_title="Ch",
            chapter_content="content",
            book_metadata={},
            count=3,
            feedback_guidance="The author rated some earlier questions as unhelpful. Be more specific.",
        )
        assert "rated some earlier questions as unhelpful" in prompt
        assert "Be more specific" in prompt

    def test_build_feedback_guidance_none_without_low_ratings(self, service):
        assert service._build_feedback_guidance([]) is None
        assert service._build_feedback_guidance(
            [{"question_text": "q", "rating": 5, "feedback": "great"}]
        ) is None

    def test_build_feedback_guidance_summarizes_low_ratings(self, service):
        guidance = service._build_feedback_guidance([
            {"question_text": "Too vague?", "rating": 1, "feedback": "too generic"},
            {"question_text": "Fine one", "rating": 4, "feedback": None},
            {"question_text": "No feedback low", "rating": 2, "feedback": None},
        ])
        assert guidance is not None
        assert "too generic" in guidance
        assert "Too vague?" in guidance
        # 4-star question is not treated as negative signal
        assert "Fine one" not in guidance

    async def test_regenerate_single_question_success_increments_count(self, service, mock_ai_service):
        existing = _saved_question_dict(qid="q-old", order=3, qtype="character")
        existing["regeneration_count"] = 1
        book = {
            "id": "book-1", "title": "Bk", "genre": "", "target_audience": "",
            "table_of_contents": {"chapters": [{"id": "ch-1", "title": "Ch", "content": ""}]},
        }
        mock_ai_service.generate_chapter_questions.return_value = [
            {"question_text": "A brand new distinct question about the hero?", "question_type": "character", "difficulty": "medium"}
        ]
        # In-place replace keeps the same id; returns the updated doc.
        updated = _saved_question_dict(qid="q-old", order=3)
        updated["question_text"] = "A brand new distinct question about the hero?"
        updated["regeneration_count"] = 2

        with patch(f"{MODULE}.get_question_by_id", AsyncMock(return_value=existing)), \
             patch(f"{MODULE}.get_book_by_id", AsyncMock(return_value=book)), \
             patch(f"{MODULE}.db_get_questions_for_chapter",
                   AsyncMock(return_value=QuestionListResponse(questions=[existing], total=1, page=1, pages=1))), \
             patch(f"{MODULE}.db_get_ratings_for_chapter", AsyncMock(return_value=[])), \
             patch(f"{MODULE}.replace_question_in_place", AsyncMock(return_value=updated)) as mock_replace:
            result = await service.regenerate_single_question(
                book_id="book-1", chapter_id="ch-1", question_id="q-old", user_id="u1",
            )

        # CAS uses the current count as the guard, writes the incremented count + preserved slot
        mock_replace.assert_awaited_once()
        kwargs = mock_replace.await_args.kwargs
        assert kwargs["expected_regeneration_count"] == 1
        assert kwargs["new_fields"]["regeneration_count"] == 2
        assert kwargs["new_fields"]["order"] == 3
        assert result.id == "q-old"
        assert result.regeneration_count == 2

    async def test_regenerate_single_question_lost_race_raises(self, service, mock_ai_service):
        # If a concurrent regeneration already replaced the original, the CAS matches
        # no document (returns None) and this caller must abort with a not-found error.
        existing = _saved_question_dict(qid="q-old", order=1)
        book = {
            "id": "book-1", "title": "Bk", "genre": "", "target_audience": "",
            "table_of_contents": {"chapters": [{"id": "ch-1", "title": "Ch", "content": ""}]},
        }
        mock_ai_service.generate_chapter_questions.return_value = [
            {"question_text": "A distinct new question about the plot?", "question_type": "plot", "difficulty": "medium"}
        ]
        with patch(f"{MODULE}.get_question_by_id", AsyncMock(return_value=existing)), \
             patch(f"{MODULE}.get_book_by_id", AsyncMock(return_value=book)), \
             patch(f"{MODULE}.db_get_questions_for_chapter",
                   AsyncMock(return_value=QuestionListResponse(questions=[existing], total=1, page=1, pages=1))), \
             patch(f"{MODULE}.db_get_ratings_for_chapter", AsyncMock(return_value=[])), \
             patch(f"{MODULE}.replace_question_in_place", AsyncMock(return_value=None)):
            with pytest.raises(QuestionNotFoundError):
                await service.regenerate_single_question(
                    book_id="book-1", chapter_id="ch-1", question_id="q-old", user_id="u1",
                )

    async def test_generate_chapter_questions_honors_count_one(self, service, mock_ai_service):
        # Single-question regeneration relies on count=1 not being bumped to 3.
        mock_ai_service.generate_chapter_questions.return_value = [
            {"question_text": "One good question about the theme?", "question_type": "theme", "difficulty": "medium"}
        ]
        result = await service.generate_chapter_questions(
            book_id="book-1", chapter_id="ch-1", chapter_title="Ch",
            chapter_content="content", book_metadata={}, count=1,
        )
        assert len(result) == 1

    async def test_regenerate_single_question_at_limit_raises(self, service):
        existing = _saved_question_dict(qid="q-old")
        existing["regeneration_count"] = 5  # == MAX default
        with patch(f"{MODULE}.get_question_by_id", AsyncMock(return_value=existing)):
            with pytest.raises(RegenerationLimitError):
                await service.regenerate_single_question(
                    book_id="book-1", chapter_id="ch-1", question_id="q-old", user_id="u1",
                )

    async def test_regenerate_single_question_not_found_raises(self, service):
        with patch(f"{MODULE}.get_question_by_id", AsyncMock(return_value=None)):
            with pytest.raises(QuestionNotFoundError):
                await service.regenerate_single_question(
                    book_id="book-1", chapter_id="ch-1", question_id="missing", user_id="u1",
                )

    async def test_regenerate_single_question_wrong_chapter_raises(self, service):
        existing = _saved_question_dict(qid="q-old")
        existing["chapter_id"] = "different-chapter"
        with patch(f"{MODULE}.get_question_by_id", AsyncMock(return_value=existing)):
            with pytest.raises(QuestionNotFoundError):
                await service.regenerate_single_question(
                    book_id="book-1", chapter_id="ch-1", question_id="q-old", user_id="u1",
                )


# --------------------------------------------------------------------------- #
# Thin delegators + validation
# --------------------------------------------------------------------------- #
class TestDelegators:
    async def test_get_questions_for_chapter(self, service):
        resp = QuestionListResponse(questions=[], total=0, page=1, pages=0)
        with patch(f"{MODULE}.db_get_questions_for_chapter", AsyncMock(return_value=resp)) as m:
            result = await service.get_questions_for_chapter("book-1", "ch-1", "u1")
        assert result is resp
        m.assert_awaited_once()

    async def test_save_question_response_happy(self, service):
        question = {"book_id": "book-1", "chapter_id": "ch-1"}
        with patch(f"{MODULE}.get_question_by_id", AsyncMock(return_value=question)), \
             patch(f"{MODULE}.db_save_question_response", AsyncMock(return_value={"id": "r1"})) as m:
            data = QuestionResponseCreate(response_text="answer")
            result = await service.save_question_response("book-1", "ch-1", "q1", data, "u1")
        assert result == {"id": "r1"}
        m.assert_awaited_once()

    async def test_save_question_response_not_found(self, service):
        with patch(f"{MODULE}.get_question_by_id", AsyncMock(return_value=None)):
            data = QuestionResponseCreate(response_text="answer")
            with pytest.raises(ValueError, match="not found"):
                await service.save_question_response("book-1", "ch-1", "q1", data, "u1")

    async def test_save_question_response_wrong_book(self, service):
        question = {"book_id": "other", "chapter_id": "ch-1"}
        with patch(f"{MODULE}.get_question_by_id", AsyncMock(return_value=question)):
            data = QuestionResponseCreate(response_text="answer")
            with pytest.raises(ValueError, match="does not belong"):
                await service.save_question_response("book-1", "ch-1", "q1", data, "u1")

    async def test_get_question_response(self, service):
        with patch(f"{MODULE}.db_get_question_response", AsyncMock(return_value={"id": "r1"})) as m:
            result = await service.get_question_response("q1", "u1")
        assert result == {"id": "r1"}
        m.assert_awaited_once_with("q1", "u1")

    async def test_save_question_rating_happy(self, service):
        question = {"book_id": "book-1", "chapter_id": "ch-1"}
        with patch(f"{MODULE}.get_question_by_id", AsyncMock(return_value=question)), \
             patch(f"{MODULE}.db_save_question_rating", AsyncMock(return_value={"id": "rat1"})) as m:
            rating = QuestionRating(question_id="q1", user_id="u1", rating=4)
            result = await service.save_question_rating("q1", rating, "u1")
        assert result == {"id": "rat1"}
        m.assert_awaited_once()

    async def test_save_question_rating_not_found(self, service):
        with patch(f"{MODULE}.get_question_by_id", AsyncMock(return_value=None)):
            with pytest.raises(ValueError, match="not found"):
                rating = QuestionRating(question_id="q1", user_id="u1", rating=4)
                await service.save_question_rating("q1", rating, "u1")

    async def test_get_chapter_question_progress(self, service):
        prog = QuestionProgressResponse(total=1, completed=1, in_progress=0, progress=1.0, status="completed")
        with patch(f"{MODULE}.db_get_chapter_question_progress", AsyncMock(return_value=prog)) as m:
            result = await service.get_chapter_question_progress("book-1", "ch-1", "u1")
        assert result is prog
        m.assert_awaited_once()


def test_factory_returns_service():
    svc = get_question_generation_service()
    assert isinstance(svc, QuestionGenerationService)
    assert svc.ai_service is not None
