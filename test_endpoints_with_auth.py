#!/usr/bin/env python3
"""
Test script to check API endpoints using the backend's test infrastructure.
This script directly imports and uses the backend's authentication system.
"""

import sys
import os
import asyncio

# Change to backend directory and add to path
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(script_dir, "backend")
os.chdir(backend_path)
sys.path.insert(0, backend_path)

# Set up test environment
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import json
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from app.main import app
import app.core.security as sec
import app.api.dependencies as deps
from app.db import base
from fastapi import Request
from bson import ObjectId
import pymongo


# Patch rate limiter for testing
def fake_get_rate_limiter(limit: int = 10, window: int = 60):
    async def _always_allow(request: Request):
        return {"limit": float("inf"), "remaining": float("inf"), "reset": None}

    return _always_allow


deps.get_rate_limiter = fake_get_rate_limiter

# Test MongoDB connection
TEST_MONGO_URI = "mongodb://localhost:27017/auto-author-test"
_sync_client = pymongo.MongoClient(TEST_MONGO_URI)
_sync_db = _sync_client.get_default_database()
_sync_users = _sync_db.get_collection("users")
_sync_books = _sync_db.get_collection("books")


def create_test_user():
    """Create a test user in the database."""
    user = {
        "_id": ObjectId(),
        "clerk_id": "test_clerk_id_endpoint_test",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "display_name": "Test User",
        "avatar_url": None,
        "bio": "Test user for endpoint testing",
        "role": "user",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "books": [],
        "preferences": {
            "theme": "light",
            "email_notifications": False,
            "marketing_emails": False,
        },
    }
    user["id"] = str(user["_id"])

    # Insert or update the user
    _sync_users.replace_one({"clerk_id": user["clerk_id"]}, user, upsert=True)
    return user


def create_test_book(user):
    """Create a test book owned by the user."""
    book = {
        "_id": ObjectId(),
        "title": "Test Book for Endpoint Testing",
        "subtitle": "A test book",
        "description": "This is a test book for endpoint testing.",
        "genre": "Fiction",
        "target_audience": "Adults",
        "owner_id": user["clerk_id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "toc": {
            "chapters": [
                {
                    "id": "chapter_1",
                    "title": "Chapter 1",
                    "subtitle": "The Beginning",
                    "questions": [],
                },
                {
                    "id": "chapter_2",
                    "title": "Chapter 2",
                    "subtitle": "The Middle",
                    "questions": [],
                },
            ]
        },
        "chapter_states": {
            "chapter_1": {
                "status": "complete",
                "content": "Sample content for chapter 1",
            },
            "chapter_2": {"status": "in_progress", "content": ""},
        },
    }
    book["id"] = str(book["_id"])

    # Insert or update the book
    _sync_books.replace_one({"_id": book["_id"]}, book, upsert=True)
    return book


async def test_endpoint(client, url, description):
    """Test a single endpoint and return the response."""
    print(f"\n--- Testing {description} ---")
    print(f"URL: {url}")

    try:
        response = await client.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")

        # Try to parse JSON response
        try:
            if response.content:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
            else:
                print("Empty response")
        except Exception as e:
            print(f"Raw Response: {response.text}")
            print(f"JSON Parse Error: {e}")

        return response
    except Exception as e:
        print(f"Error: {e}")
        return None


async def main():
    print("=" * 60)
    print("TESTING API ENDPOINTS WITH PROPER AUTHENTICATION")
    print("=" * 60)

    # Create test data
    print("Setting up test data...")
    user = create_test_user()
    book = create_test_book(user)
    print(f"Created test user: {user['clerk_id']}")
    print(f"Created test book: {book['id']}")

    # Set up authentication bypass
    async def fake_verify_jwt(token: str):
        return {"sub": user["clerk_id"]}

    # Override the JWT verification
    sec.verify_jwt_token = fake_verify_jwt

    # Override get_current_user to return our test user
    from app.core.security import get_current_user

    app.dependency_overrides[get_current_user] = lambda: user

    # Create authenticated client
    headers = {"Authorization": "Bearer test.jwt.token"}
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers=headers,
    ) as client:

        # Test endpoints
        endpoints = [
            (f"/api/v1/books/{book['id']}/toc", "TOC endpoint"),
            (f"/api/v1/books/{book['id']}/chapters/tab-state", "Tab State endpoint"),
            (
                f"/api/v1/books/{book['id']}/chapters/metadata",
                "Chapters Metadata endpoint",
            ),
        ]

        results = []
        for url, description in endpoints:
            response = await test_endpoint(client, url, description)
            results.append((description, response))

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        for description, response in results:
            if response:
                print(f"{description}: {response.status_code}")
            else:
                print(f"{description}: ERROR")

    # Clean up
    app.dependency_overrides.clear()
    _sync_users.delete_many({"clerk_id": user["clerk_id"]})
    _sync_books.delete_many({"_id": book["_id"]})
    print("\nCleaned up test data.")


if __name__ == "__main__":
    asyncio.run(main())
