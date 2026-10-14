import re
import json
import os


def validate_text_safety(text: str) -> bool:
    """
    Validate text for offensive content

    Args:
        text: Text to validate for safety

    Returns:
        True if text is safe, False if it contains offensive content
    """
    if not text:
        return True

    # Load offensive words list
    offensive_words_path = os.path.join(os.path.dirname(__file__), 'offensive_words.json')

    try:
        with open(offensive_words_path, 'r') as f:
            offensive_words = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # If file not found or invalid JSON, default to allowing the text
        return True

    # Convert text to lowercase for comparison
    text_lower = text.lower()

    # Check if any offensive word is present in the text
    for word in offensive_words:
        # Use word boundaries to avoid false positives (e.g., "class" containing "ass")
        pattern = r'\b' + re.escape(word.lower()) + r'\b'
        if re.search(pattern, text_lower):
            return False

    return True
