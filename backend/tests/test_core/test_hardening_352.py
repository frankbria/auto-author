"""Regression tests for the #352 hardening cluster.

Each of these guards a fail-open: a condition where the previous code accepted
something it should have refused, or refused to fail when it should have.
"""
import pytest
from pydantic import ValidationError

import app.core.config as config

CI_TEST_SECRET = "test-secret-for-ci-minimum-32-characters-long-safe-for-testing"

# Note: these monkeypatch is_deployed_env rather than setting ENVIRONMENT and
# reloading the module. Reloading re-runs the module-level `settings =
# Settings()`, which — correctly, as of this change — raises when the CI secret
# meets a deployed marker, so the reload blows up before the assertion. That the
# import itself fails is the point of the fix; it just makes reload useless as a
# test fixture.


class TestBetterAuthSecretOnDeployedEnvironments:
    """The committed CI secret must not be usable anywhere real.

    It previously only failed on production, so a staging deploy that forgot the
    secret booted and signed every JWT with a key committed to this repository —
    and passed its health check, so nothing surfaced it.
    """

    def test_ci_secret_is_rejected_on_a_deployed_environment(self, monkeypatch):
        monkeypatch.setattr(config, "is_deployed_env", lambda: True)

        with pytest.raises(ValidationError) as exc:
            config.Settings(BETTER_AUTH_SECRET=CI_TEST_SECRET)

        assert "committed CI test secret" in str(exc.value)

    def test_ci_secret_still_allowed_off_deployment(self, monkeypatch):
        # CI and local development must keep working without provisioning a
        # secret, which is the whole reason the default exists.
        monkeypatch.setattr(config, "is_deployed_env", lambda: False)

        settings = config.Settings(BETTER_AUTH_SECRET=CI_TEST_SECRET)
        assert settings.BETTER_AUTH_SECRET == CI_TEST_SECRET

    def test_a_real_secret_is_accepted_on_a_deployed_environment(self, monkeypatch):
        monkeypatch.setattr(config, "is_deployed_env", lambda: True)

        real = "x" * 64
        assert config.Settings(BETTER_AUTH_SECRET=real).BETTER_AUTH_SECRET == real

    @pytest.mark.parametrize(
        "environment,node_env,expected",
        [
            ("staging", "", True),
            ("STAGING", "", True),
            ("production", "", True),
            ("Production", "", True),
            ("", "production", True),
            ("development", "", False),
            ("test", "", False),
            ("", "", False),
        ],
    )
    def test_is_deployed_env_markers(self, monkeypatch, environment, node_env, expected):
        # Staging must count as deployed here even though is_production_env()
        # deliberately excludes it — that is the distinction this fix rests on.
        monkeypatch.setenv("ENVIRONMENT", environment)
        monkeypatch.setenv("NODE_ENV", node_env)
        assert config.is_deployed_env() is expected


class TestAiMaxRetriesFloor:
    """range(0) never enters the loop, so _retry_with_backoff returned None and
    the caller raised AttributeError on it. Fail at config load instead."""

    @pytest.mark.parametrize("bad", [0, -1])
    def test_retry_count_below_one_is_rejected(self, bad):
        with pytest.raises(ValidationError):
            config.Settings(AI_MAX_RETRIES=bad)

    def test_one_is_allowed(self):
        assert config.Settings(AI_MAX_RETRIES=1).AI_MAX_RETRIES == 1


class TestApiKeyStubIsGone:
    def test_get_api_key_no_longer_exists(self):
        """The stub accepted any non-empty header — a trap for whoever wired it up."""
        import app.api.dependencies as dependencies

        assert not hasattr(dependencies, "get_api_key")


class TestSessionWithoutExpiryFailsClosed:
    """`if expires_at:` meant a session document missing the field skipped the
    expiry check entirely and was accepted — an unexpirable session from a
    malformed or partially-written record."""

    @pytest.mark.asyncio
    async def test_session_missing_expires_at_is_rejected(self, monkeypatch):
        from app.core import better_auth_session

        session_doc = {"_id": "s1", "userId": "u1", "token": "t"}  # no expiresAt

        class _Coll:
            async def find_one(self, *a, **kw):
                return session_doc

            def __init__(self):
                self.refreshed = False

            async def update_one(self, *a, **kw):
                # Record rather than raise: validate_better_auth_session catches
                # exceptions and returns None, so a raising fake would make this
                # test pass against the fail-open code for the wrong reason —
                # it did, until the mutation check caught it.
                self.refreshed = True

            async def delete_one(self, *a, **kw):
                return None

        coll = _Coll()

        async def _fake_collection(_name):
            return coll

        monkeypatch.setattr(better_auth_session, "get_collection", _fake_collection)

        class _Req:
            cookies = {"better-auth.session_token": "t"}
            headers: dict = {}

        result = await better_auth_session.validate_better_auth_session(_Req())

        assert result is None
        # The fail-open path fell through to refreshing last-activity on a
        # session it had never dated.
        assert coll.refreshed is False


class TestAiMaxRetriesUpperBound:
    """The backoff is exponential, so an oversized retry count does not fail
    loudly — it holds the request open past any sane client timeout while
    occupying a worker."""

    @pytest.mark.parametrize("bad", [11, 100])
    def test_retry_count_above_the_cap_is_rejected(self, bad):
        with pytest.raises(ValidationError):
            config.Settings(AI_MAX_RETRIES=bad)

    def test_the_cap_itself_is_allowed(self):
        assert config.Settings(AI_MAX_RETRIES=10).AI_MAX_RETRIES == 10


class TestStripeOrderingIsEnforcedByTheQuery:
    """The guard must live in the write, not in a read before it.

    Two deliveries for the same customer carry different event ids, so the
    idempotency claim does not serialize them. A read-then-write check lets both
    pass their comparison and the older one land last — the exact downgrade the
    guard exists to prevent.
    """

    @pytest.mark.asyncio
    async def test_update_user_passes_the_ordering_condition_to_mongo(self, monkeypatch):
        from app.api.endpoints import webhooks

        captured = {}

        async def _fake_update_user(auth_id, data, actor_id=None, extra_filter=None):
            captured["filter"] = extra_filter
            captured["data"] = data
            return {"auth_id": auth_id, **data}

        async def _fake_lookup(_customer_id):
            return {"auth_id": "u1", "stripe_event_created": 500}

        monkeypatch.setattr(webhooks, "update_user", _fake_update_user)
        monkeypatch.setattr(
            webhooks, "get_user_by_stripe_customer_id", _fake_lookup
        )

        await webhooks._apply_subscription_event(
            "customer.subscription.deleted",
            {"customer": "cus_1", "id": "sub_1"},
            "evt_1",
            400,  # older than the applied 500
        )

        # The condition must be part of the query, not evaluated beforehand.
        assert captured["filter"] is not None, (
            "ordering must be enforced by the write; a prior read races with a "
            "concurrent delivery"
        )
        assert captured["data"]["stripe_event_created"] == 400

    @pytest.mark.asyncio
    async def test_a_rejected_write_reports_the_event_as_stale(self, monkeypatch):
        from app.api.endpoints import webhooks

        async def _fake_update_user(auth_id, data, actor_id=None, extra_filter=None):
            return None  # Mongo matched nothing: a newer event already applied

        async def _fake_lookup(_customer_id):
            return {"auth_id": "u1", "stripe_event_created": 900}

        monkeypatch.setattr(webhooks, "update_user", _fake_update_user)
        monkeypatch.setattr(
            webhooks, "get_user_by_stripe_customer_id", _fake_lookup
        )

        result = await webhooks._apply_subscription_event(
            "customer.subscription.deleted",
            {"customer": "cus_1", "id": "sub_1"},
            "evt_old",
            100,
        )

        assert result["status"] == "stale_event"
