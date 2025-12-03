"""
Request tracking middleware for monitoring and observability.

Tracks all HTTP requests with unique request IDs, logs request/response details,
and collects metrics for monitoring dashboards.
"""

import logging
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.core.logging import get_context_filter
from app.api.metrics import get_metrics_store

logger = logging.getLogger(__name__)


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tracking HTTP requests.

    Features:
    - Assigns unique request ID to each request
    - Logs request start/end with duration
    - Tracks slow requests (>1s warning, >3s error)
    - Tracks 4xx and 5xx errors
    - Collects metrics for monitoring
    - Adds request context to all log records
    """

    def __init__(self, app: ASGIApp, slow_request_threshold_ms: float = 1000):
        super().__init__(app)
        self.slow_request_threshold_ms = slow_request_threshold_ms
        self.very_slow_request_threshold_ms = 3000
        self.metrics_store = get_metrics_store()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request with tracking and metrics."""
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Extract user ID if available (from auth)
        user_id = None
        if hasattr(request.state, "user") and request.state.user:
            user_id = request.state.user.get("user_id")

        # Set logging context
        context_filter = get_context_filter()
        context_filter.set_context(
            request_id=request_id,
            user_id=user_id,
            endpoint=request.url.path,
            method=request.method,
        )

        # Log request start
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "endpoint": request.url.path,
                "method": request.method,
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
        )

        # Record start time
        start_time = time.time()

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            # Record metrics
            self.metrics_store.record_request(
                endpoint=request.url.path,
                duration_ms=duration_ms,
                status_code=response.status_code,
            )

            # Log request end
            log_level = self._get_log_level(response.status_code, duration_ms)
            log_message = (
                f"Request completed: {request.method} {request.url.path} - "
                f"Status: {response.status_code}, Duration: {duration_ms:.2f}ms"
            )

            logger.log(
                log_level,
                log_message,
                extra={
                    "request_id": request_id,
                    "user_id": user_id,
                    "endpoint": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )

            # Log slow requests
            if duration_ms > self.very_slow_request_threshold_ms:
                logger.error(
                    f"Very slow request detected: {request.method} {request.url.path} "
                    f"took {duration_ms:.2f}ms (>{self.very_slow_request_threshold_ms}ms)",
                    extra={
                        "request_id": request_id,
                        "user_id": user_id,
                        "endpoint": request.url.path,
                        "method": request.method,
                        "duration_ms": round(duration_ms, 2),
                        "threshold_ms": self.very_slow_request_threshold_ms,
                    },
                )
            elif duration_ms > self.slow_request_threshold_ms:
                logger.warning(
                    f"Slow request detected: {request.method} {request.url.path} "
                    f"took {duration_ms:.2f}ms (>{self.slow_request_threshold_ms}ms)",
                    extra={
                        "request_id": request_id,
                        "user_id": user_id,
                        "endpoint": request.url.path,
                        "method": request.method,
                        "duration_ms": round(duration_ms, 2),
                        "threshold_ms": self.slow_request_threshold_ms,
                    },
                )

            return response

        except Exception as e:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Record error metrics
            self.metrics_store.record_request(
                endpoint=request.url.path,
                duration_ms=duration_ms,
                status_code=500,
            )

            # Log error
            logger.error(
                f"Request failed: {request.method} {request.url.path} - "
                f"Error: {str(e)}, Duration: {duration_ms:.2f}ms",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "user_id": user_id,
                    "endpoint": request.url.path,
                    "method": request.method,
                    "duration_ms": round(duration_ms, 2),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )

            # Re-raise the exception
            raise

        finally:
            # Clear logging context
            context_filter.clear_context()

    def _get_log_level(self, status_code: int, duration_ms: float) -> int:
        """Determine the appropriate log level based on status code and duration."""
        # Errors
        if status_code >= 500:
            return logging.ERROR
        if status_code >= 400:
            return logging.WARNING

        # Slow requests
        if duration_ms > self.very_slow_request_threshold_ms:
            return logging.WARNING
        if duration_ms > self.slow_request_threshold_ms:
            return logging.INFO

        # Success
        return logging.INFO


def add_request_tracking_middleware(app: ASGIApp) -> None:
    """
    Add request tracking middleware to the application.

    Args:
        app: FastAPI application instance
    """
    app.add_middleware(
        RequestTrackingMiddleware,
        slow_request_threshold_ms=1000,  # 1 second
    )
    logger.info("Request tracking middleware added")
