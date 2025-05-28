#!/usr/bin/env python3
"""
Test script to verify question responses are being saved and retrieved correctly.
This helps debug the 400 error "question responses are required for toc generation".
"""

import asyncio
import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_BOOK_ID = (
    "675acb6ef5a3c5a23e67ba5a"  # Replace with a real book ID from your test data
)

# Test authentication token - you'll need to get this from your browser
# Go to Network tab -> any API call -> Copy the Authorization header
AUTH_TOKEN = "your_auth_token_here"


async def test_question_responses_flow():
    """Test the complete question responses flow"""

    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json",
    }

    print("🧪 Testing Question Responses Flow")
    print("=" * 50)

    # Step 1: Test GET question responses (should be empty initially)
    print("\n1️⃣ Testing GET question responses...")
    response = requests.get(
        f"{BASE_URL}/books/{TEST_BOOK_ID}/question-responses", headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Existing responses: {len(data.get('responses', []))}")
        print(f"Status: {data.get('status', 'unknown')}")
    else:
        print(f"Error: {response.text}")

    # Step 2: Test saving question responses
    print("\n2️⃣ Testing PUT question responses...")
    test_responses = [
        {
            "question": "What is the main problem your book addresses?",
            "answer": "This book addresses the challenge of creating efficient table of contents for non-fiction books using AI assistance.",
        },
        {
            "question": "Who is your target audience?",
            "answer": "Authors, content creators, and publishers who want to streamline their book organization process.",
        },
        {
            "question": "What are the key concepts you want to cover?",
            "answer": "AI-assisted content organization, automated TOC generation, and user-friendly interfaces for authors.",
        },
    ]

    save_data = {"responses": test_responses}
    response = requests.put(
        f"{BASE_URL}/books/{TEST_BOOK_ID}/question-responses",
        headers=headers,
        json=save_data,
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Saved {data.get('responses_saved', 0)} responses")
        print(f"Ready for TOC: {data.get('ready_for_toc_generation', False)}")
    else:
        print(f"❌ Error: {response.text}")
        return False

    # Step 3: Verify responses were saved
    print("\n3️⃣ Verifying responses were saved...")
    response = requests.get(
        f"{BASE_URL}/books/{TEST_BOOK_ID}/question-responses", headers=headers
    )
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Retrieved {len(data.get('responses', []))} responses")
        print(f"Status: {data.get('status', 'unknown')}")
    else:
        print(f"❌ Error retrieving responses: {response.text}")
        return False

    # Step 4: Test TOC readiness check
    print("\n4️⃣ Testing TOC readiness check...")
    response = requests.get(
        f"{BASE_URL}/books/{TEST_BOOK_ID}/toc-readiness", headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Ready for TOC: {data.get('is_ready_for_toc', False)}")
        print(f"Confidence: {data.get('confidence_score', 0)}")
    else:
        print(f"❌ Error: {response.text}")

    # Step 5: Test TOC generation
    print("\n5️⃣ Testing TOC generation...")
    response = requests.post(
        f"{BASE_URL}/books/{TEST_BOOK_ID}/generate-toc", headers=headers, json={}
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ TOC generated successfully!")
        print(f"Chapters: {len(data.get('toc', {}).get('chapters', []))}")
    else:
        print(f"❌ TOC Generation Error: {response.text}")
        return False

    print("\n🎉 All tests completed successfully!")
    return True


def get_auth_instructions():
    """Print instructions for getting the auth token"""
    print(
        """
🔑 To get your auth token:
1. Open your browser and go to http://localhost:3002
2. Login to your account
3. Open Developer Tools (F12)
4. Go to Network tab
5. Make any API call (like checking TOC readiness)
6. Find the request in Network tab
7. Click on it and look for the Authorization header
8. Copy the token part (after 'Bearer ')
9. Replace 'your_auth_token_here' in this script

📚 To get a book ID:
1. Go to your books list in the frontend
2. Click on any book
3. Copy the book ID from the URL
4. Replace TEST_BOOK_ID in this script
"""
    )


if __name__ == "__main__":
    if AUTH_TOKEN == "your_auth_token_here":
        print("❌ Please set your AUTH_TOKEN first!")
        get_auth_instructions()
        sys.exit(1)

    asyncio.run(test_question_responses_flow())
