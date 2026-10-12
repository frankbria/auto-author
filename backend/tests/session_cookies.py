"""Session cookies for tests that drive the real session path (#795).

The backend only accepts a cookie signed with BETTER_AUTH_SECRET, so a test
that sends one has to sign it. This mirrors the production check, which means
it cannot catch a wrong algorithm; ``test_better_auth_session.py`` holds
cookies signed by the real library for that.
"""

import base64
import hashlib
import hmac
from urllib.parse import quote

from app.core.config import settings


def signed_session_cookie(token: str) -> str:
    """``token`` as better-call would set it: url-encoded "<token>.<signature>"."""
    signature = base64.b64encode(
        hmac.new(settings.BETTER_AUTH_SECRET.encode(), token.encode(), hashlib.sha256).digest()
    ).decode()
    return quote(f"{token}.{signature}", safe="")
