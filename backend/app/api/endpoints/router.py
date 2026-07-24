import asyncio

from fastapi import APIRouter, Response, status
from app.api.endpoints import users, webhooks, books, chapters, export, billing
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
router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
router.include_router(books.router, prefix="/books", tags=["books"])
router.include_router(chapters.router, prefix="/books", tags=["chapters"])
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
        bad.append("OPENAI_API_KEY")
    if not settings.BETTER_AUTH_SECRET or (prod and settings.BETTER_AUTH_SECRET == _CI_SECRET):
        bad.append("BETTER_AUTH_SECRET")
    return bad


@router.get("/")
async def read_root():
    return {"message": "Welcome to the Auto Author API!"}


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

    healthy = checks["mongodb"] == "ok" and not missing
    response.status_code = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "healthy" if healthy else "unhealthy", "checks": checks}
