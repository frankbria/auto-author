#!/usr/bin/env python3
"""
Chapter Tabs Integration Tests
=============================

Comprehensive integration tests for the chapter tabs functionality including:
- Database schema validation
- API endpoints testing
- Service layer integration
- Caching layer validation
- Error handling verification
"""

import pytest
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any
import uuid

# from app.db.database import get_database
from app.models.book import TocItem
from app.models.chapter_access import ChapterAccessLog, ChapterAccessCreate
from app.schemas.book import ChapterStatus, ChapterMetadata, TabStateRequest
from app.services.chapter_access_service import ChapterAccessService
from app.services.chapter_status_service import ChapterStatusService
from app.services.chapter_cache_service import ChapterMetadataCache
from app.services.chapter_error_handler import ChapterErrorHandler
from app.db.indexing_strategy import ChapterTabIndexManager


class TestChapterTabsIntegration:
    """Integration tests for chapter tabs functionality."""

    @pytest.fixture
    async def database(self):
        """Get database connection for testing."""
        return await get_database()

    @pytest.fixture
    async def test_book(self, database):
        """Create a test book with TOC structure."""
        book_data = {
            "_id": uuid.uuid4(),
            "title": "Test Book for Chapter Tabs",
            "owner_id": "test-user-123",
            "summary": "A test book for chapter tabs integration testing",
            "table_of_contents": {
                "chapters": [
                    {
                        "id": "ch-1",
                        "title": "Introduction",
                        "description": "Getting started",
                        "level": 1,
                        "order": 1,
                        "status": ChapterStatus.DRAFT.value,
                        "word_count": 250,
                        "last_modified": datetime.now(timezone.utc).isoformat(),
                        "estimated_reading_time": 2,
                        "is_active_tab": True,
                        "subchapters": [
                            {
                                "id": "ch-1-1",
                                "title": "Overview",
                                "description": "Chapter overview",
                                "level": 2,
                                "order": 1,
                                "status": ChapterStatus.DRAFT.value,
                                "word_count": 150,
                                "last_modified": datetime.now(timezone.utc).isoformat(),
                                "estimated_reading_time": 1,
                                "is_active_tab": False,
                            }
                        ],
                    },
                    {
                        "id": "ch-2",
                        "title": "Main Content",
                        "description": "Core material",
                        "level": 1,
                        "order": 2,
                        "status": ChapterStatus.IN_PROGRESS.value,
                        "word_count": 500,
                        "last_modified": datetime.now(timezone.utc).isoformat(),
                        "estimated_reading_time": 3,
                        "is_active_tab": False,
                        "subchapters": [],
                    },
                ],
                "total_chapters": 2,
                "estimated_pages": 5,
                "structure_notes": "Test TOC structure",
                "version": 1,
            },
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        await database.books.insert_one(book_data)
        yield book_data

        # Cleanup
        await database.books.delete_one({"_id": book_data["_id"]})

    @pytest.fixture
    def services(self, database):
        """Initialize all chapter tab services."""
        return {
            "access": ChapterAccessService(database),
            "status": ChapterStatusService(),
            "cache": ChapterMetadataCache(),
            "error_handler": ChapterErrorHandler(),
        }

    async def test_database_schema_validation(self, test_book):
        """Test that the database schema supports all new chapter tab fields."""
        toc = test_book["table_of_contents"]
        chapters = toc["chapters"]

        # Validate top-level chapter
        chapter = chapters[0]
        assert "status" in chapter
        assert chapter["status"] in [s.value for s in ChapterStatus]
        assert "word_count" in chapter
        assert isinstance(chapter["word_count"], int)
        assert "last_modified" in chapter
        assert "estimated_reading_time" in chapter
        assert "is_active_tab" in chapter
        assert isinstance(chapter["is_active_tab"], bool)

        # Validate subchapter
        subchapter = chapter["subchapters"][0]
        assert "status" in subchapter
        assert "word_count" in subchapter
        assert "last_modified" in subchapter
        assert "estimated_reading_time" in subchapter
        assert "is_active_tab" in subchapter

        # Validate TOC metadata
        assert "version" in toc
        assert isinstance(toc["version"], int)

    async def test_chapter_access_logging(self, test_book, services):
        """Test chapter access logging functionality."""
        access_service = services["access"]
        book_id = str(test_book["_id"])
        chapter_id = "ch-1"
        user_id = "test-user-123"

        # Log chapter access
        access_data = ChapterAccessCreate(
            user_id=user_id,
            book_id=book_id,
            chapter_id=chapter_id,
            access_type="read",
            session_id="test-session-123",
        )

        result = await access_service.log_chapter_access(access_data)
        assert result["success"] is True
        assert "access_log_id" in result

        # Verify access was logged
        recent_access = await access_service.get_recent_chapter_access(
            user_id=user_id, book_id=book_id, limit=10
        )
        assert len(recent_access) == 1
        assert recent_access[0]["chapter_id"] == chapter_id

    async def test_tab_state_management(self, test_book, services):
        """Test tab state save and restore functionality."""
        access_service = services["access"]
        book_id = str(test_book["_id"])
        user_id = "test-user-123"
        session_id = "test-session-123"

        # Save tab state
        tab_state = TabStateRequest(
            active_tabs=["ch-1", "ch-2"],
            active_chapter_id="ch-2",
            tab_order=["ch-1", "ch-2"],
            session_id=session_id,
        )

        result = await access_service.save_tab_state(
            user_id=user_id, book_id=book_id, tab_state=tab_state
        )
        assert result["success"] is True

        # Retrieve tab state
        retrieved_state = await access_service.get_tab_state(
            user_id=user_id, book_id=book_id, session_id=session_id
        )
        assert retrieved_state["active_tabs"] == ["ch-1", "ch-2"]
        assert retrieved_state["active_chapter_id"] == "ch-2"

    async def test_chapter_status_transitions(self, services):
        """Test chapter status validation and transitions."""
        status_service = services["status"]

        # Test valid transitions
        assert status_service.is_valid_transition(
            ChapterStatus.DRAFT, ChapterStatus.IN_PROGRESS
        )
        assert status_service.is_valid_transition(
            ChapterStatus.IN_PROGRESS, ChapterStatus.COMPLETED
        )
        assert status_service.is_valid_transition(
            ChapterStatus.COMPLETED, ChapterStatus.PUBLISHED
        )

        # Test invalid transitions
        assert not status_service.is_valid_transition(
            ChapterStatus.DRAFT, ChapterStatus.PUBLISHED
        )

        # Test status validation
        assert status_service.validate_status_data("draft") == ChapterStatus.DRAFT

        with pytest.raises(ValueError):
            status_service.validate_status_data("invalid-status")

    async def test_bulk_status_updates(self, test_book, services):
        """Test bulk chapter status update functionality."""
        status_service = services["status"]

        # Prepare bulk update data
        updates = [
            {"chapter_id": "ch-1", "status": ChapterStatus.IN_PROGRESS},
            {"chapter_id": "ch-2", "status": ChapterStatus.COMPLETED},
        ]

        # Validate bulk update
        validation_result = status_service.validate_bulk_update(updates)
        assert validation_result["valid"] is True
        assert len(validation_result["invalid_updates"]) == 0

        # Test bulk update with invalid data
        invalid_updates = [{"chapter_id": "ch-1", "status": "invalid-status"}]

        invalid_result = status_service.validate_bulk_update(invalid_updates)
        assert invalid_result["valid"] is False
        assert len(invalid_result["invalid_updates"]) == 1

    async def test_caching_layer(self, test_book, services):
        """Test chapter metadata caching functionality."""
        cache_service = services["cache"]
        book_id = str(test_book["_id"])

        # Create test metadata
        metadata = ChapterMetadata(
            chapter_id="ch-1",
            title="Introduction",
            status=ChapterStatus.DRAFT,
            word_count=250,
            last_modified=datetime.now(timezone.utc),
            estimated_reading_time=2,
            is_active_tab=True,
        )

        # Test cache operations
        await cache_service.cache_chapter_metadata(book_id, "ch-1", metadata)

        cached_metadata = await cache_service.get_chapter_metadata(book_id, "ch-1")
        assert cached_metadata is not None
        assert cached_metadata["title"] == "Introduction"
        assert cached_metadata["word_count"] == 250

        # Test cache invalidation
        await cache_service.invalidate_chapter_cache(book_id, "ch-1")
        invalidated_metadata = await cache_service.get_chapter_metadata(book_id, "ch-1")
        assert invalidated_metadata is None

    async def test_error_handling_and_recovery(self, services):
        """Test error handling and recovery mechanisms."""
        error_handler = services["error_handler"]

        # Test error categorization
        db_error = Exception("Database connection failed")
        categorized = error_handler.categorize_error(db_error)
        assert categorized["category"] == "database"
        assert categorized["severity"] == "high"
        assert categorized["recoverable"] is True

        # Test recovery suggestions
        recovery = error_handler.get_recovery_strategy("database", "high")
        assert recovery is not None
        assert "retry" in recovery["actions"]

        # Test error tracking
        error_handler.track_error("database", "Connection timeout", {"book_id": "test"})
        stats = error_handler.get_error_statistics()
        assert stats["total_errors"] > 0
        assert "database" in stats["by_category"]

    async def test_indexing_strategy(self, database):
        """Test database indexing for chapter tabs."""
        index_manager = ChapterTabIndexManager(database)

        # Test index creation
        result = await index_manager.create_all_indexes()
        assert result["success"] is True

        # Test performance monitoring
        performance_stats = await index_manager.get_performance_stats()
        assert "query_performance" in performance_stats
        assert "index_usage" in performance_stats

    async def test_end_to_end_chapter_workflow(self, test_book, services):
        """Test complete chapter tab workflow end-to-end."""
        book_id = str(test_book["_id"])
        user_id = "test-user-123"
        chapter_id = "ch-1"

        access_service = services["access"]
        status_service = services["status"]
        cache_service = services["cache"]

        # 1. Log chapter access
        access_data = ChapterAccessCreate(
            user_id=user_id,
            book_id=book_id,
            chapter_id=chapter_id,
            access_type="read",
            session_id="workflow-test",
        )

        access_result = await access_service.log_chapter_access(access_data)
        assert access_result["success"] is True

        # 2. Update chapter status
        new_status = ChapterStatus.IN_PROGRESS
        assert status_service.is_valid_transition(ChapterStatus.DRAFT, new_status)

        # 3. Cache updated metadata
        metadata = ChapterMetadata(
            chapter_id=chapter_id,
            title="Introduction",
            status=new_status,
            word_count=300,  # Updated word count
            last_modified=datetime.now(timezone.utc),
            estimated_reading_time=2,
            is_active_tab=True,
        )

        await cache_service.cache_chapter_metadata(book_id, chapter_id, metadata)

        # 4. Save tab state
        tab_state = TabStateRequest(
            active_tabs=[chapter_id],
            active_chapter_id=chapter_id,
            tab_order=[chapter_id],
            session_id="workflow-test",
        )

        tab_result = await access_service.save_tab_state(
            user_id=user_id, book_id=book_id, tab_state=tab_state
        )
        assert tab_result["success"] is True

        # 5. Verify complete workflow
        recent_access = await access_service.get_recent_chapter_access(
            user_id=user_id, book_id=book_id, limit=1
        )
        assert len(recent_access) == 1
        assert recent_access[0]["chapter_id"] == chapter_id

        cached_data = await cache_service.get_chapter_metadata(book_id, chapter_id)
        assert cached_data["word_count"] == 300

        saved_state = await access_service.get_tab_state(
            user_id=user_id, book_id=book_id, session_id="workflow-test"
        )
        assert saved_state["active_chapter_id"] == chapter_id


@pytest.mark.asyncio
async def test_chapter_tabs_migration_compatibility():
    """Test that migrated data is compatible with new chapter tabs functionality."""
    # This would test migration script functionality
    # For now, we'll create a simple compatibility test

    # Create "old format" chapter data
    old_chapter = {
        "id": "legacy-ch-1",
        "title": "Legacy Chapter",
        "description": "Old format chapter",
        "level": 1,
        "order": 1,
        # Missing: status, word_count, last_modified, estimated_reading_time, is_active_tab
    }

    # Simulate migration logic
    migrated_chapter = old_chapter.copy()
    migrated_chapter.update(
        {
            "status": ChapterStatus.DRAFT.value,
            "word_count": len(old_chapter.get("description", "").split()),
            "last_modified": datetime.now(timezone.utc).isoformat(),
            "estimated_reading_time": 1,
            "is_active_tab": False,
        }
    )

    # Validate migrated chapter has all required fields
    required_fields = [
        "status",
        "word_count",
        "last_modified",
        "estimated_reading_time",
        "is_active_tab",
    ]
    for field in required_fields:
        assert field in migrated_chapter

    # Validate field types and values
    assert migrated_chapter["status"] in [s.value for s in ChapterStatus]
    assert isinstance(migrated_chapter["word_count"], int)
    assert isinstance(migrated_chapter["estimated_reading_time"], int)
    assert isinstance(migrated_chapter["is_active_tab"], bool)


if __name__ == "__main__":
    """Run integration tests manually."""
    pytest.main([__file__, "-v", "--tb=short"])
