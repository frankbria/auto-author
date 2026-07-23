"""Designated staging E2E test account is exempt from limiter/quota/entitlement.

The staging E2E suite signs in as ONE real user (BYPASS_AUTH off) and
legitimately exceeds human per-user limits, so the rate limiter (#180) and AI
quota (#173) were throttling it into perpetual red. `_is_exempt_e2e_user`
exempts that specific account, FENCED to non-production.
"""

import pytest
from unittest.mock import patch
from fastapi import HTTPException

import app.api.dependencies as deps


EXEMPT = "e2e-bot@staging.example, other@staging.example"


def _cfg(email_setting=EXEMPT, production=False):
    """Patch the exempt list + production fence around a test."""
    return (
        patch.object(deps.settings, "E2E_EXEMPT_EMAILS", email_setting),
        patch.object(deps, "is_production_env", lambda: production),
    )


# --- Pure helper: this is where all the branch logic lives ----------------

@pytest.mark.parametrize("email,expected", [
    ("e2e-bot@staging.example", True),      # exact listed
    ("E2E-Bot@Staging.Example", True),      # case-insensitive
    ("other@staging.example", True),        # second entry in the list
    ("  e2e-bot@staging.example  ", True),  # whitespace tolerant
    ("real-user@example.com", False),       # not listed
    ("", False),                            # no email on the session
    (None, False),                          # missing email key
])
def test_exempt_match(email, expected):
    cfg_email, cfg_prod = _cfg()
    with cfg_email, cfg_prod:
        assert deps._is_exempt_e2e_user({"email": email}) is expected


def test_not_exempt_when_list_unset():
    """No configured emails → nobody is exempt (default posture)."""
    cfg_email, cfg_prod = _cfg(email_setting="")
    with cfg_email, cfg_prod:
        assert deps._is_exempt_e2e_user({"email": "e2e-bot@staging.example"}) is False


def test_never_exempt_in_production():
    """The fence: even a listed email is NOT exempt in production."""
    cfg_email, cfg_prod = _cfg(production=True)
    with cfg_email, cfg_prod:
        assert deps._is_exempt_e2e_user({"email": "e2e-bot@staging.example"}) is False


# --- Integration: an exempt user isn't metered past the AI quota cap -------

@pytest.mark.asyncio
async def test_exempt_user_skips_ai_quota(motor_reinit_db, real_ai_quota):
    """With a daily cap of 1, the exempt user still passes on every call."""
    user = {"auth_id": "e2e-bot", "email": "e2e-bot@staging.example"}
    cfg_email, cfg_prod = _cfg()
    with cfg_email, cfg_prod, \
         patch.object(deps.settings, "BYPASS_AUTH", False), \
         patch.object(deps.settings, "AI_QUOTA_ENABLED", True), \
         patch.object(deps.settings, "AI_QUOTA_DAILY_LIMIT", 1), \
         patch.object(deps.settings, "AI_QUOTA_MONTHLY_LIMIT", 1):
        checker = real_ai_quota()
        for _ in range(5):  # far past the cap of 1
            assert await checker(current_user=user) is None


@pytest.mark.asyncio
async def test_non_exempt_user_still_capped(motor_reinit_db, real_ai_quota):
    """The exemption is targeted: a normal user still hits 429 at the cap."""
    user = {"auth_id": "normal", "email": "real-user@example.com"}
    cfg_email, cfg_prod = _cfg()
    with cfg_email, cfg_prod, \
         patch.object(deps.settings, "BYPASS_AUTH", False), \
         patch.object(deps.settings, "AI_QUOTA_ENABLED", True), \
         patch.object(deps.settings, "AI_QUOTA_DAILY_LIMIT", 1), \
         patch.object(deps.settings, "AI_QUOTA_MONTHLY_LIMIT", 0):
        checker = real_ai_quota()
        await checker(current_user=user)  # 1 → ok
        with pytest.raises(HTTPException) as exc:
            await checker(current_user=user)  # 2 → 429
    assert exc.value.status_code == 429
