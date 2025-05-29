#!/usr/bin/env python3
"""
Test script to compare the behavior of /toc and /chapters/tab-state endpoints
"""
import requests
import json
import os
import base64
from datetime import datetime, timezone
from typing import Dict, Any

# Configuration
BACKEND_URL = "http://localhost:8000"
API_BASE = f"{BACKEND_URL}/api/v1"


def get_test_auth_token():
    """
    Create a properly formatted mock JWT token for testing.
    This creates a valid JWT structure but without a real signature.
    """
    # JWT Header
    header = {"alg": "RS256", "typ": "JWT"}

    # JWT Payload
    payload = {
        "sub": "user_mock123456789",  # Mock Clerk user ID
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc)).timestamp()) + 3600,  # 1 hour from now
        "aud": "example.com",
        "iss": "https://clerk.your-domain.com",
    }

    # Base64 encode (note: this won't have a valid signature, but it has the right structure)
    header_b64 = (
        base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    )
    payload_b64 = (
        base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    )

    # Create a mock signature (in real JWT this would be cryptographically signed)
    signature = "mock_signature_for_testing_purposes_only"

    return f"{header_b64}.{payload_b64}.{signature}"


def test_endpoint(endpoint: str, headers: Dict[str, str] = None) -> Dict[str, Any]:
    """Test a specific endpoint and return detailed response info"""
    url = f"{API_BASE}{endpoint}"

    print(f"\n=== Testing {endpoint} ===")
    print(f"URL: {url}")

    if headers:
        print(f"Headers: {json.dumps(headers, indent=2)}")

    try:
        response = requests.get(url, headers=headers or {}, timeout=10)

        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")

        # Try to parse JSON response
        try:
            response_data = response.json()
            print(f"Response Body: {json.dumps(response_data, indent=2)}")
        except json.JSONDecodeError:
            print(f"Response Body (text): {response.text}")

        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
            "success": response.status_code < 400,
        }

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return {"status_code": None, "headers": {}, "body": str(e), "success": False}


def main():
    print("Testing Auto Author API endpoints...")
    print("=" * 50)

    # Get auth token (if available)
    auth_token = get_test_auth_token()
    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    # Test book ID - you'll need to replace this with a real book ID from your database
    # For testing, let's use a dummy ID to see the error
    test_book_id = "507f1f77bcf86cd799439011"  # Example MongoDB ObjectId format

    # Test endpoints
    endpoints_to_test = [
        f"/books/{test_book_id}/toc",
        f"/books/{test_book_id}/chapters/tab-state",
        f"/books/{test_book_id}/chapters/metadata",  # Additional comparison endpoint
    ]

    results = {}

    for endpoint in endpoints_to_test:
        results[endpoint] = test_endpoint(endpoint, headers)

    # Summary comparison
    print("\n" + "=" * 50)
    print("SUMMARY COMPARISON")
    print("=" * 50)

    for endpoint, result in results.items():
        status = "✓ SUCCESS" if result["success"] else "✗ FAILED"
        print(f"{endpoint}: {result['status_code']} - {status}")

    # Check for differences in behavior
    toc_result = results.get(f"/books/{test_book_id}/toc")
    tab_state_result = results.get(f"/books/{test_book_id}/chapters/tab-state")

    if toc_result and tab_state_result:
        if toc_result["status_code"] != tab_state_result["status_code"]:
            print(f"\n⚠️  DIFFERENT STATUS CODES DETECTED:")
            print(f"TOC endpoint: {toc_result['status_code']}")
            print(f"Tab-state endpoint: {tab_state_result['status_code']}")
            print("\nThis confirms the issue described in the task.")


if __name__ == "__main__":
    main()
