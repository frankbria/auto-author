import pytest
from datetime import datetime, timezone
from bson import ObjectId
from app.models.chapter_access import ChapterAccessLog
from app.schemas.book import ChapterStatus

@pytest.fixture
def chapter_with_metadata():
    """Create a chapter with complete metadata for testing tab functionality"""
    return {
        "id": "ch-test-1",
        "title": "Test Chapter",
        "status": ChapterStatus.DRAFT.value,
        "last_modified": datetime.now(timezone.utc).isoformat(),
        "word_count": 1000,
        "estimated_reading_time": 5,
        "level": 1,
        "order": 1,
        "has_content": True,
        "content": "This is test chapter content.",
        "parent_id": None
    }

@pytest.fixture
def book_with_chapters(test_book):
    """Create a test book with multiple chapters for tab testing"""
    chapters = []
    for i in range(1, 6):
        status_map = {1: ChapterStatus.DRAFT, 2: ChapterStatus.IN_PROGRESS, 
                     3: ChapterStatus.COMPLETED, 4: ChapterStatus.REVIEW, 5: ChapterStatus.PUBLISHED}
        
        chapters.append({
            "id": f"ch-{i}",
            "title": f"Chapter {i}",
            "status": status_map.get(i, ChapterStatus.DRAFT).value,
            "last_modified": datetime.now(timezone.utc).isoformat(),
            "word_count": i * 200,
            "estimated_reading_time": i,
            "level": 1,
            "order": i,
            "has_content": i > 1,
            "content": f"Content for chapter {i}" if i > 1 else "",
            "parent_id": None
        })
    
    # Add nested chapter (subchapter)
    chapters.append({
        "id": "ch-2-1",
        "title": "Subchapter 2.1",
        "status": ChapterStatus.DRAFT.value,
        "last_modified": datetime.now(timezone.utc).isoformat(),
        "word_count": 150,
        "estimated_reading_time": 1,
        "level": 2,
        "order": 1,
        "has_content": True,
        "content": "This is a subchapter content",
        "parent_id": "ch-2"
    })

    book = test_book.copy()
    book["table_of_contents"] = {
        "chapters": chapters,
        "total_chapters": len(chapters),
        "estimated_pages": sum(ch.get("estimated_reading_time", 0) for ch in chapters),
        "status": "edited",
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    return book

@pytest.fixture
def book_with_many_chapters(test_book):
    """Create a book with 50+ chapters for performance testing"""
    chapters = []
    for i in range(1, 51):
        chapters.append({
            "id": f"ch-{i}",
            "title": f"Chapter {i}: Long Title That Tests Overflow Behavior",
            "status": ChapterStatus.DRAFT.value,
            "last_modified": datetime.now(timezone.utc).isoformat(),
            "word_count": i * 100,
            "estimated_reading_time": max(1, i // 2),
            "level": 1 if i % 10 != 0 else 2,  # Every 10th chapter is a subchapter
            "order": i,
            "has_content": i % 3 != 0,
            "content": f"Content for chapter {i}" if i % 3 != 0 else "",
            "parent_id": f"ch-{i-1}" if i % 10 == 0 and i > 1 else None
        })

    book = test_book.copy()
    book["table_of_contents"] = {
        "chapters": chapters,
        "total_chapters": len(chapters),
        "estimated_pages": sum(ch.get("estimated_reading_time", 0) for ch in chapters),
        "status": "edited",
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    return book

@pytest.fixture
def tab_state_data():
    """Tab state data for testing persistence"""
    return {
        "active_chapter_id": "ch-2",
        "open_tab_ids": ["ch-1", "ch-2", "ch-3"],
        "tab_order": ["ch-1", "ch-2", "ch-3"]
    }

@pytest.fixture
async def chapter_access_logs_fixture(test_user, test_book):
    """Generate sample chapter access logs for testing"""
    from app.db.database import get_collection
    
    logs = []
    chapter_ids = [f"ch-{i}" for i in range(1, 6)]
    access_types = ["view", "edit", "tab_state", "status_update"]
    
    for i, chapter_id in enumerate(chapter_ids):
        for access_type in access_types:
            logs.append(
                ChapterAccessLog(
                    user_id=test_user["clerk_id"],
                    book_id=test_book["id"],
                    chapter_id=chapter_id,
                    access_type=access_type,
                    timestamp=datetime.now(timezone.utc),
                    metadata={"test": True, "chapter_index": i}
                ).model_dump(by_alias=True)
            )
    
    # Insert logs into test database
    collection = await get_collection("chapter_access_logs")
    await collection.insert_many(logs)
    
    return logs
