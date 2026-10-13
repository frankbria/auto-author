from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import uuid
from typing import Callable
import logging

import sentry_sdk

from app.core.config import is_deployed_env
from app.core.request_context import request_id_var

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# jsdelivr, the FastAPI logo and 'unsafe-inline' are what the Swagger page at
# /docs needs; the font host is a leftover nothing loads. A deployed host does
# not serve that page (#815), so it allows none of them.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'"
    if is_deployed_env()
    else (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https://fastapi.tiangolo.com; "
        "connect-src 'self'; "
        "frame-src 'self'; "
        "font-src 'self' data: https://r2cdn.perplexity.ai;"
    )
)


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
        # For every log line, error body and error report made on the way (#810).
        request_id_var.set(request_id)
        sentry_sdk.set_tag("request_id", request_id)

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
        except Exception as e:
            # Log exceptions
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"[ID: {request_id}] - Error: {str(e)}, "
                f"Took: {process_time:.2f}ms"
            )
            # Answered here instead of re-raised (#810). A response made
            # outside this middleware passes no CORS middleware, so a page on
            # the frontend's origin could not read a 500 at all.
            handler = request.app.exception_handlers.get(Exception)
            if handler is None:
                raise
            response = await handler(request, e)
        else:
            # Calculate and log request duration
            process_time = (time.time() - start_time) * 1000
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"[ID: {request_id}] - Status: {response.status_code}, "
                f"Took: {process_time:.2f}ms"
            )

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Same value and reasoning as frontend/next.config.ts (#814). A browser
        # ignores it on an answer that did not arrive over https.
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
        response.headers["X-Request-ID"] = request_id

        response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY

        return response
