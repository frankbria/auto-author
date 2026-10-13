"""Session cookies for tests that drive the real session path (#795).

The backend only accepts a cookie signed with BETTER_AUTH_SECRET, so a test
that sends one has to sign it. This mirrors the production check, which means
it cannot catch a wrong algorithm; ``test_better_auth_session.py`` holds
cookies signed by the real library for that.
"""

import base64
import hashlib
import hmac
from unittest.mock import AsyncMock, Mock
from urllib.parse import quote

from app.core.config import settings


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
