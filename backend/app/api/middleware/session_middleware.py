"""
Session tracking middleware
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable
import logging

from app.services.session_service import (
    create_user_session,
    validate_session,
    get_active_session_by_user,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class SessionMiddleware(BaseHTTPMiddleware):
    """Middleware to track user sessions"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track session

        Args:
            request: FastAPI request
            call_next: Next middleware/endpoint

        Returns:
            Response
        """
        # Skip session tracking for certain paths
        skip_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/api/v1/webhooks",  # Webhooks
            "/api/auth",         # Better-auth API routes
        ]

        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)

        # Skip if auth is bypassed (E2E testing)
        if settings.BYPASS_AUTH:
            return await call_next(request)

        # Try to get session ID from cookie or header
        session_id = request.cookies.get("session_id") or request.headers.get("X-Session-ID")

        # Try to get user ID from state (set by auth middleware)
        user_id = None
        if hasattr(request.state, "user"):
            # Better-auth uses auth_id, support clerk_id for migration period
            user_id = (
                request.state.user.get("auth_id")
                or request.state.user.get("clerk_id")
                or request.state.user.get("id")
            )

        session = None

        if session_id:
            # Validate existing session
            try:
                session = await validate_session(session_id, request)
                if session:
                    # Attach session to request state
                    request.state.session = session

                    # Log suspicious activity
                    if session.is_suspicious:
                        logger.warning(
                            f"Suspicious session activity detected: {session_id} "
                            f"for user {session.user_id}"
                        )
            except Exception as e:
                logger.error(f"Error validating session {session_id}: {e}")

        elif user_id:
            # No session ID but user is authenticated - check for existing active session
            try:
                session = await get_active_session_by_user(user_id)
                if not session:
                    # Create new session
                    # Better-auth session ID may be in headers (similar to Clerk)
                    auth_session_id = request.headers.get("X-Auth-Session-ID") or request.headers.get("X-Clerk-Session-ID")
                    session = await create_user_session(user_id, request, auth_session_id)
                    logger.info(f"Created new session {session.session_id} for user {user_id}")

                # Attach session to request state
                if session:
                    request.state.session = session
            except Exception as e:
                logger.error(f"Error creating/retrieving session for user {user_id}: {e}")

        # Process request
        response = await call_next(request)

        # Add session ID to response cookies if we have a session
        if session and session.is_active:
            response.set_cookie(
                key="session_id",
                value=session.session_id,
                httponly=True,
                secure=True,  # HTTPS only in production
                samesite="lax",
                max_age=43200,  # 12 hours
            )

            # Also add as header for client-side access if needed
            response.headers["X-Session-ID"] = session.session_id

        return response


def add_session_middleware(app):
    """Add session middleware to FastAPI app

    Args:
        app: FastAPI application instance
    """
    app.add_middleware(SessionMiddleware)
