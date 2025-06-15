"""Test actual book CRUD operations"""

import pytest
from app.db.book import (
    create_book, get_book_by_id, get_books_by_user, 
    update_book, delete_book
)
from bson import ObjectId


@pytest.mark.asyncio
async def test_create_and_get_book():
    """Test creating and retrieving a book"""
    book_data = {
        "title": "Test Book",
        "description": "A test book",
        "genre": "Fiction",
        "target_audience": "General"
    }
    user_id = "test_user_123"
    
    # Create book
    new_book = await create_book(book_data, user_id)
    assert new_book["title"] == "Test Book"
    assert new_book["owner_id"] == user_id
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
async def test_get_books_by_user():
    """Test retrieving all books for a user"""
    user_id = "test_user_456"
    
    # Create multiple books
    for i in range(3):
        await create_book({
            "title": f"Book {i}",
            "description": f"Description {i}",
            "genre": "Fiction",
            "target_audience": "General"
        }, user_id)
    
    # Get user's books
    books = await get_books_by_user(user_id)
    assert len(books) >= 3
    assert all(book["owner_id"] == user_id for book in books)
    
    # Test pagination
    books_page1 = await get_books_by_user(user_id, skip=0, limit=2)
    assert len(books_page1) == 2
    
    books_page2 = await get_books_by_user(user_id, skip=2, limit=2)
    assert len(books_page2) >= 1


@pytest.mark.asyncio
async def test_update_book():
    """Test updating a book"""
    user_id = "test_user_789"
    
    # Create a book
    book = await create_book({
        "title": "Original Title",
        "description": "Original description",
        "genre": "Fiction",
        "target_audience": "General"
    }, user_id)
    
    book_id = str(book["_id"])
    
    # Update the book
    updated = await update_book(
        book_id,
        {"title": "Updated Title", "genre": "Non-Fiction"},
        user_id
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
async def test_delete_book():
    """Test deleting a book"""
    user_id = "test_user_delete"
    
    # Create a book
    book = await create_book({
        "title": "Book to Delete",
        "description": "This will be deleted",
        "genre": "Fiction",
        "target_audience": "General"
    }, user_id)
    
    book_id = str(book["_id"])
    
    # Delete the book
    deleted = await delete_book(book_id, user_id)
    assert deleted is True
    
    # Verify deletion
    deleted_book = await get_book_by_id(book_id)
    assert deleted_book is None
    
    # Try to delete non-existent book
    not_deleted = await delete_book(str(ObjectId()), user_id)
    assert not_deleted is False