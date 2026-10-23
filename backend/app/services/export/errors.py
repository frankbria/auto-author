"""The errors an export raises, for the service, the builders and the routes (#988)."""


class ExportUnavailableError(RuntimeError):
    """Raised when an export format's required library is not installed."""


class ExportValidationError(ValueError):
    """Raised when a book has no exportable content (clear, user-facing message)."""


class ExportTimeoutError(TimeoutError):
    """Raised when export generation exceeds the configured time budget."""
