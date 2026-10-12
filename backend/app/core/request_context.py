"""The id of the request being handled, for everything that leaves a trace of it (#810).

The request middleware mints it. A log line, an error body, an audit record and
a Sentry report then all name the same request, and it is the "Reference ID"
the user is shown.
"""

import logging
from contextvars import ContextVar

NO_REQUEST = "-"
request_id_var: ContextVar[str] = ContextVar("request_id", default=NO_REQUEST)

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] %(message)s"


class RequestIdFilter(logging.Filter):
    """Stamps every log record with the request it was written for."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def configure_logging() -> None:
    """Put the request id on every line the root handler prints.

    Sets the format on the handler rather than through basicConfig: whichever
    module calls basicConfig first wins, and the format main.py asked for had
    never been applied.
    """
    logging.basicConfig(level=logging.INFO)
    for handler in logging.getLogger().handlers:
        if type(handler) is logging.StreamHandler:  # ours, not a test runner's capture
            handler.setFormatter(logging.Formatter(LOG_FORMAT))
            handler.addFilter(RequestIdFilter())
