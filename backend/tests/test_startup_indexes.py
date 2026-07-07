"""Startup index creation for books + chapter_access_logs (issue #183).

ChapterTabIndexManager held the book owner_id indexes and the 90-day
access-log TTL but ran nowhere at runtime. These tests pin that the manager
creates them and that the app lifespan actually invokes it.
"""
from unittest.mock import AsyncMock, patch

import pytest

from app.db import base
from app.db.indexing_strategy import ChapterTabIndexManager
from app.main import app

NINETY_DAYS = 60 * 60 * 24 * 90


async def _warm_collections():
    """First createIndexes after a drop_database can be silently lost; do a
    real write on each collection so the index builds land."""
    await base._db.books.insert_one({"warm": True})
    await base._db.chapter_access_logs.insert_one({"warm": True})


async def _index_map(collection):
    return {idx["name"]: idx for idx in await collection.list_indexes().to_list(None)}


@pytest.mark.asyncio
async def test_create_all_indexes_creates_owner_and_ttl_indexes(motor_reinit_db):
    await _warm_collections()
    result = await ChapterTabIndexManager(base._db).create_all_indexes()
    assert result["success"] is True

    books_indexes = await _index_map(base._db.books)
    assert "owner_book_id_idx" in books_indexes
    assert "owner_updated_idx" in books_indexes

    access_indexes = await _index_map(base._db.chapter_access_logs)
    assert "access_logs_ttl_idx" in access_indexes
    assert access_indexes["access_logs_ttl_idx"]["expireAfterSeconds"] == NINETY_DAYS
    for name in (
        "user_book_timestamp_idx",
        "book_chapter_timestamp_idx",
        "user_access_type_timestamp_idx",
        "user_book_access_type_idx",
    ):
        assert name in access_indexes


@pytest.mark.asyncio
async def test_create_all_indexes_is_idempotent(motor_reinit_db):
    await _warm_collections()
    manager = ChapterTabIndexManager(base._db)
    assert (await manager.create_all_indexes())["success"] is True
    assert (await manager.create_all_indexes())["success"] is True

    books_indexes = await _index_map(base._db.books)
    assert "owner_book_id_idx" in books_indexes


@pytest.mark.asyncio
async def test_no_text_index_on_books(motor_reinit_db):
    """The unused chapter-content text index was removed (no $text queries;
    it re-tokenized full chapter content on every autosave)."""
    await _warm_collections()
    await ChapterTabIndexManager(base._db).create_all_indexes()

    books_indexes = await _index_map(base._db.books)
    assert "chapter_content_text_idx" not in books_indexes


@pytest.mark.asyncio
async def test_lifespan_runs_chapter_tab_index_creation(motor_reinit_db):
    """App startup must invoke create_all_indexes (the actual #183 bug)."""
    with patch.object(
        ChapterTabIndexManager, "create_all_indexes", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = {"success": True}
        async with app.router.lifespan_context(app):
            pass
    mock_create.assert_awaited_once()
