"""TOC generation token budget and truncation handling (#774)."""
import json

import pytest

from app.services.ai_errors import AIServiceError
from app.services.ai_service import AIService
from tests.test_services.openai_autospec import autospec_openai_client


def _toc(chapters: int, subs: int) -> str:
    """Pretty-printed TOC JSON shaped like the production prompt asks for."""
    return json.dumps(
        {
            "chapters": [
                {
                    "id": f"ch{c}",
                    "title": f"Chapter {c}: A descriptive chapter title",
                    "description": "A brief description of what this chapter covers in detail.",
                    "level": 1,
                    "order": c,
                    "subchapters": [
                        {
                            "id": f"ch{c}-{s}",
                            "title": f"Subchapter {s} of chapter {c}",
                            "description": "A brief description of this subchapter.",
                            "level": 2,
                            "order": s,
                        }
                        for s in range(1, subs + 1)
                    ],
                }
                for c in range(1, chapters + 1)
            ],
            "total_chapters": chapters,
            "estimated_pages": 200,
            "structure_notes": "Organised from fundamentals to advanced topics.",
        },
        indent=2,
    )


RESPONSES = [{"question": "Q?", "answer": "A"}]


@pytest.mark.asyncio
async def test_truncated_toc_raises_non_retryable_distinct_code():
    svc = AIService()
    svc.client = autospec_openai_client(content=_toc(10, 3)[:900], finish_reason="length")

    with pytest.raises(AIServiceError) as exc:
        await svc.generate_toc_from_summary_and_responses("s" * 200, RESPONSES)

    assert exc.value.error_code == "AI_RESPONSE_TRUNCATED"
    assert exc.value.retryable is False
    # Non-retryable: must not burn quota on repeats.
    assert svc.client.chat.completions.create.call_count == 1


@pytest.mark.asyncio
async def test_realistic_10x3_toc_parses_within_budget():
    svc = AIService()
    svc.client = autospec_openai_client(content=_toc(10, 3))

    result = await svc.generate_toc_from_summary_and_responses("s" * 200, RESPONSES)

    assert result["chapters_count"] == 10
    sent = svc.client.chat.completions.create.call_args.kwargs["max_tokens"]
    # Measured: 8x3 ~2k tokens, 12x4 ~3.7k. ~3 chars/token is a conservative estimate.
    assert sent >= len(_toc(12, 4)) // 3
    # gpt-4's 8192 context is shared with the prompt; 6000 output needs gpt-4o.
    assert svc.client.chat.completions.create.call_args.kwargs["model"] == "gpt-4o"
