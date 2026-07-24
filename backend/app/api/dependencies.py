from fastapi import Depends, Header, HTTPException, status, Request
from typing import Dict, Optional, Any
import logging
import time
import re
from pydantic import BaseModel

from datetime import datetime, timezone

from app.db.database import get_collection
from app.db.database import create_audit_log
from app.db.usage import increment_usage
from app.core.config import settings, is_production_env
from app.core.security import get_current_user_from_session

logger = logging.getLogger(__name__)


def _is_exempt_e2e_user(current_user: Dict) -> bool:
    """True for a designated staging E2E test account.

    The staging E2E suite signs in as ONE real user (BYPASS_AUTH off — it tests
    real auth end-to-end) and legitimately blows past human per-user limits, so
    the rate limiter (#180) and AI quota (#173) throttled it into perpetual red.
    Exempt that specific account — same idea as the existing ``BYPASS_AUTH``
    skip, keyed on email and FENCED to non-production so it can never loosen
    limits on the real product.
    """
    if is_production_env():
        return False
    exempt = settings.E2E_EXEMPT_EMAILS
    if not exempt:
        return False
    email = (current_user.get("email") or "").strip().lower()
    if not email:
        return False
    return email in {e.strip().lower() for e in exempt.split(",") if e.strip()}


# MongoDB collection dependency
async def get_database_collection(collection_name: str):
    """Get a MongoDB collection"""
    return await get_collection(collection_name)


async def get_api_key(x_api_key: str = Header(None)):
    """Validate API key for external services"""
    # This would compare against a stored API key in a real application
    if x_api_key is None or x_api_key == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API key is missing"
        )
    # You would validate the API key against your stored value here
    # For now, this is a placeholder
    return x_api_key


def sanitize_input(text: str) -> str:
    """Basic sanitization of user input"""
    if not text:
        return text

    # Remove any potential script tags
    text = re.sub(r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>", "", text)

    # Remove any potential HTML tags
    text = re.sub(r"<[^>]*>", "", text)

    # Replace multiple spaces with a single space
    text = re.sub(r"\s+", " ", text)

    return text.strip()


class SanitizedModel(BaseModel):
    """Base class for models that automatically sanitize string fields"""

    def __init__(self, **data):
        # Sanitize any string fields before initialization
        for field_name, field_value in data.items():
            if isinstance(field_value, str):
                data[field_name] = sanitize_input(field_value)
        super().__init__(**data)


def get_rate_limiter(limit: int = 10, window: int = 60):
    """Create a rate limiter dependency with specific limits (issue #180).

    Buckets are keyed per **authenticated user** (every rate-limited endpoint
    also requires session auth, so FastAPI's per-request dependency cache makes
    the user lookup free) and persisted in Mongo via the same atomic
    ``$inc``+TTL counter as the AI quota (#173) — shared across uvicorn
    workers, surviving restarts, self-evicting.

    Fixed epoch-aligned windows: a client can burst up to 2x the limit across
    a window boundary (standard fixed-window tradeoff; the boundary is now
    predictable, unlike the old first-request-anchored reset). Mongo failure
    propagates (fail-closed) — auth on these endpoints already requires the
    same Mongo, so there's no new blast radius.

    Args:
        limit: Maximum number of requests allowed in the time window
        window: Time window in seconds

    Returns:
        A dependency function that can be used with Depends()
    """

    async def rate_limiter(
        request: Request,
        current_user: Dict = Depends(get_current_user_from_session),
    ):
        """Rate limiting dependency function"""
        # Skip rate limiting in auth-bypass mode (E2E/test only; BYPASS_AUTH is
        # rejected in production by Settings validation), so test suites can
        # create many resources without tripping the limiter.
        if settings.BYPASS_AUTH or _is_exempt_e2e_user(current_user):
            return {"limit": limit, "remaining": limit, "reset": 0}

        # Key per authenticated user; client IP only as a defense-in-depth
        # fallback if a caller somehow has no id.
        subject = (
            current_user.get("auth_id")
            or current_user.get("id")
            or current_user.get("clerk_id")
            or (request.client.host if request.client else "unknown")
        )

        now = time.time()
        bucket_start = int(now // window) * window
        reset_at = bucket_start + window

        # TTL of 2 windows: the bucket outlives its own window, then Mongo reaps it.
        count = await increment_usage(
            subject, f"rl:{request.url.path}:{bucket_start}", ttl_seconds=window * 2
        )

        if count > limit:
            retry_after = max(1, int(reset_at - now) + 1)
            logger.warning(
                "Rate limit exceeded: subject=%s path=%s limit=%s window=%ss count=%s",
                subject, request.url.path, limit, window, count,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_at),
                    "Retry-After": str(retry_after),
                },
            )

        return {
            "limit": limit,
            "remaining": limit - count,
            "reset": reset_at,
        }

    return rate_limiter


def get_ai_usage_quota():
    """Create a per-user AI-generation quota dependency (issue #173, cost control).

    Increments a per-user counter (daily + monthly) in Mongo on every call and
    raises 429 once the configured cap is exceeded — enforced *before* the AI
    call so a leaked cookie or runaway client can't rack up unbounded spend.

    Counts off the user's ``auth_id`` today; swap to plan/entitlement when P0.2
    lands. ponytail: rejected calls still increment (matches the in-memory
    limiter) — the counter tracks attempts, which is fine for a spend cap.
    """

    async def check_quota(
        current_user: Dict = Depends(get_current_user_from_session),
        request: Request = None,  # noqa: RUF013 (FastAPI injects; None only for direct-call tests)
    ):
        # Bare `Request` annotation so FastAPI injects the real request in
        # production; the None default keeps the direct-call unit tests working
        # without a stub. NB: Optional[Request] would NOT be injected — FastAPI
        # only special-cases the bare Request type, and a Union raises
        # FastAPIError at route registration (would block startup).
        # Skip in auth-bypass mode (E2E/test) and when disabled, mirroring the
        # rate limiter so test suites can generate freely.
        if settings.BYPASS_AUTH or not settings.AI_QUOTA_ENABLED:
            return
        if _is_exempt_e2e_user(current_user):
            return

        user_id = (
            current_user.get("auth_id")
            or current_user.get("id")
            or current_user.get("clerk_id")
        )
        if not user_id:
            # Auth runs before this dependency, so an authenticated user always
            # has an id; fail closed rather than silently un-metering if not.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to identify user for AI usage metering.",
            )

        now = datetime.now(timezone.utc)
        windows = (
            ("day", now.strftime("%Y-%m-%d"), settings.AI_QUOTA_DAILY_LIMIT, 2 * 86400),
            ("month", now.strftime("%Y-%m"), settings.AI_QUOTA_MONTHLY_LIMIT, 40 * 86400),
        )
        for period, bucket, limit, ttl in windows:
            if limit <= 0:  # window disabled
                continue
            count = await increment_usage(user_id, f"{period}:{bucket}", ttl)
            if count > limit:
                path = getattr(getattr(request, "url", None), "path", "unknown")
                logger.warning(
                    "AI quota exceeded: subject=%s path=%s period=%s limit=%s count=%s",
                    user_id, path, period, limit, count,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"AI usage limit reached ({limit} generations per {period}). "
                        "Try again later or contact support to raise your limit."
                    ),
                    headers={"X-AI-Quota-Limit": str(limit), "X-AI-Quota-Period": period},
                )

    return check_quota


def get_entitlement_checker(feature: str):
    """Create a per-request entitlement gate for an AI ``feature`` (issue #174).

    Mirrors ``get_ai_usage_quota``: resolves the caller (cached via ``Depends``),
    checks their ``plan`` against ``app.core.entitlements``, and raises 402 when
    the plan doesn't permit ``feature``. For the free-invite beta every plan is
    ``free`` (full access) so this never denies a real user — it's the hook so
    P0.1 keys caps off plan and paid launch adds a tier, not a rebuild.

    Bypassed under ``BYPASS_AUTH`` / when ``PLAN_ENFORCEMENT_ENABLED`` is off,
    matching the rate limiter and quota so tests/E2E aren't gated.
    """

    async def check_entitlement(
        current_user: Dict = Depends(get_current_user_from_session),
    ):
        from app.core.entitlements import DEFAULT_PLAN, is_feature_allowed
        from app.utils.error_handlers import handle_entitlement_denied

        if settings.BYPASS_AUTH or not settings.PLAN_ENFORCEMENT_ENABLED:
            return
        if _is_exempt_e2e_user(current_user):
            return

        plan = current_user.get("plan")
        if not is_feature_allowed(plan, feature):
            raise handle_entitlement_denied(feature=feature, plan=plan or DEFAULT_PLAN)

    return check_entitlement


async def audit_request(
    request: Optional[Request],
    current_user: Dict,
    action: str,
    resource_type: str,
    target_id: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Log an audit entry for the current request.

    Note: Authentication is handled by get_current_user_from_session via session cookies.
    This function trusts that current_user has already been authenticated.

    Args:
        request: The FastAPI request object (may be None in some contexts)
        current_user: The authenticated user making the request (already validated)
        action: The action being performed (e.g., "create", "update", "delete")
        resource_type: The type of resource being accessed (e.g., "user", "book")
        target_id: The ID of the resource being accessed (if applicable)
        metadata: Optional dictionary of additional metadata to include in the audit log

    Returns:
        User payload dictionary with sub and email fields
    """
    # Create user payload from current_user (already authenticated via session)
    user_payload = {
        "sub": current_user.get("auth_id") or current_user.get("clerk_id") or current_user.get("id"),
        "email": current_user.get("email", "")
    }

    # Extract request details (request may be None in some contexts)
    if request is not None:
        method = request.method
        path = request.url.path
        client = getattr(request, "client", None)
        ip_address = getattr(client, "host", None) if client else None
        user_agent = request.headers.get("user-agent", "")
        request_id = (
            str(getattr(request.state, "request_id", None))
            if hasattr(request, "state")
            else None
        )
    else:
        method = None
        path = None
        ip_address = None
        user_agent = ""
        request_id = None

    # Build details dictionary with request info
    details = {
        "method": method,
        "path": path,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "request_id": request_id,
    }

    # Merge in any additional metadata
    if metadata:
        details.update(metadata)

    # Get user ID - better-auth uses auth_id instead of clerk_id
    # Support both for migration period
    user_id = current_user.get("auth_id") or current_user.get("clerk_id") or current_user.get("id")

    # Create audit log
    await create_audit_log(
        action=action,
        actor_id=user_id,
        target_id=target_id or "unknown",
        resource_type=resource_type,
        details=details,
    )

    # Return user payload
    return user_payload
