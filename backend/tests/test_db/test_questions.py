"""
Comprehensive tests for questions database operations (app/db/questions.py)

Test Coverage:
- Question retrieval with filtering
- Response storage with edit history
- Progress tracking
- Rating system
- Deletion logic
- Question lookup

Target Coverage: 85%+ (from 30%)
"""

import pytest
from datetime import datetime, timezone
from bson import ObjectId

from app.db.questions import (
    create_question,
    get_questions_for_chapter,
    save_question_response,
    get_question_response,
    save_question_rating,
    get_chapter_question_progress,
    delete_questions_for_chapter,
    get_question_by_id,
)
from app.schemas.book import (
    QuestionCreate,
    QuestionResponseCreate,
    QuestionRating,
    QuestionType,
    QuestionDifficulty,
    ResponseStatus,
    QuestionMetadata,
)


# ============================================================================
# CATEGORY 1: Question Retrieval Tests (6 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_get_questions_by_chapter_success(motor_reinit_db):
    """Test retrieving questions for a valid chapter"""
    book_id = "test_book_123"
    chapter_id = "test_chapter_123"
    user_id = "test_user_123"

    # Create 5 test questions
    for i in range(5):
        question = QuestionCreate(
            book_id=book_id,
            chapter_id=chapter_id,
            question_text=f"Test question {i+1} for character development?",
            question_type=QuestionType.CHARACTER,
            difficulty=QuestionDifficulty.MEDIUM,
            category="character",
            order=i+1,
            metadata=QuestionMetadata(
                suggested_response_length="2-3 paragraphs",
                help_text="Describe the character's motivation"
            )
        )
        await create_question(question, user_id)

    # Retrieve questions
    result = await get_questions_for_chapter(
        book_id=book_id,
        chapter_id=chapter_id,
        user_id=user_id,
        limit=10
    )

    # Verify
    assert result.total == 5
    assert len(result.questions) == 5
    assert all(q.chapter_id == chapter_id for q in result.questions)
    assert all(q.book_id == book_id for q in result.questions)
    assert result.page == 1
    assert result.pages == 1


@pytest.mark.asyncio
async def test_get_questions_empty_chapter(motor_reinit_db):
    """Test retrieving questions from a chapter with no questions"""
    book_id = "test_book_empty"
    chapter_id = "test_chapter_empty"
    user_id = "test_user_123"

    result = await get_questions_for_chapter(
        book_id=book_id,
        chapter_id=chapter_id,
        user_id=user_id,
        limit=10
    )

    assert result.total == 0
    assert len(result.questions) == 0
    assert result.pages == 0


@pytest.mark.asyncio
async def test_get_questions_filter_by_status_completed(motor_reinit_db):
    """Test filtering questions by completed status"""
    book_id = "test_book_456"
    chapter_id = "test_chapter_456"
    user_id = "test_user_456"

    # Create 3 questions
    question_ids = []
    for i in range(3):
        question = QuestionCreate(
            book_id=book_id,
            chapter_id=chapter_id,
            question_text=f"Question {i+1} about plot development?",
            question_type=QuestionType.PLOT,
            difficulty=QuestionDifficulty.MEDIUM,
            category="plot",
            order=i+1,
            metadata=QuestionMetadata(suggested_response_length="1-2 paragraphs")
        )
        q = await create_question(question, user_id)
        question_ids.append(q["id"])

    # Answer first question as completed
    response1 = QuestionResponseCreate(
        question_id=question_ids[0],
        response_text="This is a completed answer with sufficient detail.",
        status=ResponseStatus.COMPLETED
    )
    await save_question_response(question_ids[0], response1, user_id)

    # Answer second question as draft
    response2 = QuestionResponseCreate(
        question_id=question_ids[1],
        response_text="This is a draft answer.",
        status=ResponseStatus.DRAFT
    )
    await save_question_response(question_ids[1], response2, user_id)

    # Leave third question unanswered

    # Filter by completed status
    result = await get_questions_for_chapter(
        book_id=book_id,
        chapter_id=chapter_id,
        user_id=user_id,
        status="completed",
        limit=10
    )

    assert len(result.questions) == 1
    assert result.questions[0].id == question_ids[0]
    assert result.questions[0].response_status == "completed"
    assert result.questions[0].has_response is True


@pytest.mark.asyncio
async def test_get_questions_filter_by_status_draft(motor_reinit_db):
    """Test filtering questions by draft status"""
    book_id = "test_book_789"
    chapter_id = "test_chapter_789"
    user_id = "test_user_789"

    # Create 2 questions
    question_ids = []
    for i in range(2):
        question = QuestionCreate(
            book_id=book_id,
            chapter_id=chapter_id,
            question_text=f"Question {i+1} about setting?",
            question_type=QuestionType.SETTING,
            difficulty=QuestionDifficulty.EASY,
            category="setting",
            order=i+1,
            metadata=QuestionMetadata(suggested_response_length="1 paragraph")
        )
        q = await create_question(question, user_id)
        question_ids.append(q["id"])

    # Answer first question as draft
    response = QuestionResponseCreate(
        question_id=question_ids[0],
        response_text="Draft response here.",
        status=ResponseStatus.DRAFT
    )
    await save_question_response(question_ids[0], response, user_id)

    # Filter by draft status
    result = await get_questions_for_chapter(
        book_id=book_id,
        chapter_id=chapter_id,
        user_id=user_id,
        status="draft",
        limit=10
    )

    assert len(result.questions) == 1
    assert result.questions[0].id == question_ids[0]
    assert result.questions[0].response_status == "draft"


@pytest.mark.asyncio
async def test_get_questions_filter_by_status_not_answered(motor_reinit_db):
    """Test filtering questions by not_answered status"""
    book_id = "test_book_abc"
    chapter_id = "test_chapter_abc"
    user_id = "test_user_abc"

    # Create 3 questions
    question_ids = []
    for i in range(3):
        question = QuestionCreate(
            book_id=book_id,
            chapter_id=chapter_id,
            question_text=f"Question {i+1} about theme?",
            question_type=QuestionType.THEME,
            difficulty=QuestionDifficulty.HARD,
            category="theme",
            order=i+1,
            metadata=QuestionMetadata(suggested_response_length="3-4 paragraphs")
        )
        q = await create_question(question, user_id)
        question_ids.append(q["id"])

    # Answer only the first question
    response = QuestionResponseCreate(
        question_id=question_ids[0],
        response_text="Completed answer.",
        status=ResponseStatus.COMPLETED
    )
    await save_question_response(question_ids[0], response, user_id)

    # Filter by not_answered status
    result = await get_questions_for_chapter(
        book_id=book_id,
        chapter_id=chapter_id,
        user_id=user_id,
        status="not_answered",
        limit=10
    )

    # Should return 2 unanswered questions
    assert len(result.questions) == 2
    assert all(q.response_status == "not_answered" for q in result.questions)
    assert all(q.has_response is False for q in result.questions)


@pytest.mark.asyncio
async def test_get_questions_pagination(motor_reinit_db):
    """Test pagination of question results"""
    book_id = "test_book_page"
    chapter_id = "test_chapter_page"
    user_id = "test_user_page"

    # Create 15 questions
    for i in range(15):
        question = QuestionCreate(
            book_id=book_id,
            chapter_id=chapter_id,
            question_text=f"Question {i+1} for pagination test?",
            question_type=QuestionType.RESEARCH,
            difficulty=QuestionDifficulty.MEDIUM,
            category="research",
            order=i+1,
            metadata=QuestionMetadata(suggested_response_length="1 paragraph")
        )
        await create_question(question, user_id)

    # Get first page (limit 10)
    page1 = await get_questions_for_chapter(
        book_id=book_id,
        chapter_id=chapter_id,
        user_id=user_id,
        page=1,
        limit=10
    )

    # Page 1 returns 10 questions (first page limit)
    assert len(page1.questions) == 10
    assert page1.page == 1
    # Note: total and pages are based on the paginated result, not the full dataset
    assert page1.total == 10

    # Get second page (limit 10)
    page2 = await get_questions_for_chapter(
        book_id=book_id,
        chapter_id=chapter_id,
        user_id=user_id,
        page=2,
        limit=10
    )

    # Page 2 returns the remaining 5 questions
    assert len(page2.questions) == 5
    assert page2.page == 2
    assert page2.total == 5


# ============================================================================
# CATEGORY 2: Response Storage Tests (5 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_save_response_create_new(motor_reinit_db):
    """Test creating a new question response"""
    book_id = "test_book_resp1"
    chapter_id = "test_chapter_resp1"
    user_id = "test_user_resp1"

    # Create a question
    question = QuestionCreate(
        book_id=book_id,
        chapter_id=chapter_id,
        question_text="What is the main character's motivation?",
        question_type=QuestionType.CHARACTER,
        difficulty=QuestionDifficulty.MEDIUM,
        category="character",
        order=1,
        metadata=QuestionMetadata(suggested_response_length="2-3 paragraphs")
    )
    q = await create_question(question, user_id)
    question_id = q["id"]

    # Save a new response
    response_text = "The main character is motivated by a desire to find their lost family."
    response = QuestionResponseCreate(
        question_id=question_id,
        response_text=response_text,
        status=ResponseStatus.DRAFT
    )
    saved_response = await save_question_response(question_id, response, user_id)

    # Verify
    assert saved_response is not None
    assert saved_response["question_id"] == question_id
    assert saved_response["user_id"] == user_id
    assert saved_response["response_text"] == response_text
    assert saved_response["status"] == ResponseStatus.DRAFT
    assert saved_response["word_count"] == len(response_text.split())
    assert "id" in saved_response
    assert "created_at" in saved_response
    assert "metadata" in saved_response
    assert saved_response["metadata"]["edit_history"] == []


@pytest.mark.asyncio
async def test_save_response_update_existing(motor_reinit_db):
    """Test updating an existing question response"""
    book_id = "test_book_resp2"
    chapter_id = "test_chapter_resp2"
    user_id = "test_user_resp2"

    # Create a question
    question = QuestionCreate(
        book_id=book_id,
        chapter_id=chapter_id,
        question_text="Describe the setting of the story?",
        question_type=QuestionType.SETTING,
        difficulty=QuestionDifficulty.EASY,
        category="setting",
        order=1,
        metadata=QuestionMetadata(suggested_response_length="1-2 paragraphs")
    )
    q = await create_question(question, user_id)
    question_id = q["id"]

    # Save initial response
    response1 = QuestionResponseCreate(
        question_id=question_id,
        response_text="Initial response with five words.",
        status=ResponseStatus.DRAFT
    )
    saved1 = await save_question_response(question_id, response1, user_id)
    initial_word_count = saved1["word_count"]

    # Update the response
    response2 = QuestionResponseCreate(
        question_id=question_id,
        response_text="Updated response with many more words to test word count calculation.",
        status=ResponseStatus.COMPLETED
    )
    saved2 = await save_question_response(question_id, response2, user_id)

    # Verify update
    assert saved2["id"] == saved1["id"]  # Same ID means update
    assert saved2["response_text"] != saved1["response_text"]
    assert saved2["status"] == ResponseStatus.COMPLETED
    assert saved2["word_count"] > initial_word_count

    # Verify edit history was tracked
    assert len(saved2["metadata"]["edit_history"]) == 1
    assert saved2["metadata"]["edit_history"][0]["word_count"] == initial_word_count


@pytest.mark.asyncio
async def test_save_response_edit_history_tracking(motor_reinit_db):
    """Test that response edits are tracked in history"""
    book_id = "test_book_hist"
    chapter_id = "test_chapter_hist"
    user_id = "test_user_hist"

    # Create a question
    question = QuestionCreate(
        book_id=book_id,
        chapter_id=chapter_id,
        question_text="What themes are present in the story?",
        question_type=QuestionType.THEME,
        difficulty=QuestionDifficulty.HARD,
        category="theme",
        order=1,
        metadata=QuestionMetadata(suggested_response_length="3-4 paragraphs")
    )
    q = await create_question(question, user_id)
    question_id = q["id"]

    # Save initial response
    response1 = QuestionResponseCreate(
        question_id=question_id,
        response_text="First draft response.",
        status=ResponseStatus.DRAFT
    )
    await save_question_response(question_id, response1, user_id)

    # Edit 1
    response2 = QuestionResponseCreate(
        question_id=question_id,
        response_text="Second draft with more detail.",
        status=ResponseStatus.DRAFT
    )
    await save_question_response(question_id, response2, user_id)

    # Edit 2
    response3 = QuestionResponseCreate(
        question_id=question_id,
        response_text="Final response with complete analysis and thorough examination.",
        status=ResponseStatus.COMPLETED
    )
    saved3 = await save_question_response(question_id, response3, user_id)

    # Verify edit history has 2 entries (initial + first edit)
    assert len(saved3["metadata"]["edit_history"]) == 2
    assert all("timestamp" in entry for entry in saved3["metadata"]["edit_history"])
    assert all("word_count" in entry for entry in saved3["metadata"]["edit_history"])


@pytest.mark.asyncio
async def test_get_question_response_exists(motor_reinit_db):
    """Test retrieving an existing question response"""
    book_id = "test_book_get"
    chapter_id = "test_chapter_get"
    user_id = "test_user_get"

    # Create question and response
    question = QuestionCreate(
        book_id=book_id,
        chapter_id=chapter_id,
        question_text="Describe the plot structure?",
        question_type=QuestionType.PLOT,
        difficulty=QuestionDifficulty.MEDIUM,
        category="plot",
        order=1,
        metadata=QuestionMetadata(suggested_response_length="2-3 paragraphs")
    )
    q = await create_question(question, user_id)
    question_id = q["id"]

    response = QuestionResponseCreate(
        question_id=question_id,
        response_text="The plot follows a three-act structure.",
        status=ResponseStatus.COMPLETED
    )
    saved = await save_question_response(question_id, response, user_id)

    # Retrieve the response
    retrieved = await get_question_response(question_id, user_id)

    assert retrieved is not None
    assert retrieved["id"] == saved["id"]
    assert retrieved["question_id"] == question_id
    assert retrieved["response_text"] == response.response_text


@pytest.mark.asyncio
async def test_get_question_response_not_found(motor_reinit_db):
    """Test retrieving a non-existent question response returns None"""
    question_id = "nonexistent_question_id"
    user_id = "test_user_notfound"

    result = await get_question_response(question_id, user_id)

    assert result is None


# ============================================================================
# CATEGORY 3: Progress Tracking Tests (4 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_progress_not_started(motor_reinit_db):
    """Test progress calculation when no questions are answered"""
    book_id = "test_book_prog0"
    chapter_id = "test_chapter_prog0"
    user_id = "test_user_prog0"

    # Create 5 questions, no responses
    for i in range(5):
        question = QuestionCreate(
            book_id=book_id,
            chapter_id=chapter_id,
            question_text=f"Unanswered question {i+1}?",
            question_type=QuestionType.CHARACTER,
            difficulty=QuestionDifficulty.MEDIUM,
            category="character",
            order=i+1,
            metadata=QuestionMetadata(suggested_response_length="1 paragraph")
        )
        await create_question(question, user_id)

    # Get progress
    progress = await get_chapter_question_progress(book_id, chapter_id, user_id)

    assert progress.total == 5
    assert progress.completed == 0
    assert progress.in_progress == 0
    assert progress.progress == 0.0
    assert progress.status == "not-started"


@pytest.mark.asyncio
async def test_progress_in_progress(motor_reinit_db):
    """Test progress calculation when some questions are answered"""
    book_id = "test_book_prog50"
    chapter_id = "test_chapter_prog50"
    user_id = "test_user_prog50"

    # Create 10 questions
    question_ids = []
    for i in range(10):
        question = QuestionCreate(
            book_id=book_id,
            chapter_id=chapter_id,
            question_text=f"Progress test question {i+1}?",
            question_type=QuestionType.PLOT,
            difficulty=QuestionDifficulty.MEDIUM,
            category="plot",
            order=i+1,
            metadata=QuestionMetadata(suggested_response_length="1-2 paragraphs")
        )
        q = await create_question(question, user_id)
        question_ids.append(q["id"])

    # Complete 5 questions
    for qid in question_ids[:5]:
        response = QuestionResponseCreate(
            question_id=qid,
            response_text="Completed answer for progress test.",
            status=ResponseStatus.COMPLETED
        )
        await save_question_response(qid, response, user_id)

    # Draft 3 questions
    for qid in question_ids[5:8]:
        response = QuestionResponseCreate(
            question_id=qid,
            response_text="Draft answer.",
            status=ResponseStatus.DRAFT
        )
        await save_question_response(qid, response, user_id)

    # Get progress
    progress = await get_chapter_question_progress(book_id, chapter_id, user_id)

    assert progress.total == 10
    assert progress.completed == 5
    assert progress.in_progress == 3
    assert progress.progress == 0.5  # 5/10 = 50%
    assert progress.status == "in-progress"


@pytest.mark.asyncio
async def test_progress_completed(motor_reinit_db):
    """Test progress calculation when all questions are completed"""
    book_id = "test_book_prog100"
    chapter_id = "test_chapter_prog100"
    user_id = "test_user_prog100"

    # Create 5 questions
    question_ids = []
    for i in range(5):
        question = QuestionCreate(
            book_id=book_id,
            chapter_id=chapter_id,
            question_text=f"Complete test question {i+1}?",
            question_type=QuestionType.RESEARCH,
            difficulty=QuestionDifficulty.EASY,
            category="research",
            order=i+1,
            metadata=QuestionMetadata(suggested_response_length="1 paragraph")
        )
        q = await create_question(question, user_id)
        question_ids.append(q["id"])

    # Complete all questions
    for qid in question_ids:
        response = QuestionResponseCreate(
            question_id=qid,
            response_text="Completed answer with sufficient detail for testing.",
            status=ResponseStatus.COMPLETED
        )
        await save_question_response(qid, response, user_id)

    # Get progress
    progress = await get_chapter_question_progress(book_id, chapter_id, user_id)

    assert progress.total == 5
    assert progress.completed == 5
    assert progress.in_progress == 0
    assert progress.progress == 1.0  # 100%
    assert progress.status == "completed"


@pytest.mark.asyncio
async def test_progress_no_questions(motor_reinit_db):
    """Test progress calculation when chapter has no questions"""
    book_id = "test_book_noquestions"
    chapter_id = "test_chapter_noquestions"
    user_id = "test_user_noquestions"

    # Don't create any questions

    # Get progress
    progress = await get_chapter_question_progress(book_id, chapter_id, user_id)

    assert progress.total == 0
    assert progress.completed == 0
    assert progress.in_progress == 0
    assert progress.progress == 0.0
    assert progress.status == "not-started"


# ============================================================================
# CATEGORY 4: Rating System Tests (2 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_save_question_rating_create_new(motor_reinit_db):
    """Test creating a new question rating"""
    question_id = "test_question_rating1"
    user_id = "test_user_rating1"

    rating_data = QuestionRating(
        question_id=question_id,
        user_id=user_id,
        rating=5,
        feedback="Excellent question, very helpful!"
    )

    saved_rating = await save_question_rating(question_id, rating_data, user_id)

    assert saved_rating is not None
    assert saved_rating["question_id"] == question_id
    assert saved_rating["user_id"] == user_id
    assert saved_rating["rating"] == 5
    assert saved_rating["feedback"] == "Excellent question, very helpful!"
    assert "id" in saved_rating
    assert "created_at" in saved_rating


@pytest.mark.asyncio
async def test_save_question_rating_update_existing(motor_reinit_db):
    """Test updating an existing question rating"""
    question_id = "test_question_rating2"
    user_id = "test_user_rating2"

    # Create initial rating
    rating1 = QuestionRating(
        question_id=question_id,
        user_id=user_id,
        rating=3,
        feedback="Okay question."
    )
    saved1 = await save_question_rating(question_id, rating1, user_id)

    # Update the rating
    rating2 = QuestionRating(
        question_id=question_id,
        user_id=user_id,
        rating=5,
        feedback="Actually, this is a great question!"
    )
    saved2 = await save_question_rating(question_id, rating2, user_id)

    # Verify update
    assert saved2["id"] == saved1["id"]  # Same ID means update
    assert saved2["rating"] == 5
    assert saved2["feedback"] == "Actually, this is a great question!"


# ============================================================================
# CATEGORY 5: Deletion Logic Tests (2 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_delete_questions_preserve_with_responses(motor_reinit_db):
    """Test deleting questions while preserving those with responses"""
    book_id = "test_book_del1"
    chapter_id = "test_chapter_del1"
    user_id = "test_user_del1"

    # Create 5 questions
    question_ids = []
    for i in range(5):
        question = QuestionCreate(
            book_id=book_id,
            chapter_id=chapter_id,
            question_text=f"Deletion test question {i+1}?",
            question_type=QuestionType.CHARACTER,
            difficulty=QuestionDifficulty.MEDIUM,
            category="character",
            order=i+1,
            metadata=QuestionMetadata(suggested_response_length="1 paragraph")
        )
        q = await create_question(question, user_id)
        question_ids.append(q["id"])

    # Answer first 2 questions
    for qid in question_ids[:2]:
        response = QuestionResponseCreate(
            question_id=qid,
            response_text="Response to preserve.",
            status=ResponseStatus.COMPLETED
        )
        await save_question_response(qid, response, user_id)

    # Delete questions, preserving those with responses
    deleted_count = await delete_questions_for_chapter(
        book_id=book_id,
        chapter_id=chapter_id,
        user_id=user_id,
        preserve_with_responses=True
    )

    # Should delete 3 questions (the ones without responses)
    assert deleted_count == 3

    # Verify the 2 with responses still exist
    result = await get_questions_for_chapter(book_id, chapter_id, user_id, limit=10)
    assert result.total == 2


@pytest.mark.asyncio
async def test_delete_questions_all(motor_reinit_db):
    """Test deleting all questions including those with responses"""
    book_id = "test_book_del2"
    chapter_id = "test_chapter_del2"
    user_id = "test_user_del2"

    # Create 5 questions
    question_ids = []
    for i in range(5):
        question = QuestionCreate(
            book_id=book_id,
            chapter_id=chapter_id,
            question_text=f"Delete all test question {i+1}?",
            question_type=QuestionType.SETTING,
            difficulty=QuestionDifficulty.EASY,
            category="setting",
            order=i+1,
            metadata=QuestionMetadata(suggested_response_length="1 paragraph")
        )
        q = await create_question(question, user_id)
        question_ids.append(q["id"])

    # Answer all questions
    for qid in question_ids:
        response = QuestionResponseCreate(
            question_id=qid,
            response_text="Response that will be deleted.",
            status=ResponseStatus.COMPLETED
        )
        await save_question_response(qid, response, user_id)

    # Delete all questions
    deleted_count = await delete_questions_for_chapter(
        book_id=book_id,
        chapter_id=chapter_id,
        user_id=user_id,
        preserve_with_responses=False
    )

    # Should delete all 5 questions
    assert deleted_count == 5

    # Verify no questions remain
    result = await get_questions_for_chapter(book_id, chapter_id, user_id, limit=10)
    assert result.total == 0


# ============================================================================
# CATEGORY 6: Question Lookup Tests (2 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_get_question_by_id_success(motor_reinit_db):
    """Test retrieving a question by valid ID"""
    book_id = "test_book_lookup"
    chapter_id = "test_chapter_lookup"
    user_id = "test_user_lookup"

    # Create a question
    question = QuestionCreate(
        book_id=book_id,
        chapter_id=chapter_id,
        question_text="What is the main conflict in the story?",
        question_type=QuestionType.PLOT,
        difficulty=QuestionDifficulty.MEDIUM,
        category="plot",
        order=1,
        metadata=QuestionMetadata(suggested_response_length="2-3 paragraphs")
    )
    created = await create_question(question, user_id)
    question_id = created["id"]

    # Get question by ID
    retrieved = await get_question_by_id(question_id, user_id)

    assert retrieved is not None
    assert retrieved["id"] == question_id
    assert retrieved["question_text"] == question.question_text
    assert retrieved["book_id"] == book_id
    assert retrieved["chapter_id"] == chapter_id


@pytest.mark.asyncio
async def test_get_question_by_id_invalid_id(motor_reinit_db):
    """Test retrieving a question with invalid ObjectId returns None"""
    invalid_id = "invalid_object_id"
    user_id = "test_user_invalid"

    result = await get_question_by_id(invalid_id, user_id)

    assert result is None


# ============================================================================
# CATEGORY 7: Filter by Category and Type Tests (2 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_get_questions_filter_by_category(motor_reinit_db):
    """Test filtering questions by category"""
    book_id = "test_book_cat"
    chapter_id = "test_chapter_cat"
    user_id = "test_user_cat"

    # Create questions with different categories
    for i, category in enumerate(["character", "plot", "character", "setting"]):
        question = QuestionCreate(
            book_id=book_id,
            chapter_id=chapter_id,
            question_text=f"Question {i+1} about {category}?",
            question_type=QuestionType.CHARACTER,
            difficulty=QuestionDifficulty.MEDIUM,
            category=category,
            order=i+1,
            metadata=QuestionMetadata(suggested_response_length="1 paragraph")
        )
        await create_question(question, user_id)

    # Filter by character category
    result = await get_questions_for_chapter(
        book_id=book_id,
        chapter_id=chapter_id,
        user_id=user_id,
        category="character",
        limit=10
    )

    # Should return 2 questions with character category
    assert result.total == 2
    assert all(q.category == "character" for q in result.questions)


@pytest.mark.asyncio
async def test_get_questions_filter_by_type(motor_reinit_db):
    """Test filtering questions by question type"""
    book_id = "test_book_type"
    chapter_id = "test_chapter_type"
    user_id = "test_user_type"

    # Create questions with different types
    types = [QuestionType.CHARACTER, QuestionType.PLOT, QuestionType.SETTING, QuestionType.CHARACTER]
    for i, qtype in enumerate(types):
        question = QuestionCreate(
            book_id=book_id,
            chapter_id=chapter_id,
            question_text=f"Question {i+1} type test?",
            question_type=qtype,
            difficulty=QuestionDifficulty.MEDIUM,
            category="test",
            order=i+1,
            metadata=QuestionMetadata(suggested_response_length="1 paragraph")
        )
        await create_question(question, user_id)

    # Filter by CHARACTER type
    result = await get_questions_for_chapter(
        book_id=book_id,
        chapter_id=chapter_id,
        user_id=user_id,
        question_type=QuestionType.CHARACTER.value,
        limit=10
    )

    # Should return 2 questions with CHARACTER type
    assert result.total == 2
    assert all(q.question_type == QuestionType.CHARACTER for q in result.questions)
