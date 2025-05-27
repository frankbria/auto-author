#!/usr/bin/env python3
"""
Chapter Tabs Implementation Validator
===================================

A standalone validation script to verify that our chapter tabs implementation
is complete and ready for integration.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
import re

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))


class ChapterTabsValidator:
    """Validates the completeness of chapter tabs implementation."""

    def __init__(self):
        self.backend_dir = Path(__file__).parent.parent
        self.errors = []
        self.warnings = []
        self.passed_checks = []

    def validate_file_exists(self, file_path: str, description: str):
        """Check if a required file exists."""
        full_path = self.backend_dir / file_path
        if full_path.exists():
            self.passed_checks.append(f"✅ {description}: {file_path}")
            return True
        else:
            self.errors.append(f"❌ Missing {description}: {file_path}")
            return False

    def validate_model_extensions(self):
        """Validate that the book model has been properly extended."""
        model_file = self.backend_dir / "app" / "models" / "book.py"

        if not model_file.exists():
            self.errors.append("❌ Book model file not found")
            return

        content = model_file.read_text()

        # Check for new TocItem fields
        required_fields = [
            "status:",
            "word_count:",
            "last_modified:",
            "estimated_reading_time:",
            "is_active_tab:",
        ]

        for field in required_fields:
            if field in content:
                self.passed_checks.append(f"✅ TocItem has {field.rstrip(':')}")
            else:
                self.errors.append(f"❌ TocItem missing {field.rstrip(':')}")

    def validate_schema_extensions(self):
        """Validate that the book schema has been properly extended."""
        schema_file = self.backend_dir / "app" / "schemas" / "book.py"

        if not schema_file.exists():
            self.errors.append("❌ Book schema file not found")
            return

        content = schema_file.read_text()

        # Check for new schemas
        required_schemas = [
            "ChapterStatus",
            "ChapterMetadata",
            "ChapterMetadataResponse",
            "TabStateRequest",
            "TabStateResponse",
            "BulkStatusUpdate",
        ]

        for schema in required_schemas:
            if f"class {schema}" in content or f"{schema} =" in content:
                self.passed_checks.append(f"✅ Schema has {schema}")
            else:
                self.errors.append(f"❌ Schema missing {schema}")

    def validate_api_endpoints(self):
        """Validate that new API endpoints have been added."""
        api_file = self.backend_dir / "app" / "api" / "endpoints" / "books.py"

        if not api_file.exists():
            self.errors.append("❌ Books API file not found")
            return

        content = api_file.read_text()

        # Check for new endpoints
        required_endpoints = [
            "/chapters/metadata",
            "/chapters/bulk-status",
            "/chapters/tab-state",
            "/chapters/{chapter_id}/content",
            "/chapters/{chapter_id}/analytics",
            "/chapters/batch-content",
        ]

        for endpoint in required_endpoints:
            if endpoint in content:
                self.passed_checks.append(f"✅ API has {endpoint}")
            else:
                self.warnings.append(f"⚠️ API might be missing {endpoint}")

    def validate_service_files(self):
        """Validate that all required service files exist."""
        services = [
            ("app/services/chapter_access_service.py", "Chapter Access Service"),
            ("app/services/chapter_status_service.py", "Chapter Status Service"),
            ("app/services/chapter_cache_service.py", "Chapter Cache Service"),
            ("app/services/chapter_error_handler.py", "Chapter Error Handler"),
        ]

        for file_path, description in services:
            self.validate_file_exists(file_path, description)

    def validate_infrastructure_files(self):
        """Validate that infrastructure files exist."""
        infrastructure = [
            ("app/db/indexing_strategy.py", "Database Indexing Strategy"),
            ("app/scripts/migration_chapter_tabs.py", "Migration Script"),
            ("app/models/chapter_access.py", "Chapter Access Models"),
        ]

        for file_path, description in infrastructure:
            self.validate_file_exists(file_path, description)

    def validate_service_implementations(self):
        """Validate that service classes are properly implemented."""
        service_classes = [
            ("app/services/chapter_access_service.py", "ChapterAccessService"),
            ("app/services/chapter_status_service.py", "ChapterStatusService"),
            ("app/services/chapter_cache_service.py", "ChapterMetadataCache"),
            ("app/services/chapter_error_handler.py", "ChapterErrorHandler"),
        ]

        for file_path, class_name in service_classes:
            full_path = self.backend_dir / file_path
            if full_path.exists():
                content = full_path.read_text()
                if f"class {class_name}" in content:
                    self.passed_checks.append(f"✅ Service class {class_name} exists")
                else:
                    self.errors.append(
                        f"❌ Service class {class_name} not found in {file_path}"
                    )
            else:
                self.errors.append(f"❌ Service file {file_path} not found")

    def validate_test_files(self):
        """Validate that test files have been created."""
        test_file = (
            self.backend_dir
            / "tests"
            / "integration"
            / "test_chapter_tabs_integration.py"
        )
        if test_file.exists():
            self.passed_checks.append("✅ Integration tests created")
        else:
            self.warnings.append("⚠️ Integration tests not found")

    def check_import_compatibility(self):
        """Check if the main modules can be imported without syntax errors."""
        try:
            from app.schemas.book import ChapterStatus, ChapterMetadata

            self.passed_checks.append("✅ Schema imports work correctly")
        except ImportError as e:
            self.errors.append(f"❌ Schema import error: {e}")
        except SyntaxError as e:
            self.errors.append(f"❌ Schema syntax error: {e}")
        except Exception as e:
            self.warnings.append(f"⚠️ Schema import warning: {e}")

    def run_validation(self):
        """Run all validation checks."""
        print("🔍 Validating Chapter Tabs Implementation")
        print("=" * 50)

        # Run all validation checks
        self.validate_model_extensions()
        self.validate_schema_extensions()
        self.validate_api_endpoints()
        self.validate_service_files()
        self.validate_infrastructure_files()
        self.validate_service_implementations()
        self.validate_test_files()
        self.check_import_compatibility()

        # Print results
        print("\n✅ PASSED CHECKS:")
        for check in self.passed_checks:
            print(f"  {check}")

        if self.warnings:
            print("\n⚠️ WARNINGS:")
            for warning in self.warnings:
                print(f"  {warning}")

        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"  {error}")

        # Summary
        total_checks = len(self.passed_checks) + len(self.warnings) + len(self.errors)
        passed_percentage = (
            (len(self.passed_checks) / total_checks) * 100 if total_checks > 0 else 0
        )

        print("\n" + "=" * 50)
        print(f"📊 VALIDATION SUMMARY")
        print(f"   Passed: {len(self.passed_checks)}")
        print(f"   Warnings: {len(self.warnings)}")
        print(f"   Errors: {len(self.errors)}")
        print(f"   Success Rate: {passed_percentage:.1f}%")

        if len(self.errors) == 0:
            print("\n🎉 Chapter Tabs Implementation is READY!")
            return True
        else:
            print(
                f"\n🔧 {len(self.errors)} issues need to be resolved before deployment"
            )
            return False


def main():
    """Main validation function."""
    validator = ChapterTabsValidator()
    success = validator.run_validation()

    if success:
        print("\n📋 NEXT STEPS:")
        print("  1. Run integration tests")
        print("  2. Test API endpoints manually")
        print("  3. Run migration script in staging")
        print("  4. Deploy to production")
    else:
        print("\n🛠️ REQUIRED ACTIONS:")
        print("  1. Fix the errors listed above")
        print("  2. Re-run this validation script")
        print("  3. Proceed with testing once all errors are resolved")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
