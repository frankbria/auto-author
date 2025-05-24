# backend/app/db/database.py

from .base import (
    users_collection,
    books_collection,
    audit_logs_collection,
    get_collection,
    ObjectId,
)

from datetime import datetime, timezone

__all__ = [
    "users_collection",
    "books_collection",
    "audit_logs_collection",
    "get_collection",
    "ObjectId",
    "datetime",
    "timezone",
]

# Late imports to avoid circular dependencies

from .user import (
    get_user_by_clerk_id,
    get_user_by_id,
    get_user_by_email,
    create_user,
    update_user,
    delete_user,
    delete_user_books,
)

from .book import (
    create_book,
    get_book_by_id,
    get_books_by_user,
    update_book,
    delete_book,
)

from .audit_log import create_audit_log

__all__ += [
    # User DAOs
    "get_user_by_clerk_id",
    "get_user_by_id",
    "get_user_by_email",
    "create_user",
    "update_user",
    "delete_user",
    "delete_user_books",
    # Book DAOs
    "create_book",
    "get_book_by_id",
    "get_books_by_user",
    "update_book",
    "delete_book",
    # Audit log DAOs
    "create_audit_log",
]
