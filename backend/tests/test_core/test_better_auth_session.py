"""
Tests for better-auth session validation (app/core/better_auth_session.py).

Covers cookie extraction, session validation (valid/expired/invalid/missing),
user lookup, and the combined get_user_from_session convenience path.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

from app.core import better_auth_session as bas


def _request_with_cookies(cookies: dict) -> Mock:
    req = Mock()
    req.cookies = cookies
    return req


@pytest.mark.asyncio
class TestGetSessionTokenFromCookies:
    async def test_secure_prefixed_cookie(self):
        req = _request_with_cookies({"__Secure-better-auth.session_token": "tok123"})
        assert await bas.get_session_token_from_cookies(req) == "tok123"

    async def test_dev_cookie(self):
        req = _request_with_cookies({"better-auth.session_token": "devtok"})
        assert await bas.get_session_token_from_cookies(req) == "devtok"

    async def test_signed_cookie_strips_signature(self):
        req = _request_with_cookies({"better-auth.session_token": "base.signaturepart"})
        assert await bas.get_session_token_from_cookies(req) == "base"

    async def test_no_cookie_returns_none(self):
        req = _request_with_cookies({"unrelated": "x"})
        assert await bas.get_session_token_from_cookies(req) is None


@pytest.mark.asyncio
class TestValidateBetterAuthSession:
    async def test_missing_token_returns_none(self):
        req = _request_with_cookies({})
        assert await bas.validate_better_auth_session(req) is None

    async def test_session_not_found_returns_none(self):
        req = _request_with_cookies({"better-auth.session_token": "tok"})
        coll = AsyncMock()
        coll.find_one.return_value = None
        with patch.object(bas, "get_collection", AsyncMock(return_value=coll)):
            assert await bas.validate_better_auth_session(req) is None

    async def test_valid_session_updates_activity(self):
        req = _request_with_cookies({"better-auth.session_token": "tok"})
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        coll = AsyncMock()
        coll.find_one.return_value = {"_id": "s1", "userId": "u1", "expiresAt": future}
        with patch.object(bas, "get_collection", AsyncMock(return_value=coll)):
            result = await bas.validate_better_auth_session(req)
        assert result["userId"] == "u1"
        coll.update_one.assert_awaited_once()

    async def test_expired_datetime_deletes_and_returns_none(self):
        req = _request_with_cookies({"better-auth.session_token": "tok"})
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        coll = AsyncMock()
        coll.find_one.return_value = {"_id": "s1", "userId": "u1", "expiresAt": past}
        with patch.object(bas, "get_collection", AsyncMock(return_value=coll)):
            assert await bas.validate_better_auth_session(req) is None
        coll.delete_one.assert_awaited_once()

    async def test_expired_iso_string(self):
        req = _request_with_cookies({"better-auth.session_token": "tok"})
        past_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
        coll = AsyncMock()
        coll.find_one.return_value = {"_id": "s1", "userId": "u1", "expiresAt": past_iso}
        with patch.object(bas, "get_collection", AsyncMock(return_value=coll)):
            assert await bas.validate_better_auth_session(req) is None

    async def test_expires_at_timestamp_number(self):
        req = _request_with_cookies({"better-auth.session_token": "tok"})
        future_ts = (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        coll = AsyncMock()
        coll.find_one.return_value = {"_id": "s1", "userId": "u1", "expiresAt": future_ts}
        with patch.object(bas, "get_collection", AsyncMock(return_value=coll)):
            result = await bas.validate_better_auth_session(req)
        assert result["userId"] == "u1"

    async def test_invalid_expires_at_format_returns_none(self):
        req = _request_with_cookies({"better-auth.session_token": "tok"})
        coll = AsyncMock()
        coll.find_one.return_value = {"_id": "s1", "userId": "u1", "expiresAt": object()}
        with patch.object(bas, "get_collection", AsyncMock(return_value=coll)):
            assert await bas.validate_better_auth_session(req) is None

    async def test_naive_datetime_treated_as_utc(self):
        req = _request_with_cookies({"better-auth.session_token": "tok"})
        naive_future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
        coll = AsyncMock()
        coll.find_one.return_value = {"_id": "s1", "userId": "u1", "expiresAt": naive_future}
        with patch.object(bas, "get_collection", AsyncMock(return_value=coll)):
            result = await bas.validate_better_auth_session(req)
        assert result["userId"] == "u1"

    async def test_no_expires_at_still_valid(self):
        req = _request_with_cookies({"better-auth.session_token": "tok"})
        coll = AsyncMock()
        coll.find_one.return_value = {"_id": "s1", "userId": "u1"}
        with patch.object(bas, "get_collection", AsyncMock(return_value=coll)):
            result = await bas.validate_better_auth_session(req)
        assert result["userId"] == "u1"

    async def test_db_exception_returns_none(self):
        req = _request_with_cookies({"better-auth.session_token": "tok"})
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
