from typing import Dict, Any
import re
from pydantic import ValidationError
from app.schemas.book import BookCreate, BookUpdate, TocItemCreate, TocItemUpdate


def validate_book_create_data(book_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate book creation data against the BookCreate schema
    
    Args:
        book_data: Dictionary containing book data
        
    Returns:
        Validated book data or raises ValidationError
    """
    try:
        validated = BookCreate(**book_data)
        return validated.dict()
    except ValidationError as e:
        raise e


def validate_book_update_data(book_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate book update data against the BookUpdate schema
    
    Args:
        book_data: Dictionary containing book update data
        
    Returns:
        Validated book data or raises ValidationError
    """
    try:
        validated = BookUpdate(**book_data)
        # Only return fields that are not None
        return {k: v for k, v in validated.dict().items() if v is not None}
    except ValidationError as e:
        raise e


def validate_toc_item_data(toc_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate table of contents item data
    
    Args:
        toc_data: Dictionary containing TOC item data
        
    Returns:
        Validated TOC item data or raises ValidationError
    """
    try:
        validated = TocItemCreate(**toc_data)
        return validated.dict()
    except ValidationError as e:
        raise e


def sanitize_book_title(title: str) -> str:
    """
    Sanitize a book title to prevent injection and ensure it fits standards
    
    Args:
        title: Book title to sanitize
        
    Returns:
        Sanitized book title
    """
    # Remove any HTML/script tags
    sanitized = re.sub(r'<[^>]*>', '', title)
    
    # Trim excess whitespace
    sanitized = ' '.join(sanitized.split())
    
    # Limit length
    if len(sanitized) > 200:
        sanitized = sanitized[:197] + '...'
        
    return sanitized


def validate_book_relationship(user_id: str, book_owner_id: str) -> bool:
    """
    Validate if a user has relationship with a book
    
    Args:
        user_id: ID of the user
        book_owner_id: ID of the book owner
        
    Returns:
        True if the user has relationship with the book, False otherwise
    """
    # Currently just checking ownership
    # In future implementations, this can be expanded to check collaborators
    return user_id == book_owner_id
