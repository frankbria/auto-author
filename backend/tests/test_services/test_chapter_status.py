"""Test chapter status service"""

import pytest
from app.services.chapter_status_service import ChapterStatusService


@pytest.fixture
def status_service():
    """Create chapter status service instance"""
    return ChapterStatusService()


@pytest.mark.asyncio
async def test_get_chapter_status(status_service):
    """Test getting chapter status"""
    # Test draft status
    status = await status_service.get_status("book123", "chapter1")
    assert status in ["not_started", "draft", "edited", "final", "published"]
    
    # Test with metadata
    status_data = await status_service.get_status_with_metadata("book123", "chapter1")
    assert "status" in status_data
    assert "last_modified" in status_data
    assert "word_count" in status_data


@pytest.mark.asyncio
async def test_update_chapter_status(status_service):
    """Test updating chapter status"""
    # Update to draft
    result = await status_service.update_status(
        book_id="book123",
        chapter_id="chapter1",
        new_status="draft",
        metadata={"word_count": 500}
    )
    assert result["success"] is True
    assert result["status"] == "draft"
    
    # Invalid status
    result = await status_service.update_status(
        book_id="book123",
        chapter_id="chapter1",
        new_status="invalid_status"
    )
    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_bulk_status_update(status_service):
    """Test updating multiple chapter statuses"""
    updates = [
        {"chapter_id": "ch1", "status": "draft"},
        {"chapter_id": "ch2", "status": "edited"},
        {"chapter_id": "ch3", "status": "final"}
    ]
    
    results = await status_service.bulk_update_status("book123", updates)
    assert len(results) == 3
    assert all(r["success"] for r in results)


@pytest.mark.asyncio
async def test_get_book_progress(status_service):
    """Test getting overall book progress"""
    progress = await status_service.get_book_progress("book123")
    
    assert "total_chapters" in progress
    assert "chapters_by_status" in progress
    assert "overall_progress" in progress
    assert 0 <= progress["overall_progress"] <= 100
    
    # Check status breakdown
    status_breakdown = progress["chapters_by_status"]
    assert isinstance(status_breakdown, dict)
    for status in ["not_started", "draft", "edited", "final", "published"]:
        assert status in status_breakdown