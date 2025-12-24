#!/usr/bin/env python3
"""
Simple test script to verify API endpoints without authentication
"""
import requests
import json
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("d:\\Projects\\auto-author\\backend\\.env")

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")


def get_books_from_db():
    """Get books directly from database to find real book IDs"""
    try:
        client = MongoClient(DATABASE_URL)
        db = client[DATABASE_NAME]
        books = list(db["books"].find({}, {"_id": 1, "title": 1}).limit(5))
        client.close()
        return books
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return []


def test_toc_readiness_endpoint():
    """Test the /toc-readiness endpoint with a real book ID"""
    books = get_books_from_db()

    if not books:
        print("No books found in database")
        return

    print(f"Found {len(books)} books in database:")
    for book in books:
        print(f"  - {book['title']} (ID: {book['_id']})")

    # Test with the first book
    book_id = str(books[0]["_id"])
    url = f"http://localhost:8000/api/v1/books/{book_id}/toc-readiness"

    print(f"\nTesting endpoint: {url}")

    try:
        # Test without auth first to see what happens
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 404:
            print(
                "Book not found - this is expected if the endpoint requires the book to have a summary"
            )
        elif response.status_code == 401:
            print("Authentication required - this confirms the endpoint exists")
        elif response.status_code == 200:
            print("Success! Response structure:")
            try:
                data = response.json()
                print(json.dumps(data, indent=2))
            except:
                print("Response is not JSON")

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")


if __name__ == "__main__":
    test_toc_readiness_endpoint()
