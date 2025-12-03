"""
Comprehensive tests for TOC transaction handling.

Tests cover:
1. Transaction Support (transaction mode, fallback mode, rollback)
2. Optimistic Locking (version conflicts, concurrent updates)
3. Chapter Operations (add, update, delete, reorder)
4. Concurrency & Isolation (concurrent adds, updates)

Target: 85%+ coverage for toc_transactions.py (currently 15%)
"""

import pytest
import asyncio
from datetime import datetime, timezone
from bson import ObjectId
from typing import Dict, Any
from unittest.mock import AsyncMock, patch

from app.db import toc_transactions
from app.db import base


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================

@pytest.fixture(autouse=True)
def mock_audit_log():
    """Mock audit log creation to avoid session conflicts"""
    with patch("app.db.toc_transactions.create_audit_log", new_callable=AsyncMock) as mock:
        mock.return_value = None
        yield mock


@pytest.fixture
def sample_book_data():
    """Sample book data with initial TOC"""
    return {
        "title": "Test Book",
        "owner_id": "test_clerk_id",
        "description": "A test book for TOC transactions",
        "genre": "Fiction",
        "table_of_contents": {
            "chapters": [
                {
                    "id": "ch1",
                    "title": "Chapter 1",
                    "level": 1,
                    "order": 1,
                    "description": "First chapter"
                },
                {
                    "id": "ch2",
                    "title": "Chapter 2",
                    "level": 1,
                    "order": 2,
                    "description": "Second chapter",
                    "subchapters": [
                        {
                            "id": "ch2-1",
                            "title": "Subchapter 2.1",
                            "level": 2,
                            "order": 1,
                            "description": "First subchapter"
                        }
                    ]
                }
            ],
            "version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "generated"
        },
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }


@pytest.fixture
def sample_chapter():
    """Sample chapter data"""
    return {
        "title": "New Chapter",
        "level": 1,
        "order": 3,
        "description": "A new chapter to add"
    }


@pytest.fixture
def sample_subchapter():
    """Sample subchapter data"""
    return {
        "title": "New Subchapter",
        "level": 2,
        "order": 2,
        "description": "A new subchapter"
    }


# ============================================================================
# CATEGORY 1: TOC UPDATE TESTS (Transaction Support & Optimistic Locking)
# ============================================================================

@pytest.mark.asyncio
async def test_update_toc_success(motor_reinit_db, sample_book_data):
    """Test successful TOC update with version increment"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    user_clerk_id = sample_book_data["owner_id"]

    new_toc = {
        "chapters": [
            {
                "id": "ch1",
                "title": "Updated Chapter 1",
                "level": 1,
                "order": 1
            }
        ],
        "expected_version": 1
    }

    updated_toc = await toc_transactions.update_toc_with_transaction(
        book_id, new_toc, user_clerk_id
    )

    assert updated_toc["version"] == 2
    assert updated_toc["status"] == "edited"
    assert len(updated_toc["chapters"]) == 1
    assert updated_toc["chapters"][0]["title"] == "Updated Chapter 1"
    assert "updated_at" in updated_toc


@pytest.mark.asyncio
async def test_update_toc_version_conflict(motor_reinit_db, sample_book_data):
    """Test optimistic locking - version conflict detection"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    user_clerk_id = sample_book_data["owner_id"]

    # First update (version 1 -> 2)
    toc_data = {
        "chapters": [{"id": "ch1", "title": "First Update"}],
        "expected_version": 1
    }
    updated_toc = await toc_transactions.update_toc_with_transaction(
        book_id, toc_data, user_clerk_id
    )
    assert updated_toc["version"] == 2

    # Try to update with stale version (should fail)
    stale_toc_data = {
        "chapters": [{"id": "ch2", "title": "Stale Update"}],
        "expected_version": 1  # Stale version!
    }

    with pytest.raises(ValueError, match="Version conflict"):
        await toc_transactions.update_toc_with_transaction(
            book_id, stale_toc_data, user_clerk_id
        )


@pytest.mark.asyncio
async def test_update_toc_book_not_found(motor_reinit_db):
    """Test TOC update with non-existent book"""
    fake_book_id = str(ObjectId())

    toc_data = {
        "chapters": [],
        "expected_version": 1
    }

    with pytest.raises(ValueError, match="Book not found"):
        await toc_transactions.update_toc_with_transaction(
            fake_book_id, toc_data, "test_clerk_id"
        )


@pytest.mark.asyncio
async def test_update_toc_unauthorized(motor_reinit_db, sample_book_data):
    """Test TOC update with wrong user (not authorized)"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    wrong_user = "wrong_clerk_id"

    toc_data = {
        "chapters": [],
        "expected_version": 1
    }

    with pytest.raises(ValueError, match="Not authorized"):
        await toc_transactions.update_toc_with_transaction(
            book_id, toc_data, wrong_user
        )


@pytest.mark.asyncio
async def test_update_toc_assigns_chapter_ids(motor_reinit_db, sample_book_data):
    """Test that TOC update assigns IDs to chapters without them"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    user_clerk_id = sample_book_data["owner_id"]

    toc_data = {
        "chapters": [
            {
                "title": "Chapter without ID",
                "level": 1,
                "order": 1
            },
            {
                "title": "Parent chapter",
                "level": 1,
                "order": 2,
                "subchapters": [
                    {
                        "title": "Subchapter without ID",
                        "level": 2,
                        "order": 1
                    }
                ]
            }
        ],
        "expected_version": 1
    }

    updated_toc = await toc_transactions.update_toc_with_transaction(
        book_id, toc_data, user_clerk_id
    )

    # Verify IDs were assigned
    assert "id" in updated_toc["chapters"][0]
    assert updated_toc["chapters"][0]["id"]
    assert "id" in updated_toc["chapters"][1]
    assert updated_toc["chapters"][1]["id"]
    assert "id" in updated_toc["chapters"][1]["subchapters"][0]
    assert updated_toc["chapters"][1]["subchapters"][0]["id"]


@pytest.mark.asyncio
async def test_update_toc_invalid_book_id_format():
    """Test TOC update with invalid book ID format"""
    invalid_book_id = "not-a-valid-objectid"

    toc_data = {
        "chapters": [],
        "expected_version": 1
    }

    with pytest.raises(ValueError, match="Invalid book ID format"):
        await toc_transactions.update_toc_with_transaction(
            invalid_book_id, toc_data, "test_clerk_id"
        )


# ============================================================================
# CATEGORY 2: ADD CHAPTER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_add_top_level_chapter(motor_reinit_db, sample_book_data, sample_chapter):
    """Test adding a top-level chapter"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    book_oid = result.inserted_id
    user_clerk_id = sample_book_data["owner_id"]

    added_chapter = await toc_transactions.add_chapter_with_transaction(
        book_id, sample_chapter, user_clerk_id
    )

    assert added_chapter["id"]
    assert added_chapter["title"] == sample_chapter["title"]
    assert "created_at" in added_chapter
    assert "updated_at" in added_chapter

    # Verify chapter was added to book
    book = await base.books_collection.find_one({"_id": book_oid})
    assert book["table_of_contents"]["version"] == 2
    assert len(book["table_of_contents"]["chapters"]) == 3


@pytest.mark.asyncio
async def test_add_subchapter(motor_reinit_db, sample_book_data, sample_subchapter):
    """Test adding a subchapter to existing chapter"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    book_oid = result.inserted_id
    user_clerk_id = sample_book_data["owner_id"]
    parent_chapter_id = "ch2"

    added_subchapter = await toc_transactions.add_chapter_with_transaction(
        book_id, sample_subchapter, user_clerk_id, parent_chapter_id
    )

    assert added_subchapter["id"]
    assert added_subchapter["title"] == sample_subchapter["title"]

    # Verify subchapter was added
    book = await base.books_collection.find_one({"_id": book_oid})
    ch2 = next(ch for ch in book["table_of_contents"]["chapters"] if ch["id"] == "ch2")
    assert len(ch2["subchapters"]) == 2


@pytest.mark.asyncio
async def test_add_subchapter_parent_not_found(motor_reinit_db, sample_book_data, sample_subchapter):
    """Test adding subchapter when parent chapter doesn't exist"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    user_clerk_id = sample_book_data["owner_id"]
    fake_parent_id = "non-existent-chapter"

    with pytest.raises(ValueError, match="Parent chapter not found"):
        await toc_transactions.add_chapter_with_transaction(
            book_id, sample_subchapter, user_clerk_id, fake_parent_id
        )


@pytest.mark.asyncio
async def test_add_chapter_book_not_found(motor_reinit_db, sample_chapter):
    """Test adding chapter to non-existent book"""
    fake_book_id = str(ObjectId())

    with pytest.raises(ValueError, match="Book not found or not authorized"):
        await toc_transactions.add_chapter_with_transaction(
            fake_book_id, sample_chapter, "test_clerk_id"
        )


@pytest.mark.asyncio
async def test_add_chapter_to_parent_without_subchapters(motor_reinit_db, sample_book_data):
    """Test adding first subchapter to chapter that has no subchapters array"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    book_oid = result.inserted_id
    user_clerk_id = sample_book_data["owner_id"]

    # Add subchapter to ch1 (which has no subchapters array)
    subchapter = {
        "title": "First Subchapter of Ch1",
        "level": 2,
        "order": 1
    }

    added = await toc_transactions.add_chapter_with_transaction(
        book_id, subchapter, user_clerk_id, "ch1"
    )

    assert added["id"]

    # Verify subchapters array was created
    book = await base.books_collection.find_one({"_id": book_oid})
    ch1 = next(ch for ch in book["table_of_contents"]["chapters"] if ch["id"] == "ch1")
    assert "subchapters" in ch1
    assert len(ch1["subchapters"]) == 1


# ============================================================================
# CATEGORY 3: UPDATE CHAPTER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_update_chapter_success(motor_reinit_db, sample_book_data):
    """Test updating a chapter"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    book_oid = result.inserted_id
    user_clerk_id = sample_book_data["owner_id"]
    chapter_id = "ch1"

    updates = {
        "title": "Updated Chapter 1 Title",
        "description": "Updated description"
    }

    updated_chapter = await toc_transactions.update_chapter_with_transaction(
        book_id, chapter_id, updates, user_clerk_id
    )

    assert updated_chapter["title"] == "Updated Chapter 1 Title"
    assert updated_chapter["description"] == "Updated description"
    assert "updated_at" in updated_chapter

    # Verify TOC version incremented
    book = await base.books_collection.find_one({"_id": book_oid})
    assert book["table_of_contents"]["version"] == 2


@pytest.mark.asyncio
async def test_update_subchapter_success(motor_reinit_db, sample_book_data):
    """Test updating a subchapter (recursive search)"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    user_clerk_id = sample_book_data["owner_id"]
    subchapter_id = "ch2-1"

    updates = {
        "title": "Updated Subchapter Title"
    }

    updated_subchapter = await toc_transactions.update_chapter_with_transaction(
        book_id, subchapter_id, updates, user_clerk_id
    )

    assert updated_subchapter["title"] == "Updated Subchapter Title"


@pytest.mark.asyncio
async def test_update_chapter_not_found(motor_reinit_db, sample_book_data):
    """Test updating non-existent chapter"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    user_clerk_id = sample_book_data["owner_id"]
    fake_chapter_id = "non-existent-chapter"

    updates = {"title": "This won't work"}

    with pytest.raises(ValueError, match="Chapter not found"):
        await toc_transactions.update_chapter_with_transaction(
            book_id, fake_chapter_id, updates, user_clerk_id
        )


@pytest.mark.asyncio
async def test_update_chapter_unauthorized(motor_reinit_db, sample_book_data):
    """Test updating chapter with wrong user"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    wrong_user = "wrong_clerk_id"

    updates = {"title": "Unauthorized update"}

    with pytest.raises(ValueError, match="Book not found or not authorized"):
        await toc_transactions.update_chapter_with_transaction(
            book_id, "ch1", updates, wrong_user
        )


# ============================================================================
# CATEGORY 4: DELETE CHAPTER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_delete_top_level_chapter(motor_reinit_db, sample_book_data):
    """Test deleting a top-level chapter"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    book_oid = result.inserted_id
    user_clerk_id = sample_book_data["owner_id"]
    chapter_id = "ch1"

    result = await toc_transactions.delete_chapter_with_transaction(
        book_id, chapter_id, user_clerk_id
    )

    assert result is True

    # Verify chapter was deleted
    book = await base.books_collection.find_one({"_id": book_oid})
    assert len(book["table_of_contents"]["chapters"]) == 1
    assert book["table_of_contents"]["chapters"][0]["id"] == "ch2"
    assert book["table_of_contents"]["version"] == 2


@pytest.mark.asyncio
async def test_delete_subchapter(motor_reinit_db, sample_book_data):
    """Test deleting a subchapter"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    book_oid = result.inserted_id
    user_clerk_id = sample_book_data["owner_id"]
    subchapter_id = "ch2-1"

    result = await toc_transactions.delete_chapter_with_transaction(
        book_id, subchapter_id, user_clerk_id
    )

    assert result is True

    # Verify subchapter was deleted
    book = await base.books_collection.find_one({"_id": book_oid})
    ch2 = next(ch for ch in book["table_of_contents"]["chapters"] if ch["id"] == "ch2")
    assert len(ch2["subchapters"]) == 0


@pytest.mark.asyncio
async def test_delete_chapter_cascade_subchapters(motor_reinit_db, sample_book_data):
    """Test deleting chapter with subchapters (cascade delete)"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    book_oid = result.inserted_id
    user_clerk_id = sample_book_data["owner_id"]

    # Delete ch2 which has subchapters
    result = await toc_transactions.delete_chapter_with_transaction(
        book_id, "ch2", user_clerk_id
    )

    assert result is True

    # Verify chapter and all subchapters were deleted
    book = await base.books_collection.find_one({"_id": book_oid})
    assert len(book["table_of_contents"]["chapters"]) == 1
    assert book["table_of_contents"]["chapters"][0]["id"] == "ch1"


@pytest.mark.asyncio
async def test_delete_chapter_not_found(motor_reinit_db, sample_book_data):
    """Test deleting non-existent chapter"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    user_clerk_id = sample_book_data["owner_id"]
    fake_chapter_id = "non-existent-chapter"

    with pytest.raises(ValueError, match="Chapter not found"):
        await toc_transactions.delete_chapter_with_transaction(
            book_id, fake_chapter_id, user_clerk_id
        )


# ============================================================================
# CATEGORY 5: REORDER CHAPTERS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_reorder_chapters_success(motor_reinit_db, sample_book_data):
    """Test reordering chapters"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    user_clerk_id = sample_book_data["owner_id"]

    # Reverse the order of chapters
    chapter_orders = [
        {"id": "ch2", "order": 1},
        {"id": "ch1", "order": 2}
    ]

    updated_toc = await toc_transactions.reorder_chapters_with_transaction(
        book_id, chapter_orders, user_clerk_id
    )

    assert updated_toc["version"] == 2
    assert updated_toc["chapters"][0]["id"] == "ch2"
    assert updated_toc["chapters"][0]["order"] == 1
    assert updated_toc["chapters"][1]["id"] == "ch1"
    assert updated_toc["chapters"][1]["order"] == 2


@pytest.mark.asyncio
async def test_reorder_chapters_partial_list(motor_reinit_db, sample_book_data):
    """Test reordering with partial chapter list (unmentioned chapters go to end)"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    user_clerk_id = sample_book_data["owner_id"]

    # Only specify order for ch2
    chapter_orders = [
        {"id": "ch2", "order": 1}
    ]

    updated_toc = await toc_transactions.reorder_chapters_with_transaction(
        book_id, chapter_orders, user_clerk_id
    )

    assert updated_toc["chapters"][0]["id"] == "ch2"
    assert updated_toc["chapters"][1]["id"] == "ch1"  # ch1 goes to end


@pytest.mark.asyncio
async def test_reorder_chapters_gaps_in_ordering(motor_reinit_db, sample_book_data):
    """Test reordering with gaps in order values (e.g., 1, 5, 10)"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    user_clerk_id = sample_book_data["owner_id"]

    # Use non-sequential order values
    chapter_orders = [
        {"id": "ch2", "order": 5},
        {"id": "ch1", "order": 10}
    ]

    updated_toc = await toc_transactions.reorder_chapters_with_transaction(
        book_id, chapter_orders, user_clerk_id
    )

    # Should still be ordered correctly (ch2 before ch1)
    assert updated_toc["chapters"][0]["id"] == "ch2"
    assert updated_toc["chapters"][0]["order"] == 5
    assert updated_toc["chapters"][1]["id"] == "ch1"
    assert updated_toc["chapters"][1]["order"] == 10


# ============================================================================
# CATEGORY 6: CONCURRENCY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_concurrent_toc_updates_version_conflict(motor_reinit_db, sample_book_data):
    """Test concurrent TOC updates - one should succeed, one should fail"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    user_clerk_id = sample_book_data["owner_id"]

    async def update_with_version(chapter_title: str):
        """Attempt to update TOC with version 1"""
        try:
            toc_data = {
                "chapters": [
                    {"id": f"ch-{chapter_title}", "title": chapter_title, "level": 1, "order": 1}
                ],
                "expected_version": 1
            }
            return await toc_transactions.update_toc_with_transaction(
                book_id, toc_data, user_clerk_id
            )
        except ValueError as e:
            return e

    # Both updates expect version 1
    results = await asyncio.gather(
        update_with_version("Update A"),
        update_with_version("Update B"),
        return_exceptions=True
    )

    # One should succeed (version 2), one should fail (version conflict)
    successes = [r for r in results if isinstance(r, dict) and "version" in r]
    failures = [r for r in results if isinstance(r, (ValueError, Exception)) and not isinstance(r, dict)]

    assert len(successes) == 1, f"Expected 1 success, got {len(successes)}: {successes}"
    assert len(failures) == 1, f"Expected 1 failure, got {len(failures)}: {failures}"
    assert successes[0]["version"] == 2
    assert "Version conflict" in str(failures[0])


@pytest.mark.asyncio
async def test_concurrent_chapter_adds_different_chapters(motor_reinit_db, sample_book_data):
    """Test concurrent adds of different chapters (should both succeed)"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    book_oid = result.inserted_id
    user_clerk_id = sample_book_data["owner_id"]

    async def add_chapter(title: str):
        """Add a top-level chapter"""
        chapter_data = {
            "title": title,
            "level": 1,
            "order": 100,  # Use high order to avoid conflicts
            "description": f"Chapter {title}"
        }
        return await toc_transactions.add_chapter_with_transaction(
            book_id, chapter_data, user_clerk_id
        )

    # Add two different chapters concurrently
    results = await asyncio.gather(
        add_chapter("Concurrent Chapter A"),
        add_chapter("Concurrent Chapter B"),
        return_exceptions=True
    )

    # Both should succeed
    assert all(isinstance(r, dict) for r in results), f"Some operations failed: {results}"
    assert all("id" in r for r in results)

    # Verify both chapters were added
    book = await base.books_collection.find_one({"_id": book_oid})
    assert len(book["table_of_contents"]["chapters"]) == 4  # Original 2 + 2 new


@pytest.mark.asyncio
async def test_concurrent_updates_different_chapters(motor_reinit_db, sample_book_data):
    """Test concurrent updates to different chapters (both should succeed)"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    user_clerk_id = sample_book_data["owner_id"]

    async def update_chapter(chapter_id: str, new_title: str):
        """Update a chapter title"""
        updates = {"title": new_title}
        return await toc_transactions.update_chapter_with_transaction(
            book_id, chapter_id, updates, user_clerk_id
        )

    # Update two different chapters concurrently
    results = await asyncio.gather(
        update_chapter("ch1", "Updated Ch1"),
        update_chapter("ch2", "Updated Ch2"),
        return_exceptions=True
    )

    # Both should succeed
    assert all(isinstance(r, dict) for r in results), f"Some operations failed: {results}"
    assert results[0]["title"] == "Updated Ch1"
    assert results[1]["title"] == "Updated Ch2"


# ============================================================================
# CATEGORY 7: EDGE CASES & ERROR HANDLING
# ============================================================================

@pytest.mark.asyncio
async def test_update_toc_empty_chapters(motor_reinit_db, sample_book_data):
    """Test updating TOC with empty chapters list"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    user_clerk_id = sample_book_data["owner_id"]

    toc_data = {
        "chapters": [],
        "expected_version": 1
    }

    updated_toc = await toc_transactions.update_toc_with_transaction(
        book_id, toc_data, user_clerk_id
    )

    assert updated_toc["version"] == 2
    assert updated_toc["chapters"] == []


@pytest.mark.asyncio
async def test_add_chapter_with_preset_id(motor_reinit_db, sample_book_data):
    """Test adding chapter that already has an ID"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    user_clerk_id = sample_book_data["owner_id"]

    chapter_with_id = {
        "id": "custom-chapter-id",
        "title": "Chapter with Custom ID",
        "level": 1,
        "order": 3
    }

    added = await toc_transactions.add_chapter_with_transaction(
        book_id, chapter_with_id, user_clerk_id
    )

    # Should preserve the custom ID
    assert added["id"] == "custom-chapter-id"


@pytest.mark.asyncio
async def test_update_chapter_preserves_other_fields(motor_reinit_db, sample_book_data):
    """Test that updating chapter preserves fields not in update"""
    # Create test book
    result = await base.books_collection.insert_one(sample_book_data)
    book_id = str(result.inserted_id)
    user_clerk_id = sample_book_data["owner_id"]

    # Update only title, should preserve other fields
    updates = {"title": "New Title Only"}

    updated = await toc_transactions.update_chapter_with_transaction(
        book_id, "ch1", updates, user_clerk_id
    )

    # Should still have original description
    assert updated["title"] == "New Title Only"
    assert updated["description"] == "First chapter"
    assert updated["level"] == 1
