"""
Structured logging configuration for production observability.

Provides JSON-formatted logging with context, request tracking, and log rotation.
"""

import logging
import sys
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Formats log records as JSON with timestamp, level, message, and context.
    Includes exception information when present.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add context from record if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "endpoint"):
            log_data["endpoint"] = record.endpoint
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add any extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data)


class ContextFilter(logging.Filter):
    """
    Filter that adds context to log records.

    Can be used to add request-specific context (request_id, user_id, etc.)
    to all log records within a request.
    """

    def __init__(self):
        super().__init__()
        self.context: Dict[str, Any] = {}

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to the log record."""
        for key, value in self.context.items():
            setattr(record, key, value)
        return True

    def set_context(self, **kwargs):
        """Set context values."""
        self.context.update(kwargs)

    def clear_context(self):
        """Clear all context values."""
        self.context.clear()


# Global context filter for adding request context
_context_filter = ContextFilter()


def get_context_filter() -> ContextFilter:
    """Get the global context filter."""
    return _context_filter


def setup_logging(
    level: str = "INFO",
    use_json: bool = True,
    enable_file_logging: bool = True,
    log_dir: Optional[str] = None,
) -> None:
    """
    Configure structured logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: Whether to use JSON formatting (True for production)
        enable_file_logging: Whether to enable file logging
        log_dir: Directory for log files (default: ./logs)
    """
    # Convert level string to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatters
    if use_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(_context_filter)
    root_logger.addHandler(console_handler)

    # File handlers (if enabled)
    if enable_file_logging:
        # Create log directory
        log_path = Path(log_dir or "logs")
        log_path.mkdir(exist_ok=True)

        # General application log (daily rotation)
        app_log_file = log_path / "app.log"
        app_handler = TimedRotatingFileHandler(
            app_log_file,
            when="midnight",
            interval=1,
            backupCount=7,  # Keep 7 days of logs
            encoding="utf-8",
        )
        app_handler.setLevel(numeric_level)
        app_handler.setFormatter(formatter)
        app_handler.addFilter(_context_filter)
        root_logger.addHandler(app_handler)

        # Error log (size-based rotation)
        error_log_file = log_path / "error.log"
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        error_handler.addFilter(_context_filter)
        root_logger.addHandler(error_handler)

    # Configure third-party loggers to reduce noise
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)

    # Log configuration
    root_logger.info(
        f"Logging configured: level={level}, json={use_json}, file_logging={enable_file_logging}"
    )


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context: Any
) -> None:
    """
    Log a message with additional context.

    Args:
        logger: Logger instance to use
        level: Logging level (logging.DEBUG, logging.INFO, etc.)
        message: Log message
        **context: Additional context to include in the log record
    """
    # Create a LogRecord with context
    record = logger.makeRecord(
        logger.name,
        level,
        "(unknown file)",
        0,
        message,
        (),
        None,
    )

    # Add context to record
    for key, value in context.items():
        setattr(record, key, value)

    # Handle the record
    logger.handle(record)


# Environment-specific configuration
def configure_production_logging():
    """Configure logging for production environment."""
    setup_logging(
        level="INFO",
        use_json=True,
        enable_file_logging=True,
        log_dir="/var/log/auto-author",  # Production log directory
    )


def configure_development_logging():
    """Configure logging for development environment."""
    setup_logging(
        level="DEBUG",
        use_json=False,  # Human-readable format for development
        enable_file_logging=True,
        log_dir="./logs",
    )


def configure_testing_logging():
    """Configure logging for testing environment."""
    setup_logging(
        level="WARNING",  # Reduce noise in tests
        use_json=False,
        enable_file_logging=False,  # No file logging in tests
    )
