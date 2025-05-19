from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import uuid
from typing import Callable
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request validation, logging, and security

    This middleware:
    1. Adds a unique ID to each request
    2. Logs request information
    3. Measures request processing time
    4. Adds security headers to responses
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Log request info
        client_host = request.client.host if request.client else "unknown"
        logger.info(
            f"Request started: {request.method} {request.url.path} "
            f"from {client_host} [ID: {request_id}]"
        )

        # Measure request processing time
        start_time = time.time()

        try:
            # Process the request
            response = await call_next(request)

            # Add security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["X-Request-ID"] = request_id

            # Set Content Security Policy
            # This is a basic policy - customize as needed
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' https://clerk.your-domain.com; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https://img.clerk.com; "
                "connect-src 'self' https://clerk.your-domain.com; "
                "frame-src 'self' https://clerk.your-domain.com; "
                "font-src 'self';"
            )

            # Calculate and log request duration
            process_time = (time.time() - start_time) * 1000
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"[ID: {request_id}] - Status: {response.status_code}, "
                f"Took: {process_time:.2f}ms"
            )

            return response

        except Exception as e:
            # Log exceptions
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"[ID: {request_id}] - Error: {str(e)}, "
                f"Took: {process_time:.2f}ms"
            )
            raise
