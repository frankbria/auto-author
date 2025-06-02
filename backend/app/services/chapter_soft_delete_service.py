"""
Service for handling soft deletion of chapters.
Allows chapters to be marked as deleted without removing the actual content.
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List
from bson import ObjectId


class ChapterSoftDeleteService:
    """Service for managing soft deletion of chapters."""
    
    @staticmethod
    def mark_chapter_as_deleted(chapter: Dict, deleted_by: str) -> Dict:
        """
        Mark a chapter as soft deleted by adding deletion metadata.
        
        Args:
            chapter: The chapter dictionary to mark as deleted
            deleted_by: The user ID who is deleting the chapter
            
        Returns:
            Updated chapter dictionary with soft delete markers
        """
        chapter["is_deleted"] = True
        chapter["deleted_at"] = datetime.now(timezone.utc)
        chapter["deleted_by"] = deleted_by
        chapter["status"] = "deleted"
        return chapter
    
    @staticmethod
    def restore_chapter(chapter: Dict) -> Dict:
        """
        Restore a soft deleted chapter by removing deletion metadata.
        
        Args:
            chapter: The chapter dictionary to restore
            
        Returns:
            Updated chapter dictionary with soft delete markers removed
        """
        # Remove soft delete markers
        chapter.pop("is_deleted", None)
        chapter.pop("deleted_at", None)
        chapter.pop("deleted_by", None)
        
        # Restore previous status or set to draft
        if chapter.get("status") == "deleted":
            chapter["status"] = "draft"
        
        return chapter
    
    @staticmethod
    def filter_active_chapters(chapters: List[Dict]) -> List[Dict]:
        """
        Filter out soft deleted chapters from a list.
        
        Args:
            chapters: List of chapter dictionaries
            
        Returns:
            List of active (non-deleted) chapters
        """
        return [ch for ch in chapters if not ch.get("is_deleted", False)]
    
    @staticmethod
    def get_deleted_chapters(chapters: List[Dict]) -> List[Dict]:
        """
        Get only soft deleted chapters from a list.
        
        Args:
            chapters: List of chapter dictionaries
            
        Returns:
            List of soft deleted chapters
        """
        return [ch for ch in chapters if ch.get("is_deleted", False)]
    
    @staticmethod
    async def soft_delete_chapter_in_toc(
        book: Dict, 
        chapter_id: str, 
        deleted_by: str
    ) -> Optional[Dict]:
        """
        Soft delete a chapter within a book's TOC structure.
        
        Args:
            book: The book dictionary containing the TOC
            chapter_id: ID of the chapter to soft delete
            deleted_by: User ID performing the deletion
            
        Returns:
            The soft deleted chapter if found, None otherwise
        """
        toc = book.get("table_of_contents", {})
        chapters = toc.get("chapters", [])
        
        def soft_delete_in_list(chapter_list: List[Dict]) -> Optional[Dict]:
            for chapter in chapter_list:
                if chapter.get("id") == chapter_id:
                    # Mark as soft deleted
                    ChapterSoftDeleteService.mark_chapter_as_deleted(chapter, deleted_by)
                    return chapter
                
                # Recursively check subchapters
                if chapter.get("subchapters"):
                    result = soft_delete_in_list(chapter["subchapters"])
                    if result:
                        return result
            return None
        
        return soft_delete_in_list(chapters)
    
    @staticmethod
    async def restore_chapter_in_toc(
        book: Dict, 
        chapter_id: str
    ) -> Optional[Dict]:
        """
        Restore a soft deleted chapter within a book's TOC structure.
        
        Args:
            book: The book dictionary containing the TOC
            chapter_id: ID of the chapter to restore
            
        Returns:
            The restored chapter if found, None otherwise
        """
        toc = book.get("table_of_contents", {})
        chapters = toc.get("chapters", [])
        
        def restore_in_list(chapter_list: List[Dict]) -> Optional[Dict]:
            for chapter in chapter_list:
                if chapter.get("id") == chapter_id and chapter.get("is_deleted"):
                    # Restore the chapter
                    ChapterSoftDeleteService.restore_chapter(chapter)
                    return chapter
                
                # Recursively check subchapters
                if chapter.get("subchapters"):
                    result = restore_in_list(chapter["subchapters"])
                    if result:
                        return result
            return None
        
        return restore_in_list(chapters)
    
    @staticmethod
    def permanently_delete_soft_deleted_chapters(
        chapters: List[Dict], 
        days_old: int = 30
    ) -> List[Dict]:
        """
        Permanently remove chapters that have been soft deleted for a specified time.
        
        Args:
            chapters: List of chapter dictionaries
            days_old: Number of days after which soft deleted chapters are permanently removed
            
        Returns:
            List of chapters with old soft deleted chapters removed
        """
        cutoff_date = datetime.now(timezone.utc) - timezone.timedelta(days=days_old)
        active_chapters = []
        
        for chapter in chapters:
            # Check if chapter should be permanently deleted
            if chapter.get("is_deleted") and chapter.get("deleted_at"):
                if chapter["deleted_at"] < cutoff_date:
                    continue  # Skip this chapter (permanently delete)
            
            # Keep the chapter and process subchapters
            if chapter.get("subchapters"):
                chapter["subchapters"] = ChapterSoftDeleteService.permanently_delete_soft_deleted_chapters(
                    chapter["subchapters"], 
                    days_old
                )
            
            active_chapters.append(chapter)
        
        return active_chapters


# Create a singleton instance
chapter_soft_delete_service = ChapterSoftDeleteService()
