"""
Books API module - modular organization of book-related endpoints.

This module aggregates routers from sub-modules for better code organization.
All endpoints maintain backward compatibility with the original monolithic structure.

Structure:
- books_crud: Basic CRUD operations (create, read, update, delete, cover upload, summary)
- books_toc: Table of Contents generation and management
- books_chapters: Chapter operations (CRUD, metadata, tab state, content, analytics)
- books_questions: Question generation for chapters
- books_drafts: Draft generation for chapters
"""

from fastapi import APIRouter
from . import books_crud, books_toc, books_chapters, books_questions, books_drafts

# Create main router for all book endpoints
router = APIRouter()

# Include all sub-routers
# All routes are added with empty prefix since they already have the full path
router.include_router(books_crud.router, tags=["books-crud"])
router.include_router(books_toc.router, tags=["books-toc"])
router.include_router(books_chapters.router, tags=["books-chapters"])
router.include_router(books_questions.router, tags=["books-questions"])
router.include_router(books_drafts.router, tags=["books-drafts"])

# Export the main router
__all__ = ["router"]
