"""Tell Sentry about a failure the code handles and carries on from (#996).

No log line reaches Sentry (#808), and the SDK reports only what is raised: an
unhandled exception, or a 5xx that a route raises. A failure that is logged and
carried on from has to be reported by hand, and every such report goes through
this one function, so the limit on how often lives here and not in each caller.
"""

import logging
import time

import sentry_sdk

logger = logging.getLogger(__name__)

REPORT_AGAIN_SECONDS = 300
# When each kind of failure was last sent.
_last_reported: dict[str, float] = {}


def report_failure(
    kind: str,
    error: BaseException | None = None,
    message: str | None = None,
    *,
    every_time: bool = False,
    group: str = "handled",
) -> None:
    """Send one report for ``kind``, and no more of that kind for five minutes.

    Most of these come from a loop, a retry or a route anyone can call, so one
    report per kind every few minutes is enough to be told. ``every_time`` is
    for a failure only a trusted sender can cause and where each one names a
    different thing to act on. Give the error when there is one; otherwise a
    message with nothing from the request or the user in it.
    """
    now = time.monotonic()
    if not every_time and now - _last_reported.get(kind, -REPORT_AGAIN_SECONDS) < REPORT_AGAIN_SECONDS:
        return
    try:
        if error is not None:
            sentry_sdk.capture_exception(error, fingerprint=[group, kind])
        else:
            sentry_sdk.capture_message(message or kind, level="error", fingerprint=[group, kind])
    except Exception:
        # Reporting a failure must never become one for the code that asked.
        logger.warning("Could not report %s to Sentry", kind, exc_info=True)
    else:
        # Only once it has gone: a report that could not be sent must not
        # silence the next one.
        _last_reported[kind] = now
