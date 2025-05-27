import os
import sys
from pathlib import Path


def main():
    backend_dir = Path(__file__).parent

    print("🔍 Validating Chapter Tabs Implementation")
    print("=" * 50)

    # Check required files
    files_to_check = [
        "app/models/book.py",
        "app/schemas/book.py",
        "app/api/endpoints/books.py",
        "app/services/chapter_access_service.py",
        "app/services/chapter_status_service.py",
        "app/services/chapter_cache_service.py",
        "app/services/chapter_error_handler.py",
        "app/db/indexing_strategy.py",
        "app/scripts/migration_chapter_tabs.py",
        "app/models/chapter_access.py",
    ]

    passed = 0
    failed = 0

    for file_path in files_to_check:
        full_path = backend_dir / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
            passed += 1
        else:
            print(f"❌ {file_path}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"📊 SUMMARY: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All required files are present!")
        print("\n📋 NEXT STEPS:")
        print("  1. Test API endpoints")
        print("  2. Run migration script")
        print("  3. Verify frontend integration")
    else:
        print(f"🔧 {failed} files are missing")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
