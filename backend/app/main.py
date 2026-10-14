from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from pymongo.errors import PyMongoError
from contextlib import asynccontextmanager
from app.api.endpoints.router import router as api_router
from app.core.config import settings, is_deployed_env, is_production_env
import asyncio
import logging
import os
from pathlib import Path
from app.api.request_validation import RequestValidationMiddleware
from app.core.better_auth_session import SESSION_LOOKUP_TIMEOUT_SECONDS, SessionStoreUnavailable
from app.core.reporting import report_failure
from app.core.request_context import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


# Field names that hold what a user wrote or who they are (#808). Frame locals,
# request bodies and log lines are off, so these cover what is attached by key:
# breadcrumb data, contexts, extras.
_USER_TEXT_KEYS = [
    "content", "text", "title", "subtitle", "description", "question", "question_text",
    "answer", "response_text", "feedback", "bio", "prompt", "transcript",
    "email", "first_name", "last_name", "display_name",
    # Not user text: the header a Stripe delivery is authenticated by (#812).
    "stripe-signature",
]  # fmt: skip


def _scrub_free_text(event, hint):
    """Take out what a key-based scrubber cannot see (#808).

    The query string is one string, the referer is the address of the page the
    user was on, and MongoDB's duplicate-key error quotes the colliding value
    (an email address, for the users index) in its message.
    """
    request = event.get("request", {})
    request.pop("query_string", None)
    request.get("headers", {}).pop("referer", None)
    for failure in event.get("exception", {}).get("values", []):
        if failure.get("value"):
            # The driver also ends a write error with the server's whole answer,
            # which for a schema rule holds the value that failed (#996).
            failure["value"] = failure["value"].split(" dup key:")[0].split(", full error:")[0]
    return event


def _init_sentry() -> None:
    """Initialize Sentry error tracking (issue #334).

    Inert when SENTRY_DSN is unset — no events are sent, so CI/local/tests are
    unaffected. When set (staging/prod), an unhandled 500 reaches Sentry once,
    from the global exception handler below. The request middleware answers the
    failure by calling that handler (#810), so the exception never travels on to
    where the SDK's own Starlette integration would see it.
    """
    if not settings.SENTRY_DSN:
        return
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.scrubber import DEFAULT_DENYLIST, EventScrubber

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=os.getenv("ENVIRONMENT") or os.getenv("NODE_ENV") or "unknown",
        # The commit the image was built from; the container has no git to ask.
        release=settings.GIT_SHA or None,
        # Errors-only by default; enable tracing later via config if needed.
        traces_sample_rate=0.0,
        send_default_pii=False,
        # The SDK's defaults attach every frame's locals and the request body:
        # in this app those are the manuscript (#808).
        include_local_variables=False,
        max_request_body_size="never",
        event_scrubber=EventScrubber(denylist=DEFAULT_DENYLIST + _USER_TEXT_KEYS, recursive=True),
        before_send=_scrub_free_text,
        # No log line reaches Sentry, as a breadcrumb or as an event. A log
        # message is free text no scrubber can read, and lines all over this
        # app log at ERROR, some quoting what the user wrote. An unhandled
        # exception is still reported (see above), and so is a 5xx that a route
        # raises as an HTTPException: the SDK's Starlette integration reports
        # those itself. A failure answered below 500, or logged and carried on
        # from, has to call capture_exception or capture_message to be seen.
        integrations=[LoggingIntegration(level=None, event_level=None)],
    )
    logger.info("Sentry error tracking initialized")


_init_sentry()


def validate_production_security() -> None:
    """Validate critical security settings before application startup.

    This function provides fail-fast behavior for security-critical
    configuration errors that could expose user data.

    Raises:
        RuntimeError: If BYPASS_AUTH is enabled in production environment, or if
            BACKEND_CORS_ORIGINS contains a wildcard in production.
    """
    # CORS must never reflect arbitrary origins (issue #339). Starlette echoes the
    # *requested* origin back in Access-Control-Allow-Origin whenever "*" is in
    # allow_origins AND the request carries a cookie — note the trigger is the
    # cookie, not allow_credentials, so flipping allow_credentials off does not
    # disable the reflection. A wildcard is never correct for this app (every
    # deploy path sets explicit origins), so this is fatal in every environment
    # rather than only in production: staging is internet-reachable too, and the
    # fix is simply to list the origins.
    origins = settings.BACKEND_CORS_ORIGINS
    if isinstance(origins, str):
        origins = [o.strip() for o in origins.split(",")]
    if "*" in origins:
        message = (
            "BACKEND_CORS_ORIGINS contains a wildcard ('*'). Combined with cookie "
            "authentication this reflects arbitrary origins back on credentialed "
            "requests. List explicit origins instead."
        )
        logger.critical(f"FATAL SECURITY ERROR: {message}")
        raise RuntimeError(f"Application startup blocked: {message}")

    # PM2 sets ENVIRONMENT (not NODE_ENV) on the backend, so resolve production
    # from whichever marker the deployment sets (issue #176).
    if is_production_env():
        if settings.BYPASS_AUTH:
            logger.critical(
                "FATAL SECURITY ERROR: BYPASS_AUTH is enabled in production. "
                "Application startup blocked to prevent unauthorized access."
            )
            raise RuntimeError(
                "Application startup blocked: BYPASS_AUTH is enabled in production environment. "
                "This would allow unauthorized access to all user data. "
                "Remove BYPASS_AUTH=true from your production configuration."
            )
        logger.info("Production security validation passed: BYPASS_AUTH is disabled")
        # No local-disk fallback in production (#806): a container's disk is
        # gone at the next deploy, and the image has no writable uploads/.
        if settings.storage_provider == "local":
            message = (
                "no upload storage is configured, so uploads would go to local disk "
                f"in production. {settings.storage_setup_help}"
            )
            logger.critical(f"FATAL CONFIGURATION ERROR: {message}")
            raise RuntimeError(f"Application startup blocked: {message}")
    elif settings.BYPASS_AUTH:
        current_env = os.getenv("ENVIRONMENT") or os.getenv("NODE_ENV") or "unset"
        logger.warning(
            f"BYPASS_AUTH is enabled in {current_env} environment. "
            "Authentication will be bypassed - DO NOT use in production."
        )


# Validate security settings before creating the app
validate_production_security()


# After a failed attempt to reach the database at start-up, which itself takes the
# driver's thirty seconds, how long before the next (#1012).
DATABASE_RETRY_SECONDS = 5


# Lifespan context manager for startup and shutdown tasks
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events (startup and shutdown)."""
    # Startup tasks
    logger.info("Running startup tasks...")

    # Import here to avoid circular dependencies
    from app.db.audit_log import ensure_audit_log_indexes
    from app.db.base import get_database
    from app.db.indexing_strategy import ChapterTabIndexManager
    from app.db.questions import ensure_question_indexes
    from app.db.user import (
        ensure_user_indexes,
        grandfather_unverified_accounts,
        purge_expired_users,
    )
    from app.db.toc_repair import repair_duplicate_chapter_ids

    async def database_answers() -> bool:
        try:
            await get_database().command("ping")
            return True
        except PyMongoError as error:
            logger.error(
                "The database cannot be reached (%s); indexes are waiting for it",
                type(error).__name__,
            )
            report_failure("startup-database", error)
            await asyncio.sleep(DATABASE_RETRY_SECONDS)
            return False

    async def prepare_database_when_it_is_there():
        """The indexes and the one-off account fix-up, beside the server and not
        in front of it (#1012).

        Each step used to be awaited before the first request was taken, and each
        waits the driver's thirty seconds for a database that is not there: a
        backend restarted during an outage answered nothing, its liveness route
        included, for over ten minutes, and whatever had failed was not tried
        again until the next restart. So this waits for the database first, for
        as long as that takes, and then does the work.
        """
        while True:
            if not await database_answers():
                continue
            await prepare_database()
            # Every step logs its own failure and carries on, so with a database
            # that went away under them they have all "finished". Ask again; if
            # it is gone, do them again when it is back. Each is safe to repeat.
            if await database_answers():
                break
        logger.info("Database prepared")

    async def prepare_database():
        # Create indexes for question collections
        await ensure_question_indexes()

        # Create unique indexes guarding against duplicate user records (issue #178)
        await ensure_user_indexes()

        # audit_logs 90-day TTL + actor index, backfill of legacy rows (issue #787)
        await ensure_audit_log_indexes()

        # Book owner_id indexes + chapter_access_logs indexes and 90-day TTL
        # (issue #183). Idempotent; per-index errors are logged, never fatal
        # (queries work unindexed, just slower).
        result = await ChapterTabIndexManager(get_database()).create_all_indexes()
        if not result.get("success"):
            logger.error(f"Startup index creation failed: {result.get('message')}")
            report_failure("startup-indexes", message="Startup index creation failed")

        # Accounts older than the email-verification requirement count as verified
        # (#792). Never fatal.
        try:
            grandfathered = await grandfather_unverified_accounts()
            if grandfathered:
                logger.info("Marked %d existing account(s) as email-verified", grandfathered)
        except Exception as error:
            logger.error("Marking existing accounts as verified failed", exc_info=True)
            report_failure("startup-verify-accounts", error)

        # Books stored before #754 may hold duplicate chapter ids (#885). Never fatal.
        try:
            repaired = await repair_duplicate_chapter_ids()
            if repaired:
                logger.info("Gave duplicate chapter ids fresh ids in %d book(s)", repaired)
        except Exception as error:
            logger.error("Repairing duplicate chapter ids failed", exc_info=True)
            report_failure("startup-duplicate-chapter-ids", error)

    # On the app, so that a test (or anything else) can wait for it.
    app.state.database_prepared = asyncio.create_task(prepare_database_when_it_is_there())

    # Erase deactivated accounts whose 18 months are up (#954): now, then daily,
    # so the purge does not wait for the next deploy.
    async def purge_daily():
        while True:
            try:
                purged = await purge_expired_users()
                if purged:
                    logger.info("Purged %d expired deactivated account(s)", purged)
            except Exception as error:
                # Accounts past their 18 months are still held (#954, #996).
                logger.error("Purge of deactivated accounts failed", exc_info=True)
                report_failure("purge-accounts", error)
            await asyncio.sleep(24 * 60 * 60)

    purge_task = asyncio.create_task(purge_daily())

    logger.info("Startup tasks started")

    # Application runs here
    yield

    purge_task.cancel()
    app.state.database_prepared.cancel()

    # Shutdown tasks
    # Drop any export builds still queued on the dedicated pool (#345).
    # wait=False so shutdown isn't held hostage by an in-flight build — a
    # running thread cannot be cancelled, only waited on.
    from app.services.export_service import export_executor

    export_executor.shutdown(wait=False, cancel_futures=True)
    logger.info("Application shutdown")


# Create FastAPI app with lifespan handler
app = FastAPI(
    title="Auto Author API",
    description="API for the Auto Author application",
    version="0.1.0",
    lifespan=lifespan,
    # No /docs, /redoc or /openapi.json where real users are (#815): without
    # the schema FastAPI serves none of the three.
    openapi_url=None if is_deployed_env() else "/openapi.json",
)

# The last one added is the outermost. CORS has to be outside the request
# middleware, which is where an unhandled failure becomes a response: a 500
# made outside CORS carries no CORS headers and the page cannot read it (#810).
app.add_middleware(RequestValidationMiddleware)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # What a page on the frontend's origin may read on a refusal (#803): when
    # to come back, and which AI allowance ran out. And the request's id, which
    # is the reference the user is shown (#810).
    expose_headers=["Retry-After", "X-AI-Quota-Limit", "X-AI-Quota-Period", "X-Request-ID"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

def mount_local_uploads(target: FastAPI) -> None:
    """Serve ``uploads/`` when, and only when, the upload service writes there.

    Both ask ``settings.storage_provider`` (#806). They used to ask different
    questions, and half a cloud configuration wrote local files nothing served.
    """
    if settings.storage_provider == "local":
        logger.info("Mounting local uploads directory for static file serving")
        # check_dir=False: the first upload creates the directory, after startup.
        target.mount("/uploads", StaticFiles(directory="uploads", check_dir=False), name="uploads")
    elif any(
        path.is_file() and not path.name.startswith(".")  # not the tracked .gitkeep
        for path in Path("uploads").rglob("*")
    ):
        # The provider follows backend/.env since #806, so a checkout that wrote
        # to local disk can find itself on a cloud provider after an upgrade.
        logger.warning(
            "Uploads now go to %s, and uploads/ still holds files from local storage. "
            "Their /uploads/... URLs are no longer served.",
            settings.storage_provider,
        )


mount_local_uploads(app)


# Validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Enhanced validation error handler with more detailed error information"""
    errors = []
    for error in exc.errors():
        error_loc = " -> ".join([str(loc) for loc in error["loc"]])
        error_msg = f"{error_loc}: {error['msg']}"
        errors.append(error_msg)

    error_details = "; ".join(errors)
    # No traceback: the exception's text contains the rejected input, which is
    # the user's writing and, for an oversize request, most of the request.
    # A warning: a refused request is the client's mistake, not an error to
    # report (#808).
    logger.warning(f"Validation error: {error_details}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": "Validation error",
            # Without the input, for the same reason. Encoded, because a custom
            # validator's error carries the exception itself.
            "errors": jsonable_encoder(
                [{k: v for k, v in error.items() if k != "input"} for error in exc.errors()]
            ),
            "error_summary": error_details,
        },
    )


# Pydantic validation error handler
@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    # Which model and which fields, never the values: str(exc) and its traceback
    # quote the rejected input (#808).
    fields = "; ".join(
        f"{'.'.join(map(str, error['loc']))}: {error['type']}"
        for error in exc.errors(include_input=False, include_context=False, include_url=False)
    )
    logger.warning("Pydantic validation error for %s: %s", exc.title, fields)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": "Validation error"},
    )


# A session that could not be checked (#1007). Answered 503 with when to come
# back: a 401 here would end the session in the browser for what is our outage.
# Its own exception with no status on it, so the Sentry SDK does not report
# every such request; the lookup reports it once every few minutes.
@app.exception_handler(SessionStoreUnavailable)
async def session_store_unavailable_handler(request: Request, exc: SessionStoreUnavailable):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "The service is temporarily unavailable. Please try again in a moment."},
        headers={"Retry-After": str(SESSION_LOOKUP_TIMEOUT_SECONDS)},
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    # Route to Sentry (#334). No-op when Sentry isn't initialized (no DSN).
    if settings.SENTRY_DSN:
        import sentry_sdk

        sentry_sdk.capture_exception(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred",
            # What the user can quote and the logs and the error report carry (#810).
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.get("/")
def read_root():
    return JSONResponse(
        content={"message": "Welcome to the Auto Author API!"},
        status_code=status.HTTP_200_OK,
    )
