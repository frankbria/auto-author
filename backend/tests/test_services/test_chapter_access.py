"""Test chapter access service"""

import pytest
from app.services.chapter_access_service import ChapterAccessService
from datetime import datetime


@pytest.fixture
def access_service():
    """Create chapter access service instance"""
    return ChapterAccessService()


@pytest.mark.asyncio
async def test_track_chapter_access(access_service):
    """Test tracking chapter access"""
    # Track access
    result = await access_service.track_access(
        user_id="user123",
        book_id="book456",
        chapter_id="ch1",
        action="read"
    )
    
    assert result["success"] is True
    assert "access_id" in result
    assert result["action"] == "read"
    
    # Track edit access
    edit_result = await access_service.track_access(
        user_id="user123",
        book_id="book456", 
        chapter_id="ch1",
        action="edit",
        metadata={"word_count_change": 150}
    )
    
    assert edit_result["success"] is True
    assert edit_result["action"] == "edit"


@pytest.mark.asyncio
async def test_get_chapter_access_history(access_service):
    """Test retrieving access history"""
    # First track some accesses
    await access_service.track_access("user123", "book456", "ch1", "read")
    await access_service.track_access("user123", "book456", "ch1", "edit")
    await access_service.track_access("user456", "book456", "ch1", "read")
    
    # Get history for chapter
    history = await access_service.get_chapter_history(
        book_id="book456",
        chapter_id="ch1",
        limit=10
    )
    
    assert isinstance(history, list)
    assert len(history) >= 2
    assert all("user_id" in h for h in history)
    assert all("action" in h for h in history)
    assert all("timestamp" in h for h in history)


@pytest.mark.asyncio
async def test_get_user_activity(access_service):
    """Test getting user activity summary"""
    # Track various activities
    await access_service.track_access("user123", "book1", "ch1", "read")
    await access_service.track_access("user123", "book1", "ch2", "read")
    await access_service.track_access("user123", "book2", "ch1", "edit")
    
    # Get user activity
    activity = await access_service.get_user_activity(
        user_id="user123",
        days=30
    )
    
    assert "total_reads" in activity
    assert "total_edits" in activity
    assert "unique_books" in activity
    assert "unique_chapters" in activity
    assert "daily_activity" in activity
    assert activity["total_reads"] >= 2
    assert activity["total_edits"] >= 1


@pytest.mark.asyncio
async def test_get_popular_chapters(access_service):
    """Test getting most accessed chapters"""
    # Simulate access patterns
    for i in range(5):
        await access_service.track_access(f"user{i}", "book1", "ch1", "read")
    for i in range(3):
        await access_service.track_access(f"user{i}", "book1", "ch2", "read")
    await access_service.track_access("user1", "book1", "ch3", "read")
    
    # Get popular chapters
    popular = await access_service.get_popular_chapters(
        book_id="book1",
        limit=3
    )
    
    assert isinstance(popular, list)
    assert len(popular) <= 3
    if len(popular) > 0:
        assert popular[0]["chapter_id"] == "ch1"  # Most accessed
        assert popular[0]["access_count"] >= 5