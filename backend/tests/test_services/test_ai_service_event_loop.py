"""Regression test for #175: OpenAI calls must run off the event loop.

`_make_openai_request` wraps a blocking OpenAI SDK call. If it runs the call
inline on the event loop, one in-flight generation freezes the whole worker.
These tests prove the blocking call is offloaded (via ``asyncio.to_thread``),
so a concurrent request is served while an AI call is in flight.
"""
import asyncio
import time

import pytest

from app.services.ai_service import AIService


@pytest.mark.asyncio
async def test_ai_call_does_not_block_event_loop(monkeypatch):
    """A concurrent coroutine makes progress while an AI call is in flight."""
    service = AIService()

    # Simulate a slow, blocking OpenAI HTTP call.
    def blocking_create(*args, **kwargs):
        time.sleep(0.3)
        return "ok"

    monkeypatch.setattr(service.client.chat.completions, "create", blocking_create)

    ticks = 0

    async def health_check():
        # If the loop is blocked by the AI call, this never advances.
        nonlocal ticks
        while True:
            ticks += 1
            await asyncio.sleep(0.02)

    ticker = asyncio.create_task(health_check())
    await service._make_openai_request(messages=[{"role": "user", "content": "hi"}])
    ticker.cancel()

    # ~15 ticks expected during a 0.3s off-loop call; require clear progress.
    assert ticks >= 5, f"event loop was blocked during AI call (ticks={ticks})"


@pytest.mark.asyncio
async def test_concurrent_ai_calls_run_in_parallel(monkeypatch):
    """Two AI calls overlap instead of serializing on the event loop."""
    service = AIService()

    def blocking_create(*args, **kwargs):
        time.sleep(0.3)
        return "ok"

    monkeypatch.setattr(service.client.chat.completions, "create", blocking_create)

    start = time.perf_counter()
    await asyncio.gather(
        service._make_openai_request(messages=[{"role": "user", "content": "a"}]),
        service._make_openai_request(messages=[{"role": "user", "content": "b"}]),
    )
    elapsed = time.perf_counter() - start

    # Serialized (inline) would be ~0.6s; parallel threads finish near ~0.3s.
    assert elapsed < 0.5, f"AI calls serialized on the loop (elapsed={elapsed:.2f}s)"
