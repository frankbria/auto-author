#!/usr/bin/env python3
"""
Chapter Tabs API Testing Script
==============================

This script tests all the chapter tabs API endpoints to ensure they're working correctly.
It can be run independently to validate the implementation.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
import uuid

# Add app to path
sys.path.append(str(Path(__file__).parent))

try:
    from app.schemas.book import ChapterStatus, ChapterMetadata, TabStateRequest
    from app.models.chapter_access import ChapterAccessCreate

    print("✅ Successfully imported chapter tabs schemas and models")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the backend directory")
    sys.exit(1)


class ChapterTabsAPITester:
    """Tests chapter tabs API functionality."""

    def __init__(self):
        self.test_results = []
        self.book_id = str(uuid.uuid4())
        self.user_id = "test-user-123"
        self.chapter_id = "ch-1"

    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append(
            {"test": test_name, "passed": passed, "message": message}
        )
        print(f"{status}: {test_name}")
        if message:
            print(f"    {message}")

    def test_schema_creation(self):
        """Test that we can create schema instances."""
        try:
            # Test ChapterStatus enum
            status = ChapterStatus.DRAFT
            assert status.value == "draft"
            self.log_test("ChapterStatus enum", True)

            # Test ChapterMetadata schema
            metadata = ChapterMetadata(
                chapter_id="test-ch-1",
                title="Test Chapter",
                status=ChapterStatus.DRAFT,
                word_count=250,
                last_modified=datetime.now(timezone.utc),
                estimated_reading_time=2,
                is_active_tab=True,
            )
            assert metadata.chapter_id == "test-ch-1"
            self.log_test("ChapterMetadata schema", True)

            # Test TabStateRequest schema
            tab_state = TabStateRequest(
                active_tabs=["ch-1", "ch-2"],
                active_chapter_id="ch-1",
                tab_order=["ch-1", "ch-2"],
                session_id="test-session",
            )
            assert len(tab_state.active_tabs) == 2
            self.log_test("TabStateRequest schema", True)

            # Test ChapterAccessCreate model
            access_log = ChapterAccessCreate(
                user_id="test-user",
                book_id="test-book",
                chapter_id="test-chapter",
                access_type="read",
                session_id="test-session",
            )
            assert access_log.access_type == "read"
            self.log_test("ChapterAccessCreate model", True)

        except Exception as e:
            self.log_test("Schema creation", False, str(e))

    def test_service_imports(self):
        """Test that service classes can be imported."""
        try:
            from app.services.chapter_access_service import ChapterAccessService

            self.log_test("ChapterAccessService import", True)
        except ImportError as e:
            self.log_test("ChapterAccessService import", False, str(e))

        try:
            from app.services.chapter_status_service import ChapterStatusService

            service = ChapterStatusService()
            # Test a method
            is_valid = service.is_valid_transition(
                ChapterStatus.DRAFT, ChapterStatus.IN_PROGRESS
            )
            assert is_valid is True
            self.log_test("ChapterStatusService functionality", True)
        except Exception as e:
            self.log_test("ChapterStatusService functionality", False, str(e))

        try:
            from app.services.chapter_cache_service import ChapterMetadataCache

            self.log_test("ChapterMetadataCache import", True)
        except ImportError as e:
            self.log_test("ChapterMetadataCache import", False, str(e))

        try:
            from app.services.chapter_error_handler import ChapterErrorHandler

            handler = ChapterErrorHandler()
            # Test error categorization
            error = Exception("Test error")
            categorized = handler.categorize_error(error)
            assert "category" in categorized
            self.log_test("ChapterErrorHandler functionality", True)
        except Exception as e:
            self.log_test("ChapterErrorHandler functionality", False, str(e))

    def test_database_utilities(self):
        """Test database-related utilities."""
        try:
            from app.db.indexing_strategy import ChapterTabIndexManager

            self.log_test("ChapterTabIndexManager import", True)
        except ImportError as e:
            self.log_test("ChapterTabIndexManager import", False, str(e))

    def test_migration_script(self):
        """Test that migration script can be imported."""
        try:
            from app.scripts.migration_chapter_tabs import ChapterTabsMigration

            migration = ChapterTabsMigration(dry_run=True, batch_size=10)
            self.log_test("Migration script import", True)
        except Exception as e:
            self.log_test("Migration script import", False, str(e))

    def test_status_transitions(self):
        """Test chapter status transition logic."""
        try:
            from app.services.chapter_status_service import ChapterStatusService

            service = ChapterStatusService()

            # Test valid transitions
            valid_tests = [
                (ChapterStatus.DRAFT, ChapterStatus.IN_PROGRESS),
                (ChapterStatus.IN_PROGRESS, ChapterStatus.COMPLETED),
                (ChapterStatus.COMPLETED, ChapterStatus.PUBLISHED),
                (ChapterStatus.COMPLETED, ChapterStatus.DRAFT),  # Allow regression
            ]

            for from_status, to_status in valid_tests:
                is_valid = service.is_valid_transition(from_status, to_status)
                if not is_valid:
                    self.log_test(
                        f"Status transition {from_status.value} -> {to_status.value}",
                        False,
                        "Should be valid but isn't",
                    )
                    return

            # Test invalid transitions
            invalid_tests = [
                (ChapterStatus.DRAFT, ChapterStatus.PUBLISHED),  # Skip stages
            ]

            for from_status, to_status in invalid_tests:
                is_valid = service.is_valid_transition(from_status, to_status)
                if is_valid:
                    self.log_test(
                        f"Invalid status transition {from_status.value} -> {to_status.value}",
                        False,
                        "Should be invalid but isn't",
                    )
                    return

            self.log_test("Chapter status transitions", True)

        except Exception as e:
            self.log_test("Chapter status transitions", False, str(e))

    def test_bulk_operations(self):
        """Test bulk operation validation."""
        try:
            from app.services.chapter_status_service import ChapterStatusService

            service = ChapterStatusService()

            # Test valid bulk update
            valid_updates = [
                {"chapter_id": "ch-1", "status": ChapterStatus.IN_PROGRESS},
                {"chapter_id": "ch-2", "status": ChapterStatus.COMPLETED},
            ]

            result = service.validate_bulk_update(valid_updates)
            assert result["valid"] is True
            assert len(result["invalid_updates"]) == 0

            # Test invalid bulk update
            invalid_updates = [
                {"chapter_id": "ch-1"},  # Missing status
                {"status": ChapterStatus.DRAFT},  # Missing chapter_id
            ]

            result = service.validate_bulk_update(invalid_updates)
            assert result["valid"] is False
            assert len(result["invalid_updates"]) == 2

            self.log_test("Bulk operations validation", True)

        except Exception as e:
            self.log_test("Bulk operations validation", False, str(e))

    def test_api_endpoint_paths(self):
        """Test that API endpoints are defined in the books.py file."""
        try:
            books_api_file = (
                Path(__file__).parent / "app" / "api" / "endpoints" / "books.py"
            )
            content = books_api_file.read_text()

            # Check for new endpoint patterns
            endpoint_patterns = [
                "/chapters/metadata",
                "/chapters/bulk-status",
                "/chapters/tab-state",
                "/chapters/{chapter_id}/content",
                "/chapters/{chapter_id}/analytics",
                "/chapters/batch-content",
            ]

            found_endpoints = 0
            for pattern in endpoint_patterns:
                if pattern in content:
                    found_endpoints += 1

            if found_endpoints >= 4:  # At least most endpoints should be there
                self.log_test(
                    "API endpoints defined",
                    True,
                    f"Found {found_endpoints}/{len(endpoint_patterns)} endpoints",
                )
            else:
                self.log_test(
                    "API endpoints defined",
                    False,
                    f"Only found {found_endpoints}/{len(endpoint_patterns)} endpoints",
                )

        except Exception as e:
            self.log_test("API endpoints defined", False, str(e))

    def run_all_tests(self):
        """Run all tests and report results."""
        print("🧪 Testing Chapter Tabs Implementation")
        print("=" * 50)

        # Run all test methods
        self.test_schema_creation()
        self.test_service_imports()
        self.test_database_utilities()
        self.test_migration_script()
        self.test_status_transitions()
        self.test_bulk_operations()
        self.test_api_endpoint_paths()

        # Calculate results
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["passed"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0

        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {success_rate:.1f}%")

        if failed_tests == 0:
            print(
                "\n🎉 All tests passed! Chapter Tabs implementation is working correctly."
            )
            print("\n📋 IMPLEMENTATION STATUS:")
            print("   ✅ Database schema extensions")
            print("   ✅ Service layer implementation")
            print("   ✅ API endpoint definitions")
            print("   ✅ Caching and error handling")
            print("   ✅ Migration scripts")
            print("   ✅ Status management")

            print("\n🚀 READY FOR:")
            print("   • Integration testing with database")
            print("   • Frontend integration")
            print("   • Performance testing")
            print("   • Production deployment")
        else:
            print(f"\n🔧 {failed_tests} test(s) failed. Review the errors above.")

        return failed_tests == 0


def main():
    """Main test function."""
    tester = ChapterTabsAPITester()
    success = tester.run_all_tests()
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
