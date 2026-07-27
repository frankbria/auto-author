"""Issue #340: route-wiring guard + HTTP-level enforcement for the two AI cost
gates.

Every AI generation endpoint declares BOTH
``Depends(get_ai_usage_quota())`` (cost control, #173) and
``Depends(get_entitlement_checker(<feature>))`` (paywall hook, #174). The suite
globally no-ops the quota (``tests/conftest.py::noop_ai_quota``) and the
entitlement gate self-disables under ``BYPASS_AUTH``, so before this file either
dependency could be deleted from 9 of the 10 endpoints and the whole suite would
stay green — exactly the hole #199 closed for the rate limiter.

Three classes, mirroring `test_rate_limit_routes.py`:

- ``TestAIGateWiringCompleteness`` — walks the live FastAPI app and names any
  endpoint that lost either dependency (plus a drift check for new AI routes).
- ``TestEntitlementDenialPerRoute`` — a restricted plan gets 402 on *every* one
  of the 10 endpoints, before the handler runs.
- ``TestQuotaExhaustionPerRoute`` — the real quota, armed via
  ``arm_real_ai_quota`` against real Mongo-backed counting, returns the
  production 429 contract on *every* one of the 10 endpoints.

The denial tests use a nonexistent book id on purpose: both gates are route-level
dependencies, so they fire before the handler ever looks the book up.
"""

import pytest

from app.core.config import settings
from app.schemas.errors import ErrorCode
from tests.route_introspection import route_dependency_calls, shared_dependency_call

# Provenance: `grep -n "get_ai_usage_quota()" app/api/endpoints/books.py`.
# These are the same 10 AI routes listed in
# test_rate_limit_routes.py::EXPECTED_RATE_LIMITED_ROUTES.
AI_GATED_ROUTES = [
    ("POST", "/api/v1/books/{book_id}/analyze-summary"),
    ("POST", "/api/v1/books/{book_id}/generate-questions"),
    ("POST", "/api/v1/books/{book_id}/generate-toc"),
    ("POST", "/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions"),
    (
        "POST",
        "/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/regenerate",
    ),
    ("POST", "/api/v1/books/{book_id}/chapters/{chapter_id}/regenerate-questions"),
    ("POST", "/api/v1/books/{book_id}/chapters/{chapter_id}/generate-draft"),
    ("POST", "/api/v1/books/{book_id}/chapters/{chapter_id}/transform-style"),
    ("POST", "/api/v1/books/{book_id}/chapters/{chapter_id}/enhance-text"),
    ("POST", "/api/v1/books/{book_id}/chapters/{chapter_id}/enhance-transcription"),
]

assert len(AI_GATED_ROUTES) == 10

# Well-formed but nonexistent ids — the gates reject before any DB lookup.
_PATH_IDS = {
    "book_id": "507f1f77bcf86cd799439099",
    "chapter_id": "507f1f77bcf86cd799439098",
    "question_id": "507f1f77bcf86cd799439097",
}

# The inner dependency function names the two factories return. Identity is
# derived from the live routes by name rather than by calling the factories —
# see tests/route_introspection.py::shared_dependency_call for why.
QUOTA_DEP_NAME = "noop_ai_quota"          # conftest's shared no-op
ENTITLEMENT_DEP_NAME = "check_entitlement"  # the real one; never faked


def _url(path: str) -> str:
    return path.format(**_PATH_IDS)


def _ids(routes):
    """Readable parametrize ids: 'POST /api/v1/books/{book_id}/generate-toc'."""
    return [f"{method} {path}" for method, path in routes]


class TestAIGateWiringCompleteness:
    """Static pin: the dependencies are still declared on every AI route."""

    def test_every_ai_route_declares_the_usage_quota(self):
        calls_by_route = route_dependency_calls()
        shared = shared_dependency_call(calls_by_route, QUOTA_DEP_NAME)
        assert len(shared) == 1, (
            f"Expected exactly one {QUOTA_DEP_NAME} callable across the live "
            f"app's routes; found {shared}. The conftest quota swap may have "
            "changed shape (it must return ONE shared module-level function)."
        )
        quota = next(iter(shared))

        missing = [
            pair
            for pair in AI_GATED_ROUTES
            if quota not in calls_by_route.get(pair, set())
        ]
        assert not missing, (
            "The following AI routes no longer declare "
            f"Depends(get_ai_usage_quota()): {missing}"
        )

    def test_every_ai_route_declares_an_entitlement_check(self):
        calls_by_route = route_dependency_calls()

        missing = [
            pair
            for pair in AI_GATED_ROUTES
            if not any(
                getattr(c, "__name__", "") == ENTITLEMENT_DEP_NAME
                for c in calls_by_route.get(pair, set())
            )
        ]
        assert not missing, (
            "The following AI routes no longer declare "
            f"Depends(get_entitlement_checker(...)): {missing}"
        )

    def test_no_unlisted_route_carries_the_ai_gates(self):
        """Drift guard: a new AI endpoint must be added to AI_GATED_ROUTES (and
        get its own 402/429 coverage below) rather than silently appearing."""
        calls_by_route = route_dependency_calls()
        quota = next(iter(shared_dependency_call(calls_by_route, QUOTA_DEP_NAME)))

        gated = {
            pair
            for pair, calls in calls_by_route.items()
            if quota in calls
            or any(getattr(c, "__name__", "") == ENTITLEMENT_DEP_NAME for c in calls)
        }
        unexpected = gated - set(AI_GATED_ROUTES)
        assert not unexpected, (
            "Found AI-gated routes not accounted for in AI_GATED_ROUTES: "
            f"{sorted(unexpected)}. Add them (and their denial coverage) if "
            "this is intentional."
        )


@pytest.mark.parametrize(
    "method,path", AI_GATED_ROUTES, ids=_ids(AI_GATED_ROUTES)
)
class TestEntitlementDenialPerRoute:
    """A plan without the feature gets 402 on every AI endpoint (#174, #340)."""

    @pytest.mark.asyncio
    async def test_restricted_plan_gets_402(
        self, method, path, auth_client_factory, monkeypatch
    ):
        # Env-independent: force enforcement on, bypass and the E2E exemption off.
        monkeypatch.setattr(settings, "BYPASS_AUTH", False)
        monkeypatch.setattr(settings, "PLAN_ENFORCEMENT_ENABLED", True)
        monkeypatch.setattr(settings, "E2E_EXEMPT_EMAILS", "")

        client = await auth_client_factory(overrides={"plan": "restricted"})
        resp = await client.request(method, _url(path), json={})

        assert resp.status_code == 402, (
            f"{method} {path} did not deny a restricted plan — the entitlement "
            f"dependency is not enforcing (got {resp.status_code})."
        )
        assert resp.json()["detail"]["error_code"] == (
            ErrorCode.ENTITLEMENT_REQUIRED.value
        )

    @pytest.mark.asyncio
    async def test_entitled_plan_is_not_blocked(
        self, method, path, auth_client_factory, monkeypatch
    ):
        """Companion: the gate denies on plan, not on everything (a gate that
        402s unconditionally would pass the test above for the wrong reason)."""
        monkeypatch.setattr(settings, "BYPASS_AUTH", False)
        monkeypatch.setattr(settings, "PLAN_ENFORCEMENT_ENABLED", True)
        monkeypatch.setattr(settings, "E2E_EXEMPT_EMAILS", "")

        client = await auth_client_factory(overrides={"plan": "free"})
        resp = await client.request(method, _url(path), json={})

        assert resp.status_code != 402


@pytest.mark.parametrize(
    "method,path", AI_GATED_ROUTES, ids=_ids(AI_GATED_ROUTES)
)
class TestQuotaExhaustionPerRoute:
    """The real quota returns the production 429 on every AI endpoint (#173, #340)."""

    @pytest.mark.asyncio
    async def test_call_past_the_cap_gets_429(
        self, method, path, auth_client_factory, arm_real_ai_quota, monkeypatch
    ):
        monkeypatch.setattr(settings, "E2E_EXEMPT_EMAILS", "")
        arm_real_ai_quota(limit=1)

        # `plan: free` clears the entitlement gate so the quota is what trips.
        client = await auth_client_factory(overrides={"plan": "free"})
        url = _url(path)

        first = await client.request(method, url, json={})
        assert first.status_code != 429, (
            f"{method} {path} 429'd on the first call — the quota counter is "
            "not starting clean."
        )

        second = await client.request(method, url, json={})
        assert second.status_code == 429, (
            f"{method} {path} did not enforce the AI usage quota — "
            f"Depends(get_ai_usage_quota()) is not wired (got "
            f"{second.status_code})."
        )
        assert second.headers["X-AI-Quota-Limit"] == "1"
        assert second.headers["X-AI-Quota-Period"] == "day"
        assert "limit reached" in second.json()["detail"].lower()
