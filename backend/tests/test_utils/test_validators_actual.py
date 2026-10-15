"""Test actual utility validators"""

from app.utils.validators import (
    validate_text_safety
)


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
