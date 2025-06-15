"""Test actual utility validators"""

import pytest
from pydantic import ValidationError
from app.utils.validators import (
    validate_book_create_data, validate_book_update_data,
    validate_toc_item_data, sanitize_book_title,
    validate_book_relationship, validate_text_safety
)


def test_validate_book_create_data():
    """Test book creation data validation"""
    # Valid data
    valid_data = {
        "title": "My Book",
        "description": "A great book",
        "genre": "Fiction",
        "target_audience": "Adults"
    }
    result = validate_book_create_data(valid_data)
    assert result["title"] == "My Book"
    assert result["genre"] == "Fiction"
    
    # Missing required field
    with pytest.raises(ValidationError) as exc_info:
        validate_book_create_data({
            "title": "Book",
            "description": "Desc"
            # Missing genre and target_audience
        })
    assert "genre" in str(exc_info.value)
    
    # Invalid genre
    with pytest.raises(ValidationError) as exc_info:
        validate_book_create_data({
            "title": "Book",
            "description": "Desc",
            "genre": "InvalidGenre",
            "target_audience": "Adults"
        })


def test_validate_book_update_data():
    """Test book update data validation"""
    # Valid partial update
    update_data = {
        "title": "Updated Title",
        "genre": "Non-Fiction"
    }
    result = validate_book_update_data(update_data)
    assert result["title"] == "Updated Title"
    assert result["genre"] == "Non-Fiction"
    assert "description" not in result  # None values filtered out
    
    # All fields None
    result = validate_book_update_data({})
    assert result == {}
    
    # Invalid data
    with pytest.raises(ValidationError):
        validate_book_update_data({
            "genre": "InvalidGenre"
        })


def test_validate_toc_item_data():
    """Test TOC item validation"""
    # Valid TOC item
    toc_item = {
        "title": "Chapter 1",
        "description": "Introduction",
        "level": 1,
        "order": 1
    }
    result = validate_toc_item_data(toc_item)
    assert result["title"] == "Chapter 1"
    assert result["level"] == 1
    
    # With subchapters
    toc_with_sub = {
        "title": "Part 1",
        "description": "First part",
        "level": 1,
        "order": 1,
        "subchapters": [
            {
                "title": "Chapter 1.1",
                "description": "Sub chapter",
                "level": 2,
                "order": 1
            }
        ]
    }
    result = validate_toc_item_data(toc_with_sub)
    assert len(result["subchapters"]) == 1
    
    # Invalid level
    with pytest.raises(ValidationError):
        validate_toc_item_data({
            "title": "Chapter",
            "description": "Desc",
            "level": 7,  # Max is 6
            "order": 1
        })


def test_sanitize_book_title():
    """Test book title sanitization"""
    # Normal title
    assert sanitize_book_title("My Awesome Book") == "My Awesome Book"
    
    # HTML tags
    assert sanitize_book_title("Book <script>alert('xss')</script>") == "Book alert('xss')"
    assert sanitize_book_title("<h1>Title</h1>") == "Title"
    
    # Excess whitespace
    assert sanitize_book_title("Book   With    Spaces") == "Book With Spaces"
    assert sanitize_book_title("  Trimmed  ") == "Trimmed"
    
    # Long title
    long_title = "A" * 250
    result = sanitize_book_title(long_title)
    assert len(result) == 200
    assert result.endswith("...")


def test_validate_book_relationship():
    """Test book relationship validation"""
    # Owner has relationship
    assert validate_book_relationship("user123", "user123") is True
    
    # Non-owner doesn't have relationship
    assert validate_book_relationship("user456", "user123") is False
    
    # Empty IDs
    assert validate_book_relationship("", "") is True
    assert validate_book_relationship("user", "") is False


def test_validate_text_safety():
    """Test text safety validation"""
    # Safe text
    assert validate_text_safety("This is a nice book about programming") is True
    assert validate_text_safety("The class implements a new feature") is True
    assert validate_text_safety("") is True
    assert validate_text_safety(None) is True
    
    # Create a temporary offensive words file for testing
    import json
    import os
    import tempfile
    
    offensive_words = ["badword", "offensive", "inappropriate"]
    
    # Temporarily replace the offensive words file
    original_file = os.path.join(os.path.dirname(__file__), '../../app/utils/offensive_words.json')
    
    # Save original content if file exists
    original_content = None
    if os.path.exists(original_file):
        with open(original_file, 'r') as f:
            original_content = f.read()
    
    try:
        # Write test offensive words
        os.makedirs(os.path.dirname(original_file), exist_ok=True)
        with open(original_file, 'w') as f:
            json.dump(offensive_words, f)
        
        # Test with offensive words
        assert validate_text_safety("This contains badword in it") is False
        assert validate_text_safety("Something offensive here") is False
        assert validate_text_safety("Totally inappropriate content") is False
        
        # Test word boundaries (should not match partial words)
        assert validate_text_safety("This is inoffensive") is True  # "offensive" is part of "inoffensive"
        
    finally:
        # Restore original file or remove test file
        if original_content:
            with open(original_file, 'w') as f:
                f.write(original_content)
        elif os.path.exists(original_file):
            os.remove(original_file)