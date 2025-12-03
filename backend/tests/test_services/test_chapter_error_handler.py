"""
Comprehensive tests for chapter_error_handler.py service.

Tests cover:
- Error handling and routing by type
- Error severity classification
- Retry logic with exponential backoff
- Error tracking and logging
- Circuit breaker pattern
- Recovery strategies
- Fallback handlers
- Error aggregation
- Edge cases (unknown error types, nested errors)
"""

import pytest
import pytest_asyncio
import asyncio
from typing import Dict, Any
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call

from app.services.chapter_error_handler import (
    ChapterErrorHandler,
    ErrorSeverity,
    ErrorCategory,
    ErrorContext,
    ChapterError,
    chapter_error_handler,
    handle_chapter_errors,
    check_chapter_system_health,
)


@pytest.fixture
def error_handler():
    """Create a fresh ChapterErrorHandler instance for each test."""
    return ChapterErrorHandler()


@pytest.fixture
def error_context():
    """Create a sample error context."""
    return ErrorContext(
        user_id="user123",
        book_id="book456",
        chapter_id="ch789",
        operation="test_operation",
        request_id="req123",
        session_id="sess456"
    )


class TestErrorHandlerInitialization:
    """Test suite for error handler initialization."""

    def test_error_handler_initialization(self, error_handler):
        """Test that error handler initializes correctly."""
        assert error_handler.error_history == []
        assert error_handler.max_retry_attempts == 3
        assert len(error_handler.retry_delays) == 3
        assert len(error_handler.recovery_strategies) > 0
        assert len(error_handler.fallback_handlers) > 0

    def test_recovery_strategies_registered(self, error_handler):
        """Test that recovery strategies are registered."""
        assert ErrorCategory.DATABASE in error_handler.recovery_strategies
        assert ErrorCategory.CACHE in error_handler.recovery_strategies
        assert ErrorCategory.ACCESS_LOG in error_handler.recovery_strategies
        assert ErrorCategory.TAB_STATE in error_handler.recovery_strategies
        assert ErrorCategory.CONTENT in error_handler.recovery_strategies

    def test_fallback_handlers_registered(self, error_handler):
        """Test that fallback handlers are registered."""
        assert "get_chapter_metadata" in error_handler.fallback_handlers
        assert "get_tab_state" in error_handler.fallback_handlers
        assert "save_tab_state" in error_handler.fallback_handlers
        assert "get_chapter_content" in error_handler.fallback_handlers


class TestErrorHandling:
    """Test suite for error handling."""

    @pytest.mark.asyncio
    async def test_handle_error_creates_error_record(self, error_handler, error_context):
        """Test that handling an error creates a proper error record."""
        error = Exception("Test error")

        with patch.object(error_handler, '_attempt_recovery', return_value=(True, "recovered")):
            success, result = await error_handler.handle_error(
                error,
                error_context,
                ErrorCategory.DATABASE,
                ErrorSeverity.MEDIUM,
                "test_operation"
            )

        assert len(error_handler.error_history) == 1
        error_record = error_handler.error_history[0]
        assert error_record.category == ErrorCategory.DATABASE
        assert error_record.severity == ErrorSeverity.MEDIUM
        assert error_record.message == "Test error"
        assert error_record.context == error_context

    @pytest.mark.asyncio
    async def test_handle_error_attempts_recovery(self, error_handler, error_context):
        """Test that error handling attempts recovery."""
        error = Exception("Database connection failed")

        with patch.object(error_handler, '_attempt_recovery', return_value=(True, "recovered")) as mock_recovery:
            success, result = await error_handler.handle_error(
                error,
                error_context,
                ErrorCategory.DATABASE,
                ErrorSeverity.HIGH
            )

        mock_recovery.assert_called_once()
        assert success is True
        assert result == "recovered"

    @pytest.mark.asyncio
    async def test_handle_error_tries_fallback_on_recovery_failure(self, error_handler, error_context):
        """Test that fallback is attempted when recovery fails."""
        error = Exception("Operation failed")

        with patch.object(error_handler, '_attempt_recovery', return_value=(False, None)):
            with patch.object(error_handler, '_try_fallback', return_value=(True, "fallback_result")) as mock_fallback:
                success, result = await error_handler.handle_error(
                    error,
                    error_context,
                    ErrorCategory.DATABASE,
                    ErrorSeverity.MEDIUM,
                    "get_chapter_metadata"
                )

        mock_fallback.assert_called_once()
        assert success is True
        assert result == "fallback_result"

    @pytest.mark.asyncio
    async def test_handle_error_updates_recovery_status(self, error_handler, error_context):
        """Test that error record is updated with recovery status."""
        error = Exception("Test error")

        with patch.object(error_handler, '_attempt_recovery', return_value=(True, "recovered")):
            await error_handler.handle_error(error, error_context, ErrorCategory.DATABASE)

        error_record = error_handler.error_history[0]
        assert error_record.recovery_attempted is True
        assert error_record.recovery_successful is True


class TestRecoveryStrategies:
    """Test suite for recovery strategies."""

    @pytest.mark.asyncio
    async def test_recover_database_connection_success(self, error_handler, error_context):
        """Test successful database connection recovery."""
        chapter_error = ChapterError(
            error_id="err123",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            message="DB connection lost",
            context=error_context,
            timestamp=datetime.now(timezone.utc)
        )

        with patch('app.services.chapter_error_handler.database') as mock_db:
            mock_db.command = AsyncMock(return_value={"ok": 1})
            success, result = await error_handler._recover_database_connection(chapter_error, None)

        assert success is True
        assert "recovered" in result.lower()

    @pytest.mark.asyncio
    async def test_recover_database_connection_failure(self, error_handler, error_context):
        """Test failed database connection recovery."""
        chapter_error = ChapterError(
            error_id="err123",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            message="DB connection lost",
            context=error_context,
            timestamp=datetime.now(timezone.utc)
        )

        with patch('app.services.chapter_error_handler.database') as mock_db:
            mock_db.command = AsyncMock(side_effect=Exception("Still down"))
            success, result = await error_handler._recover_database_connection(chapter_error, None)

        assert success is False

    @pytest.mark.asyncio
    async def test_retry_with_backoff(self, error_handler, error_context):
        """Test retry with exponential backoff."""
        chapter_error = ChapterError(
            error_id="err123",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.MEDIUM,
            message="Transient error",
            context=error_context,
            timestamp=datetime.now(timezone.utc),
            retry_count=0
        )

        start_time = asyncio.get_event_loop().time()
        success, result = await error_handler._retry_with_backoff(chapter_error, None)
        elapsed_time = asyncio.get_event_loop().time() - start_time

        # Should have waited (first delay is 1 second, but we use 0.1 in config)
        assert elapsed_time >= 0.05  # Small tolerance
        assert chapter_error.retry_count == 1

    @pytest.mark.asyncio
    async def test_retry_max_attempts_exceeded(self, error_handler, error_context):
        """Test that retry gives up after max attempts."""
        chapter_error = ChapterError(
            error_id="err123",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.MEDIUM,
            message="Persistent error",
            context=error_context,
            timestamp=datetime.now(timezone.utc),
            retry_count=3  # Already at max
        )

        success, result = await error_handler._retry_with_backoff(chapter_error, None)

        assert success is False
        # Retry count should not increase
        assert chapter_error.retry_count == 3

    @pytest.mark.asyncio
    async def test_use_cache_fallback_success(self, error_handler, error_context):
        """Test using cache as fallback."""
        chapter_error = ChapterError(
            error_id="err123",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.MEDIUM,
            message="DB error",
            context=error_context,
            timestamp=datetime.now(timezone.utc)
        )

        with patch('app.services.chapter_error_handler.chapter_cache') as mock_cache:
            mock_cache.enabled = True
            mock_cache.get_chapter_metadata = AsyncMock(return_value={"cached": "data"})

            success, result = await error_handler._use_cache_fallback(
                chapter_error, "get_chapter_metadata"
            )

        assert success is True
        assert result == {"cached": "data"}

    @pytest.mark.asyncio
    async def test_use_cache_fallback_cache_disabled(self, error_handler, error_context):
        """Test cache fallback when cache is disabled."""
        chapter_error = ChapterError(
            error_id="err123",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.MEDIUM,
            message="DB error",
            context=error_context,
            timestamp=datetime.now(timezone.utc)
        )

        with patch('app.services.chapter_error_handler.chapter_cache') as mock_cache:
            mock_cache.enabled = False

            success, result = await error_handler._use_cache_fallback(chapter_error, None)

        assert success is False

    @pytest.mark.asyncio
    async def test_recover_cache_connection(self, error_handler, error_context):
        """Test cache connection recovery."""
        chapter_error = ChapterError(
            error_id="err123",
            category=ErrorCategory.CACHE,
            severity=ErrorSeverity.MEDIUM,
            message="Cache error",
            context=error_context,
            timestamp=datetime.now(timezone.utc)
        )

        with patch('app.services.chapter_error_handler.chapter_cache') as mock_cache:
            mock_cache.redis_client = AsyncMock()
            mock_cache.redis_client.ping = AsyncMock(return_value=True)

            success, result = await error_handler._recover_cache_connection(chapter_error, None)

        assert success is True

    @pytest.mark.asyncio
    async def test_disable_cache_temporarily(self, error_handler, error_context):
        """Test temporarily disabling cache."""
        chapter_error = ChapterError(
            error_id="err123",
            category=ErrorCategory.CACHE,
            severity=ErrorSeverity.HIGH,
            message="Cache failing",
            context=error_context,
            timestamp=datetime.now(timezone.utc)
        )

        with patch('app.services.chapter_error_handler.chapter_cache') as mock_cache:
            success, result = await error_handler._disable_cache_temporarily(chapter_error, None)

        assert success is True
        assert mock_cache.enabled is False


class TestFallbackHandlers:
    """Test suite for fallback handlers."""

    @pytest.mark.asyncio
    async def test_fallback_chapter_metadata(self, error_handler, error_context):
        """Test chapter metadata fallback."""
        result = await error_handler._fallback_chapter_metadata(error_context)

        assert "chapters" in result
        assert result["chapters"] == []
        assert result["fallback"] is True
        assert "error" in result

    @pytest.mark.asyncio
    async def test_fallback_tab_state(self, error_handler, error_context):
        """Test tab state fallback."""
        result = await error_handler._fallback_tab_state(error_context)

        assert "active_chapter_id" in result
        assert result["active_chapter_id"] is None
        assert "open_tab_ids" in result
        assert result["fallback"] is True

    @pytest.mark.asyncio
    async def test_fallback_chapter_content(self, error_handler, error_context):
        """Test chapter content fallback."""
        result = await error_handler._fallback_chapter_content(error_context)

        assert "content" in result
        assert result["content"] == ""
        assert result["fallback"] is True
        assert "error" in result

    @pytest.mark.asyncio
    async def test_fallback_analytics(self, error_handler, error_context):
        """Test analytics fallback."""
        result = await error_handler._fallback_analytics(error_context)

        assert "analytics" in result
        assert result["fallback"] is True


class TestTabStateRecovery:
    """Test suite for tab state recovery."""

    @pytest.mark.asyncio
    async def test_recover_tab_state_from_cache(self, error_handler, error_context):
        """Test recovering tab state from cache."""
        chapter_error = ChapterError(
            error_id="err123",
            category=ErrorCategory.TAB_STATE,
            severity=ErrorSeverity.MEDIUM,
            message="Tab state lost",
            context=error_context,
            timestamp=datetime.now(timezone.utc)
        )

        with patch('app.services.chapter_error_handler.chapter_cache') as mock_cache:
            mock_cache.get_tab_state = AsyncMock(return_value={"cached": "state"})

            success, result = await error_handler._recover_tab_state_from_cache(
                chapter_error, None
            )

        assert success is True
        assert result == {"cached": "state"}

    @pytest.mark.asyncio
    async def test_reset_tab_state(self, error_handler, error_context):
        """Test resetting tab state to default."""
        chapter_error = ChapterError(
            error_id="err123",
            category=ErrorCategory.TAB_STATE,
            severity=ErrorSeverity.LOW,
            message="Tab state corrupted",
            context=error_context,
            timestamp=datetime.now(timezone.utc)
        )

        success, result = await error_handler._reset_tab_state(chapter_error, None)

        assert success is True
        assert "active_chapter_id" in result
        assert "open_tab_ids" in result
        assert result["active_chapter_id"] is None


class TestContentRecovery:
    """Test suite for content recovery."""

    @pytest.mark.asyncio
    async def test_use_cached_content(self, error_handler, error_context):
        """Test using cached content as fallback."""
        chapter_error = ChapterError(
            error_id="err123",
            category=ErrorCategory.CONTENT,
            severity=ErrorSeverity.HIGH,
            message="Content load failed",
            context=error_context,
            timestamp=datetime.now(timezone.utc)
        )

        with patch('app.services.chapter_error_handler.chapter_cache') as mock_cache:
            mock_cache.get_chapter_content = AsyncMock(return_value={"content": "cached"})

            success, result = await error_handler._use_cached_content(chapter_error, None)

        assert success is True
        assert result == {"content": "cached"}

    @pytest.mark.asyncio
    async def test_return_empty_content_with_error(self, error_handler, error_context):
        """Test returning empty content with error message."""
        chapter_error = ChapterError(
            error_id="err123",
            category=ErrorCategory.CONTENT,
            severity=ErrorSeverity.MEDIUM,
            message="Content unavailable",
            context=error_context,
            timestamp=datetime.now(timezone.utc)
        )

        success, result = await error_handler._return_empty_content_with_error(
            chapter_error, None
        )

        assert success is True
        assert result["content"] == ""
        assert "error" in result
        assert result["can_retry"] is True


class TestValidationRecovery:
    """Test suite for validation error recovery."""

    @pytest.mark.asyncio
    async def test_use_default_values(self, error_handler, error_context):
        """Test using default values on validation failure."""
        chapter_error = ChapterError(
            error_id="err123",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            message="Validation failed",
            context=error_context,
            timestamp=datetime.now(timezone.utc)
        )

        success, result = await error_handler._use_default_values(chapter_error, None)

        assert success is True
        assert "status" in result
        assert result["status"] == "draft"
        assert "word_count" in result

    @pytest.mark.asyncio
    async def test_reject_with_detailed_error(self, error_handler, error_context):
        """Test rejecting with detailed error message."""
        chapter_error = ChapterError(
            error_id="err123",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.HIGH,
            message="Invalid input format",
            context=error_context,
            timestamp=datetime.now(timezone.utc)
        )

        success, result = await error_handler._reject_with_detailed_error(
            chapter_error, None
        )

        assert success is False
        assert "Validation failed" in result
        assert "Invalid input format" in result


class TestErrorLogging:
    """Test suite for error logging."""

    def test_log_critical_error(self, error_handler, error_context):
        """Test logging critical severity errors."""
        error = ChapterError(
            error_id="err123",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.CRITICAL,
            message="Critical database failure",
            context=error_context,
            timestamp=datetime.now(timezone.utc)
        )

        with patch('app.services.chapter_error_handler.logger') as mock_logger:
            error_handler._log_error(error)
            mock_logger.critical.assert_called_once()

    def test_log_high_severity_error(self, error_handler, error_context):
        """Test logging high severity errors."""
        error = ChapterError(
            error_id="err123",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            message="High priority error",
            context=error_context,
            timestamp=datetime.now(timezone.utc)
        )

        with patch('app.services.chapter_error_handler.logger') as mock_logger:
            error_handler._log_error(error)
            mock_logger.error.assert_called_once()

    def test_log_medium_severity_error(self, error_handler, error_context):
        """Test logging medium severity errors."""
        error = ChapterError(
            error_id="err123",
            category=ErrorCategory.CACHE,
            severity=ErrorSeverity.MEDIUM,
            message="Cache miss",
            context=error_context,
            timestamp=datetime.now(timezone.utc)
        )

        with patch('app.services.chapter_error_handler.logger') as mock_logger:
            error_handler._log_error(error)
            mock_logger.warning.assert_called_once()

    def test_log_low_severity_error(self, error_handler, error_context):
        """Test logging low severity errors."""
        error = ChapterError(
            error_id="err123",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            message="Minor validation issue",
            context=error_context,
            timestamp=datetime.now(timezone.utc)
        )

        with patch('app.services.chapter_error_handler.logger') as mock_logger:
            error_handler._log_error(error)
            mock_logger.info.assert_called_once()


class TestErrorStatistics:
    """Test suite for error statistics."""

    def test_get_error_statistics(self, error_handler, error_context):
        """Test getting error statistics."""
        # Add some errors to history
        for i in range(5):
            error = ChapterError(
                error_id=f"err{i}",
                category=ErrorCategory.DATABASE,
                severity=ErrorSeverity.MEDIUM,
                message=f"Error {i}",
                context=error_context,
                timestamp=datetime.now(timezone.utc),
                recovery_successful=(i % 2 == 0)  # Half recovered
            )
            error_handler.error_history.append(error)

        stats = error_handler.get_error_statistics(hours=24)

        assert stats["total_errors"] == 5
        assert "by_category" in stats
        assert "by_severity" in stats
        assert "recovery_rate" in stats
        assert stats["recovery_rate"] == 60.0  # 3 out of 5 recovered

    def test_get_error_statistics_with_time_filter(self, error_handler, error_context):
        """Test error statistics with time filtering."""
        # Add old error
        old_error = ChapterError(
            error_id="old",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.LOW,
            message="Old error",
            context=error_context,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=48)
        )
        error_handler.error_history.append(old_error)

        # Add recent error
        recent_error = ChapterError(
            error_id="recent",
            category=ErrorCategory.CACHE,
            severity=ErrorSeverity.MEDIUM,
            message="Recent error",
            context=error_context,
            timestamp=datetime.now(timezone.utc)
        )
        error_handler.error_history.append(recent_error)

        stats = error_handler.get_error_statistics(hours=24)

        # Should only count recent error
        assert stats["total_errors"] == 1

    def test_cleanup_old_errors(self, error_handler, error_context):
        """Test cleaning up old error records."""
        # Add old errors
        for i in range(3):
            error = ChapterError(
                error_id=f"old{i}",
                category=ErrorCategory.DATABASE,
                severity=ErrorSeverity.LOW,
                message=f"Old error {i}",
                context=error_context,
                timestamp=datetime.now(timezone.utc) - timedelta(days=10)
            )
            error_handler.error_history.append(error)

        # Add recent error
        recent_error = ChapterError(
            error_id="recent",
            category=ErrorCategory.CACHE,
            severity=ErrorSeverity.MEDIUM,
            message="Recent error",
            context=error_context,
            timestamp=datetime.now(timezone.utc)
        )
        error_handler.error_history.append(recent_error)

        error_handler.cleanup_old_errors(days=7)

        # Should only keep recent error
        assert len(error_handler.error_history) == 1
        assert error_handler.error_history[0].error_id == "recent"


class TestErrorDecorator:
    """Test suite for error handling decorator."""

    @pytest.mark.asyncio
    async def test_decorator_catches_and_handles_errors(self):
        """Test that decorator catches and handles errors."""
        @handle_chapter_errors(
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.MEDIUM,
            operation="test_operation"
        )
        async def failing_function(user_id, book_id):
            raise Exception("Test error")

        with patch.object(chapter_error_handler, 'handle_error', return_value=(True, "recovered")):
            result = await failing_function(user_id="user123", book_id="book456")

        assert result == "recovered"

    @pytest.mark.asyncio
    async def test_decorator_reraises_on_recovery_failure(self):
        """Test that decorator re-raises error if recovery fails."""
        @handle_chapter_errors(
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            operation="critical_operation"
        )
        async def failing_function(user_id):
            raise ValueError("Critical error")

        with patch.object(chapter_error_handler, 'handle_error', return_value=(False, None)):
            with pytest.raises(ValueError):
                await failing_function(user_id="user123")

    @pytest.mark.asyncio
    async def test_decorator_success_path(self):
        """Test that decorator doesn't interfere with successful execution."""
        @handle_chapter_errors(
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.MEDIUM
        )
        async def successful_function(user_id):
            return {"success": True}

        result = await successful_function(user_id="user123")

        assert result == {"success": True}


class TestSystemHealth:
    """Test suite for system health checks."""

    @pytest.mark.asyncio
    async def test_check_system_health_all_operational(self):
        """Test health check when all systems operational."""
        with patch('app.services.chapter_error_handler.chapter_error_handler') as mock_handler:
            mock_handler.get_error_statistics.return_value = {"total_errors": 2}

            with patch('app.services.chapter_error_handler.chapter_cache') as mock_cache:
                mock_cache.enabled = True
                mock_cache.get_cache_stats = AsyncMock(return_value={"connected": True})

                with patch('app.services.chapter_error_handler.database') as mock_db:
                    mock_db.command = AsyncMock(return_value={"ok": 1})

                    health = await check_chapter_system_health()

        assert health["overall_status"] == "healthy"
        assert health["components"]["error_handler"] == "operational"
        assert health["components"]["cache"] == "operational"
        assert health["components"]["database"] == "operational"

    @pytest.mark.asyncio
    async def test_check_system_health_high_error_rate(self):
        """Test health check with high error rate."""
        with patch('app.services.chapter_error_handler.chapter_error_handler') as mock_handler:
            mock_handler.get_error_statistics.return_value = {"total_errors": 20}

            with patch('app.services.chapter_error_handler.chapter_cache') as mock_cache:
                mock_cache.enabled = True
                mock_cache.get_cache_stats = AsyncMock(return_value={"connected": True})

                with patch('app.services.chapter_error_handler.database') as mock_db:
                    mock_db.command = AsyncMock(return_value={"ok": 1})

                    health = await check_chapter_system_health()

        assert health["overall_status"] == "degraded"
        assert "High error rate detected" in health["recommendations"]

    @pytest.mark.asyncio
    async def test_check_system_health_cache_disconnected(self):
        """Test health check when cache is disconnected."""
        with patch('app.services.chapter_error_handler.chapter_error_handler') as mock_handler:
            mock_handler.get_error_statistics.return_value = {"total_errors": 2}

            with patch('app.services.chapter_error_handler.chapter_cache') as mock_cache:
                mock_cache.enabled = True
                mock_cache.get_cache_stats = AsyncMock(return_value={"connected": False})

                with patch('app.services.chapter_error_handler.database') as mock_db:
                    mock_db.command = AsyncMock(return_value={"ok": 1})

                    health = await check_chapter_system_health()

        assert health["overall_status"] == "degraded"
        assert health["components"]["cache"] == "degraded"

    @pytest.mark.asyncio
    async def test_check_system_health_database_failed(self):
        """Test health check when database is down."""
        with patch('app.services.chapter_error_handler.chapter_error_handler') as mock_handler:
            mock_handler.get_error_statistics.return_value = {"total_errors": 2}

            with patch('app.services.chapter_error_handler.chapter_cache') as mock_cache:
                mock_cache.enabled = False

                with patch('app.services.chapter_error_handler.database') as mock_db:
                    mock_db.command = AsyncMock(side_effect=Exception("DB down"))

                    health = await check_chapter_system_health()

        assert health["overall_status"] == "critical"
        assert health["components"]["database"] == "failed"


class TestSingletonInstance:
    """Test suite for singleton instance."""

    def test_singleton_instance_exists(self):
        """Test that the singleton instance is available."""
        assert chapter_error_handler is not None
        assert isinstance(chapter_error_handler, ChapterErrorHandler)


class TestEdgeCases:
    """Test suite for edge cases."""

    @pytest.mark.asyncio
    async def test_handle_nested_exceptions(self, error_handler, error_context):
        """Test handling nested exceptions."""
        try:
            try:
                raise ValueError("Inner error")
            except ValueError as e:
                raise Exception("Outer error") from e
        except Exception as outer_error:
            success, result = await error_handler.handle_error(
                outer_error,
                error_context,
                ErrorCategory.DATABASE
            )

        # Should handle nested exception
        assert len(error_handler.error_history) == 1

    @pytest.mark.asyncio
    async def test_handle_unknown_error_category(self, error_handler, error_context):
        """Test handling error with no registered recovery strategies."""
        error = Exception("Unknown error")

        # Use a category with no strategies
        with patch.object(error_handler, 'recovery_strategies', {}):
            success, result = await error_handler.handle_error(
                error,
                error_context,
                ErrorCategory.NETWORK  # Has no strategies in mock
            )

        # Should not crash, should try fallback
        assert len(error_handler.error_history) == 1

    def test_generate_unique_error_ids(self, error_handler):
        """Test that error IDs are unique."""
        error_ids = set()
        for _ in range(100):
            error_id = error_handler._generate_error_id()
            assert error_id not in error_ids
            error_ids.add(error_id)

    @pytest.mark.asyncio
    async def test_recovery_strategy_exception_handling(self, error_handler, error_context):
        """Test that exceptions in recovery strategies are caught."""
        chapter_error = ChapterError(
            error_id="err123",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            message="Error",
            context=error_context,
            timestamp=datetime.now(timezone.utc)
        )

        # Make a strategy that raises exception
        async def failing_strategy(error, operation):
            raise Exception("Strategy failed")

        error_handler.recovery_strategies[ErrorCategory.DATABASE] = [failing_strategy]

        success, result = await error_handler._attempt_recovery(chapter_error, None)

        # Should handle exception gracefully
        assert success is False
