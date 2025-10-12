#!/usr/bin/env python3
"""
Simple System Test for Auto Author
This version uses direct HTTP requests without pytest fixtures
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
AUTH_TOKEN = "Bearer test.token.here"  # You'll need to get a real token

# Test data
TEST_BOOK = {
    "title": f"System Test: Psychology of Habits - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    "author_name": "System Test Author",
    "genre": "Non-Fiction",
    "target_audience": "Adults interested in personal development",
    "description": "A comprehensive guide to understanding how habits are formed in the brain.",
    "language": "English",
    "estimated_word_count": 50000,
}


class SimpleSystemTest:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": AUTH_TOKEN,
            "Content-Type": "application/json"
        })
        self.book_id = None
        self.chapter_id = None
        
    def log(self, message: str, level: str = "INFO"):
        icons = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "STEP": "🔸"
        }
        print(f"{icons.get(level, '•')} {message}")
        
    def test_health(self):
        """Test basic connectivity"""
        self.log("Testing API health...", "STEP")
        response = requests.get(f"{BASE_URL}/health")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                self.log("API is healthy!", "SUCCESS")
                return True
        
        self.log(f"Health check failed: {response.text}", "ERROR")
        return False
        
    def test_auth_required(self):
        """Test that authentication is required"""
        self.log("Testing authentication requirement...", "STEP")
        
        # Try without auth
        response = requests.get(f"{BASE_URL}/books/")
        
        if response.status_code == 403:
            self.log("Authentication properly enforced", "SUCCESS")
            return True
        
        self.log(f"Unexpected response: {response.status_code}", "ERROR")
        return False
        
    def create_book(self):
        """Create a test book"""
        self.log("Creating test book...", "STEP")
        
        response = self.session.post(f"{BASE_URL}/books/", json=TEST_BOOK)
        
        if response.status_code == 200 or response.status_code == 201:
            book = response.json()
            self.book_id = book.get("id")
            self.log(f"Book created: {book.get('title')} (ID: {self.book_id})", "SUCCESS")
            return True
        
        self.log(f"Failed to create book: {response.status_code} - {response.text}", "ERROR")
        return False
        
    def run_tests(self):
        """Run all tests"""
        print("\n🚀 Auto Author Simple System Test\n")
        
        tests = [
            ("Health Check", self.test_health),
            ("Auth Required", self.test_auth_required),
        ]
        
        # Only run book creation if we have a valid auth token
        if AUTH_TOKEN != "Bearer test.token.here":
            tests.append(("Create Book", self.create_book))
        else:
            self.log("Skipping authenticated tests - no valid token provided", "INFO")
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            print(f"\n--- {test_name} ---")
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log(f"Test failed with exception: {e}", "ERROR")
                failed += 1
        
        print(f"\n📊 Results: {passed} passed, {failed} failed")
        
        if failed == 0:
            self.log("All tests passed!", "SUCCESS")
        else:
            self.log("Some tests failed", "ERROR")
            
        return failed == 0


if __name__ == "__main__":
    test = SimpleSystemTest()
    success = test.run_tests()
    exit(0 if success else 1)