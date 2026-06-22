"""
Chapter Tabs Integration Tests (issue #45)

Integration tests for chapter-tabs functionality against a real local MongoDB
(via the ``motor_reinit_db`` fixture from conftest). Covers the data flow that
the shipped services actually implement:

- Chapter access logging + recent-chapter retrieval (``ChapterAccessService``)
- Tab-state persistence and restore (``ChapterAccessService``)
- Status transition / bulk-update validation (``ChapterStatusService``)
- Index creation (``ChapterTabIndexManager``)

This replaces an older ``run_test_*`` file (never collected by pytest) that was
written against an imagined API — `ChapterAccessService(database)`,
`cache_chapter_metadata`, `categorize_error`, etc. — none of which exists in the
current service layer. Tests here use the real signatures only.
"""

import pytest
from datetime import datetime, timezone
from bson import ObjectId

from app.db import base
from app.schemas.book import ChapterStatus
from app.services.chapter_access_service import ChapterAccessService
from app.services.chapter_status_service import ChapterStatusService
from app.db.indexing_strategy import ChapterTabIndexManager

USER_ID = "test-user-123"


@pytest.fixture
def database(motor_reinit_db):
    """Real test database (rebound by motor_reinit_db)."""
    return base._db


@pytest.fixture
def access_service():
    return ChapterAccessService()


@pytest.fixture
def status_service():
    return ChapterStatusService()


@pytest.fixture
async def test_book(database):
    """Insert a book with a TOC structure; return its id."""
    book_doc = {
        "_id": ObjectId(),
        "title": "Test Book for Chapter Tabs",
        "owner_id": USER_ID,
        "table_of_contents": {
            "chapters": [
                {
                    "id": "ch-1", "title": "Introduction", "level": 1, "order": 1,
                    "status": ChapterStatus.DRAFT.value, "word_count": 250,
                    "is_active_tab": True, "subchapters": [],
                },
                {
                    "id": "ch-2", "title": "Main Content", "level": 1, "order": 2,
                    "status": ChapterStatus.IN_PROGRESS.value, "word_count": 500,
                    "is_active_tab": False, "subchapters": [],
                },
            ],
            "version": 1,
        },
    }
    await base.books_collection.insert_one(book_doc)
    return str(book_doc["_id"])


# --- Access logging (real DB) -------------------------------------------------

@pytest.mark.asyncio
async def test_access_logging_and_recent_chapters(access_service, test_book):
    """Logged chapter views are persisted and surfaced via recent-chapters."""
    log_id = await access_service.log_access(
        user_id=USER_ID, book_id=test_book, chapter_id="ch-1",
        access_type="view", session_id="sess-1",
    )
    assert log_id  # inserted id returned

    recent = await access_service.get_user_recent_chapters(
        user_id=USER_ID, book_id=test_book, limit=10
    )
    assert any(entry["_id"] == "ch-1" for entry in recent)


@pytest.mark.asyncio
async def test_tab_state_save_and_restore(access_service, test_book):
    """Tab state round-trips through the database."""
    await access_service.save_tab_state(
        user_id=USER_ID, book_id=test_book,
        active_chapter_id="ch-2", open_tab_ids=["ch-1", "ch-2"],
        tab_order=["ch-1", "ch-2"], session_id="sess-1",
    )

    state = await access_service.get_user_tab_state(user_id=USER_ID, book_id=test_book)
    assert state is not None
    assert state["metadata"]["active_chapter_id"] == "ch-2"
    assert state["metadata"]["open_tab_ids"] == ["ch-1", "ch-2"]


# --- Status validation (pure logic) ------------------------------------------

@pytest.mark.asyncio
async def test_status_transitions(status_service):
    assert status_service.is_valid_transition(ChapterStatus.DRAFT, ChapterStatus.IN_PROGRESS)
    assert status_service.is_valid_transition(ChapterStatus.IN_PROGRESS, ChapterStatus.COMPLETED)
    assert not status_service.is_valid_transition(ChapterStatus.DRAFT, ChapterStatus.PUBLISHED)

    assert status_service.validate_status_data("draft") == ChapterStatus.DRAFT
    with pytest.raises(ValueError):
        status_service.validate_status_data("invalid-status")


@pytest.mark.asyncio
async def test_bulk_status_update_validation(status_service):
    valid = status_service.validate_bulk_update([
        {"chapter_id": "ch-1", "status": ChapterStatus.IN_PROGRESS},
        {"chapter_id": "ch-2", "status": ChapterStatus.COMPLETED},
    ])
    assert valid["valid"] is True
    assert valid["invalid_count"] == 0

    invalid = status_service.validate_bulk_update([
        {"chapter_id": "ch-1", "status": "invalid-status"},
    ])
    assert invalid["valid"] is False
    assert invalid["invalid_count"] == 1


# --- Indexing (real DB) -------------------------------------------------------

@pytest.mark.asyncio
async def test_index_creation(database):
    index_manager = ChapterTabIndexManager(database)
    result = await index_manager.create_all_indexes()
    assert result["success"] is True


# --- Migration compatibility (pure logic) ------------------------------------

@pytest.mark.asyncio
async def test_chapter_tabs_migration_compatibility():
    """Legacy chapter dicts can be migrated to include the new tab fields."""
    old_chapter = {"id": "legacy-ch-1", "title": "Legacy Chapter",
                   "description": "Old format chapter", "level": 1, "order": 1}

    migrated = old_chapter.copy()
    migrated.update({
        "status": ChapterStatus.DRAFT.value,
        "word_count": len(old_chapter.get("description", "").split()),
        "last_modified": datetime.now(timezone.utc).isoformat(),
        "estimated_reading_time": 1,
        "is_active_tab": False,
    })

    for field in ["status", "word_count", "last_modified",
                  "estimated_reading_time", "is_active_tab"]:
        assert field in migrated
    assert migrated["status"] in [s.value for s in ChapterStatus]
    assert isinstance(migrated["word_count"], int)
