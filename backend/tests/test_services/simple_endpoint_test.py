#!/usr/bin/env python3
"""
Simplified test script to check API endpoints with mock authentication.
"""
import asyncio
import json
import sys
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport

print("Starting imports...")
try:
    from app.main import app

    print("✓ App imported")
    from app.core.security import get_current_user

    print("✓ Security imported")
    from bson import ObjectId

    print("✓ BSON imported")
except Exception as e:
    print(f"Import error: {e}")
    sys.exit(1)

# Mock user data
MOCK_USER = {
    "_id": ObjectId(),
    "id": str(ObjectId()),
    "clerk_id": "test_clerk_id_simple",
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "display_name": "Test User",
    "role": "user",
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
}

# Mock book data
MOCK_BOOK_ID = "675e30c6acada5e0b5b7b89a"  # Use a real book ID from the database


async def test_endpoints():
    print("Starting simplified endpoint tests...")

    try:
        # Override authentication
        print("Setting up authentication override...")
        app.dependency_overrides[get_current_user] = lambda: MOCK_USER
        print("✓ Authentication override set")

        print("Creating HTTP client...")
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            headers={"Authorization": "Bearer test.token"},
        ) as client:
            print("✓ Client created")

            endpoints = [
                f"/api/v1/books/{MOCK_BOOK_ID}/toc",
                f"/api/v1/books/{MOCK_BOOK_ID}/chapters/tab-state",
                f"/api/v1/books/{MOCK_BOOK_ID}/chapters/metadata",
            ]

            for endpoint in endpoints:
                print(f"\nTesting: {endpoint}")
                try:
                    response = await client.get(endpoint)
                    print(f"Status: {response.status_code}")
                    if response.status_code != 200:
                        print(f"Error: {response.text}")
                    else:
                        print("✓ Success")
                except Exception as e:
                    print(f"Exception during request: {e}")
                    import traceback

                    traceback.print_exc()

        print("\nCleaning up...")
        # Clean up
        app.dependency_overrides.clear()
        print("✓ Done!")

    except Exception as e:
        print(f"Error in test_endpoints: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("Script starting...")
    try:
        asyncio.run(test_endpoints())
    except Exception as e:
        print(f"Error running async main: {e}")
        import traceback

        traceback.print_exc()
