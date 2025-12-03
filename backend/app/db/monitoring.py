"""
Database query monitoring for observability.

Provides decorators and context managers for tracking database operations,
detecting slow queries, and collecting metrics.
"""

import logging
import time
import functools
from typing import Any, Callable, Optional, TypeVar, cast
from contextlib import asynccontextmanager
from app.api.metrics import get_metrics_store

logger = logging.getLogger(__name__)

# Type variable for generic function decoration
F = TypeVar('F', bound=Callable[..., Any])


def track_query(
    operation_name: str,
    slow_query_threshold_ms: float = 500
) -> Callable[[F], F]:
    """
    Decorator to track database query execution time.

    Logs slow queries and records metrics for monitoring.

    Args:
        operation_name: Name of the database operation (for logging)
        slow_query_threshold_ms: Threshold in milliseconds for slow query warning

    Usage:
        @track_query("get_user_by_id", slow_query_threshold_ms=500)
        async def get_user_by_id(user_id: str):
            return await users_collection.find_one({"_id": user_id})
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            metrics_store = get_metrics_store()

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                # Record metrics
                metrics_store.record_db_query(duration_ms)

                # Log slow queries
                if duration_ms > slow_query_threshold_ms:
                    logger.warning(
                        f"Slow query detected: {operation_name} took {duration_ms:.2f}ms "
                        f"(>{slow_query_threshold_ms}ms threshold)",
                        extra={
                            "operation": operation_name,
                            "duration_ms": round(duration_ms, 2),
                            "threshold_ms": slow_query_threshold_ms,
                            "function": func.__name__,
                        },
                    )
                else:
                    logger.debug(
                        f"Query completed: {operation_name} in {duration_ms:.2f}ms",
                        extra={
                            "operation": operation_name,
                            "duration_ms": round(duration_ms, 2),
                            "function": func.__name__,
                        },
                    )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Query failed: {operation_name} failed after {duration_ms:.2f}ms - {str(e)}",
                    exc_info=True,
                    extra={
                        "operation": operation_name,
                        "duration_ms": round(duration_ms, 2),
                        "function": func.__name__,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    },
                )
                raise

        return cast(F, wrapper)

    return decorator


@asynccontextmanager
async def query_tracker(
    operation_name: str,
    slow_query_threshold_ms: float = 500,
    **context: Any
):
    """
    Async context manager to track database query execution time.

    Logs slow queries and records metrics for monitoring.

    Args:
        operation_name: Name of the database operation (for logging)
        slow_query_threshold_ms: Threshold in milliseconds for slow query warning
        **context: Additional context to include in logs

    Usage:
        async with query_tracker("complex_aggregation", collection="books"):
            result = await books_collection.aggregate(pipeline).to_list(length=None)
    """
    start_time = time.time()
    metrics_store = get_metrics_store()

    try:
        yield

        duration_ms = (time.time() - start_time) * 1000

        # Record metrics
        metrics_store.record_db_query(duration_ms)

        # Log slow queries
        if duration_ms > slow_query_threshold_ms:
            logger.warning(
                f"Slow query detected: {operation_name} took {duration_ms:.2f}ms "
                f"(>{slow_query_threshold_ms}ms threshold)",
                extra={
                    "operation": operation_name,
                    "duration_ms": round(duration_ms, 2),
                    "threshold_ms": slow_query_threshold_ms,
                    **context,
                },
            )
        else:
            logger.debug(
                f"Query completed: {operation_name} in {duration_ms:.2f}ms",
                extra={
                    "operation": operation_name,
                    "duration_ms": round(duration_ms, 2),
                    **context,
                },
            )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Query failed: {operation_name} failed after {duration_ms:.2f}ms - {str(e)}",
            exc_info=True,
            extra={
                "operation": operation_name,
                "duration_ms": round(duration_ms, 2),
                "error_type": type(e).__name__,
                "error_message": str(e),
                **context,
            },
        )
        raise


class QueryMonitor:
    """
    Utility class for manual query monitoring.

    Useful when you need more control over when to start/stop tracking.

    Usage:
        monitor = QueryMonitor("complex_operation")
        monitor.start()
        # ... perform database operations ...
        monitor.stop()
    """

    def __init__(
        self,
        operation_name: str,
        slow_query_threshold_ms: float = 500,
        **context: Any
    ):
        self.operation_name = operation_name
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.context = context
        self.start_time: Optional[float] = None
        self.metrics_store = get_metrics_store()

    def start(self) -> None:
        """Start tracking query execution time."""
        self.start_time = time.time()
        logger.debug(
            f"Query started: {self.operation_name}",
            extra={
                "operation": self.operation_name,
                **self.context,
            },
        )

    def stop(self, success: bool = True, error: Optional[Exception] = None) -> float:
        """
        Stop tracking query execution time.

        Args:
            success: Whether the query succeeded
            error: Exception if query failed

        Returns:
            Duration in milliseconds
        """
        if self.start_time is None:
            logger.warning(f"QueryMonitor.stop() called without start() for {self.operation_name}")
            return 0.0

        duration_ms = (time.time() - self.start_time) * 1000

        # Record metrics
        self.metrics_store.record_db_query(duration_ms)

        if success:
            # Log slow queries
            if duration_ms > self.slow_query_threshold_ms:
                logger.warning(
                    f"Slow query detected: {self.operation_name} took {duration_ms:.2f}ms "
                    f"(>{self.slow_query_threshold_ms}ms threshold)",
                    extra={
                        "operation": self.operation_name,
                        "duration_ms": round(duration_ms, 2),
                        "threshold_ms": self.slow_query_threshold_ms,
                        **self.context,
                    },
                )
            else:
                logger.debug(
                    f"Query completed: {self.operation_name} in {duration_ms:.2f}ms",
                    extra={
                        "operation": self.operation_name,
                        "duration_ms": round(duration_ms, 2),
                        **self.context,
                    },
                )
        else:
            logger.error(
                f"Query failed: {self.operation_name} failed after {duration_ms:.2f}ms",
                exc_info=error,
                extra={
                    "operation": self.operation_name,
                    "duration_ms": round(duration_ms, 2),
                    "error_type": type(error).__name__ if error else "Unknown",
                    "error_message": str(error) if error else "Unknown error",
                    **self.context,
                },
            )

        self.start_time = None
        return duration_ms


# Pre-configured decorators for common operations
track_read_query = functools.partial(track_query, slow_query_threshold_ms=500)  # 500ms for reads
track_write_query = functools.partial(track_query, slow_query_threshold_ms=1000)  # 1s for writes
track_aggregation_query = functools.partial(track_query, slow_query_threshold_ms=2000)  # 2s for aggregations
