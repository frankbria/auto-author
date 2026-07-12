"""Tests for AIService.transform_text_style (issue #58).

The OpenAI boundary uses the autospec helper (issue #202) so every
``chat.completions.create`` call is validated against the real SDK signature
instead of a bare Mock that accepts anything.
"""
import pytest
from app.services.ai_service import AIService
from tests.test_services.openai_autospec import autospec_openai_client


class TestAIServiceStyleTransformation:
    @pytest.fixture
    def ai_service(self):
        service = AIService()
        service.client = autospec_openai_client(
            content="The rewritten text in the requested style."
        )
        return service

    @pytest.mark.asyncio
    async def test_transform_success(self, ai_service):
        result = await ai_service.transform_text_style(
            content="The cat sat on the mat.", target_style="professional"
        )
        assert result["success"] is True
        assert result["transformed"] == "The rewritten text in the requested style."
        assert result["metadata"]["target_style"] == "professional"
        assert result["metadata"]["style_label"] == "Professional"
        assert result["metadata"]["original_word_count"] == 6
        assert result["metadata"]["transformed_word_count"] > 0

        # temperature tuned for rewriting
        call_args = ai_service.client.chat.completions.create.call_args
        assert call_args[1]["temperature"] == 0.7

    @pytest.mark.asyncio
    async def test_empty_content_rejected_without_calling_openai(self, ai_service):
        result = await ai_service.transform_text_style(content="   ", target_style="academic")
        assert result["success"] is False
        assert "required" in result["error"].lower()
        ai_service.client.chat.completions.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_style_rejected_without_calling_openai(self, ai_service):
        result = await ai_service.transform_text_style(content="Hello.", target_style="bogus")
        assert result["success"] is False
        assert "unsupported" in result["error"].lower()
        ai_service.client.chat.completions.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_openai_error_handled(self, ai_service):
        ai_service.client.chat.completions.create.side_effect = Exception("OpenAI down")
        result = await ai_service.transform_text_style(content="Hello.", target_style="creative")
        assert result["success"] is False
        assert "OpenAI down" in result["error"]
        assert result["transformed"] == ""

    @pytest.mark.asyncio
    async def test_truncated_output_is_rejected_not_saved(self, ai_service):
        """A length-truncated rewrite must fail, not silently overwrite the chapter."""
        ai_service.client = autospec_openai_client(
            content="The rewritten text in the requested style.",
            finish_reason="length",
        )
        result = await ai_service.transform_text_style(
            content="A very long chapter...", target_style="professional"
        )
        assert result["success"] is False
        assert "too long" in result["error"].lower()
        assert result["transformed"] == ""

    @pytest.mark.asyncio
    async def test_each_style_sends_distinct_prompt(self, ai_service):
        """Different target styles must send different prompts to the model."""
        sent_prompts = []
        for style in ["professional", "conversational", "academic", "creative", "technical"]:
            await ai_service.transform_text_style(content="Same source.", target_style=style)
            user_msg = ai_service.client.chat.completions.create.call_args[1]["messages"][-1]
            sent_prompts.append(user_msg["content"])
        assert len(set(sent_prompts)) == 5
