"""Tests for the entitlement gate dependency + endpoint denial (issue #174)."""

import pytest
from fastapi import HTTPException

from app.api.dependencies import get_entitlement_checker
from app.core.config import settings
from app.schemas.errors import ErrorCode


class TestEntitlementCheckerDependency:
    """Unit tests for get_entitlement_checker's inner dependency."""

    @pytest.mark.asyncio
    async def test_allows_free_user(self, monkeypatch):
        monkeypatch.setattr(settings, "BYPASS_AUTH", False)
        monkeypatch.setattr(settings, "PLAN_ENFORCEMENT_ENABLED", True)
        check = get_entitlement_checker("generate_toc")
        # No exception raised for an entitled plan.
        assert await check(current_user={"plan": "free"}) is None

    @pytest.mark.asyncio
    async def test_denies_restricted_user_with_402(self, monkeypatch):
        monkeypatch.setattr(settings, "BYPASS_AUTH", False)
        monkeypatch.setattr(settings, "PLAN_ENFORCEMENT_ENABLED", True)
        check = get_entitlement_checker("generate_toc")
        with pytest.raises(HTTPException) as exc:
            await check(current_user={"plan": "restricted"})
        assert exc.value.status_code == 402
        assert exc.value.detail["error_code"] == ErrorCode.ENTITLEMENT_REQUIRED.value
        assert exc.value.headers["X-Entitlement-Feature"] == "generate_toc"

    @pytest.mark.asyncio
    async def test_bypass_auth_short_circuits(self, monkeypatch):
        monkeypatch.setattr(settings, "BYPASS_AUTH", True)
        monkeypatch.setattr(settings, "PLAN_ENFORCEMENT_ENABLED", True)
        check = get_entitlement_checker("generate_toc")
        # Restricted plan would normally deny; bypass returns without checking.
        assert await check(current_user={"plan": "restricted"}) is None

    @pytest.mark.asyncio
    async def test_enforcement_disabled_short_circuits(self, monkeypatch):
        monkeypatch.setattr(settings, "BYPASS_AUTH", False)
        monkeypatch.setattr(settings, "PLAN_ENFORCEMENT_ENABLED", False)
        check = get_entitlement_checker("generate_toc")
        assert await check(current_user={"plan": "restricted"}) is None


class TestEntitlementGateOnEndpoint:
    """Route-level: a denied user hits 402 before the AI handler runs."""

    @pytest.mark.asyncio
    async def test_restricted_user_gets_402_on_ai_endpoint(
        self, auth_client_factory, monkeypatch
    ):
        # Env-independent: force enforcement on, bypass off.
        monkeypatch.setattr(settings, "BYPASS_AUTH", False)
        monkeypatch.setattr(settings, "PLAN_ENFORCEMENT_ENABLED", True)

        client = await auth_client_factory(overrides={"plan": "restricted"})
        # Entitlement is a route dependency: denied before book lookup, so any id works.
        resp = await client.post(
            "/api/v1/books/507f1f77bcf86cd799439099/generate-toc", json={}
        )
        assert resp.status_code == 402
        body = resp.json()["detail"]
        assert body["error_code"] == ErrorCode.ENTITLEMENT_REQUIRED.value

    @pytest.mark.asyncio
    async def test_free_user_not_blocked_by_entitlement(
        self, auth_client_factory, monkeypatch
    ):
        monkeypatch.setattr(settings, "BYPASS_AUTH", False)
        monkeypatch.setattr(settings, "PLAN_ENFORCEMENT_ENABLED", True)

        client = await auth_client_factory(overrides={"plan": "free"})
        # Free plan passes the gate; a missing book then yields a non-402 error.
        resp = await client.post(
            "/api/v1/books/507f1f77bcf86cd799439099/generate-toc", json={}
        )
        assert resp.status_code != 402
