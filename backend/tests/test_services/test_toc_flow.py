#!/usr/bin/env python3
"""
Test script to verify the TOC generation flow step by step.
This script tests the logical sequence of API calls needed for TOC generation.
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_BOOK_ID = "67666aec7a1f3e1b72bf6df9"  # Using the book ID from test data

# Mock auth token (you would need a real one in production)
AUTH_TOKEN = "test-token"


def make_request(method, endpoint, data=None):
    """Make HTTP request with authentication headers"""
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json",
    }

    url = f"{BASE_URL}{endpoint}"

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data if data else {})
        else:
            raise ValueError(f"Unsupported method: {method}")

        print(f"\n{method.upper()} {endpoint}")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None


def test_toc_generation_flow():
    """Test the complete TOC generation flow"""

    print("=" * 60)
    print("TESTING TOC GENERATION FLOW")
    print("=" * 60)

    # Step 1: Get book details
    print("\n1. Getting book details...")
    book = make_request("GET", f"/books/{TEST_BOOK_ID}")
    if not book:
        print("❌ Failed to get book details - stopping test")
        return

    print(f"✅ Book found: {book.get('title', 'Unknown Title')}")
    print(
        f"   Summary length: {len(book.get('summary', '')) if book.get('summary') else 0} characters"
    )

    # Step 2: Analyze summary with AI
    print("\n2. Analyzing summary with AI...")
    analysis_result = make_request("POST", f"/books/{TEST_BOOK_ID}/analyze-summary")
    if not analysis_result:
        print("❌ Failed to analyze summary")
        return

    analysis = analysis_result.get("analysis", {})
    print(f"✅ Analysis completed:")
    print(f"   Ready for TOC: {analysis.get('is_ready_for_toc', False)}")
    print(f"   Confidence Score: {analysis.get('confidence_score', 0.0):.1%}")
    print(f"   Word Count: {analysis.get('word_count', 0)}")
    print(f"   Analysis: {analysis.get('analysis', 'N/A')[:100]}...")

    # Step 3: Check TOC readiness (should now have analysis data)
    print("\n3. Checking TOC readiness...")
    readiness = make_request("GET", f"/books/{TEST_BOOK_ID}/toc-readiness")
    if not readiness:
        print("❌ Failed to check TOC readiness")
        return

    print(f"✅ Readiness check completed:")
    print(f"   Ready for TOC: {readiness.get('is_ready_for_toc', False)}")
    print(f"   Confidence Score: {readiness.get('confidence_score', 0.0):.1%}")
    print(
        f"   Meets Requirements: {readiness.get('meets_minimum_requirements', False)}"
    )

    if not readiness.get("is_ready_for_toc", False):
        print("\n⚠️  Summary is not ready for TOC generation")
        print("   Suggestions:")
        for suggestion in readiness.get("suggestions", []):
            print(f"   - {suggestion}")
        return

    # Step 4: Generate clarifying questions
    print("\n4. Generating clarifying questions...")
    questions_result = make_request("POST", f"/books/{TEST_BOOK_ID}/generate-questions")
    if not questions_result:
        print("❌ Failed to generate questions")
        return

    questions = questions_result.get("questions", [])
    print(f"✅ Generated {len(questions)} questions:")
    for i, question in enumerate(questions, 1):
        print(f"   {i}. {question}")

    # Step 5: Simulate answering questions
    print("\n5. Simulating question responses...")
    mock_responses = []
    for question in questions:
        mock_responses.append(
            {
                "question": question,
                "answer": "This is a mock answer for testing purposes. In a real scenario, the user would provide detailed answers.",
            }
        )

    # Save responses
    save_result = make_request(
        "POST", f"/books/{TEST_BOOK_ID}/save-responses", {"responses": mock_responses}
    )
    if save_result:
        print(f"✅ Saved {len(mock_responses)} question responses")

    # Step 6: Generate TOC
    print("\n6. Generating Table of Contents...")
    toc_result = make_request(
        "POST",
        f"/books/{TEST_BOOK_ID}/generate-toc",
        {"question_responses": mock_responses},
    )
    if not toc_result:
        print("❌ Failed to generate TOC")
        return

    toc = toc_result.get("toc", {})
    chapters = toc.get("chapters", [])
    print(f"✅ TOC generated successfully:")
    print(f"   Total chapters: {toc.get('total_chapters', 0)}")
    print(f"   Estimated pages: {toc.get('estimated_pages', 0)}")
    print(f"   Structure notes: {toc.get('structure_notes', 'N/A')[:100]}...")

    print(f"\n   Chapter titles:")
    for chapter in chapters[:5]:  # Show first 5 chapters
        print(f"   - {chapter.get('title', 'Untitled Chapter')}")

    if len(chapters) > 5:
        print(f"   ... and {len(chapters) - 5} more chapters")

    print("\n✅ TOC generation flow completed successfully!")


if __name__ == "__main__":
    test_toc_generation_flow()
