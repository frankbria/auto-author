#!/usr/bin/env python3
"""
Script to fix test files that access chapter_resp.json()["id"] to use ["chapter_id"] instead.
"""

import re
from pathlib import Path

def fix_chapter_id_access(content: str) -> tuple[str, int]:
    """
    Replace chapter_resp.json()["id"] with chapter_resp.json()["chapter_id"]
    Returns: (fixed_content, num_replacements)
    """
    # Pattern to match: chapter_resp = ... followed by chapter_id = chapter_resp.json()["id"]
    pattern = r'(chapter_resp\s*=.*?\n\s+chapter_id\s*=\s*chapter_resp\.json\(\)\[")id("\])'
    replacement = r'\1chapter_id\2'

    fixed_content, count = re.subn(pattern, replacement, content)
    return fixed_content, count

def process_test_file(file_path: Path) -> int:
    """Process a single test file. Returns number of fixes made."""
    content = file_path.read_text()
    fixed_content, count = fix_chapter_id_access(content)

    if count > 0:
        file_path.write_text(fixed_content)
        print(f"Fixed {count} occurrences in {file_path}")

    return count

def main():
    """Find and fix all test files with chapter ID issues."""
    test_dir = Path(__file__).parent / "tests"
    test_files = list(test_dir.rglob("test_*.py"))

    total_fixes = 0
    for test_file in test_files:
        fixes = process_test_file(test_file)
        total_fixes += fixes

    print(f"\nTotal: Fixed {total_fixes} occurrences across {len([f for f in test_files if process_test_file(f) > 0])} files")

if __name__ == "__main__":
    main()
