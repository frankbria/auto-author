# tests/test_batch_question_responses.py

import pytest
from datetime import datetime, timezone
from bson import ObjectId

from app.db.questions import save_question_responses_batch, create_question
from app.schemas.book import QuestionCreate, QuestionType, QuestionDifficulty, QuestionMetadata


@pytest.mark.asyncio
async def test_batch_save_new_responses(motor_reinit_db):
    """Test batch saving new question responses."""
    user_id = "test_user_123"
    book_id = "book_123"
    chapter_id = "chapter_123"

    # Create test questions
    questions = []
    for i in range(3):
        question_data = QuestionCreate(
            book_id=book_id,
            chapter_id=chapter_id,
            question_text=f"Test question {i+1}?",
            question_type=QuestionType.PLOT,
            difficulty=QuestionDifficulty.MEDIUM,
            category="plot",
            order=i,
            metadata=QuestionMetadata(
                suggested_response_length="100-200 words",
                help_text="Provide details",
                examples=["Example 1"]
            )
        )
        question = await create_question(question_data, user_id)
        questions.append(question)

    # Prepare batch responses
    responses = [
        {
            "question_id": questions[0]["id"],
            "response_text": "This is response 1",
            "status": "completed"
        },
        {
            "question_id": questions[1]["id"],
            "response_text": "This is response 2",
            "status": "draft"
        },
        {
            "question_id": questions[2]["id"],
            "response_text": "This is response 3",
            "status": "completed"
        }
    ]

    # Save batch
    result = await save_question_responses_batch(responses, user_id)

    # Assertions
    assert result["success"] is True
    assert result["total"] == 3
    assert result["saved"] == 3
    assert result["failed"] == 0
    assert len(result["results"]) == 3
    assert result["errors"] is None

    # Verify each response was saved
    for i, response_result in enumerate(result["results"]):
        assert response_result["success"] is True
        assert response_result["question_id"] == questions[i]["id"]
        assert "response_id" in response_result
        assert response_result["is_update"] is False


@pytest.mark.asyncio
async def test_batch_save_update_existing_responses(motor_reinit_db):
    """Test batch updating existing question responses."""
    user_id = "test_user_123"
    book_id = "book_123"
    chapter_id = "chapter_123"

    # Create test question
    question_data = QuestionCreate(
        book_id=book_id,
        chapter_id=chapter_id,
        question_text="Test question?",
        question_type=QuestionType.PLOT,
        difficulty=QuestionDifficulty.MEDIUM,
        category="plot",
        order=0,
        metadata=QuestionMetadata(
            suggested_response_length="100-200 words"
        )
    )
    question = await create_question(question_data, user_id)

    # Save initial response
    initial_responses = [
        {
            "question_id": question["id"],
            "response_text": "Initial response",
            "status": "draft"
        }
    ]
    initial_result = await save_question_responses_batch(initial_responses, user_id)
    assert initial_result["saved"] == 1

    # Update response
    updated_responses = [
        {
            "question_id": question["id"],
            "response_text": "Updated response with more content",
            "status": "completed"
        }
    ]
    update_result = await save_question_responses_batch(updated_responses, user_id)

    # Assertions
    assert update_result["success"] is True
    assert update_result["total"] == 1
    assert update_result["saved"] == 1
    assert update_result["failed"] == 0
    assert update_result["results"][0]["is_update"] is True
    assert update_result["results"][0]["success"] is True


@pytest.mark.asyncio
async def test_batch_save_partial_failure(motor_reinit_db):
    """Test batch save with some invalid responses."""
    user_id = "test_user_123"
    book_id = "book_123"
    chapter_id = "chapter_123"

    # Create valid question
    question_data = QuestionCreate(
        book_id=book_id,
        chapter_id=chapter_id,
        question_text="Valid question?",
        question_type=QuestionType.PLOT,
        difficulty=QuestionDifficulty.MEDIUM,
        category="plot",
        order=0,
        metadata=QuestionMetadata(
            suggested_response_length="100-200 words"
        )
    )
    question = await create_question(question_data, user_id)

    # Mix of valid and invalid responses
    responses = [
        {
            "question_id": question["id"],
            "response_text": "Valid response",
            "status": "completed"
        },
        {
            # Missing question_id
            "response_text": "Invalid response - no question_id",
            "status": "draft"
        },
        {
            "question_id": "invalid_question_id",
            "response_text": "",  # Empty response_text
            "status": "draft"
        }
    ]

    result = await save_question_responses_batch(responses, user_id)

    # Assertions
    assert result["success"] is False  # Overall failure due to partial failures
    assert result["total"] == 3
    assert result["saved"] == 1  # Only the valid one
    assert result["failed"] == 2
    assert len(result["errors"]) == 2

    # Check specific failures
    errors = {e["index"]: e for e in result["errors"]}
    assert 1 in errors
    assert "Missing question_id" in errors[1]["error"]
    assert 2 in errors
    assert "Missing response_text" in errors[2]["error"]


@pytest.mark.asyncio
async def test_batch_save_empty_list(motor_reinit_db):
    """Test batch save with empty response list."""
    user_id = "test_user_123"
    responses = []

    result = await save_question_responses_batch(responses, user_id)

    assert result["success"] is True  # Empty batch is technically successful
    assert result["total"] == 0
    assert result["saved"] == 0
    assert result["failed"] == 0
    assert len(result["results"]) == 0


@pytest.mark.asyncio
async def test_batch_save_word_count_calculation(motor_reinit_db):
    """Test that word counts are calculated correctly."""
    user_id = "test_user_123"
    book_id = "book_123"
    chapter_id = "chapter_123"

    # Create test question
    question_data = QuestionCreate(
        book_id=book_id,
        chapter_id=chapter_id,
        question_text="Test question?",
        question_type=QuestionType.PLOT,
        difficulty=QuestionDifficulty.MEDIUM,
        category="plot",
        order=0,
        metadata=QuestionMetadata(
            suggested_response_length="100-200 words"
        )
    )
    question = await create_question(question_data, user_id)

    # Response with known word count
    response_text = "This is a test response with exactly ten words in it"
    responses = [
        {
            "question_id": question["id"],
            "response_text": response_text,
            "status": "draft"
        }
    ]

    result = await save_question_responses_batch(responses, user_id)

    # Verify save succeeded
    assert result["saved"] == 1

    # Get the saved response and check word count
    from app.db.questions import get_question_response
    saved_response = await get_question_response(question["id"], user_id)

    assert saved_response is not None
    assert saved_response["word_count"] == len(response_text.split())
    assert saved_response["word_count"] == 11  # Actual count


@pytest.mark.asyncio
async def test_batch_save_edit_history_tracking(motor_reinit_db):
    """Test that edit history is tracked for updates."""
    user_id = "test_user_123"
    book_id = "book_123"
    chapter_id = "chapter_123"

    # Create test question
    question_data = QuestionCreate(
        book_id=book_id,
        chapter_id=chapter_id,
        question_text="Test question?",
        question_type=QuestionType.PLOT,
        difficulty=QuestionDifficulty.MEDIUM,
        category="plot",
        order=0,
        metadata=QuestionMetadata(
            suggested_response_length="100-200 words"
        )
    )
    question = await create_question(question_data, user_id)

    # Save initial response
    initial_responses = [
        {
            "question_id": question["id"],
            "response_text": "Initial short response",
            "status": "draft"
        }
    ]
    await save_question_responses_batch(initial_responses, user_id)

    # Update response
    updated_responses = [
        {
            "question_id": question["id"],
            "response_text": "Updated much longer response with more words",
            "status": "completed"
        }
    ]
    await save_question_responses_batch(updated_responses, user_id)

    # Get the response and check edit history
    from app.db.questions import get_question_response
    saved_response = await get_question_response(question["id"], user_id)

    assert saved_response is not None
    assert "metadata" in saved_response
    assert "edit_history" in saved_response["metadata"]
    assert len(saved_response["metadata"]["edit_history"]) == 1

    # Check that edit history contains the previous word count
    edit_entry = saved_response["metadata"]["edit_history"][0]
    assert "timestamp" in edit_entry
    assert "word_count" in edit_entry
    assert edit_entry["word_count"] == 3  # "Initial short response"


@pytest.mark.asyncio
async def test_batch_save_mixed_new_and_updates(motor_reinit_db):
    """Test batch with mix of new responses and updates."""
    user_id = "test_user_123"
    book_id = "book_123"
    chapter_id = "chapter_123"

    # Create two questions
    questions = []
    for i in range(2):
        question_data = QuestionCreate(
            book_id=book_id,
            chapter_id=chapter_id,
            question_text=f"Test question {i+1}?",
            question_type=QuestionType.PLOT,
            difficulty=QuestionDifficulty.MEDIUM,
            category="plot",
            order=i,
            metadata=QuestionMetadata(
                suggested_response_length="100-200 words"
            )
        )
        question = await create_question(question_data, user_id)
        questions.append(question)

    # Save response for first question
    initial_responses = [
        {
            "question_id": questions[0]["id"],
            "response_text": "Initial response",
            "status": "draft"
        }
    ]
    await save_question_responses_batch(initial_responses, user_id)

    # Batch with update to first and new response for second
    mixed_responses = [
        {
            "question_id": questions[0]["id"],
            "response_text": "Updated response",
            "status": "completed"
        },
        {
            "question_id": questions[1]["id"],
            "response_text": "New response",
            "status": "draft"
        }
    ]

    result = await save_question_responses_batch(mixed_responses, user_id)

    # Assertions
    assert result["success"] is True
    assert result["total"] == 2
    assert result["saved"] == 2
    assert result["failed"] == 0

    # Check which were updates vs new
    results_by_question = {r["question_id"]: r for r in result["results"]}
    assert results_by_question[questions[0]["id"]]["is_update"] is True
    assert results_by_question[questions[1]["id"]]["is_update"] is False
