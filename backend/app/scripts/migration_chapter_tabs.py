#!/usr/bin/env python3
"""
Database Migration Script for Chapter Tabs Functionality
=========================================================

This script migrates existing book data to support the new chapter tabs functionality.
It adds the required metadata fields to existing chapters and creates necessary indexes.

Usage:
    python migration_chapter_tabs.py [--dry-run] [--batch-size=100]

Options:
    --dry-run       Show what would be changed without making actual changes
    --batch-size    Number of books to process per batch (default: 100)
    --force         Skip confirmation prompts
"""

import asyncio
import argparse
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
import sys
import os

# Add the parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_database
from app.db.indexing_strategy import ChapterTabIndexManager
from app.schemas.book import ChapterStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("migration_chapter_tabs.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class ChapterTabsMigration:
    """
    Handles migration of existing book data to support chapter tabs functionality.
    """

    def __init__(self, dry_run: bool = False, batch_size: int = 100):
        self.dry_run = dry_run
        self.batch_size = batch_size
        self.migration_stats = {
            "books_processed": 0,
            "chapters_updated": 0,
            "books_with_errors": 0,
            "start_time": None,
            "end_time": None,
        }

    async def initialize(self):
        """Initialize database connection and index manager."""
        self.database = await get_database()
        self.index_manager = ChapterTabIndexManager(self.database)

    async def migrate_chapter_metadata(self, book: Dict) -> Dict:
        """
        Add new metadata fields to all chapters in a book's TOC.

        Args:
            book: Book document from database

        Returns:
            Updated book document or None if no changes needed
        """
        updated = False
        toc = book.get("table_of_contents", {})
        chapters = toc.get("chapters", [])

        if not chapters:
            return None

        def update_chapter_metadata(chapter_list: List[Dict], level: int = 1) -> bool:
            """Recursively update chapter metadata."""
            changes_made = False

            for chapter in chapter_list:
                # Check if new fields are missing
                if "status" not in chapter:
                    chapter["status"] = ChapterStatus.DRAFT.value
                    changes_made = True

                if "word_count" not in chapter:
                    # Calculate word count from existing content
                    content = chapter.get("content", "")
                    chapter["word_count"] = len(content.split()) if content else 0
                    changes_made = True

                if "last_modified" not in chapter:
                    # Use book's updated_at or current time
                    chapter["last_modified"] = book.get(
                        "updated_at", datetime.now(timezone.utc)
                    )
                    changes_made = True

                if "estimated_reading_time" not in chapter:
                    # Calculate reading time (200 words per minute)
                    word_count = chapter.get("word_count", 0)
                    chapter["estimated_reading_time"] = max(1, word_count // 200)
                    changes_made = True

                if "is_active_tab" not in chapter:
                    chapter["is_active_tab"] = False
                    changes_made = True

                # Ensure chapter has an ID
                if "id" not in chapter:
                    import uuid

                    chapter["id"] = str(uuid.uuid4())
                    changes_made = True

                # Process subchapters
                if "subchapters" in chapter and chapter["subchapters"]:
                    if update_chapter_metadata(chapter["subchapters"], level + 1):
                        changes_made = True

            return changes_made

        updated = update_chapter_metadata(chapters)

        if updated:
            # Update TOC metadata
            if "version" not in toc:
                toc["version"] = 1

            toc["updated_at"] = datetime.now(timezone.utc).isoformat()
            book["table_of_contents"] = toc
            book["updated_at"] = datetime.now(timezone.utc)

            return book

        return None

    async def migrate_single_book(self, book: Dict) -> bool:
        """
        Migrate a single book to the new schema.

        Args:
            book: Book document to migrate

        Returns:
            True if migration was successful, False otherwise
        """
        try:
            book_id = str(book["_id"])
            logger.info(
                f"Processing book: {book_id} - '{book.get('title', 'Untitled')}'"
            )

            # Check if migration is needed
            updated_book = await self.migrate_chapter_metadata(book)

            if updated_book is None:
                logger.info(f"Book {book_id} already up to date")
                return True

            chapter_count = self._count_chapters(
                updated_book.get("table_of_contents", {})
            )

            if self.dry_run:
                logger.info(
                    f"[DRY RUN] Would update {chapter_count} chapters in book {book_id}"
                )
                self.migration_stats["chapters_updated"] += chapter_count
                return True

            # Perform actual update
            update_result = await self.database.books.update_one(
                {"_id": book["_id"]},
                {
                    "$set": {
                        "table_of_contents": updated_book["table_of_contents"],
                        "updated_at": updated_book["updated_at"],
                    }
                },
            )

            if update_result.modified_count > 0:
                logger.info(
                    f"Successfully updated {chapter_count} chapters in book {book_id}"
                )
                self.migration_stats["chapters_updated"] += chapter_count
                return True
            else:
                logger.warning(f"No changes made to book {book_id}")
                return True

        except Exception as e:
            logger.error(f"Error migrating book {book.get('_id', 'unknown')}: {e}")
            self.migration_stats["books_with_errors"] += 1
            return False

    def _count_chapters(self, toc: Dict) -> int:
        """Count total number of chapters (including subchapters) in TOC."""
        chapters = toc.get("chapters", [])
        total = 0

        def count_recursive(chapter_list: List[Dict]) -> int:
            count = len(chapter_list)
            for chapter in chapter_list:
                if "subchapters" in chapter and chapter["subchapters"]:
                    count += count_recursive(chapter["subchapters"])
            return count

        return count_recursive(chapters)

    async def run_migration(self):
        """Run the complete migration process."""
        self.migration_stats["start_time"] = datetime.now(timezone.utc)

        logger.info("Starting Chapter Tabs Migration")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE MIGRATION'}")
        logger.info(f"Batch size: {self.batch_size}")

        try:
            # Get total book count
            total_books = await self.database.books.count_documents({})
            logger.info(f"Total books to process: {total_books}")

            if total_books == 0:
                logger.info("No books found, migration complete")
                return

            # Process books in batches
            skip = 0
            while skip < total_books:
                logger.info(
                    f"Processing batch: {skip + 1} to {min(skip + self.batch_size, total_books)}"
                )

                # Get batch of books
                cursor = self.database.books.find({}).skip(skip).limit(self.batch_size)
                books = await cursor.to_list(length=self.batch_size)

                # Process each book
                for book in books:
                    success = await self.migrate_single_book(book)
                    if success:
                        self.migration_stats["books_processed"] += 1

                skip += self.batch_size

                # Small delay between batches to avoid overloading
                if not self.dry_run:
                    await asyncio.sleep(0.1)

            # Create indexes if not dry run
            if not self.dry_run:
                logger.info("Creating optimized indexes...")
                index_result = await self.index_manager.create_all_indexes()
                if index_result["success"]:
                    logger.info("Index creation completed successfully")
                else:
                    logger.error(f"Index creation failed: {index_result['message']}")

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise

        finally:
            self.migration_stats["end_time"] = datetime.now(timezone.utc)
            self._print_migration_summary()

    def _print_migration_summary(self):
        """Print migration summary statistics."""
        stats = self.migration_stats
        duration = stats["end_time"] - stats["start_time"]

        logger.info("=" * 50)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE MIGRATION'}")
        logger.info(f"Duration: {duration}")
        logger.info(f"Books processed: {stats['books_processed']}")
        logger.info(f"Chapters updated: {stats['chapters_updated']}")
        logger.info(f"Books with errors: {stats['books_with_errors']}")

        if stats["books_with_errors"] > 0:
            logger.warning(
                "Some books had errors during migration. Check logs for details."
            )
        else:
            logger.info("Migration completed successfully with no errors!")

        logger.info("=" * 50)


async def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(
        description="Migrate database for chapter tabs functionality"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show changes without applying them"
    )
    parser.add_argument(
        "--batch-size", type=int, default=100, help="Number of books per batch"
    )
    parser.add_argument(
        "--force", action="store_true", help="Skip confirmation prompts"
    )

    args = parser.parse_args()

    # Confirmation prompt
    if not args.force and not args.dry_run:
        print("WARNING: This will modify your database.")
        print("Make sure you have a backup before proceeding.")
        response = input("Continue? (yes/no): ")
        if response.lower() != "yes":
            print("Migration cancelled.")
            return

    # Initialize and run migration
    migration = ChapterTabsMigration(dry_run=args.dry_run, batch_size=args.batch_size)
    await migration.initialize()
    await migration.run_migration()


if __name__ == "__main__":
    asyncio.run(main())
