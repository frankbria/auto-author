"""Chapter access logging service for analytics and tab persistence"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from bson import ObjectId
from app.models.chapter_access import ChapterAccessLog, ChapterAccessCreate
from app.db.database import get_collection


class ChapterAccessService:
    """Service for managing chapter access logs"""

    def __init__(self):
        pass  # No collection initialization here

    async def _get_collection(self):
        return await get_collection("chapter_access_logs")

    async def log_access(
        self,
        user_id: str,
        book_id: str,
        chapter_id: str,
        access_type: str,
        session_id: Optional[str] = None,
        tab_order: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Log chapter access for analytics and tab persistence"""

        log_entry = ChapterAccessLog(
            user_id=user_id,
            book_id=book_id,
            chapter_id=chapter_id,
            access_type=access_type,
            session_id=session_id,
            tab_order=tab_order,
            metadata=metadata or {},
        )

        collection = await self._get_collection()
        result = await collection.insert_one(log_entry.model_dump(by_alias=True))
        return str(result.inserted_id)

    async def get_user_tab_state(self, user_id: str, book_id: str) -> Optional[Dict]:
        """Retrieve latest tab state for user and book"""

        collection = await self._get_collection()
        cursor = (
            collection.find(
                {"user_id": user_id, "book_id": book_id, "access_type": "tab_state"}
            )
            .sort("timestamp", -1)
            .limit(1)
        )

        result = await cursor.to_list(length=1)
        return result[0] if result else None

    async def get_chapter_analytics(self, book_id: str, days: int = 30) -> List[Dict]:
        """Get chapter access analytics for the past N days"""

        since_date = datetime.now(timezone.utc) - timedelta(days=days)
        collection = await self._get_collection()
        pipeline = [
            {"$match": {"book_id": book_id, "timestamp": {"$gte": since_date}}},
            {
                "$group": {
                    "_id": {"chapter_id": "$chapter_id", "access_type": "$access_type"},
                    "count": {"$sum": 1},
                    "last_access": {"$max": "$timestamp"},
                }
            },
        ]

        return await collection.aggregate(pipeline).to_list(None)

    async def get_user_recent_chapters(
        self, user_id: str, book_id: str, limit: int = 10
    ) -> List[Dict]:
        """Get recently accessed chapters for a user"""

        collection = await self._get_collection()
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "book_id": book_id,
                    "access_type": {"$in": ["view", "edit"]},
                }
            },
            {"$sort": {"timestamp": -1}},
            {
                "$group": {
                    "_id": "$chapter_id",
                    "last_access": {"$first": "$timestamp"},
                    "access_count": {"$sum": 1},
                }
            },
            {"$sort": {"last_access": -1}},
            {"$limit": limit},
        ]

        return await collection.aggregate(pipeline).to_list(None)

    async def save_tab_state(
        self,
        user_id: str,
        book_id: str,
        active_chapter_id: str,
        open_tab_ids: List[str],
        tab_order: List[str],
        session_id: Optional[str] = None,
    ) -> str:
        """Save tab state for persistence across sessions"""

        tab_state_metadata = {
            "active_chapter_id": active_chapter_id,
            "open_tab_ids": open_tab_ids,
            "tab_order": tab_order,
        }

        return await self.log_access(
            user_id=user_id,
            book_id=book_id,
            chapter_id=active_chapter_id,
            access_type="tab_state",
            session_id=session_id,
            metadata=tab_state_metadata,
        )


# Create service instance
chapter_access_service = ChapterAccessService()
