#!/usr/bin/env python3
"""
Script to split monolithic books.py into modular files.
This maintains all functionality while improving code organization.
"""

import os
import re

# Define the base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOKS_FILE = os.path.join(BASE_DIR, "app/api/endpoints/books.py")
OUTPUT_DIR = os.path.join(BASE_DIR, "app/api/endpoints/books")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Read the original file
with open(BOOKS_FILE, 'r') as f:
    content = f.read()
    lines = content.split('\n')

# Common imports header (lines 0-76)
COMMON_IMPORTS = '\n'.join(lines[0:77])

# Extract helper code (offensive words loader, lines 71-76)
HELPER_CODE = '\n'.join(lines[67:77])

# Define route mappings with line ranges (approximate, will be refined)
ROUTE_MAPPINGS = {
    'books_crud.py': {
        'description': 'Basic CRUD operations for books',
        'routes': [
            'create_new_book',  # Line 80
            'get_user_books',   # Line 137
            'get_book',         # Line 168
            'update_book_details',  # Line 230
            'patch_book_details',   # Line 321
            'delete_book_endpoint', # Line 407
            'upload_book_cover_image',  # Line 474
            'get_book_summary',     # Line 550
            'update_book_summary',  # Line 573
            'patch_book_summary',   # Line 635
        ],
        'end_line': 688
    },
    'books_toc.py': {
        'description': 'TOC generation and management',
        'routes': [
            'analyze_book_summary',  # Line 689
            'generate_clarifying_questions',  # Line 748
            'get_question_responses',  # Line 819
            'save_question_responses',  # Line 850
            'check_toc_generation_readiness',  # Line 919
            'generate_table_of_contents',  # Line 1019
            'get_book_toc',  # Line 1096
            'update_book_toc',  # Line 1149
        ],
        'start_line': 689,
        'end_line': 1225
    },
    'books_chapters.py': {
        'description': 'Chapter operations',
        'routes': [
            # Add chapter is in line 1226
            'get_chapter',  # Line 1292
            'update_chapter',  # Line 1339
            'delete_chapter',  # Line 1417
            'list_chapters',  # Line 1467
            'get_chapters_metadata',  # Line 1533
            'update_chapter_status_bulk',  # Line 1610
            'save_tab_state',  # Line 1704
            'get_tab_state',  # Line 1742
            'get_chapter_content',  # Line 1787
            'update_chapter_content',  # Line 1872
            'get_chapter_analytics',  # Line 1972
            'batch_get_chapter_content',  # Line 2016
        ],
        'start_line': 1226,
        'end_line': 2113
    },
    'books_questions.py': {
        'description': 'Question generation for chapters',
        'routes': [
            'generate_chapter_questions',  # Line 2114
            'list_chapter_questions',  # Line 2180
            # More question endpoints from line 2232 onward
        ],
        'start_line': 2114,
        'end_line': 2541
    },
    'books_drafts.py': {
        'description': 'Draft generation for chapters',
        'routes': [
            'generate_chapter_draft',  # Line 2542
            # More draft endpoints after this
        ],
        'start_line': 2542,
        'end_line': -1  # To end of file
    },
}

def extract_section(lines, start_line, end_line):
    """Extract a section of lines (1-indexed line numbers)"""
    if end_line == -1:
        end_line = len(lines)
    # Convert to 0-indexed
    return lines[start_line-1:end_line]

def create_module_header(description):
    """Create a module docstring"""
    return f'"""{description}"""\n\n'

# Process each module
for filename, config in ROUTE_MAPPINGS.items():
    print(f"Creating {filename}...")

    # Start with common imports
    module_content = COMMON_IMPORTS + '\n\n'

    # Add module docstring
    module_content += create_module_header(config['description'])

    # Add helper code (only for books_crud.py which needs OFFENSIVE_WORDS)
    if filename == 'books_crud.py':
        module_content += HELPER_CODE + '\n\n'

    # Extract the route functions
    start = config['start_line'] if 'start_line' in config else 78
    end = config['end_line']

    route_code = '\n'.join(extract_section(lines, start, end))
    module_content += route_code

    # Write to file
    output_path = os.path.join(OUTPUT_DIR, filename)
    with open(output_path, 'w') as f:
        f.write(module_content)

    print(f"  ✓ Created {filename} ({len(module_content.split(chr(10)))} lines)")

print("\nAll modules created successfully!")
print(f"Output directory: {OUTPUT_DIR}")
