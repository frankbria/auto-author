"""Chapter status management service"""

from typing import List, Dict
from app.schemas.book import ChapterStatus


class ChapterStatusService:
    """Service for managing chapter status transitions and validation"""

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

# Export service instance
chapter_status_service = ChapterStatusService()
