import asyncio

from fastapi import APIRouter, Response, status
from app.api.endpoints import users, account_export, webhooks, books, book_cover, chapters, chapter_questions, chapter_content, chapter_ai, book_summary, book_toc, book_questions, export, billing
from app.core.config import settings, is_production_env
from app.db.base import get_database

# Bound the readiness ping so a broken/unreachable Mongo fails the probe fast
# instead of hanging on the app client's 30s serverSelectionTimeoutMS — the
# deploy gate retries with short sleeps and must get a prompt 503.
HEALTH_PING_TIMEOUT_SECONDS = 5.0

# Main router
router = APIRouter()

# Include sub-routers
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(account_export.router, prefix="/users", tags=["users"])
router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
router.include_router(books.router, prefix="/books", tags=["books"])
router.include_router(book_cover.router, prefix="/books", tags=["book-cover"])
router.include_router(chapters.router, prefix="/books", tags=["chapters"])
router.include_router(chapter_questions.router, prefix="/books", tags=["chapter-questions"])
router.include_router(chapter_content.router, prefix="/books", tags=["chapter-content"])
router.include_router(chapter_ai.router, prefix="/books", tags=["chapter-ai"])
router.include_router(book_summary.router, prefix="/books", tags=["book-summary"])
router.include_router(book_toc.router, prefix="/books", tags=["book-toc"])
router.include_router(book_questions.router, prefix="/books", tags=["book-questions"])
router.include_router(export.router, tags=["export"])
router.include_router(billing.router, prefix="/billing", tags=["billing"])

# Placeholder secret the CI/test config ships with; a production release still
# carrying it means the real secret was never wired in.
_CI_SECRET = "test-secret-for-ci-minimum-32-characters-long-safe-for-testing"


def _misconfigured_secrets() -> list[str]:
    """Names of required secrets that are absent (or still a placeholder).

    Presence is required everywhere; the CI/test placeholders are additionally
    rejected in production, so a release that forgot to wire in a real secret
    fails the health gate while CI (which uses the placeholders) stays green.
    """
    prod = is_production_env()
    bad: list[str] = []
    if not settings.openai_api_key or (prod and settings.openai_api_key == "test-key"):
        bad.append("AI_API_KEY" if settings.AI_BASE_URL else "OPENAI_API_KEY")
    if not settings.BETTER_AUTH_SECRET or (prod and settings.BETTER_AUTH_SECRET == _CI_SECRET):
        bad.append("BETTER_AUTH_SECRET")
    return bad


_STRIPE_SETTINGS = ("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_PRICE_ID_PRO")


def _capabilities() -> dict[str, str]:
    """What this deployment can do besides answer: store uploads, bill, report
    errors (#807). Each is "ok", "disabled" or "missing: NAMES"; names only,
    never values."""
    if settings.storage_provider != "local":
        storage = "ok"
    else:
        storage = "missing: " + (", ".join(settings.storage_fields_missing) or "CLOUDINARY_* or AWS_*")

    unset = [name for name in _STRIPE_SETTINGS if not getattr(settings, name)]
    if not settings.BILLING_ENABLED:
        billing = "disabled"
    else:
        billing = f"missing: {', '.join(unset)}" if unset else "ok"

    return {
        "storage": storage,
        "billing": billing,
        "error_reporting": "ok" if settings.SENTRY_DSN else "missing: SENTRY_DSN",
    }


@router.get("/")
async def read_root():
    return {"message": "Welcome to the Auto Author API!"}


@router.get("/health/live")
async def liveness():
    """Liveness: the process is up and serving. It touches nothing else, so a
    database outage or a missing setting does not get a live container
    restarted; /health is the readiness probe and the deploy gate (#807)."""
    return {"status": "alive"}


@router.get("/health")
async def health_check(response: Response):
    """Readiness probe: verify MongoDB is reachable and required secrets are
    configured, so a misconfigured release (wrong MONGODB_URI, un-allowlisted
    Atlas IP, missing OPENAI_API_KEY/BETTER_AUTH_SECRET) fails the deploy
    `curl -f .../health` gate instead of being promoted while every real
    request 500s (issue #333)."""
    checks: dict[str, str] = {}

    # MongoDB connectivity — catches a wrong URI or an un-allowlisted Atlas IP.
    try:
        await asyncio.wait_for(
            get_database().command("ping"), timeout=HEALTH_PING_TIMEOUT_SECONDS
        )
        checks["mongodb"] = "ok"
    except Exception as e:  # report any failure; the probe must never itself crash
        checks["mongodb"] = f"error: {type(e).__name__}"

    # Required secrets must be configured (presence, not liveness).
    missing = _misconfigured_secrets()
    checks["config"] = "ok" if not missing else f"missing: {', '.join(missing)}"

    # Reported everywhere, fatal in production only (#807): a production box
    # that cannot store uploads, bill or report errors must not pass the deploy
    # gate, and staging shows the same gaps without failing its own.
    capabilities = _capabilities()
    checks.update(capabilities)
    capable = all(state in ("ok", "disabled") for state in capabilities.values())
    # The validated ENVIRONMENT, not is_production_env(): that also reads
    # NODE_ENV, and one left in the box's shared .env would fail a staging
    # deploy for having no Stripe.
    production = settings.ENVIRONMENT == "production"

    healthy = checks["mongodb"] == "ok" and not missing and (capable or not production)
    response.status_code = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "healthy" if healthy else "unhealthy", "checks": checks}
