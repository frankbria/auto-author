#!/usr/bin/env python3
"""
Script to run unit tests with mocked dependencies
"""

import subprocess
import sys
import os

# Set environment variables to use test database
os.environ['DATABASE_URL'] = 'mongodb://localhost:27017'
os.environ['DATABASE_NAME'] = 'auto_author_test'
os.environ['OPENAI_AUTOAUTHOR_API_KEY'] = 'test-key'
os.environ['BETTER_AUTH_SECRET'] = 'test-secret-key-for-better-auth'
os.environ['BETTER_AUTH_URL'] = 'http://localhost:3000'
os.environ['BETTER_AUTH_ISSUER'] = 'better-auth'

def main():
    """Run unit tests that don't require external services"""
    print("Running unit tests with mocked dependencies...")

    test_files = [
        'tests/test_services/test_ai_service_draft_generation.py',
        'tests/test_services/test_transcription_service.py',
        'tests/test_services/test_transcription_service_aws.py',
        'tests/test_services/test_cloud_storage_service.py',
        'tests/test_services/test_file_upload_service.py',
        'tests/test_api/test_book_cover_upload.py'
    ]

    # Run tests without database dependency
    cmd = [
        'pytest',
        '--no-cov',  # Disable coverage for now
        '-v',
        '--tb=short',
        '-m', 'not integration',  # Skip integration tests
        *test_files
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return result.returncode
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
