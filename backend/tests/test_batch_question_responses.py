# tests/test_batch_question_responses.py

import pytest
from datetime import datetime, timezone
from bson import ObjectId

from app.db.base import get_collection
from app.db.questions import (
    save_question_responses_batch,
    create_question,
    ensure_question_indexes,
)
from app.schemas.book import QuestionCreate, QuestionType, QuestionDifficulty, QuestionMetadata


async def _make_question(user_id, book_id, chapter_id, order=0):
    question_data = QuestionCreate(
        book_id=book_id,
        chapter_id=chapter_id,
        question_text=f"Test question {order + 1}?",
        question_type=QuestionType.PLOT,
        difficulty=QuestionDifficulty.MEDIUM,
        category="plot",
        order=order,
        metadata=QuestionMetadata(
            suggested_response_length="100-200 words"
        )
    )
    return await create_question(question_data, user_id)


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
    result = await save_question_responses_batch(responses, user_id, book_id=book_id, chapter_id=chapter_id)

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
    initial_result = await save_question_responses_batch(initial_responses, user_id, book_id=book_id, chapter_id=chapter_id)
    assert initial_result["saved"] == 1

    # Update response
    updated_responses = [
        {
            "question_id": question["id"],
            "response_text": "Updated response with more content",
            "status": "completed"
        }
    ]
    update_result = await save_question_responses_batch(updated_responses, user_id, book_id=book_id, chapter_id=chapter_id)

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

    result = await save_question_responses_batch(responses, user_id, book_id=book_id, chapter_id=chapter_id)

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

    result = await save_question_responses_batch(
        responses, user_id, book_id="book_123", chapter_id="chapter_123"
    )

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

    result = await save_question_responses_batch(responses, user_id, book_id=book_id, chapter_id=chapter_id)

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
    await save_question_responses_batch(initial_responses, user_id, book_id=book_id, chapter_id=chapter_id)

    # Update response
    updated_responses = [
        {
            "question_id": question["id"],
            "response_text": "Updated much longer response with more words",
            "status": "completed"
        }
    ]
    await save_question_responses_batch(updated_responses, user_id, book_id=book_id, chapter_id=chapter_id)

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
    await save_question_responses_batch(initial_responses, user_id, book_id=book_id, chapter_id=chapter_id)

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

    result = await save_question_responses_batch(mixed_responses, user_id, book_id=book_id, chapter_id=chapter_id)

    # Assertions
    assert result["success"] is True
    assert result["total"] == 2
    assert result["saved"] == 2
    assert result["failed"] == 0

    # Check which were updates vs new
    results_by_question = {r["question_id"]: r for r in result["results"]}
    assert results_by_question[questions[0]["id"]]["is_update"] is True
    assert results_by_question[questions[1]["id"]]["is_update"] is False

# ---------------------------------------------------------------------------
# Ownership / existence validation (#187)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_batch_rejects_question_from_another_chapter(motor_reinit_db):
    """A question_id belonging to a different chapter is flagged, not saved."""
    user_id = "test_user_123"
    book_id = "book_123"
    chapter_id = "chapter_123"

    valid_q = await _make_question(user_id, book_id, chapter_id)
    foreign_q = await _make_question(user_id, book_id, "other_chapter", order=1)

    responses = [
        {"question_id": valid_q["id"], "response_text": "Valid answer", "status": "draft"},
        {"question_id": foreign_q["id"], "response_text": "Should be rejected", "status": "draft"},
    ]
    result = await save_question_responses_batch(
        responses, user_id, book_id=book_id, chapter_id=chapter_id
    )

    assert result["success"] is False
    assert result["saved"] == 1
    assert result["failed"] == 1
    errors = {e["question_id"]: e for e in result["errors"]}
    assert foreign_q["id"] in errors
    assert "not found" in errors[foreign_q["id"]]["error"].lower()

    # No orphaned response document was written for the rejected item.
    from app.db.questions import get_question_response
    assert await get_question_response(foreign_q["id"], user_id) is None
    assert await get_question_response(valid_q["id"], user_id) is not None


@pytest.mark.asyncio
async def test_batch_rejects_other_users_question(motor_reinit_db):
    """A question owned by another user is flagged, not saved."""
    book_id = "book_123"
    chapter_id = "chapter_123"
    victim_q = await _make_question("victim_user", book_id, chapter_id)

    attacker = "attacker_user"
    result = await save_question_responses_batch(
        [{"question_id": victim_q["id"], "response_text": "Hijack attempt", "status": "draft"}],
        attacker, book_id=book_id, chapter_id=chapter_id,
    )

    assert result["success"] is False
    assert result["saved"] == 0
    assert result["failed"] == 1

    from app.db.questions import get_question_response
    assert await get_question_response(victim_q["id"], attacker) is None


@pytest.mark.asyncio
async def test_batch_rejects_nonexistent_and_malformed_ids(motor_reinit_db):
    """Nonexistent ObjectIds and unparseable ids are both flagged cleanly."""
    user_id = "test_user_123"
    responses = [
        {"question_id": str(ObjectId()), "response_text": "Ghost question", "status": "draft"},
        {"question_id": "not-an-objectid", "response_text": "Garbage id", "status": "draft"},
    ]
    result = await save_question_responses_batch(
        responses, user_id, book_id="book_123", chapter_id="chapter_123"
    )

    assert result["success"] is False
    assert result["saved"] == 0
    assert result["failed"] == 2
    assert all("not found" in e["error"].lower() for e in result["errors"])


# ---------------------------------------------------------------------------
# Repeated question_id within one batch (#242)
#
# NB motor_reinit_db drops the DB and creates no indexes, so most of this file
# exercises the collection WITHOUT the unique question_user_idx. Production
# creates it at startup (main.py -> ensure_question_indexes), and the two index
# states used to fail differently: without it the batch wrote two documents;
# with it the newer answer was silently dropped and a raw E11000 leaked. Both
# states are pinned below.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_duplicate_question_id_writes_single_document(motor_reinit_db):
    """The same question_id twice in one batch writes ONE document, last write wins."""
    user_id = "test_user_123"
    book_id = "book_123"
    chapter_id = "chapter_123"
    question = await _make_question(user_id, book_id, chapter_id)

    result = await save_question_responses_batch(
        [
            {"question_id": question["id"], "response_text": "First answer", "status": "draft"},
            {"question_id": question["id"], "response_text": "Second answer", "status": "completed"},
        ],
        user_id, book_id=book_id, chapter_id=chapter_id,
    )

    assert result["success"] is True

    responses_collection = await get_collection("question_responses")
    stored = [d async for d in responses_collection.find({"question_id": question["id"]})]
    assert len(stored) == 1, f"expected one response document, found {len(stored)}"
    assert stored[0]["response_text"] == "Second answer"
    assert stored[0]["status"] == "completed"
    assert stored[0]["word_count"] == 2


@pytest.mark.asyncio
async def test_duplicate_question_id_last_write_wins_with_unique_index(motor_reinit_db):
    """Production shape: with the unique index live, the newer answer must win cleanly.

    Before #242 this stored the FIRST answer, returned success=False, and leaked a raw
    'E11000 duplicate key error' from Mongo into the API response.
    """
    user_id = "test_user_123"
    book_id = "book_123"
    chapter_id = "chapter_123"

    # Warm the collection with a real op before creating indexes: the first
    # createIndexes after motor_reinit_db's drop can otherwise be silently lost.
    responses_collection = await get_collection("question_responses")
    await responses_collection.insert_one({"_id": ObjectId(), "warmup": True})
    await responses_collection.delete_many({"warmup": True})
    await ensure_question_indexes()
    index_names = [i["name"] async for i in responses_collection.list_indexes()]
    assert "question_user_idx" in index_names, "unique index missing; test would prove nothing"

    question = await _make_question(user_id, book_id, chapter_id)
    result = await save_question_responses_batch(
        [
            {"question_id": question["id"], "response_text": "First answer", "status": "draft"},
            {"question_id": question["id"], "response_text": "Second answer", "status": "completed"},
        ],
        user_id, book_id=book_id, chapter_id=chapter_id,
    )

    assert result["success"] is True
    assert result["failed"] == 0
    assert "E11000" not in str(result), "raw Mongo duplicate-key error leaked to the caller"

    stored = [d async for d in responses_collection.find({"question_id": question["id"]})]
    assert len(stored) == 1
    assert stored[0]["response_text"] == "Second answer"


@pytest.mark.asyncio
async def test_duplicate_question_id_reports_both_items(motor_reinit_db):
    """Both collapsed items report the one write's outcome, against the same response_id."""
    user_id = "test_user_123"
    book_id = "book_123"
    chapter_id = "chapter_123"
    question = await _make_question(user_id, book_id, chapter_id)

    result = await save_question_responses_batch(
        [
            {"question_id": question["id"], "response_text": "First answer", "status": "draft"},
            {"question_id": question["id"], "response_text": "Second answer", "status": "completed"},
        ],
        user_id, book_id=book_id, chapter_id=chapter_id,
    )

    assert result["total"] == 2
    assert result["saved"] == 2
    assert result["failed"] == 0
    assert result["total"] == result["saved"] + result["failed"]
    assert result["errors"] is None

    by_index = {r["index"]: r for r in result["results"]}
    assert set(by_index) == {0, 1}
    assert all(r["success"] is True for r in by_index.values())
    # One document => one response_id shared by both items.
    assert by_index[0]["response_id"] == by_index[1]["response_id"]


@pytest.mark.asyncio
async def test_duplicate_question_id_over_existing_response_updates_once(motor_reinit_db):
    """A repeated id on top of an already-saved response updates it once, last wins."""
    user_id = "test_user_123"
    book_id = "book_123"
    chapter_id = "chapter_123"
    question = await _make_question(user_id, book_id, chapter_id)

    await save_question_responses_batch(
        [{"question_id": question["id"], "response_text": "Original answer", "status": "draft"}],
        user_id, book_id=book_id, chapter_id=chapter_id,
    )

    result = await save_question_responses_batch(
        [
            {"question_id": question["id"], "response_text": "Edit one", "status": "draft"},
            {"question_id": question["id"], "response_text": "Edit two", "status": "completed"},
        ],
        user_id, book_id=book_id, chapter_id=chapter_id,
    )

    assert result["success"] is True
    assert all(r["is_update"] is True for r in result["results"])

    responses_collection = await get_collection("question_responses")
    stored = [d async for d in responses_collection.find({"question_id": question["id"]})]
    assert len(stored) == 1
    assert stored[0]["response_text"] == "Edit two"


@pytest.mark.asyncio
async def test_question_id_repeated_three_times_collapses_to_last_write(motor_reinit_db):
    """Three occurrences of one id still collapse to a single write of the last answer.

    Interleaves a second question so the results are also pinned to come back in
    request order (the collapsed op carries indexes 0 and 3, the other index 1).
    """
    user_id = "test_user_123"
    book_id = "book_123"
    chapter_id = "chapter_123"
    repeated = await _make_question(user_id, book_id, chapter_id)
    other = await _make_question(user_id, book_id, chapter_id, order=1)

    result = await save_question_responses_batch(
        [
            {"question_id": repeated["id"], "response_text": "Answer one", "status": "draft"},
            {"question_id": other["id"], "response_text": "Other answer", "status": "draft"},
            {"question_id": repeated["id"], "response_text": "Answer two", "status": "draft"},
            {"question_id": repeated["id"], "response_text": "Answer three", "status": "completed"},
        ],
        user_id, book_id=book_id, chapter_id=chapter_id,
    )

    assert result["success"] is True
    assert result["total"] == 4
    assert result["saved"] == 4
    assert result["total"] == result["saved"] + result["failed"]
    assert [r["index"] for r in result["results"]] == [0, 1, 2, 3]

    responses_collection = await get_collection("question_responses")
    stored = [d async for d in responses_collection.find({"question_id": repeated["id"]})]
    assert len(stored) == 1
    assert stored[0]["response_text"] == "Answer three"
    assert stored[0]["status"] == "completed"

    other_stored = [d async for d in responses_collection.find({"question_id": other["id"]})]
    assert len(other_stored) == 1
    assert other_stored[0]["response_text"] == "Other answer"


@pytest.mark.asyncio
async def test_duplicate_question_id_empty_first_then_valid_saves_valid(motor_reinit_db):
    """The reverse order of the case below: an invalid first item must not block the valid one."""
    user_id = "test_user_123"
    book_id = "book_123"
    chapter_id = "chapter_123"
    question = await _make_question(user_id, book_id, chapter_id)

    result = await save_question_responses_batch(
        [
            {"question_id": question["id"], "response_text": "", "status": "draft"},
            {"question_id": question["id"], "response_text": "Real answer", "status": "completed"},
        ],
        user_id, book_id=book_id, chapter_id=chapter_id,
    )

    assert result["saved"] == 1
    assert result["failed"] == 1
    by_index = {r["index"]: r for r in result["results"]}
    assert by_index[0]["success"] is False
    assert by_index[0]["error"] == "Missing response_text"
    assert by_index[1]["success"] is True

    responses_collection = await get_collection("question_responses")
    stored = [d async for d in responses_collection.find({"question_id": question["id"]})]
    assert len(stored) == 1
    assert stored[0]["response_text"] == "Real answer"


@pytest.mark.asyncio
async def test_duplicate_question_id_validates_each_item_independently(motor_reinit_db):
    """Collapsing must not swallow (or misattribute) a per-item validation error.

    Mirrors two sequential saves: the valid text lands, the empty follow-up is rejected
    on its own index rather than wiping the earlier value.
    """
    user_id = "test_user_123"
    book_id = "book_123"
    chapter_id = "chapter_123"
    question = await _make_question(user_id, book_id, chapter_id)

    result = await save_question_responses_batch(
        [
            {"question_id": question["id"], "response_text": "Real answer", "status": "draft"},
            {"question_id": question["id"], "response_text": "", "status": "draft"},
        ],
        user_id, book_id=book_id, chapter_id=chapter_id,
    )

    assert result["saved"] == 1
    assert result["failed"] == 1
    by_index = {r["index"]: r for r in result["results"]}
    assert by_index[0]["success"] is True
    assert by_index[1]["success"] is False
    assert by_index[1]["error"] == "Missing response_text"

    responses_collection = await get_collection("question_responses")
    stored = [d async for d in responses_collection.find({"question_id": question["id"]})]
    assert len(stored) == 1
    assert stored[0]["response_text"] == "Real answer"
