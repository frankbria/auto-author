"""Test chapter status service"""

import pytest
from app.services.chapter_status_service import ChapterStatusService
from app.schemas.book import ChapterStatus
from datetime import datetime


@pytest.fixture
def status_service():
    """Create chapter status service instance"""
    return ChapterStatusService()


def test_validate_status_transition(status_service):
    """Test status transition validation"""
    # Valid transitions
    assert status_service.validate_status_transition("draft", "in-progress") is True
    assert status_service.validate_status_transition("in-progress", "completed") is True
    assert status_service.validate_status_transition("completed", "published") is True
    
    # Same status is valid
    assert status_service.validate_status_transition("draft", "draft") is True
    
    # Invalid transitions
    assert status_service.validate_status_transition("draft", "published") is False
    assert status_service.validate_status_transition("published", "draft") is False


def test_is_valid_transition_enum(status_service):
    """Test status transition validation with enums"""
    # Valid transitions
    assert status_service.is_valid_transition(
        ChapterStatus.DRAFT, 
        ChapterStatus.IN_PROGRESS
    ) is True
    
    assert status_service.is_valid_transition(
        ChapterStatus.COMPLETED, 
        ChapterStatus.PUBLISHED
    ) is True
    
    # Invalid transition
    assert status_service.is_valid_transition(
        ChapterStatus.DRAFT, 
        ChapterStatus.PUBLISHED
    ) is False


def test_auto_suggest_status(status_service):
    """Test auto-suggesting status based on word count"""
    # No content
    assert status_service.auto_suggest_status(0) == "draft"
    
    # Short content
    assert status_service.auto_suggest_status(250) == "in-progress"
    
    # Substantial content
    assert status_service.auto_suggest_status(1000) == "completed"
    
    # Edge case
    assert status_service.auto_suggest_status(500) == "completed"


def test_calculate_reading_time(status_service):
    """Test reading time calculation"""
    # Standard reading
    assert status_service.calculate_reading_time(400) == 2  # 400 words / 200 wpm
    assert status_service.calculate_reading_time(1000) == 5  # 1000 words / 200 wpm
    
    # Custom reading speed
    assert status_service.calculate_reading_time(600, words_per_minute=300) == 2
    
    # Edge cases
    assert status_service.calculate_reading_time(0) == 0
    assert status_service.calculate_reading_time(50) == 1  # Minimum 1 minute


def test_get_completion_stats(status_service):
    """Test getting completion statistics"""
    chapters = [
        {"id": "ch1", "status": "draft"},
        {"id": "ch2", "status": "draft"},
        {"id": "ch3", "status": "in-progress"},
        {"id": "ch4", "status": "completed"},
        {"id": "ch5", "status": "published"}
    ]
    
    stats = status_service.get_completion_stats(chapters)
    
    assert stats["draft"] == 2
    assert stats["in-progress"] == 1
    assert stats["completed"] == 1
    assert stats["published"] == 1
    
    # Check all statuses are present
    for status in ChapterStatus:
        assert status.value in stats


def test_validate_bulk_status_update(status_service):
    """Test validating bulk status updates"""
    chapter_statuses = {
        "ch1": "draft",
        "ch2": "in-progress",
        "ch3": "completed"
    }
    
    # Valid transitions
    results = status_service.validate_bulk_status_update(
        chapter_statuses, "in-progress"
    )
    assert results["ch1"] is True  # draft -> in-progress
    assert results["ch2"] is True  # in-progress -> in-progress (same)
    assert results["ch3"] is True  # completed -> in-progress (valid backward transition)
    
    # Update to completed
    results = status_service.validate_bulk_status_update(
        chapter_statuses, "completed"
    )
    assert results["ch1"] is True  # draft -> completed
    assert results["ch2"] is True  # in-progress -> completed
    assert results["ch3"] is True  # completed -> completed (same)


def test_validate_status_data(status_service):
    """Test status data validation"""
    # Valid statuses
    assert status_service.validate_status_data("draft") == ChapterStatus.DRAFT
    assert status_service.validate_status_data("completed") == ChapterStatus.COMPLETED
    
    # Invalid status
    with pytest.raises(ValueError) as exc_info:
        status_service.validate_status_data("invalid_status")
    assert "Invalid status" in str(exc_info.value)


def test_validate_bulk_update(status_service):
    """Test bulk update validation"""
    # Valid updates
    updates = [
        {"chapter_id": "ch1", "status": "draft"},
        {"chapter_id": "ch2", "status": "in-progress"},
        {"chapter_id": "ch3", "status": ChapterStatus.COMPLETED}
    ]
    
    result = status_service.validate_bulk_update(updates)
    assert result["valid"] is True
    assert result["valid_count"] == 3
    assert result["invalid_count"] == 0
    
    # Invalid updates
    invalid_updates = [
        {"chapter_id": "ch1", "status": "draft"},
        {"status": "in-progress"},  # Missing chapter_id
        {"chapter_id": "ch3"},  # Missing status
        {"chapter_id": "ch4", "status": "invalid_status"}  # Invalid status
    ]
    
    result = status_service.validate_bulk_update(invalid_updates)
    assert result["valid"] is False
    assert result["valid_count"] == 1
    assert result["invalid_count"] == 3
    assert len(result["invalid_updates"]) == 3