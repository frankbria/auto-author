"""Test actual book CRUD operations"""

import pytest
from datetime import datetime, timezone


# Since these tests require actual database access, we'll mark them as integration tests
# and they should be run with a test database
pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_create_and_get_book(motor_reinit_db):
    """Test creating and retrieving a book"""
    from app.db.book import create_book, get_book_by_id
    
    book_data = {
        "title": "Test Book",
        "description": "A test book",
        "genre": "Fiction",
        "target_audience": "General"
    }
    user_clerk_id = "test_user_123"
    
    # Create book
    new_book = await create_book(book_data, user_clerk_id)
    assert new_book["title"] == "Test Book"
    assert new_book["owner_id"] == user_clerk_id
    assert "_id" in new_book
    
    # Get book by ID
    book_id = str(new_book["_id"])
    retrieved_book = await get_book_by_id(book_id)
    assert retrieved_book is not None
    assert retrieved_book["title"] == "Test Book"
    
    # Test with invalid ID
    invalid_book = await get_book_by_id("invalid_id")
    assert invalid_book is None


@pytest.mark.asyncio
async def test_get_books_by_user(motor_reinit_db):
    """Test retrieving all books for a user"""
    from app.db.book import create_book, get_books_by_user
    
    user_clerk_id = "test_user_456"
    
    # Create multiple books
    for i in range(3):
        await create_book({
            "title": f"Book {i}",
            "description": f"Description {i}",
            "genre": "Fiction",
            "target_audience": "General"
        }, user_clerk_id)
    
    # Get user's books
    books = await get_books_by_user(user_clerk_id)
    assert len(books) >= 3
    assert all(book["owner_id"] == user_clerk_id for book in books)
    
    # Test pagination
    books_page1 = await get_books_by_user(user_clerk_id, skip=0, limit=2)
    assert len(books_page1) == 2
    
    books_page2 = await get_books_by_user(user_clerk_id, skip=2, limit=2)
    assert len(books_page2) >= 1


@pytest.mark.asyncio
async def test_update_book(motor_reinit_db):
    """Test updating a book"""
    from app.db.book import create_book, update_book, get_book_by_id
    
    user_clerk_id = "test_user_789"
    
    # Create a book
    book = await create_book({
        "title": "Original Title",
        "description": "Original description",
        "genre": "Fiction",
        "target_audience": "General"
    }, user_clerk_id)
    
    book_id = str(book["_id"])
    
    # Update the book
    updated = await update_book(
        book_id,
        {"title": "Updated Title", "genre": "Non-Fiction"},
        user_clerk_id
    )
    assert updated is not None
    assert updated["title"] == "Updated Title"
    assert updated["genre"] == "Non-Fiction"
    assert updated["description"] == "Original description"  # Unchanged
    
    # Try to update as different user (should fail)
    no_update = await update_book(
        book_id,
        {"title": "Should Not Update"},
        "different_user"
    )
    assert no_update is None


@pytest.mark.asyncio
async def test_delete_book(motor_reinit_db):
    """Test deleting a book"""
    from app.db.book import create_book, delete_book, get_book_by_id
    from bson import ObjectId
    
    user_clerk_id = "test_user_delete"
    
    # Create a book
    book = await create_book({
        "title": "Book to Delete",
        "description": "This will be deleted",
        "genre": "Fiction",
        "target_audience": "General"
    }, user_clerk_id)
    
    book_id = str(book["_id"])
    
    # Delete the book
    deleted = await delete_book(book_id, user_clerk_id)
    assert deleted is True
    
    # Verify deletion
    deleted_book = await get_book_by_id(book_id)
    assert deleted_book is None
    
    # Try to delete non-existent book
    not_deleted = await delete_book(str(ObjectId()), user_clerk_id)
    assert not_deleted is False