"""
Tests for database query monitoring.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from app.db.monitoring import (
    track_query,
    query_tracker,
    QueryMonitor,
    track_read_query,
    track_write_query,
    track_aggregation_query,
)


@pytest.mark.asyncio
async def test_track_query_decorator_success():
    """Test track_query decorator with successful query."""
    @track_query("test_operation", slow_query_threshold_ms=100)
    async def test_function():
        await asyncio.sleep(0.05)  # 50ms
        return "success"

    result = await test_function()

    assert result == "success"


@pytest.mark.asyncio
async def test_track_query_decorator_slow_query():
    """Test track_query decorator logs slow queries."""
    with patch("app.db.monitoring.logger") as mock_logger:
        @track_query("slow_operation", slow_query_threshold_ms=50)
        async def slow_function():
            await asyncio.sleep(0.1)  # 100ms (over 50ms threshold)
            return "done"

        result = await slow_function()

        assert result == "done"
        # Should log warning for slow query
        assert any(
            call[0][0].startswith("Slow query detected")
            for call in mock_logger.warning.call_args_list
        )


@pytest.mark.asyncio
async def test_track_query_decorator_error():
    """Test track_query decorator with query failure."""
    with patch("app.db.monitoring.logger") as mock_logger:
        @track_query("failing_operation")
        async def failing_function():
            raise ValueError("Database error")

        with pytest.raises(ValueError, match="Database error"):
            await failing_function()

        # Should log error
        assert any(
            call[0][0].startswith("Query failed")
            for call in mock_logger.error.call_args_list
        )


@pytest.mark.asyncio
async def test_track_query_records_metrics():
    """Test track_query records metrics."""
    from app.api.metrics import get_metrics_store

    metrics_store = get_metrics_store()
    initial_count = metrics_store.db_query_count

    @track_query("metrics_test")
    async def test_function():
        return "done"

    await test_function()

    # Should have recorded one query
    assert metrics_store.db_query_count == initial_count + 1


@pytest.mark.asyncio
async def test_query_tracker_context_manager_success():
    """Test query_tracker context manager with successful operation."""
    async with query_tracker("context_test", user_id="test-user"):
        await asyncio.sleep(0.01)
        result = "success"

    assert result == "success"


@pytest.mark.asyncio
async def test_query_tracker_context_manager_slow():
    """Test query_tracker context manager logs slow queries."""
    with patch("app.db.monitoring.logger") as mock_logger:
        async with query_tracker("slow_context", slow_query_threshold_ms=50):
            await asyncio.sleep(0.1)  # 100ms (over 50ms threshold)

        # Should log warning for slow query
        assert any(
            call[0][0].startswith("Slow query detected")
            for call in mock_logger.warning.call_args_list
        )


@pytest.mark.asyncio
async def test_query_tracker_context_manager_error():
    """Test query_tracker context manager with error."""
    with patch("app.db.monitoring.logger") as mock_logger:
        with pytest.raises(RuntimeError, match="Test error"):
            async with query_tracker("error_context"):
                raise RuntimeError("Test error")

        # Should log error
        assert any(
            call[0][0].startswith("Query failed")
            for call in mock_logger.error.call_args_list
        )


@pytest.mark.asyncio
async def test_query_tracker_with_context():
    """Test query_tracker includes custom context in logs."""
    with patch("app.db.monitoring.logger") as mock_logger:
        async with query_tracker(
            "context_test",
            user_id="user-123",
            collection="books",
        ):
            await asyncio.sleep(0.01)

        # Should include context in log
        debug_calls = [call for call in mock_logger.debug.call_args_list]
        assert len(debug_calls) > 0
        # Check extra context was passed
        assert any(
            "user_id" in call[1].get("extra", {})
            for call in debug_calls
        )


def test_query_monitor_manual_tracking():
    """Test QueryMonitor for manual tracking."""
    monitor = QueryMonitor("manual_test", user_id="test-user")

    monitor.start()
    import time
    time.sleep(0.05)  # 50ms
    duration = monitor.stop(success=True)

    assert duration >= 50.0
    assert duration < 100.0


def test_query_monitor_failure():
    """Test QueryMonitor tracks failures."""
    with patch("app.db.monitoring.logger") as mock_logger:
        monitor = QueryMonitor("failing_test")

        monitor.start()
        import time
        time.sleep(0.01)
        error = ValueError("Test error")
        duration = monitor.stop(success=False, error=error)

        assert duration >= 10.0

        # Should log error
        assert any(
            call[0][0].startswith("Query failed")
            for call in mock_logger.error.call_args_list
        )


def test_query_monitor_slow_query():
    """Test QueryMonitor detects slow queries."""
    with patch("app.db.monitoring.logger") as mock_logger:
        monitor = QueryMonitor("slow_test", slow_query_threshold_ms=50)

        monitor.start()
        import time
        time.sleep(0.1)  # 100ms (over 50ms threshold)
        monitor.stop(success=True)

        # Should log warning for slow query
        assert any(
            call[0][0].startswith("Slow query detected")
            for call in mock_logger.warning.call_args_list
        )


def test_query_monitor_stop_without_start():
    """Test QueryMonitor.stop() without start()."""
    with patch("app.db.monitoring.logger") as mock_logger:
        monitor = QueryMonitor("test")
        duration = monitor.stop()

        assert duration == 0.0

        # Should log warning
        assert any(
            "stop() called without start()" in str(call)
            for call in mock_logger.warning.call_args_list
        )


def test_query_monitor_records_metrics():
    """Test QueryMonitor records metrics."""
    from app.api.metrics import get_metrics_store

    metrics_store = get_metrics_store()
    initial_count = metrics_store.db_query_count

    monitor = QueryMonitor("metrics_test")
    monitor.start()
    import time
    time.sleep(0.01)
    monitor.stop(success=True)

    # Should have recorded one query
    assert metrics_store.db_query_count == initial_count + 1


@pytest.mark.asyncio
async def test_track_read_query_threshold():
    """Test track_read_query has 500ms threshold."""
    with patch("app.db.monitoring.logger") as mock_logger:
        @track_read_query("read_test")
        async def read_function():
            await asyncio.sleep(0.6)  # 600ms (over 500ms threshold)
            return "done"

        await read_function()

        # Should log warning for slow read query
        assert any(
            call[0][0].startswith("Slow query detected")
            for call in mock_logger.warning.call_args_list
        )


@pytest.mark.asyncio
async def test_track_write_query_threshold():
    """Test track_write_query has 1000ms threshold."""
    with patch("app.db.monitoring.logger") as mock_logger:
        @track_write_query("write_test")
        async def write_function():
            await asyncio.sleep(0.8)  # 800ms (under 1000ms threshold)
            return "done"

        await write_function()

        # Should NOT log warning (under threshold)
        assert not any(
            call[0][0].startswith("Slow query detected")
            for call in mock_logger.warning.call_args_list
        )


@pytest.mark.asyncio
async def test_track_aggregation_query_threshold():
    """Test track_aggregation_query has 2000ms threshold."""
    with patch("app.db.monitoring.logger") as mock_logger:
        @track_aggregation_query("aggregation_test")
        async def aggregation_function():
            await asyncio.sleep(1.5)  # 1500ms (under 2000ms threshold)
            return "done"

        await aggregation_function()

        # Should NOT log warning (under threshold)
        assert not any(
            call[0][0].startswith("Slow query detected")
            for call in mock_logger.warning.call_args_list
        )


@pytest.mark.asyncio
async def test_multiple_concurrent_queries():
    """Test tracking multiple concurrent queries."""
    from app.api.metrics import get_metrics_store

    metrics_store = get_metrics_store()
    initial_count = metrics_store.db_query_count

    @track_query("concurrent_test")
    async def concurrent_function(duration: float):
        await asyncio.sleep(duration)
        return "done"

    # Run multiple queries concurrently
    results = await asyncio.gather(
        concurrent_function(0.01),
        concurrent_function(0.02),
        concurrent_function(0.03),
    )

    assert all(r == "done" for r in results)

    # Should have recorded all queries
    assert metrics_store.db_query_count >= initial_count + 3


@pytest.mark.asyncio
async def test_query_tracking_preserves_return_value():
    """Test that query tracking preserves function return values."""
    @track_query("return_value_test")
    async def function_with_return():
        return {"id": "123", "name": "Test"}

    result = await function_with_return()

    assert result == {"id": "123", "name": "Test"}


@pytest.mark.asyncio
async def test_query_tracking_preserves_function_metadata():
    """Test that query tracking preserves function metadata."""
    @track_query("metadata_test")
    async def documented_function():
        """This is a documented function."""
        return "done"

    assert documented_function.__name__ == "documented_function"
    assert documented_function.__doc__ == "This is a documented function."


@pytest.mark.asyncio
async def test_query_tracker_nested():
    """Test nested query tracker contexts."""
    with patch("app.db.monitoring.logger") as mock_logger:
        async with query_tracker("outer_operation"):
            await asyncio.sleep(0.01)

            async with query_tracker("inner_operation"):
                await asyncio.sleep(0.01)

        # Should have logged both operations
        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        assert any("outer_operation" in call for call in debug_calls)
        assert any("inner_operation" in call for call in debug_calls)
