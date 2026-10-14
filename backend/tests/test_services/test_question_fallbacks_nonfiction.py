"""The questions asked about a chapter are for a non-fiction book (#835).

The product writes non-fiction. When the model returned nothing usable, the
template questions that stood in asked about the protagonist, the plot and the
setting's sensory details, and the prompt's focus hints asked the model for
"world-building" and "narrative progression". A generated question whose
``help_text`` was null was dropped without a word, by an AttributeError, and
template questions added after generated ones started their numbering again
at 1.
"""

import re
from unittest.mock import MagicMock

import pytest

from app.schemas.book import QuestionType
from app.services.question_generation_service import QuestionGenerationService

FICTION = re.compile(r"\b(protagonist|antagonist|characters?|plot|world-building|narrative)\b", re.IGNORECASE)


@pytest.fixture
def service() -> QuestionGenerationService:
    return QuestionGenerationService(MagicMock())


def _generated(text: str, **fields) -> dict:
    return {"question_text": text, "question_type": "theme", "difficulty": "medium", **fields}


class TestTheTemplateQuestionsAreForNonFiction:
    def test_none_of_them_speaks_of_a_protagonist_characters_or_a_plot(self, service):
        # Five templates for each of five types: twenty-five covers every one.
        questions = service._generate_fallback_questions("b1", "c1", "Why Habits Stick", count=25)

        assert len({q.question_text for q in questions}) == 25, "the same template was used twice, so some were not checked"
        said = [text for q in questions for text in (q.question_text, q.metadata.help_text or "", *(q.metadata.examples or []))]
        assert [text for text in said if FICTION.search(text)] == []

    def test_each_type_still_has_its_own_questions(self, service):
        for kind in QuestionType:
            questions = service._generate_fallback_questions("b1", "c1", "Why Habits Stick", count=5, focus_types=[kind])

            assert [q.question_type for q in questions] == [kind] * 5
            assert len({q.question_text for q in questions}) == 5
            assert all(q.is_fallback for q in questions)

    @pytest.mark.parametrize("focus", [
        [QuestionType.PLOT, QuestionType.PLOT],
        [QuestionType.THEME, QuestionType.PLOT, QuestionType.THEME],
    ])
    def test_a_type_named_twice_in_the_focus_does_not_get_the_same_question_twice(self, service, focus):
        questions = service._generate_fallback_questions("b1", "c1", "Why Habits Stick", count=5, focus_types=focus)

        assert len({q.question_text for q in questions}) == 5, [q.question_text for q in questions]

    def test_one_of_them_names_the_chapter(self, service):
        questions = service._generate_fallback_questions("b1", "c1", "Why Habits Stick", count=25)

        assert any("Why Habits Stick" in q.question_text for q in questions)

    def test_the_patterns_test_itself(self):
        assert FICTION.search("How does the protagonist change?")
        assert FICTION.search("What conflicts exist between Characters?")
        assert not FICTION.search("What should a reader be able to do after this chapter?")
        assert not FICTION.search("Which characteristic matters most?")


class TestTheFocusHintsAreForNonFiction:
    def test_no_focus_hint_asks_the_model_for_fiction(self, service):
        prompt = service._build_question_generation_prompt(
            "Why Habits Stick", "", {"title": "Small Changes", "genre": "Self-help"}, count=5, focus_types=list(QuestionType)
        )

        hint = re.search(r"Focus the questions primarily on (.*)", prompt).group(1)
        assert FICTION.search(hint) is None, hint
        assert len(hint.split(", ")) >= len(QuestionType), "a type has no hint"

    def test_the_prompt_says_the_book_is_non_fiction(self, service):
        prompt = service._build_question_generation_prompt("Why Habits Stick", "", {"title": "Small Changes"}, count=5)

        # This sentence, not any mention: the line that explains the type names says "non-fiction" too.
        assert "The book is non-fiction." in prompt


class TestAGeneratedQuestionWithoutHelpTextIsKept:
    @pytest.mark.parametrize("missing", [{"help_text": None}, {"help_text": None, "examples": None}, {}])
    def test_it_is_kept_and_not_replaced_by_a_template(self, service, missing):
        raw = [_generated(f"What does the reader gain from part {n} of this chapter?", **missing) for n in range(1, 4)]

        questions = service._process_generated_questions(raw, "b1", "c1", count=3)

        assert [q.question_text for q in questions] == [r["question_text"] for r in raw]
        assert [q.is_fallback for q in questions] == [False, False, False]
        assert [q.metadata.help_text for q in questions] == [None, None, None]

    def test_help_text_that_is_there_is_still_used(self, service):
        raw = [_generated(f"What does the reader gain from part {n} of this chapter?", help_text="  Think of one reader.  ") for n in range(1, 4)]

        questions = service._process_generated_questions(raw, "b1", "c1", count=3)

        assert [q.metadata.help_text for q in questions] == ["Think of one reader."] * 3


class TestQuestionsAreNumberedOnceEach:
    def test_templates_alone_are_numbered_from_one(self, service):
        questions = service._generate_fallback_questions("b1", "c1", "Why Habits Stick", count=7)

        assert [q.order for q in questions] == [1, 2, 3, 4, 5, 6, 7]

    def test_templates_added_after_generated_questions_carry_on_the_numbering(self, service):
        raw = [_generated("What is the one idea a reader should leave this chapter with?")]

        questions = service._process_generated_questions(raw, "b1", "c1", count=5, chapter_title="Why Habits Stick")

        assert [q.is_fallback for q in questions] == [False, True, True, True, True]
        assert [q.order for q in questions] == [1, 2, 3, 4, 5]

    def test_a_generated_question_that_is_dropped_leaves_no_gap(self, service):
        raw = [
            _generated("What is the one idea a reader should leave this chapter with?"),
            {"question_text": "", "question_type": "theme"},  # not a question
            _generated("Which example makes that idea easiest to believe?"),
            _generated("What will a sceptical reader object to first?"),
        ]

        questions = service._process_generated_questions(raw, "b1", "c1", count=4)

        assert [q.order for q in questions] == list(range(1, len(questions) + 1))
        assert len({q.order for q in questions}) == len(questions)
