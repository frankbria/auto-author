#!/usr/bin/env python3
"""
Script to verify question collection indexes are properly created.
Run this after starting the application to confirm indexes exist.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import get_collection


async def verify_indexes():
    """Verify all expected indexes exist in question collections."""
    print("Verifying question collection indexes...\n")

    # Expected indexes for each collection
    expected_indexes = {
        "questions": [
            "book_chapter_user_idx",
            "user_created_idx",
            "chapter_order_idx"
        ],
        "question_responses": [
            "question_user_idx",
            "user_created_idx"
        ],
        "question_ratings": [
            "question_user_idx"
        ]
    }

    all_verified = True

    for collection_name, expected in expected_indexes.items():
        print(f"Checking collection: {collection_name}")
        print("=" * 60)

        collection = await get_collection(collection_name)
        indexes = await collection.list_indexes().to_list(length=None)
        index_names = [idx['name'] for idx in indexes]

        print(f"Found {len(indexes)} indexes:")
        for idx in indexes:
            print(f"  - {idx['name']}")
            if 'key' in idx:
                print(f"    Keys: {list(idx['key'].items())}")
            if 'unique' in idx and idx['unique']:
                print(f"    Unique: True")
            if 'background' in idx and idx['background']:
                print(f"    Background: True")

        # Verify expected indexes exist
        print("\nVerification:")
        for expected_idx in expected:
            if expected_idx in index_names:
                print(f"  ✓ {expected_idx} - FOUND")
            else:
                print(f"  ✗ {expected_idx} - MISSING")
                all_verified = False

        print("\n")

    if all_verified:
        print("✅ All expected indexes verified successfully!")
        return 0
    else:
        print("❌ Some indexes are missing. Run ensure_question_indexes() to create them.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(verify_indexes())
    sys.exit(exit_code)
