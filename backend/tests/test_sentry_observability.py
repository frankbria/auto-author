"""Error-tracking wiring (issue #334).

Sentry is inert unless SENTRY_DSN is set. When set, unhandled 500s must reach
Sentry via the global exception handler (our handler catches every exception, so
the ASGI integration alone would never see them).
"""

import pytest
from unittest.mock import MagicMock

import sentry_sdk
from app.core.config import Settings, settings
from app.main import global_exception_handler


class TestSentryConfig:
    def test_sentry_dsn_defaults_empty(self, monkeypatch):
        """Unset DSN => empty string => Sentry stays inert (no new behavior)."""
        monkeypatch.delenv("SENTRY_DSN", raising=False)
        assert Settings(_env_file=None).SENTRY_DSN == ""

    def test_sentry_dsn_is_stripped(self):
        """A trailing newline from `$(cat secret)` must not break init silently."""
        s = Settings(_env_file=None, SENTRY_DSN="  https://k@o1.ingest.sentry.io/1 \n")
        assert s.SENTRY_DSN == "https://k@o1.ingest.sentry.io/1"


class TestGlobalHandlerSentryCapture:
    @pytest.mark.asyncio
    async def test_captures_to_sentry_when_dsn_set(self, monkeypatch):
        monkeypatch.setattr(settings, "SENTRY_DSN", "https://k@o1.ingest.sentry.io/1", raising=False)
        captured = {}
        monkeypatch.setattr(sentry_sdk, "capture_exception", lambda e: captured.setdefault("exc", e))

        exc = ValueError("boom")
        resp = await global_exception_handler(MagicMock(), exc)

        assert resp.status_code == 500
        assert captured.get("exc") is exc

    @pytest.mark.asyncio
    async def test_no_capture_when_dsn_unset(self, monkeypatch):
        monkeypatch.setattr(settings, "SENTRY_DSN", "", raising=False)
        calls = []
        monkeypatch.setattr(sentry_sdk, "capture_exception", lambda e: calls.append(e))

        resp = await global_exception_handler(MagicMock(), ValueError("boom"))

        assert resp.status_code == 500
        assert calls == []
