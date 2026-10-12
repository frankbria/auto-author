"""AI requests have a time budget, and a refused credential is an outage (#799).

The client was built with no timeout, so the SDK's 600 seconds applied: with
three attempts a stalled provider could hold a worker thread for half an hour,
on the executor that also runs uploads and payments. And a provider that
rejects the API key was retried, then reported as an unexpected error.

The timeout test talks to a real socket that accepts and never answers. Only
the provider is fake; the SDK, its HTTP client and the retry loop are real.
"""

import logging
import socket
import threading
import time

import httpx
import openai
import pytest

from app.core.config import Settings, settings
from app.services.ai_errors import (
    AINetworkError,
    AIProviderAuthError,
    AIProviderQuotaError,
    AIServiceUnavailableError,
)
from app.services.ai_service import AIService
from tests.test_services.openai_autospec import autospec_openai_client


@pytest.fixture
def silent_provider():
    """A server that accepts connections and never sends a byte."""
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()
    held = []
    stop = threading.Event()

    def accept():
        server.settimeout(0.1)
        while not stop.is_set():
            try:
                held.append(server.accept()[0])
            except OSError:
                continue

    thread = threading.Thread(target=accept, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.getsockname()[1]}/v1"
    stop.set()
    thread.join()
    for connection in held:
        connection.close()
    server.close()


@pytest.mark.asyncio
async def test_a_provider_that_never_answers_fails_within_the_budget(silent_provider, monkeypatch):
    monkeypatch.setattr(settings, "AI_BASE_URL", silent_provider)
    monkeypatch.setattr(settings, "AI_API_KEY", "stub")
    monkeypatch.setattr(settings, "AI_REQUEST_TIMEOUT_SECONDS", 0.5)
    monkeypatch.setattr(settings, "AI_MAX_RETRIES", 2)
    service = AIService()
    service.base_delay = 0  # keep the real retry loop, skip its sleeps

    started = time.monotonic()
    with pytest.raises(AINetworkError):
        await service.generate_clarifying_questions(summary="s" * 200, num_questions=3)
    elapsed = time.monotonic() - started

    # Two attempts of half a second each. Without a timeout this would sit for
    # the SDK's ten minutes per attempt.
    assert 0.9 <= elapsed < 5, elapsed


def test_the_timeout_is_a_setting_with_a_sane_default(monkeypatch):
    assert Settings.model_fields["AI_REQUEST_TIMEOUT_SECONDS"].default == 120
    assert AIService().client.timeout == settings.AI_REQUEST_TIMEOUT_SECONDS

    monkeypatch.setattr(settings, "AI_REQUEST_TIMEOUT_SECONDS", 7)
    assert AIService().client.timeout == 7


def _status_error(cls, status: int, code: str):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    body = {"message": f"stub {code}", "type": code, "param": None, "code": code}
    return cls(f"Error code: {status} - {code}", response=httpx.Response(status, request=request), body=body)


def _service(error: Exception) -> AIService:
    service = AIService()
    service.base_delay = 0
    service.client = autospec_openai_client()
    service.client.chat.completions.create.side_effect = error
    return service


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        _status_error(openai.AuthenticationError, 401, "invalid_api_key"),
        _status_error(openai.PermissionDeniedError, 403, "model_not_allowed"),
    ],
    ids=["rejected key", "key not allowed"],
)
async def test_a_refused_credential_is_an_outage_not_something_to_retry(error, caplog):
    service = _service(error)

    with caplog.at_level(logging.WARNING, logger="app.services.ai_service"):
        with pytest.raises(AIProviderAuthError) as raised:
            await service.generate_clarifying_questions(summary="s" * 200, num_questions=3)

    # One call: a rejected key is rejected again a second later.
    assert service.client.chat.completions.create.call_count == 1
    err = raised.value
    assert err.error_code == "AI_PROVIDER_AUTH_FAILED"
    assert err.retryable is False
    # Endpoints answer 503 for this class: the user did nothing wrong.
    assert isinstance(err, AIServiceUnavailableError)
    assert "key" not in err.message.lower()
    # CRITICAL, so it pages: every AI feature is down until an operator acts.
    assert [r.levelname for r in caplog.records if "credential" in r.getMessage()] == ["CRITICAL"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        _status_error(openai.RateLimitError, 429, "insufficient_quota"),
        _status_error(openai.APIStatusError, 402, "payment_required"),
    ],
    ids=["insufficient_quota", "402"],
)
async def test_a_billing_refusal_is_logged_critical(error, caplog):
    service = _service(error)

    with caplog.at_level(logging.WARNING, logger="app.services.ai_service"):
        with pytest.raises(AIProviderQuotaError):
            await service.generate_clarifying_questions(summary="s" * 200, num_questions=3)

    assert service.client.chat.completions.create.call_count == 1
    assert [r.levelname for r in caplog.records if "billing" in r.getMessage()] == ["CRITICAL"]
