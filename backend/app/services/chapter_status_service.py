"""Chapter status management service"""

from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from app.schemas.book import ChapterStatus


class ChapterStatusService:
    """Service for managing chapter status transitions and validation"""

    VALID_STATUSES = [status.value for status in ChapterStatus]

    STATUS_TRANSITIONS = {
        ChapterStatus.DRAFT.value: [
            ChapterStatus.IN_PROGRESS.value,
            ChapterStatus.COMPLETED.value,
        ],
        ChapterStatus.IN_PROGRESS.value: [
            ChapterStatus.DRAFT.value,
            ChapterStatus.COMPLETED.value,
        ],
        ChapterStatus.COMPLETED.value: [
            ChapterStatus.IN_PROGRESS.value,
            ChapterStatus.PUBLISHED.value,
        ],
        ChapterStatus.PUBLISHED.value: [
            ChapterStatus.COMPLETED.value
        ],  # Limited backwards transition
    }

    @classmethod
    def validate_status_transition(cls, from_status: str, to_status: str) -> bool:
        """Validate if status transition is allowed"""
        if from_status == to_status:
            return True
        return to_status in cls.STATUS_TRANSITIONS.get(from_status, [])

    @classmethod
    def is_valid_transition(
        cls, from_status: ChapterStatus, to_status: ChapterStatus
    ) -> bool:
        """Validate if status transition is allowed (enum version)"""
        return cls.validate_status_transition(from_status.value, to_status.value)

    @classmethod
    def auto_suggest_status(
        cls, word_count: int, last_modified: Optional[datetime] = None
    ) -> str:
        """Auto-suggest status based on content metrics"""
        if word_count == 0:
            return ChapterStatus.DRAFT.value
        elif word_count < 500:
            return ChapterStatus.IN_PROGRESS.value
        elif word_count >= 500:
            return ChapterStatus.COMPLETED.value
        return ChapterStatus.DRAFT.value

    @classmethod
    def calculate_reading_time(
        cls, word_count: int, words_per_minute: int = 200
    ) -> int:
        """Calculate estimated reading time in minutes"""
        if word_count <= 0:
            return 0
        return max(1, round(word_count / words_per_minute))

    @classmethod
    def get_completion_stats(cls, chapters: List[Dict]) -> Dict[str, int]:
        """Calculate completion statistics from chapter list"""
        stats = {status.value: 0 for status in ChapterStatus}

        for chapter in chapters:
            status = chapter.get("status", ChapterStatus.DRAFT.value)
            if status in stats:
                stats[status] += 1

        return stats

    @classmethod
    def validate_bulk_status_update(
        cls, chapter_statuses: Dict[str, str], target_status: str
    ) -> Dict[str, bool]:
        """Validate bulk status update for multiple chapters"""
        results = {}

        for chapter_id, current_status in chapter_statuses.items():
            results[chapter_id] = cls.validate_status_transition(
                current_status, target_status
            )

        return results

    @classmethod
    def validate_status_data(cls, status: str) -> ChapterStatus:
        """Validate and convert status string to ChapterStatus enum"""
        if status not in cls.VALID_STATUSES:
            raise ValueError(
                f"Invalid status: {status}. Valid statuses: {cls.VALID_STATUSES}"
            )
        return ChapterStatus(status)

    @classmethod
    def validate_bulk_update(cls, updates: List[Dict]) -> Dict[str, Any]:
        """Validate bulk update data structure and transitions"""
        invalid_updates = []
        valid_count = 0

        for i, update in enumerate(updates):
            if "chapter_id" not in update:
                invalid_updates.append(
                    {"index": i, "error": "Missing chapter_id", "update": update}
                )
                continue

            if "status" not in update:
                invalid_updates.append(
                    {"index": i, "error": "Missing status", "update": update}
                )
                continue

            try:
                # Validate status format
                if isinstance(update["status"], ChapterStatus):
                    status_value = update["status"].value
                else:
                    cls.validate_status_data(update["status"])
                    status_value = update["status"]

                valid_count += 1

            except ValueError as e:
                invalid_updates.append({"index": i, "error": str(e), "update": update})

        return {
            "valid": len(invalid_updates) == 0,
            "valid_count": valid_count,
            "invalid_count": len(invalid_updates),
            "invalid_updates": invalid_updates,
        }


# Export service instance
chapter_status_service = ChapterStatusService()
