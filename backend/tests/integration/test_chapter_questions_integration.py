"""
Integration tests for the chapter questions feature (issue #45).

Exercises real data flow through ``QuestionGenerationService`` against a real
local MongoDB (via the ``motor_reinit_db`` fixture from conftest): question
generation, response saving, response retrieval, and progress tracking.

The only mocked dependency is the AI service call — everything else (question
persistence, response persistence, progress aggregation) hits the database, so
these tests verify the real data flow required by the issue's acceptance
criteria. They replace an older disabled suite that imported four services
(`DraftGenerationService`, `AnalyticsService`, `QuestionProgressService`,
`QuestionResponseService`) which were never implemented — that functionality
now lives in the single `QuestionGenerationService`.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId

from app.db import base
from app.services.question_generation_service import QuestionGenerationService
from app.schemas.book import QuestionResponseCreate, ResponseStatus

USER_ID = "test-user-auth-id"
CHAPTER_ID = "chapter-1"


@pytest.fixture
def mock_ai_service():
    """AI service whose question generation returns deterministic raw questions."""
    mock = MagicMock()
    mock.generate_chapter_questions = AsyncMock(return_value=[
        {"question_text": "What is the central theme of this chapter?",
         "question_type": "theme", "difficulty": "medium"},
        {"question_text": "Who are the key characters introduced here?",
         "question_type": "character", "difficulty": "easy"},
        {"question_text": "Where and when does the action take place?",
         "question_type": "setting", "difficulty": "easy"},
    ])
    return mock


@pytest.fixture
def service(mock_ai_service):
    return QuestionGenerationService(mock_ai_service)


@pytest.fixture
async def seeded_book(motor_reinit_db):
    """Insert a book with one TOC chapter into the test DB; return (book_id, chapter_id)."""
    book_doc = {
        "_id": ObjectId(),
        "title": "Integration Test Book",
        "genre": "Technical",
        "target_audience": "Developers",
        "owner_id": USER_ID,
        "table_of_contents": {
            "chapters": [
                {
                    "id": CHAPTER_ID,
                    "title": "Chapter One",
                    "description": "Introduction chapter",
                    "content": "Some chapter content for question generation.",
                }
            ]
        },
    }
    await base.books_collection.insert_one(book_doc)
    return str(book_doc["_id"]), CHAPTER_ID


@pytest.mark.asyncio
async def test_generate_questions_persists_and_is_retrievable(service, seeded_book):
    """Generated questions are saved to the DB and can be read back."""
    book_id, chapter_id = seeded_book

    gen = await service.generate_questions_for_chapter(
        book_id=book_id, chapter_id=chapter_id, count=3, user_id=USER_ID,
    )
    assert gen.total == 3

    listed = await service.get_questions_for_chapter(
        book_id=book_id, chapter_id=chapter_id, user_id=USER_ID, limit=20,
    )
    assert listed.total == 3
    texts = {q.question_text for q in listed.questions}
    assert "What is the central theme of this chapter?" in texts


@pytest.mark.asyncio
async def test_save_and_retrieve_response(service, seeded_book):
    """A saved response round-trips through the database with a computed word count."""
    book_id, chapter_id = seeded_book
    gen = await service.generate_questions_for_chapter(
        book_id=book_id, chapter_id=chapter_id, count=3, user_id=USER_ID,
    )
    question_id = gen.questions[0].id

    saved = await service.save_question_response(
        book_id=book_id,
        chapter_id=chapter_id,
        question_id=question_id,
        response_data=QuestionResponseCreate(
            response_text="My detailed answer here.",
            status=ResponseStatus.COMPLETED,
        ),
        user_id=USER_ID,
    )
    assert saved["response_text"] == "My detailed answer here."

    fetched = await service.get_question_response(question_id, USER_ID)
    assert fetched is not None
    assert fetched["response_text"] == "My detailed answer here."
    assert fetched["word_count"] == 4


@pytest.mark.asyncio
async def test_save_response_rejects_unknown_question(service, seeded_book):
    """Saving a response for a non-existent question is rejected (real ownership check)."""
    book_id, chapter_id = seeded_book
    with pytest.raises(ValueError):
        await service.save_question_response(
            book_id=book_id,
            chapter_id=chapter_id,
            question_id=str(ObjectId()),  # valid ObjectId, but not in DB
            response_data=QuestionResponseCreate(
                response_text="Orphan answer.", status=ResponseStatus.DRAFT
            ),
            user_id=USER_ID,
        )


@pytest.mark.asyncio
async def test_progress_tracking_reflects_answers(service, seeded_book):
    """Progress aggregation reflects answered questions from the database."""
    book_id, chapter_id = seeded_book
    gen = await service.generate_questions_for_chapter(
        book_id=book_id, chapter_id=chapter_id, count=3, user_id=USER_ID,
    )

    progress = await service.get_chapter_question_progress(book_id, chapter_id, USER_ID)
    assert progress.total == 3
    assert progress.completed == 0
    assert progress.status == "not-started"

    await service.save_question_response(
        book_id=book_id,
        chapter_id=chapter_id,
        question_id=gen.questions[0].id,
        response_data=QuestionResponseCreate(
            response_text="A completed answer.", status=ResponseStatus.COMPLETED
        ),
        user_id=USER_ID,
    )

    progress2 = await service.get_chapter_question_progress(book_id, chapter_id, USER_ID)
    assert progress2.completed == 1
    assert progress2.status == "in-progress"
    assert 0.0 < progress2.progress < 1.0
