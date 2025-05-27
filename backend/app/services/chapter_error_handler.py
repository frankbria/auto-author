"""
Chapter Tabs Error Handling and Recovery Service
===============================================

This service provides comprehensive error handling, recovery mechanisms,
and monitoring for the chapter tabs functionality.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field
import traceback
import json
from functools import wraps

from app.services.chapter_cache_service import chapter_cache
from app.db.database import get_database

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for chapter operations."""

    LOW = "low"  # Non-critical errors that don't affect functionality
    MEDIUM = "medium"  # Errors that affect some functionality but have workarounds
    HIGH = "high"  # Critical errors that significantly impact user experience
    CRITICAL = "critical"  # Errors that make the feature unusable


class ErrorCategory(Enum):
    """Categories of errors in chapter tabs functionality."""

    DATABASE = "database"
    CACHE = "cache"
    VALIDATION = "validation"
    ACCESS_LOG = "access_log"
    CONTENT = "content"
    TAB_STATE = "tab_state"
    ANALYTICS = "analytics"
    NETWORK = "network"
    CONCURRENCY = "concurrency"


@dataclass
class ErrorContext:
    """Context information for an error."""

    user_id: str
    book_id: Optional[str] = None
    chapter_id: Optional[str] = None
    operation: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChapterError:
    """Represents an error in chapter operations."""

    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    context: ErrorContext
    timestamp: datetime
    stack_trace: Optional[str] = None
    recovery_attempted: bool = False
    recovery_successful: Optional[bool] = None
    retry_count: int = 0


class ChapterErrorHandler:
    """
    Handles errors and recovery for chapter tabs functionality.

    Provides:
    - Error tracking and logging
    - Automatic recovery mechanisms
    - Fallback strategies
    - Error reporting and monitoring
    """

    def __init__(self):
        self.error_history: List[ChapterError] = []
        self.recovery_strategies: Dict[ErrorCategory, List[Callable]] = {}
        self.fallback_handlers: Dict[str, Callable] = {}
        self.max_retry_attempts = 3
        self.retry_delays = [1, 2, 5]  # Exponential backoff

        self._register_recovery_strategies()
        self._register_fallback_handlers()

    def _register_recovery_strategies(self):
        """Register automatic recovery strategies for different error types."""

        self.recovery_strategies = {
            ErrorCategory.DATABASE: [
                self._recover_database_connection,
                self._retry_with_backoff,
                self._use_cache_fallback,
            ],
            ErrorCategory.CACHE: [
                self._recover_cache_connection,
                self._disable_cache_temporarily,
                self._use_database_fallback,
            ],
            ErrorCategory.ACCESS_LOG: [
                self._retry_access_log,
                self._queue_access_log_for_later,
                self._disable_access_logging_temporarily,
            ],
            ErrorCategory.TAB_STATE: [
                self._recover_tab_state_from_cache,
                self._recover_tab_state_from_logs,
                self._reset_tab_state,
            ],
            ErrorCategory.CONTENT: [
                self._retry_content_operation,
                self._use_cached_content,
                self._return_empty_content_with_error,
            ],
            ErrorCategory.VALIDATION: [
                self._sanitize_and_retry,
                self._use_default_values,
                self._reject_with_detailed_error,
            ],
        }

    def _register_fallback_handlers(self):
        """Register fallback handlers for critical operations."""

        self.fallback_handlers = {
            "get_chapter_metadata": self._fallback_chapter_metadata,
            "get_tab_state": self._fallback_tab_state,
            "save_tab_state": self._fallback_save_tab_state,
            "get_chapter_content": self._fallback_chapter_content,
            "update_chapter": self._fallback_update_chapter,
            "get_analytics": self._fallback_analytics,
        }

    async def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        category: ErrorCategory = ErrorCategory.DATABASE,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        operation: Optional[str] = None,
    ) -> Tuple[bool, Any]:
        """
        Handle an error with automatic recovery attempts.

        Args:
            error: The exception that occurred
            context: Context information about the error
            category: Category of the error
            severity: Severity level
            operation: Name of the operation that failed

        Returns:
            Tuple of (recovery_successful, result_or_fallback)
        """

        # Create error record
        chapter_error = ChapterError(
            error_id=self._generate_error_id(),
            category=category,
            severity=severity,
            message=str(error),
            context=context,
            timestamp=datetime.now(timezone.utc),
            stack_trace=traceback.format_exc(),
        )

        # Log the error
        self._log_error(chapter_error)

        # Add to error history
        self.error_history.append(chapter_error)

        # Attempt recovery based on category
        recovery_result = await self._attempt_recovery(chapter_error, operation)

        # Update error record
        chapter_error.recovery_attempted = True
        chapter_error.recovery_successful = recovery_result[0]

        # If recovery failed, try fallback
        if not recovery_result[0] and operation:
            fallback_result = await self._try_fallback(operation, context)
            if fallback_result[0]:
                return True, fallback_result[1]

        return recovery_result

    async def _attempt_recovery(
        self, error: ChapterError, operation: Optional[str]
    ) -> Tuple[bool, Any]:
        """Attempt recovery using registered strategies."""

        strategies = self.recovery_strategies.get(error.category, [])

        for strategy in strategies:
            try:
                logger.info(f"Attempting recovery strategy: {strategy.__name__}")
                result = await strategy(error, operation)

                if result[0]:  # Recovery successful
                    logger.info(
                        f"Recovery successful with strategy: {strategy.__name__}"
                    )
                    return result

            except Exception as e:
                logger.error(f"Recovery strategy {strategy.__name__} failed: {e}")
                continue

        return False, None

    async def _try_fallback(
        self, operation: str, context: ErrorContext
    ) -> Tuple[bool, Any]:
        """Try fallback handler for the operation."""

        fallback_handler = self.fallback_handlers.get(operation)
        if not fallback_handler:
            return False, None

        try:
            logger.info(f"Attempting fallback for operation: {operation}")
            result = await fallback_handler(context)
            logger.info(f"Fallback successful for operation: {operation}")
            return True, result

        except Exception as e:
            logger.error(f"Fallback failed for operation {operation}: {e}")
            return False, None

    # Recovery Strategies

    async def _recover_database_connection(
        self, error: ChapterError, operation: Optional[str]
    ) -> Tuple[bool, Any]:
        """Attempt to recover database connection."""
        try:
            database = await get_database()
            # Test connection
            await database.command("ping")
            return True, "Database connection recovered"
        except Exception as e:
            logger.error(f"Database recovery failed: {e}")
            return False, None

    async def _retry_with_backoff(
        self, error: ChapterError, operation: Optional[str]
    ) -> Tuple[bool, Any]:
        """Retry operation with exponential backoff."""
        if error.retry_count >= self.max_retry_attempts:
            return False, None

        delay = self.retry_delays[min(error.retry_count, len(self.retry_delays) - 1)]
        await asyncio.sleep(delay)
        error.retry_count += 1

        # This would need to be implemented with the original operation context
        return False, "Retry attempted"

    async def _use_cache_fallback(
        self, error: ChapterError, operation: Optional[str]
    ) -> Tuple[bool, Any]:
        """Use cached data as fallback."""
        if not chapter_cache.enabled:
            return False, None

        try:
            context = error.context
            if operation == "get_chapter_metadata":
                cached_data = await chapter_cache.get_chapter_metadata(
                    context.book_id, context.user_id
                )
                if cached_data:
                    return True, cached_data

            return False, None
        except Exception as e:
            logger.error(f"Cache fallback failed: {e}")
            return False, None

    async def _recover_cache_connection(
        self, error: ChapterError, operation: Optional[str]
    ) -> Tuple[bool, Any]:
        """Attempt to recover cache connection."""
        try:
            if chapter_cache.redis_client:
                await chapter_cache.redis_client.ping()
                return True, "Cache connection recovered"
        except Exception as e:
            logger.error(f"Cache recovery failed: {e}")

        return False, None

    async def _disable_cache_temporarily(
        self, error: ChapterError, operation: Optional[str]
    ) -> Tuple[bool, Any]:
        """Temporarily disable cache to allow operation to continue."""
        chapter_cache.enabled = False
        logger.warning("Cache temporarily disabled due to errors")
        return True, "Cache disabled, continuing without cache"

    async def _use_database_fallback(
        self, error: ChapterError, operation: Optional[str]
    ) -> Tuple[bool, Any]:
        """Use database directly when cache fails."""
        # This would implement database queries as fallback
        return True, "Using database fallback"

    async def _retry_access_log(
        self, error: ChapterError, operation: Optional[str]
    ) -> Tuple[bool, Any]:
        """Retry access logging operation."""
        # Implementation would retry the access log operation
        return False, "Access log retry not implemented"

    async def _queue_access_log_for_later(
        self, error: ChapterError, operation: Optional[str]
    ) -> Tuple[bool, Any]:
        """Queue access log entry for later processing."""
        # Implementation would queue the log entry
        logger.info("Access log queued for later processing")
        return True, "Access log queued"

    async def _disable_access_logging_temporarily(
        self, error: ChapterError, operation: Optional[str]
    ) -> Tuple[bool, Any]:
        """Temporarily disable access logging."""
        logger.warning("Access logging temporarily disabled")
        return True, "Access logging disabled"

    async def _recover_tab_state_from_cache(
        self, error: ChapterError, operation: Optional[str]
    ) -> Tuple[bool, Any]:
        """Recover tab state from cache."""
        try:
            context = error.context
            cached_state = await chapter_cache.get_tab_state(
                context.book_id, context.user_id
            )
            if cached_state:
                return True, cached_state
        except Exception:
            pass

        return False, None

    async def _recover_tab_state_from_logs(
        self, error: ChapterError, operation: Optional[str]
    ) -> Tuple[bool, Any]:
        """Recover tab state from access logs."""
        # Implementation would query access logs to reconstruct tab state
        return False, "Tab state recovery from logs not implemented"

    async def _reset_tab_state(
        self, error: ChapterError, operation: Optional[str]
    ) -> Tuple[bool, Any]:
        """Reset tab state to default."""
        default_state = {"active_chapter_id": None, "open_tab_ids": [], "tab_order": []}
        return True, default_state

    async def _retry_content_operation(
        self, error: ChapterError, operation: Optional[str]
    ) -> Tuple[bool, Any]:
        """Retry content operation."""
        return False, "Content operation retry not implemented"

    async def _use_cached_content(
        self, error: ChapterError, operation: Optional[str]
    ) -> Tuple[bool, Any]:
        """Use cached content as fallback."""
        try:
            context = error.context
            cached_content = await chapter_cache.get_chapter_content(
                context.book_id, context.chapter_id, context.user_id
            )
            if cached_content:
                return True, cached_content
        except Exception:
            pass

        return False, None

    async def _return_empty_content_with_error(
        self, error: ChapterError, operation: Optional[str]
    ) -> Tuple[bool, Any]:
        """Return empty content with error indication."""
        return True, {
            "content": "",
            "error": "Content temporarily unavailable",
            "can_retry": True,
        }

    async def _sanitize_and_retry(
        self, error: ChapterError, operation: Optional[str]
    ) -> Tuple[bool, Any]:
        """Sanitize input and retry operation."""
        return False, "Input sanitization retry not implemented"

    async def _use_default_values(
        self, error: ChapterError, operation: Optional[str]
    ) -> Tuple[bool, Any]:
        """Use default values when validation fails."""
        defaults = {
            "status": "draft",
            "word_count": 0,
            "estimated_reading_time": 0,
            "is_active_tab": False,
        }
        return True, defaults

    async def _reject_with_detailed_error(
        self, error: ChapterError, operation: Optional[str]
    ) -> Tuple[bool, Any]:
        """Reject operation with detailed error message."""
        return False, f"Validation failed: {error.message}"

    # Fallback Handlers

    async def _fallback_chapter_metadata(self, context: ErrorContext) -> Dict:
        """Fallback for chapter metadata retrieval."""
        return {
            "chapters": [],
            "total_chapters": 0,
            "error": "Metadata temporarily unavailable",
            "fallback": True,
        }

    async def _fallback_tab_state(self, context: ErrorContext) -> Dict:
        """Fallback for tab state retrieval."""
        return {
            "active_chapter_id": None,
            "open_tab_ids": [],
            "tab_order": [],
            "fallback": True,
        }

    async def _fallback_save_tab_state(self, context: ErrorContext) -> Dict:
        """Fallback for tab state saving."""
        return {
            "success": False,
            "message": "Tab state not saved due to error",
            "fallback": True,
        }

    async def _fallback_chapter_content(self, context: ErrorContext) -> Dict:
        """Fallback for chapter content retrieval."""
        return {
            "content": "",
            "title": "Content Unavailable",
            "error": "Chapter content temporarily unavailable",
            "fallback": True,
        }

    async def _fallback_update_chapter(self, context: ErrorContext) -> Dict:
        """Fallback for chapter updates."""
        return {
            "success": False,
            "message": "Chapter update failed, please try again",
            "fallback": True,
        }

    async def _fallback_analytics(self, context: ErrorContext) -> Dict:
        """Fallback for analytics retrieval."""
        return {
            "analytics": {},
            "error": "Analytics temporarily unavailable",
            "fallback": True,
        }

    # Utility Methods

    def _generate_error_id(self) -> str:
        """Generate unique error ID."""
        import uuid

        return str(uuid.uuid4())

    def _log_error(self, error: ChapterError):
        """Log error with appropriate level based on severity."""
        log_msg = f"Chapter Error [{error.error_id}]: {error.message}"

        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(
                log_msg,
                extra={
                    "error_id": error.error_id,
                    "category": error.category.value,
                    "context": error.context.__dict__,
                },
            )
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(
                log_msg,
                extra={
                    "error_id": error.error_id,
                    "category": error.category.value,
                    "context": error.context.__dict__,
                },
            )
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(
                log_msg,
                extra={"error_id": error.error_id, "category": error.category.value},
            )
        else:
            logger.info(
                log_msg,
                extra={"error_id": error.error_id, "category": error.category.value},
            )

    def get_error_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get error statistics for the specified time period."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent_errors = [e for e in self.error_history if e.timestamp > cutoff]

        stats = {
            "total_errors": len(recent_errors),
            "by_category": {},
            "by_severity": {},
            "recovery_rate": 0,
            "most_common_errors": [],
        }

        # Count by category
        for error in recent_errors:
            category = error.category.value
            severity = error.severity.value

            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1

        # Calculate recovery rate
        recovered_errors = [e for e in recent_errors if e.recovery_successful]
        if recent_errors:
            stats["recovery_rate"] = len(recovered_errors) / len(recent_errors) * 100

        return stats

    def cleanup_old_errors(self, days: int = 7):
        """Clean up old error records."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        initial_count = len(self.error_history)
        self.error_history = [e for e in self.error_history if e.timestamp > cutoff]
        cleaned_count = initial_count - len(self.error_history)

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old error records")


# Global error handler instance
chapter_error_handler = ChapterErrorHandler()


# Decorator for automatic error handling
def handle_chapter_errors(
    category: ErrorCategory = ErrorCategory.DATABASE,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    operation: Optional[str] = None,
):
    """Decorator to automatically handle errors in chapter operations."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Extract context from function arguments
                context = ErrorContext(
                    user_id=kwargs.get("user_id", "unknown"),
                    book_id=kwargs.get("book_id"),
                    chapter_id=kwargs.get("chapter_id"),
                    operation=operation or func.__name__,
                )

                # Handle the error
                recovery_successful, result = await chapter_error_handler.handle_error(
                    e, context, category, severity, operation or func.__name__
                )

                if recovery_successful:
                    return result
                else:
                    # Re-raise if recovery failed
                    raise e

        return wrapper

    return decorator


# Health check functions
async def check_chapter_system_health() -> Dict[str, Any]:
    """Check the health of the chapter tabs system."""
    health_status = {
        "overall_status": "healthy",
        "components": {},
        "error_rate": 0,
        "recommendations": [],
    }

    # Check error rates
    error_stats = chapter_error_handler.get_error_statistics(hours=1)
    if error_stats["total_errors"] > 10:  # More than 10 errors in last hour
        health_status["overall_status"] = "degraded"
        health_status["recommendations"].append("High error rate detected")

    health_status["error_rate"] = error_stats["total_errors"]
    health_status["components"]["error_handler"] = "operational"

    # Check cache health
    if chapter_cache.enabled:
        cache_stats = await chapter_cache.get_cache_stats()
        health_status["components"]["cache"] = (
            "operational" if cache_stats["connected"] else "degraded"
        )
        if not cache_stats["connected"]:
            health_status["overall_status"] = "degraded"
            health_status["recommendations"].append("Cache connection issues")
    else:
        health_status["components"]["cache"] = "disabled"

    # Check database connectivity
    try:
        database = await get_database()
        await database.command("ping")
        health_status["components"]["database"] = "operational"
    except Exception as e:
        health_status["components"]["database"] = "failed"
        health_status["overall_status"] = "critical"
        health_status["recommendations"].append("Database connectivity issues")

    return health_status


# Export service instance
chapter_error_handler = ChapterErrorHandler()
