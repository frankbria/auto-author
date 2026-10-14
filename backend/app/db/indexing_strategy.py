# Database Indexing Strategy for Chapter Tabs Functionality
# This file contains MongoDB index definitions to optimize chapter access patterns

from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)


class ChapterTabIndexManager:
    """
    Manages database indexes for optimal chapter tabs performance.

    This class provides methods to create, update, and manage indexes
    for the enhanced chapter functionality including access logging,
    tab state management, and metadata queries.
    """

    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database

    async def create_chapter_access_indexes(self):
        """
        Create indexes for chapter access logging collection.
        Optimizes queries for tab state, analytics, and recent activity.
        """
        collection = self.database.chapter_access_logs

        indexes = [
            # Compound index for user-specific queries (most common pattern)
            {
                "keys": [("user_id", 1), ("book_id", 1), ("timestamp", -1)],
                "name": "user_book_timestamp_idx",
                "background": True,
            },
            # Index for chapter-specific analytics
            {
                "keys": [("book_id", 1), ("chapter_id", 1), ("timestamp", -1)],
                "name": "book_chapter_timestamp_idx",
                "background": True,
            },
            # Index for recent activity queries (tab state retrieval)
            {
                "keys": [("user_id", 1), ("access_type", 1), ("timestamp", -1)],
                "name": "user_access_type_timestamp_idx",
                "background": True,
            },
            # Index for tab state queries
            {
                "keys": [("user_id", 1), ("book_id", 1), ("access_type", 1)],
                "name": "user_book_access_type_idx",
                "background": True,
                "partialFilterExpression": {"access_type": "tab_state"},
            },
            # TTL index for automatic cleanup of old logs (optional)
            {
                "keys": [("timestamp", 1)],
                "name": "access_logs_ttl_idx",
                "background": True,
                "expireAfterSeconds": 60 * 60 * 24 * 90,  # 90 days
            },
        ]

        for index_spec in indexes:
            try:
                keys = index_spec.pop("keys")
                await collection.create_index(keys, **index_spec)
                logger.info(f"Created index: {index_spec.get('name', 'unnamed')}")
            except Exception as e:
                logger.error(
                    f"Failed to create index {index_spec.get('name', 'unnamed')}: {e}"
                )

    async def create_book_toc_indexes(self):
        """
        Create indexes for book table of contents queries.
        Optimizes chapter metadata retrieval and status filtering.
        """
        collection = self.database.books

        indexes = [
            # Compound index for book ownership and TOC queries
            {
                "keys": [("owner_id", 1), ("_id", 1)],
                "name": "owner_book_id_idx",
                "background": True,
            },
            # Index for book metadata queries
            {
                "keys": [("owner_id", 1), ("updated_at", -1)],
                "name": "owner_updated_idx",
                "background": True,
            },
            # No text index: nothing queries $text, and indexing full chapter
            # content would re-tokenize on every 3s autosave (issue #183).
        ]

        # Drop the removed text index if an earlier manual/migration run
        # created it, so it stops taxing every chapter save.
        try:
            await collection.drop_index("chapter_content_text_idx")
            logger.info("Dropped stale index: chapter_content_text_idx")
        except Exception:
            pass  # index doesn't exist (the normal case)

        for index_spec in indexes:
            try:
                keys = index_spec.pop("keys")
                await collection.create_index(keys, **index_spec)
                logger.info(f"Created index: {index_spec.get('name', 'unnamed')}")
            except Exception as e:
                logger.error(
                    f"Failed to create index {index_spec.get('name', 'unnamed')}: {e}"
                )

    async def optimize_existing_indexes(self):
        """
        Analyze and optimize existing indexes for better performance.
        """
        # Get existing indexes for analysis
        books_indexes = await self.database.books.list_indexes().to_list(None)
        access_logs_indexes = []

        try:
            access_logs_indexes = (
                await self.database.chapter_access_logs.list_indexes().to_list(None)
            )
        except Exception:
            # Collection might not exist yet
            pass

        optimization_report = {
            "books_collection": {
                "existing_indexes": len(books_indexes),
                "recommended_actions": [],
            },
            "chapter_access_logs": {
                "existing_indexes": len(access_logs_indexes),
                "recommended_actions": [],
            },
        }

        # Check for missing critical indexes
        books_index_names = [idx["name"] for idx in books_indexes]
        if "owner_book_id_idx" not in books_index_names:
            optimization_report["books_collection"]["recommended_actions"].append(
                "Create owner_book_id_idx for faster book ownership queries"
            )

        access_index_names = [idx["name"] for idx in access_logs_indexes]
        if "user_book_timestamp_idx" not in access_index_names:
            optimization_report["chapter_access_logs"]["recommended_actions"].append(
                "Create user_book_timestamp_idx for faster tab state queries"
            )

        return optimization_report

    async def create_all_indexes(self):
        """
        Create all recommended indexes for chapter tabs functionality.
        """
        logger.info("Starting index creation for chapter tabs functionality...")

        try:
            await self.create_chapter_access_indexes()
            await self.create_book_toc_indexes()

            # Generate optimization report
            report = await self.optimize_existing_indexes()

            logger.info("Index creation completed successfully")
            return {
                "success": True,
                "message": "All indexes created successfully",
                "optimization_report": report,
            }

        except Exception as e:
            logger.error(f"Index creation failed: {e}")
            return {"success": False, "message": f"Index creation failed: {str(e)}"}
