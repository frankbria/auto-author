"""OpenAI 429 ``insufficient_quota`` is a billing outage, not a rate limit (#775).

Staging's real-auth E2E showed "AI service rate limit exceeded" on every run for
12 days with no code change: a 429 that no amount of waiting fixes. Only the
OpenAI wire is stubbed here; the retry loop and error mapping are real.
"""
import httpx
import openai
import pytest

from app.services.ai_errors import (
    AIProviderQuotaError,
    AIRateLimitError,
    AIServiceUnavailableError,
)
from app.services.ai_service import AIService
from tests.test_services.openai_autospec import autospec_openai_client


def _openai_429(code: str) -> openai.RateLimitError:
    """The error the SDK raises for a 429, with the body OpenAI actually sends."""
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    body = {"message": f"stub {code}", "type": code, "param": None, "code": code}
    return openai.RateLimitError(
        f"Error code: 429 - {code}",
        response=httpx.Response(429, request=request),
        body=body,
    )


def _service(error: openai.RateLimitError) -> AIService:
    svc = AIService()
    svc.base_delay = 0  # keep the real retry loop, skip its sleeps
    svc.client = autospec_openai_client()
    svc.client.chat.completions.create.side_effect = error
    return svc


@pytest.mark.asyncio
async def test_insufficient_quota_is_a_non_retryable_outage():
    svc = _service(_openai_429("insufficient_quota"))

    with pytest.raises(AIProviderQuotaError) as exc:
        await svc.generate_clarifying_questions(summary="s" * 200, num_questions=3)

    err = exc.value
    assert err.error_code == "AI_PROVIDER_QUOTA_EXHAUSTED"
    assert err.retryable is False
    assert err.retry_after is None
    # Endpoints map AIServiceUnavailableError to 503: the user is not being
    # rate limited, the service is down until the operator adds credit.
    assert isinstance(err, AIServiceUnavailableError)
    assert "rate limit" not in err.message.lower()
    # Retrying a billing refusal only delays the error.
    assert svc.client.chat.completions.create.call_count == 1


@pytest.mark.asyncio
async def test_real_rate_limit_still_retries_and_maps_to_429_error():
    svc = _service(_openai_429("rate_limit_exceeded"))

    with pytest.raises(AIRateLimitError) as exc:
        await svc.generate_clarifying_questions(summary="s" * 200, num_questions=3)

    assert exc.value.error_code == "AI_RATE_LIMIT"
    assert svc.client.chat.completions.create.call_count == svc.max_retries
