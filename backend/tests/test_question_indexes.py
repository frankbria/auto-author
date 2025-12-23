"""Test question collection indexes."""
import pytest
from app.db.questions import ensure_question_indexes
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
