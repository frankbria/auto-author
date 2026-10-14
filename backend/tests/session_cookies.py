"""Session cookies for tests that drive the real session path (#795).

The backend only accepts a cookie signed with BETTER_AUTH_SECRET, so a test
that sends one has to sign it. This mirrors the production check, which means
it cannot catch a wrong algorithm; ``test_better_auth_session.py`` holds
cookies signed by the real library for that.
"""

import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock
from urllib.parse import quote

from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.db.base import get_collection


def signed_session_cookie(token: str) -> str:
    """``token`` as better-call would set it: url-encoded "<token>.<signature>"."""
    signature = base64.b64encode(
        hmac.new(settings.BETTER_AUTH_SECRET.encode(), token.encode(), hashlib.sha256).digest()
    ).decode()
    return quote(f"{token}.{signature}", safe="")


def session_collection(found=None, error=None) -> AsyncMock:
    """A stand-in for the session collection as the lookup reads it (#826): one
    joined read, which answers ``found`` or raises ``error``."""
    answer = AsyncMock(side_effect=error) if error else AsyncMock(return_value=[found] if found else [])
    collection = AsyncMock()
    collection.aggregate = Mock(return_value=Mock(to_list=answer))
    return collection


async def mint_session(user_oid: ObjectId, expires_in: timedelta = timedelta(days=7)) -> str:
    """A session document as better-auth's MongoDB adapter writes one; returns its token."""
    token = f"tok-{ObjectId()}"
    now = datetime.now(timezone.utc)
    await (await get_collection("session")).insert_one(
        {
            "token": token,
            "userId": user_oid,
            "expiresAt": now + expires_in,
            "createdAt": now,
            "updatedAt": now,
        }
    )
    return token


def real_session_client(token: str) -> AsyncClient:
    """A client that carries the signed cookie for ``token``, with no dependency overridden."""
    from app.main import app

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies={"better-auth.session_token": signed_session_cookie(token)},
    )
