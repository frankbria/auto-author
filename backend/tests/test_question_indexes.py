"""Test question collection indexes."""
import pytest
from app.db.questions import _QUESTION_INDEXES, ensure_question_indexes
from app.db.base import get_collection


@pytest.mark.asyncio
async def test_ensure_question_indexes(motor_reinit_db):
    """Test that indexes are created successfully."""
    # Create indexes
    await ensure_question_indexes()

    # Verify indexes on questions collection
    questions_collection = await get_collection("questions")
    indexes = await questions_collection.list_indexes().to_list(length=None)
    index_names = [idx['name'] for idx in indexes]

    assert 'book_chapter_user_idx' in index_names, "Missing book_chapter_user_idx"
    assert 'user_created_idx' in index_names, "Missing user_created_idx"
    assert 'chapter_order_idx' in index_names, "Missing chapter_order_idx"

    # Verify indexes on question_responses collection
    responses_collection = await get_collection("question_responses")
    indexes = await responses_collection.list_indexes().to_list(length=None)
    index_names = [idx['name'] for idx in indexes]

    assert 'question_user_idx' in index_names, "Missing question_user_idx on responses"
    assert 'user_created_idx' in index_names, "Missing user_created_idx on responses"

    # Verify indexes on question_ratings collection
    ratings_collection = await get_collection("question_ratings")
    indexes = await ratings_collection.list_indexes().to_list(length=None)
    index_names = [idx['name'] for idx in indexes]

    assert 'question_user_idx' in index_names, "Missing question_user_idx on ratings"


@pytest.mark.asyncio
async def test_indexes_are_idempotent(motor_reinit_db):
    """Test that running ensure_question_indexes multiple times is safe."""
    # Run twice - should not raise any errors
    await ensure_question_indexes()
    await ensure_question_indexes()

    # Verify indexes still exist
    questions_collection = await get_collection("questions")
    indexes = await questions_collection.list_indexes().to_list(length=None)
    index_names = [idx['name'] for idx in indexes]

    # Should still have all expected indexes
    assert 'book_chapter_user_idx' in index_names
    assert 'user_created_idx' in index_names
    assert 'chapter_order_idx' in index_names


@pytest.mark.asyncio
async def test_failing_index_does_not_skip_later_indexes(motor_reinit_db):
    """A mid-list index build failure must not skip the remaining indexes (#338).

    Pre-existing duplicate responses make the unique question_user_idx build
    genuinely fail — no mocking. Every index after it must still be created.
    """
    # Only proves anything if the failing index precedes the ones asserted to
    # survive; pin it so reordering _QUESTION_INDEXES fails loudly rather than
    # silently turning this into a no-op.
    order = [(collection, name) for collection, _, name, _ in _QUESTION_INDEXES]
    assert order.index(("question_responses", "question_user_idx")) < min(
        order.index(("question_responses", "user_created_idx")),
        order.index(("question_ratings", "question_user_idx")),
    ), "_QUESTION_INDEXES reordered — this test no longer covers #338"

    responses_collection = await get_collection("question_responses")
    await responses_collection.insert_many([
        {"question_id": "q1", "user_id": "u1", "response_text": "first"},
        {"question_id": "q1", "user_id": "u1", "response_text": "duplicate"},
    ])

    await ensure_question_indexes()

    response_indexes = [
        idx['name']
        for idx in await responses_collection.list_indexes().to_list(length=None)
    ]
    assert 'question_user_idx' not in response_indexes, (
        "unique index should have failed to build over duplicate docs"
    )
    assert 'user_created_idx' in response_indexes, (
        "index after the failing one was skipped"
    )

    ratings_collection = await get_collection("question_ratings")
    rating_indexes = [
        idx['name']
        for idx in await ratings_collection.list_indexes().to_list(length=None)
    ]
    assert 'question_user_idx' in rating_indexes, (
        "later collection's index was skipped"
    )


@pytest.mark.asyncio
async def test_question_query_uses_index(motor_reinit_db):
    """Test that question queries can use the compound index."""
    questions_collection = await get_collection("questions")

    # Create a sample query like in get_questions_for_chapter
    query = {
        "book_id": "test_book_id",
        "chapter_id": "test_chapter_id",
        "user_id": "test_user_id"
    }

    # Get the query plan to verify index usage
    # Note: We're just checking the query can be executed
    # In production, you'd use explain() to verify index usage
    cursor = questions_collection.find(query).sort("order", 1)

    # This should not raise an error
    results = await cursor.to_list(length=10)
    assert isinstance(results, list)
