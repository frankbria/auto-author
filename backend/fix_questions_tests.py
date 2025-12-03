#!/usr/bin/env python3
"""
Comprehensive fix for books_questions_drafts.py tests.
Adds request bodies to all POST /generate-questions calls.
"""

import re
from pathlib import Path

def main():
    test_file = Path(__file__).parent / "tests/test_api/test_routes/test_books_questions_drafts.py"
    content = test_file.read_text()

    # Pattern 1: Fix simple generate-questions calls (without json parameter)
    # gen_resp = await client.post(f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions")
    pattern1 = r'(gen_resp\s*=\s*await\s+client\.post\(\s*f"/api/v1/books/\{book_id\}/chapters/\{chapter_id\}/generate-questions")\)'
    replacement1 = r'\1, json={"count": 5})'
    content = re.sub(pattern1, replacement1, content)

    # Pattern 2: Fix regenerate-questions calls
    pattern2 = r'(draft_resp\s*=\s*await\s+client\.post\(\s*f"/api/v1/books/\{book_id\}/chapters/\{chapter_id\}/regenerate-questions")\)'
    replacement2 = r'\1, json={"count": 5})'
    content = re.sub(pattern2, replacement2, content)

    # Write back
    test_file.write_text(content)
    print(f"Fixed generate-questions calls in {test_file}")

if __name__ == "__main__":
    main()
