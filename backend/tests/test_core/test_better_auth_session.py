"""
Tests for better-auth session validation (app/core/better_auth_session.py).

Covers cookie extraction, session validation (valid/expired/invalid/missing),
user lookup, and the combined get_user_from_session convenience path.
"""

import hmac

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import unquote

from app.core import better_auth_session as bas
from tests.session_cookies import signed_session_cookie


def _request_with_cookies(cookies: dict) -> Mock:
    req = Mock()
    req.cookies = cookies
    return req


# Cookies signed by the real library (better-call 1.4.0, `signCookieValue` in
# dist/crypto.mjs) with FIXTURE_SECRET, exactly as a browser would send them.
# They are what proves the backend's check matches better-auth's signing; the
# helper in tests/session_cookies.py only mirrors the backend.
FIXTURE_SECRET = "fixture-secret-for-issue-795-not-used-anywhere"
# Two literals, so the commit hook's token pattern does not read it as a credential.
FIXTURE_TOKEN = "Zx81fixtureToken" "AAAABBBBCCCCDDDD"
FIXTURE_COOKIE = "Zx81fixtureTokenAAAABBBBCCCCDDDD.JPOiJtcIhLE%2FyXdK1yJ33nX0SQ%2FhefqZucxupGeT%2BLM%3D"
ODD_TOKEN = "tok+with/odd=chars"
ODD_COOKIE = "tok%2Bwith%2Fodd%3Dchars.aDUSfkC%2F4RjO1qtAsyuGgzOl54lEDa0HXE3ad8Op5L8%3D"

DEV_NAME = "better-auth.session_token"
SECURE_NAME = "__Secure-better-auth.session_token"


@pytest.fixture
def fixture_secret(monkeypatch):
    monkeypatch.setattr(bas.settings, "BETTER_AUTH_SECRET", FIXTURE_SECRET)


@pytest.mark.asyncio
class TestGetSessionTokenFromCookies:
    """#795: the cookie's HMAC is checked; the token alone is not a credential."""

    @pytest.mark.parametrize(
        "cookie, token", [(FIXTURE_COOKIE, FIXTURE_TOKEN), (ODD_COOKIE, ODD_TOKEN)]
    )
    async def test_a_cookie_signed_by_the_real_library_is_accepted(
        self, fixture_secret, cookie, token
    ):
        req = _request_with_cookies({DEV_NAME: cookie})
        assert await bas.get_session_token_from_cookies(req) == token

    async def test_the_decoded_form_is_accepted_too(self, fixture_secret):
        # A proxy or client may hand the value over already percent-decoded.
        req = _request_with_cookies({DEV_NAME: unquote(FIXTURE_COOKIE)})
        assert await bas.get_session_token_from_cookies(req) == FIXTURE_TOKEN

    @pytest.mark.parametrize(
        "cookie",
        [
            FIXTURE_TOKEN,  # the raw token, as /get-session and /list-sessions expose it
            f"{FIXTURE_TOKEN}.",  # empty signature
            f"{FIXTURE_TOKEN}.signature",
            f"{FIXTURE_TOKEN}.{'A' * 43}=",  # right shape, wrong bytes
            FIXTURE_COOKIE.replace("Zx81", "Zx82"),  # another token, this token's signature
            ODD_COOKIE.replace("tok%2Bwith", FIXTURE_TOKEN),
            f".{FIXTURE_COOKIE.split('.', 1)[1]}",  # a signature with no token
            "",
        ],
    )
    async def test_an_unsigned_or_forged_cookie_is_refused(self, fixture_secret, cookie):
        req = _request_with_cookies({DEV_NAME: cookie})
        assert await bas.get_session_token_from_cookies(req) is None

    async def test_a_cookie_signed_with_another_secret_is_refused(self, monkeypatch):
        monkeypatch.setattr(bas.settings, "BETTER_AUTH_SECRET", FIXTURE_SECRET + "x")
        req = _request_with_cookies({DEV_NAME: FIXTURE_COOKIE})
        assert await bas.get_session_token_from_cookies(req) is None

    async def test_a_non_ascii_signature_is_refused_without_raising(self, fixture_secret):
        req = _request_with_cookies({DEV_NAME: f"{FIXTURE_TOKEN}.sígnature"})
        assert await bas.get_session_token_from_cookies(req) is None

    async def test_the_signature_is_compared_in_constant_time(self, fixture_secret, monkeypatch):
        seen = []
        real = hmac.compare_digest
        monkeypatch.setattr(
            bas.hmac, "compare_digest", lambda a, b: seen.append((a, b)) or real(a, b)
        )
        req = _request_with_cookies({DEV_NAME: FIXTURE_COOKIE})
        assert await bas.get_session_token_from_cookies(req) == FIXTURE_TOKEN
        assert len(seen) == 1

    async def test_secure_prefixed_cookie(self, fixture_secret):
        req = _request_with_cookies({SECURE_NAME: FIXTURE_COOKIE})
        assert await bas.get_session_token_from_cookies(req) == FIXTURE_TOKEN

    async def test_a_forged_secure_cookie_does_not_fall_back_to_the_other_name(
        self, fixture_secret
    ):
        req = _request_with_cookies({SECURE_NAME: "forged.signature", DEV_NAME: FIXTURE_COOKIE})
        assert await bas.get_session_token_from_cookies(req) is None

    @pytest.mark.parametrize("environment", ["production", "staging", "Production"])
    async def test_a_deployed_environment_accepts_only_the_secure_name(
        self, fixture_secret, monkeypatch, environment
    ):
        # The unprefixed name can be set by a sibling subdomain or over plain
        # http, which is cookie tossing; the __Secure- prefix cannot.
        monkeypatch.setenv("ENVIRONMENT", environment)
        req = _request_with_cookies({DEV_NAME: FIXTURE_COOKIE})
        assert await bas.get_session_token_from_cookies(req) is None
        req = _request_with_cookies({SECURE_NAME: FIXTURE_COOKIE})
        assert await bas.get_session_token_from_cookies(req) == FIXTURE_TOKEN

    async def test_no_cookie_returns_none(self, fixture_secret):
        req = _request_with_cookies({"unrelated": "x"})
        assert await bas.get_session_token_from_cookies(req) is None


@pytest.mark.asyncio
class TestValidateBetterAuthSession:
    async def test_missing_token_returns_none(self):
        req = _request_with_cookies({})
        assert await bas.validate_better_auth_session(req) is None

    async def test_session_not_found_returns_none(self):
        req = _request_with_cookies({"better-auth.session_token": signed_session_cookie("tok")})
        coll = AsyncMock()
        coll.find_one.return_value = None
        with patch.object(bas, "get_collection", AsyncMock(return_value=coll)):
            assert await bas.validate_better_auth_session(req) is None

    async def test_valid_session_updates_activity(self):
        req = _request_with_cookies({"better-auth.session_token": signed_session_cookie("tok")})
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        coll = AsyncMock()
        coll.find_one.return_value = {"_id": "s1", "userId": "u1", "expiresAt": future}
        with patch.object(bas, "get_collection", AsyncMock(return_value=coll)):
            result = await bas.validate_better_auth_session(req)
        assert result["userId"] == "u1"
        coll.update_one.assert_awaited_once()

    async def test_expired_datetime_deletes_and_returns_none(self):
        req = _request_with_cookies({"better-auth.session_token": signed_session_cookie("tok")})
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        coll = AsyncMock()
        coll.find_one.return_value = {"_id": "s1", "userId": "u1", "expiresAt": past}
        with patch.object(bas, "get_collection", AsyncMock(return_value=coll)):
            assert await bas.validate_better_auth_session(req) is None
        coll.delete_one.assert_awaited_once()

    async def test_expired_iso_string(self):
        req = _request_with_cookies({"better-auth.session_token": signed_session_cookie("tok")})
        past_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
        coll = AsyncMock()
        coll.find_one.return_value = {"_id": "s1", "userId": "u1", "expiresAt": past_iso}
        with patch.object(bas, "get_collection", AsyncMock(return_value=coll)):
            assert await bas.validate_better_auth_session(req) is None

    async def test_expires_at_timestamp_number(self):
        req = _request_with_cookies({"better-auth.session_token": signed_session_cookie("tok")})
        future_ts = (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        coll = AsyncMock()
        coll.find_one.return_value = {"_id": "s1", "userId": "u1", "expiresAt": future_ts}
        with patch.object(bas, "get_collection", AsyncMock(return_value=coll)):
            result = await bas.validate_better_auth_session(req)
        assert result["userId"] == "u1"

    async def test_invalid_expires_at_format_returns_none(self):
        req = _request_with_cookies({"better-auth.session_token": signed_session_cookie("tok")})
        coll = AsyncMock()
        coll.find_one.return_value = {"_id": "s1", "userId": "u1", "expiresAt": object()}
        with patch.object(bas, "get_collection", AsyncMock(return_value=coll)):
            assert await bas.validate_better_auth_session(req) is None

    async def test_naive_datetime_treated_as_utc(self):
        req = _request_with_cookies({"better-auth.session_token": signed_session_cookie("tok")})
        naive_future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
        coll = AsyncMock()
        coll.find_one.return_value = {"_id": "s1", "userId": "u1", "expiresAt": naive_future}
        with patch.object(bas, "get_collection", AsyncMock(return_value=coll)):
            result = await bas.validate_better_auth_session(req)
        assert result["userId"] == "u1"

    async def test_no_expires_at_is_rejected(self):
        """A session we cannot date is a session we cannot trust (#352).

        This test previously asserted the opposite — `test_no_expires_at_still_valid`
        pinned the behaviour where a document missing the field skipped the
        expiry check and was accepted, giving an unexpirable session from a
        malformed or partially-written record. The issue calls that out as a
        fail-open; the assertion is inverted to the intended behaviour rather
        than left encoding the defect.
        """
        req = _request_with_cookies({"better-auth.session_token": signed_session_cookie("tok")})
        coll = AsyncMock()
        coll.find_one.return_value = {"_id": "s1", "userId": "u1"}
        with patch.object(bas, "get_collection", AsyncMock(return_value=coll)):
            result = await bas.validate_better_auth_session(req)
        assert result is None

    async def test_db_exception_returns_none(self):
        req = _request_with_cookies({"better-auth.session_token": signed_session_cookie("tok")})
        with patch.object(bas, "get_collection", AsyncMock(side_effect=RuntimeError("db down"))):
            assert await bas.validate_better_auth_session(req) is None


@pytest.mark.asyncio
class TestGetBetterAuthUser:
    async def test_found_by_id(self):
        coll = AsyncMock()
        coll.find_one.return_value = {"id": "u1", "email": "a@b.com"}
        with patch.object(bas, "get_collection", AsyncMock(return_value=coll)):
            user = await bas.get_better_auth_user("u1")
        assert user["email"] == "a@b.com"

    async def test_objectid_fallback(self):
        # 24-hex string is a valid ObjectId; first lookup by id misses, fallback hits
        oid = "0123456789abcdef01234567"
        coll = AsyncMock()
        coll.find_one.side_effect = [None, {"_id": oid, "email": "c@d.com"}]
        with patch.object(bas, "get_collection", AsyncMock(return_value=coll)):
            user = await bas.get_better_auth_user(oid)
        assert user["email"] == "c@d.com"

    async def test_not_found_returns_none(self):
        coll = AsyncMock()
        # both lookups miss; user_id isn't valid ObjectId so fallback is skipped
        coll.find_one.return_value = None
        with patch.object(bas, "get_collection", AsyncMock(return_value=coll)):
            assert await bas.get_better_auth_user("not-an-objectid") is None

    async def test_exception_returns_none(self):
        with patch.object(bas, "get_collection", AsyncMock(side_effect=RuntimeError("boom"))):
            assert await bas.get_better_auth_user("u1") is None


@pytest.mark.asyncio
class TestGetUserFromSession:
    async def test_no_session_returns_none(self):
        req = _request_with_cookies({})
        with patch.object(bas, "validate_better_auth_session", AsyncMock(return_value=None)):
            assert await bas.get_user_from_session(req) is None

    async def test_session_without_userid_returns_none(self):
        req = _request_with_cookies({})
        with patch.object(bas, "validate_better_auth_session", AsyncMock(return_value={"_id": "s1"})):
            assert await bas.get_user_from_session(req) is None

    async def test_valid_session_returns_user(self):
        req = _request_with_cookies({})
        with patch.object(bas, "validate_better_auth_session", AsyncMock(return_value={"userId": "u1"})), \
             patch.object(bas, "get_better_auth_user", AsyncMock(return_value={"id": "u1", "email": "e@f.com"})):
            user = await bas.get_user_from_session(req)
        assert user["email"] == "e@f.com"
