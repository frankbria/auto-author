"""
Middleware package for Auto-Author API.

This package contains custom middleware for session management and other concerns.
"""

from .session_middleware import add_session_middleware

__all__ = ['add_session_middleware']
