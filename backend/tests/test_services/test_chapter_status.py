"""Test chapter status service"""

import pytest
from app.services.chapter_status_service import ChapterStatusService
from app.schemas.book import ChapterStatus


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
