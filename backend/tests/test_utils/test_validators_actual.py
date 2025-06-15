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
    
    # Missing required field (title)
    with pytest.raises(ValidationError) as exc_info:
        validate_book_create_data({
            "description": "Desc"
            # Missing title (required)
        })
    assert "title" in str(exc_info.value)
    
    # Empty title
    with pytest.raises(ValidationError) as exc_info:
        validate_book_create_data({
            "title": "",  # Empty string fails min_length=1
            "description": "Desc"
        })
    
    # Title too long
    with pytest.raises(ValidationError) as exc_info:
        validate_book_create_data({
            "title": "A" * 101,  # Exceeds max_length=100
            "description": "Desc"
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
    
    # Valid update with just title
    result = validate_book_update_data({"title": "New Title"})
    assert result == {"title": "New Title"}
    
    # Invalid data - empty title
    with pytest.raises(ValidationError):
        validate_book_update_data({
            "title": ""  # Empty string fails min_length=1
        })
    
    # Invalid data - missing required title
    with pytest.raises(ValidationError):
        validate_book_update_data({
            "genre": "Fiction"  # Title is required
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
    
    # With metadata
    toc_with_metadata = {
        "title": "Part 1",
        "description": "First part",
        "level": 1,
        "order": 1,
        "metadata": {"status": "draft", "word_count": 0}
    }
    result = validate_toc_item_data(toc_with_metadata)
    assert result["metadata"]["status"] == "draft"
    
    # Missing required field
    with pytest.raises(ValidationError):
        validate_toc_item_data({
            "title": "Chapter",
            "description": "Desc",
            "level": 1
            # Missing order
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