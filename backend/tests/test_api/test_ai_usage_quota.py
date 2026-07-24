"""Tests for per-user AI usage quota (issue #173, cost control)."""

import pytest
from unittest.mock import patch
from fastapi import HTTPException

import app.api.dependencies as deps
from app.db.usage import increment_usage


# --- DAO: atomic counter -------------------------------------------------

@pytest.mark.asyncio
async def test_increment_usage_counts_up(motor_reinit_db):
    """Repeated increments on the same key return a monotonically rising count."""
    counts = [await increment_usage("user-a", "day:2026-07-03", 3600) for _ in range(3)]
    assert counts == [1, 2, 3]


@pytest.mark.asyncio
async def test_increment_usage_keys_are_independent(motor_reinit_db):
    """Different users / windows never share a counter."""
    assert await increment_usage("user-a", "day:2026-07-03", 3600) == 1
    assert await increment_usage("user-b", "day:2026-07-03", 3600) == 1  # other user
    assert await increment_usage("user-a", "month:2026-07", 3600) == 1  # other window
    assert await increment_usage("user-a", "day:2026-07-03", 3600) == 2


@pytest.mark.asyncio
async def test_increment_usage_sets_ttl(motor_reinit_db):
    """The doc carries an expires_at so the TTL index can reap stale buckets."""
    from app.db.base import get_collection

    await increment_usage("user-a", "day:2026-07-03", 3600)
    coll = await get_collection("usage_counters")
    doc = await coll.find_one({"_id": "user-a:day:2026-07-03"})
    assert doc["expires_at"] is not None


# --- Dependency: 429 at the cap (the AC) ---------------------------------

@pytest.mark.asyncio
async def test_quota_rejects_n_plus_one_in_window(motor_reinit_db, real_ai_quota):
    """The (cap+1)th call in a window is rejected with 429; earlier calls pass.

    Daily cap = 2 → calls 1,2 allowed, call 3 → 429. Monthly disabled (<=0)."""
    user = {"auth_id": "quota-user-1"}
    with patch.object(deps.settings, "BYPASS_AUTH", False), \
         patch.object(deps.settings, "AI_QUOTA_ENABLED", True), \
         patch.object(deps.settings, "AI_QUOTA_DAILY_LIMIT", 2), \
         patch.object(deps.settings, "AI_QUOTA_MONTHLY_LIMIT", 0):
        checker = real_ai_quota()

        await checker(current_user=user)  # 1
        await checker(current_user=user)  # 2

        with pytest.raises(HTTPException) as exc:
            await checker(current_user=user)  # 3 → rejected

    assert exc.value.status_code == 429
    assert "limit reached" in exc.value.detail.lower()
    assert exc.value.headers["X-AI-Quota-Period"] == "day"


@pytest.mark.asyncio
async def test_quota_logs_warning_before_429(motor_reinit_db, real_ai_quota, caplog):
    """A quota 429 emits a warning naming subject/path/period/limit (#334)."""
    import logging
    from unittest.mock import Mock
    from fastapi import Request

    req = Mock(spec=Request)
    req.url = Mock()
    req.url.path = "/api/v1/books/x/generate-toc"
    user = {"auth_id": "quota-log-user"}

    with patch.object(deps.settings, "BYPASS_AUTH", False), \
         patch.object(deps.settings, "AI_QUOTA_ENABLED", True), \
         patch.object(deps.settings, "AI_QUOTA_DAILY_LIMIT", 1), \
         patch.object(deps.settings, "AI_QUOTA_MONTHLY_LIMIT", 0):
        checker = real_ai_quota()
        await checker(current_user=user, request=req)  # 1
        with caplog.at_level(logging.WARNING, logger="app.api.dependencies"):
            with pytest.raises(HTTPException):
                await checker(current_user=user, request=req)  # 2 → 429

    msg = "\n".join(r.getMessage() for r in caplog.records)
    assert "AI quota exceeded" in msg
    assert "quota-log-user" in msg                     # subject
    assert "/api/v1/books/x/generate-toc" in msg       # path
    assert "period=day" in msg and "limit=1" in msg    # period + limit


@pytest.mark.asyncio
async def test_quota_dep_registers_and_injects_request_via_http(
    motor_reinit_db, real_ai_quota
):
    """Mounting the REAL quota dep on a route must register cleanly and inject
    the request (the 429 path reads request.url.path). Regression pin: a
    non-bare-`Request` annotation (e.g. Optional[Request]) raises FastAPIError
    at route registration → the app can't start. The suite-wide conftest fake
    quota dep hides this, so this test uses the real dep on its own app."""
    from fastapi import Depends, FastAPI
    from httpx import ASGITransport, AsyncClient

    from app.core.security import get_current_user_from_session

    test_app = FastAPI()

    @test_app.get("/ai")
    async def ai_route(_=Depends(real_ai_quota())):
        return {"ok": True}

    test_app.dependency_overrides[get_current_user_from_session] = (
        lambda: {"auth_id": "quota-http-user"}
    )

    transport = ASGITransport(app=test_app)
    with patch.object(deps.settings, "BYPASS_AUTH", False), \
         patch.object(deps.settings, "AI_QUOTA_ENABLED", True), \
         patch.object(deps.settings, "AI_QUOTA_DAILY_LIMIT", 1), \
         patch.object(deps.settings, "AI_QUOTA_MONTHLY_LIMIT", 0):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            assert (await client.get("/ai")).status_code == 200
            assert (await client.get("/ai")).status_code == 429


@pytest.mark.asyncio
async def test_quota_isolated_per_user(motor_reinit_db, real_ai_quota):
    """One user hitting the cap doesn't block a different user."""
    with patch.object(deps.settings, "BYPASS_AUTH", False), \
         patch.object(deps.settings, "AI_QUOTA_ENABLED", True), \
         patch.object(deps.settings, "AI_QUOTA_DAILY_LIMIT", 1), \
         patch.object(deps.settings, "AI_QUOTA_MONTHLY_LIMIT", 0):
        checker = real_ai_quota()
        await checker(current_user={"auth_id": "user-x"})  # x at cap
        with pytest.raises(HTTPException):
            await checker(current_user={"auth_id": "user-x"})
        # different user is unaffected
        await checker(current_user={"auth_id": "user-y"})


@pytest.mark.asyncio
async def test_quota_bypassed_when_disabled(motor_reinit_db, real_ai_quota):
    """Disabling the quota (or BYPASS_AUTH) short-circuits without counting."""
    with patch.object(deps.settings, "AI_QUOTA_ENABLED", False), \
         patch.object(deps.settings, "AI_QUOTA_DAILY_LIMIT", 1):
        checker = real_ai_quota()
        for _ in range(5):
            assert await checker(current_user={"auth_id": "u"}) is None


@pytest.mark.asyncio
async def test_quota_monthly_window_enforced(motor_reinit_db, real_ai_quota):
    """The monthly window rejects independently of the (higher) daily window."""
    with patch.object(deps.settings, "BYPASS_AUTH", False), \
         patch.object(deps.settings, "AI_QUOTA_ENABLED", True), \
         patch.object(deps.settings, "AI_QUOTA_DAILY_LIMIT", 100), \
         patch.object(deps.settings, "AI_QUOTA_MONTHLY_LIMIT", 2):
        checker = real_ai_quota()
        await checker(current_user={"auth_id": "m"})
        await checker(current_user={"auth_id": "m"})
        with pytest.raises(HTTPException) as exc:
            await checker(current_user={"auth_id": "m"})
    assert exc.value.headers["X-AI-Quota-Period"] == "month"


# --- Config defaults ------------------------------------------------------

def test_quota_settings_defaults():
    from app.core.config import settings

    assert settings.AI_QUOTA_ENABLED is True
    assert settings.AI_QUOTA_DAILY_LIMIT == 50
    assert settings.AI_QUOTA_MONTHLY_LIMIT == 500
