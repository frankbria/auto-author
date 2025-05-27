# Database Indexing Strategy for Chapter Tabs Functionality
# This file contains MongoDB index definitions to optimize chapter access patterns

from typing import Dict, List
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
            # Text index for chapter content search (if needed)
            {
                "keys": [
                    ("table_of_contents.chapters.title", "text"),
                    ("table_of_contents.chapters.content", "text"),
                ],
                "name": "chapter_content_text_idx",
                "background": True,
                "weights": {
                    "table_of_contents.chapters.title": 10,
                    "table_of_contents.chapters.content": 1,
                },
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

    async def get_index_usage_stats(self):
        """
        Get statistics about index usage for performance monitoring.
        """
        stats = {}

        try:
            # Get books collection stats
            books_stats = await self.database.command(
                "collStats", "books", indexDetails=True
            )
            stats["books"] = {
                "total_indexes": books_stats.get("nindexes", 0),
                "total_index_size": books_stats.get("totalIndexSize", 0),
            }

            # Get chapter access logs stats if collection exists
            try:
                access_stats = await self.database.command(
                    "collStats", "chapter_access_logs", indexDetails=True
                )
                stats["chapter_access_logs"] = {
                    "total_indexes": access_stats.get("nindexes", 0),
                    "total_index_size": access_stats.get("totalIndexSize", 0),
                    "document_count": access_stats.get("count", 0),
                }
            except Exception:
                stats["chapter_access_logs"] = {"note": "Collection does not exist yet"}

        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            stats["error"] = str(e)

        return stats


# Query optimization patterns for common chapter tab operations
OPTIMIZED_QUERIES = {
    "get_user_tab_state": {
        "description": "Optimized query for retrieving user's current tab state",
        "query": {
            "user_id": "USER_ID",
            "book_id": "BOOK_ID",
            "access_type": "tab_state",
        },
        "sort": {"timestamp": -1},
        "limit": 1,
        "indexes_used": ["user_book_access_type_idx"],
    },
    "get_recent_chapters": {
        "description": "Get recently accessed chapters for a user",
        "query": {
            "user_id": "USER_ID",
            "book_id": "BOOK_ID",
            "access_type": {"$in": ["read_content", "update_content", "view"]},
        },
        "sort": {"timestamp": -1},
        "limit": 10,
        "indexes_used": ["user_book_timestamp_idx"],
    },
    "get_chapter_analytics": {
        "description": "Get analytics data for a specific chapter",
        "query": {
            "book_id": "BOOK_ID",
            "chapter_id": "CHAPTER_ID",
            "timestamp": {"$gte": "DATE_RANGE_START"},
        },
        "sort": {"timestamp": -1},
        "indexes_used": ["book_chapter_timestamp_idx"],
    },
    "get_book_with_chapters": {
        "description": "Optimized book retrieval with chapter metadata",
        "query": {"_id": "BOOK_ID", "owner_id": "USER_ID"},
        "projection": {"table_of_contents": 1, "title": 1, "updated_at": 1},
        "indexes_used": ["owner_book_id_idx"],
    },
}


# Performance monitoring queries
PERFORMANCE_MONITORING = {
    "slow_query_analysis": {
        "description": "Analyze slow queries related to chapter operations",
        "command": "db.runCommand({profile: 2, slowms: 100})",
        "note": "Enable profiling to monitor queries > 100ms",
    },
    "index_hit_ratio": {
        "description": "Monitor index usage effectiveness",
        "aggregation": [
            {"$indexStats": {}},
            {
                "$group": {
                    "_id": "$name",
                    "accesses": {"$sum": "$accesses.ops"},
                    "since": {"$min": "$accesses.since"},
                }
            },
        ],
    },
}
