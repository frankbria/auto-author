"""Question regeneration reports what it did, and the parsers keep what the model wrote (#850).

Regeneration with answers preserved asked for at least three new questions even
when one needed replacing, then reported `count - deleted` as preserved, so the
chapter grew and the numbers were wrong. The question parser stripped one
character of a list marker ("10." became "0."), and the analysis parser split
suggestions on every full stop ("Dr." and "10.5" broke a sentence in two).

Real MongoDB; the model call is the only stand-in, and it returns as many
questions as it is asked for.
"""

import pytest

from app.db.base import get_collection
from app.db.questions import create_questions_batch, get_questions_for_chapter, save_question_response
from app.schemas.book import QuestionCreate, QuestionResponseCreate
from app.services.ai_service import AIService
from app.services.question_generation_service import QuestionGenerationService

pytestmark = pytest.mark.asyncio
OWNER = "owner-850"


def _question(book_id, order, text="What motivates the protagonist in this chapter"):
    return QuestionCreate(
        book_id=book_id, chapter_id="ch1", question_text=f"{text} ({order})?",
        question_type="character", difficulty="medium", category="development",
        order=order, metadata={"suggested_response_length": "200-300 words"},
    )


@pytest.fixture
def service(reinit_db):
    svc = QuestionGenerationService(AIService())

    async def model_obeys(*, book_id, count, **_):
        return [_question(book_id, 100 + i, "A fresh question about this chapter") for i in range(count)]

    svc.generate_chapter_questions = model_obeys
    return svc


async def _chapter_with(answered, unanswered):
    books = await get_collection("books")
    book_id = str((await books.insert_one({
        "title": "T", "owner_id": OWNER,
        "table_of_contents": {"chapters": [{"id": "ch1", "title": "One", "level": 1, "order": 1, "subchapters": []}]},
    })).inserted_id)
    saved = await create_questions_batch([_question(book_id, i) for i in range(answered + unanswered)], OWNER)
    for question in saved[:answered]:
        await save_question_response(question["id"], QuestionResponseCreate(response_text="An answer."), OWNER)
    return book_id


async def _stored(book_id):
    return (await get_questions_for_chapter(book_id, "ch1", OWNER, limit=50)).total


async def test_regenerating_one_unanswered_question_replaces_exactly_one(service):
    book_id = await _chapter_with(answered=2, unanswered=1)

    result = await service.regenerate_chapter_questions(book_id, "ch1", count=10, user_id=OWNER)

    assert (result.preserved_count, result.new_count, result.total) == (2, 1, 3)
    assert len(result.questions) == 1
    assert await _stored(book_id) == 3


async def test_regenerating_without_preserving_reports_the_new_set(service):
    book_id = await _chapter_with(answered=1, unanswered=3)

    result = await service.regenerate_chapter_questions(
        book_id, "ch1", count=5, user_id=OWNER, preserve_responses=False
    )

    assert (result.preserved_count, result.new_count, result.total) == (0, 5, 5)
    assert await _stored(book_id) == 5


@pytest.mark.parametrize("line, expected", [
    ("10. What changed for the narrator after the move?", "What changed for the narrator after the move?"),
    ("2) Why does the second meeting fail?", "Why does the second meeting fail?"),
    ("- Who did Dr. Reyes call first?", "Who did Dr. Reyes call first?"),
])
async def test_a_numbered_question_keeps_its_first_word(line, expected):
    questions = AIService()._parse_chapter_questions_response(line)

    assert [q["question_text"] for q in questions] == [expected]


async def test_suggestions_split_into_sentences_not_at_every_full_stop():
    text = "READINESS: Needs Work\nSUGGESTIONS: Cite Dr. Reyes on the 10.5% figure. Name the audience, e.g. new managers."

    suggestions = AIService()._parse_analysis_response(text, "A summary.")["suggestions"]

    assert suggestions == ["Cite Dr. Reyes on the 10.5% figure", "Name the audience, e.g. new managers"]


async def test_a_model_that_returns_fewer_is_reported_as_fewer(service):
    book_id = await _chapter_with(answered=1, unanswered=3)

    async def model_short(*, book_id, count, **_):
        return [_question(book_id, 100, "A fresh question about this chapter")]

    service.generate_chapter_questions = model_short
    result = await service.regenerate_chapter_questions(book_id, "ch1", count=10, user_id=OWNER)

    assert (result.preserved_count, result.new_count, result.total) == (1, 1, 2)
    assert await _stored(book_id) == 2
