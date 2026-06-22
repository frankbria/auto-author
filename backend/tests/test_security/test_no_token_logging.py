"""
Security guard test: session validation must never log token material.

Regression guard for issue #86. The session-validation path previously logged
full session tokens (and entire session documents) at INFO level. This test
asserts that a known token passed via cookie never appears in captured logs.
"""

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core import better_auth_session


@pytest.mark.asyncio
async def test_session_token_not_logged(caplog):
    """A session token in the cookie must not leak into any log record."""
    token = "SECRETSESSIONTOKEN0123456789ABCDEF"
    request = SimpleNamespace(
        cookies={"better-auth.session_token": token}
    )

    # No matching session -> function returns None after a token-free warning.
    collection = SimpleNamespace(find_one=AsyncMock(return_value=None))

    with patch.object(
        better_auth_session, "get_collection", AsyncMock(return_value=collection)
    ):
        with caplog.at_level(logging.DEBUG, logger=better_auth_session.__name__):
            result = await better_auth_session.validate_better_auth_session(request)

    assert result is None
    assert token not in caplog.text
