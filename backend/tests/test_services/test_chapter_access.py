"""Test chapter access service"""

import pytest
from app.services.chapter_access_service import ChapterAccessService
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def access_service():
    """Create chapter access service instance"""
    return ChapterAccessService()


@pytest.mark.asyncio
async def test_log_chapter_access(access_service):
    """Test logging chapter access"""
    # Mock the collection
    mock_collection = MagicMock()
    mock_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="123"))
    access_service._get_collection = AsyncMock(return_value=mock_collection)
    
    # Log access
    result = await access_service.log_access(
        user_id="user123",
        book_id="book456",
        chapter_id="ch1",
        access_type="view"
    )
    
    assert result == "123"
    mock_collection.insert_one.assert_called_once()
    
    # Log edit access with metadata
    edit_result = await access_service.log_access(
        user_id="user123",
        book_id="book456", 
        chapter_id="ch1",
        access_type="edit",
        metadata={"word_count_change": 150}
    )
    
    assert edit_result == "123"


@pytest.mark.asyncio
async def test_get_user_tab_state(access_service):
    """Test retrieving user tab state"""
    # Mock the collection
    mock_cursor = MagicMock()
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    mock_cursor.limit = MagicMock(return_value=mock_cursor)
    mock_cursor.to_list = AsyncMock(return_value=[{
        "user_id": "user123",
        "book_id": "book456",
        "access_type": "tab_state",
        "metadata": {
            "active_chapter_id": "ch1",
            "open_tab_ids": ["ch1", "ch2"],
            "tab_order": ["ch1", "ch2"]
        }
    }])
    
    mock_collection = MagicMock()
    mock_collection.find = MagicMock(return_value=mock_cursor)
    access_service._get_collection = AsyncMock(return_value=mock_collection)
    
    # Get tab state
    state = await access_service.get_user_tab_state(
        user_id="user123",
        book_id="book456"
    )
    
    assert state is not None
    assert state["user_id"] == "user123"
    assert state["metadata"]["active_chapter_id"] == "ch1"


@pytest.mark.asyncio
async def test_get_chapter_analytics(access_service):
    """Test getting chapter analytics"""
    # Mock the collection
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=[
        {"_id": {"chapter_id": "ch1", "access_type": "view"}, "count": 10, "last_access": datetime.now()},
        {"_id": {"chapter_id": "ch2", "access_type": "edit"}, "count": 5, "last_access": datetime.now()}
    ])
    
    mock_collection = MagicMock()
    mock_collection.aggregate = MagicMock(return_value=mock_cursor)
    access_service._get_collection = AsyncMock(return_value=mock_collection)
    
    # Get analytics
    analytics = await access_service.get_chapter_analytics(
        book_id="book456",
        days=30
    )
    
    assert isinstance(analytics, list)
    assert len(analytics) == 2
    assert analytics[0]["count"] == 10


@pytest.mark.asyncio
async def test_save_tab_state(access_service):
    """Test saving tab state"""
    # Mock the collection
    mock_collection = MagicMock()
    mock_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="456"))
    access_service._get_collection = AsyncMock(return_value=mock_collection)
    
    # Save tab state
    result = await access_service.save_tab_state(
        user_id="user123",
        book_id="book456",
        active_chapter_id="ch1",
        open_tab_ids=["ch1", "ch2", "ch3"],
        tab_order=["ch1", "ch2", "ch3"],
        session_id="session123"
    )
    
    assert result == "456"
    mock_collection.insert_one.assert_called_once()
    
    # Verify the metadata was saved correctly
    call_args = mock_collection.insert_one.call_args[0][0]
    assert call_args["metadata"]["active_chapter_id"] == "ch1"
    assert call_args["metadata"]["open_tab_ids"] == ["ch1", "ch2", "ch3"]
    assert call_args["metadata"]["tab_order"] == ["ch1", "ch2", "ch3"]


@pytest.mark.asyncio
async def test_get_user_recent_chapters(access_service):
    """Test getting user's recent chapters"""
    # Mock the collection
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=[
        {"_id": "ch1", "last_access": datetime.now(), "access_count": 5},
        {"_id": "ch2", "last_access": datetime.now(), "access_count": 3}
    ])
    
    mock_collection = MagicMock()
    mock_collection.aggregate = MagicMock(return_value=mock_cursor)
    access_service._get_collection = AsyncMock(return_value=mock_collection)
    
    # Get recent chapters
    recent = await access_service.get_user_recent_chapters(
        user_id="user123",
        book_id="book456",
        limit=10
    )
    
    assert isinstance(recent, list)
    assert len(recent) == 2
    assert recent[0]["_id"] == "ch1"
    assert recent[0]["access_count"] == 5