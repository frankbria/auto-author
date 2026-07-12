"""Request-shape regression tests for the OpenAI boundary (issue #202).

Every AI method funnels through ``AIService._make_openai_request`` →
``client.chat.completions.create``. Before this issue, tests replaced the
client with bare ``Mock``s, so request-shape drift (a renamed/invalid kwarg)
sailed through green. These tests pin the boundary against the real SDK
signature via the autospec helper.
"""
import pytest

from app.services.ai_errors import AIServiceError
from app.services.ai_service import AIService
from tests.test_services.openai_autospec import autospec_openai_client


class TestAutospecHasTeeth:
    """Meta-tests: the helper must actually enforce the real SDK signature.

    Guards the failure mode where autospec silently degrades to a bare Mock
    (e.g. ``create_autospec(OpenAI)`` hitting cached_property) — the exact
    green-but-meaningless class this issue is about.
    """

    def test_unknown_kwarg_rejected(self):
        client = autospec_openai_client()
        with pytest.raises(TypeError):
            client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": "hi"}],
                temperature=0.3,
                max_tokens=10,
                bogus_kwarg=True,
            )

    def test_missing_required_kwarg_rejected(self):
        client = autospec_openai_client()
        with pytest.raises(TypeError):
            client.chat.completions.create(model="gpt-4")

    def test_production_kwargs_accepted(self):
        client = autospec_openai_client(content="ok")
        resp = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.3,
            max_tokens=10,
        )
        assert resp.choices[0].message.content == "ok"


class TestRequestShapeThroughService:
    @pytest.mark.asyncio
    async def test_make_openai_request_sends_valid_sdk_kwargs(self):
        """The single choke point sends exactly the pinned kwarg set, and the
        kwargs pass real-SDK signature validation."""
        svc = AIService()
        svc.client = autospec_openai_client(content="pong")

        resp = await svc._make_openai_request(
            messages=[{"role": "user", "content": "ping"}]
        )

        assert resp.choices[0].message.content == "pong"
        create = svc.client.chat.completions.create
        create.assert_called_once()
        assert set(create.call_args.kwargs) == {
            "model",
            "messages",
            "temperature",
            "max_tokens",
        }
        assert create.call_args.kwargs["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_generate_clarifying_questions_through_real_sdk_shape(self):
        """A full public method through the autospec boundary: the result is
        parsed AI content — asserting the AI path (not a fallback) was taken."""
        svc = AIService()
        svc.client = autospec_openai_client(
            content="1. Why write this book?\n2. Who reads it?"
        )

        questions = await svc.generate_clarifying_questions(
            "A unique request-shape summary for issue #202."
        )

        assert questions == ["Why write this book?", "Who reads it?"]
        svc.client.chat.completions.create.assert_called_once()


class TestUnparseableQuestionsRaise:
    @pytest.mark.asyncio
    async def test_unparseable_ai_output_raises_instead_of_canned_questions(self):
        """AI output with no extractable questions must surface as a retryable
        structured error, not 4 hard-coded questions masquerading as AI output
        (same class as the #48 TOC fix)."""
        svc = AIService()
        svc.client = autospec_openai_client(
            content="I cannot help with that request."
        )

        with pytest.raises(AIServiceError) as exc_info:
            await svc.generate_clarifying_questions(
                "Another unique summary for the unparseable case, issue #202."
            )

        assert exc_info.value.error_code == "AI_INVALID_RESPONSE"
        assert exc_info.value.retryable is True
