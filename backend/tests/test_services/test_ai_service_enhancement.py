"""Tests for AIService.enhance_text (issue #57)."""
import pytest
from unittest.mock import Mock, patch
from app.services.ai_service import AIService
from openai import OpenAI


class TestAIServiceEnhancement:
    @pytest.fixture
    def mock_openai_client(self):
        mock_client = Mock(spec=OpenAI)
        mock_completion = Mock()
        mock_completion.choices = [
            Mock(
                message=Mock(content="The improved text."),
                finish_reason="stop",
            )
        ]
        mock_client.chat.completions.create.return_value = mock_completion
        return mock_client

    @pytest.fixture
    def ai_service(self, mock_openai_client):
        with patch("app.services.ai_service.OpenAI", return_value=mock_openai_client):
            service = AIService()
            service.client = mock_openai_client
            return service

    @pytest.mark.asyncio
    async def test_enhance_success(self, ai_service):
        result = await ai_service.enhance_text(
            content="The cat sat on the mat.", enhancement_type="grammar"
        )
        assert result["success"] is True
        assert result["enhanced"] == "The improved text."
        assert result["metadata"]["enhancement_type"] == "grammar"
        assert result["metadata"]["enhancement_label"] == "Grammar"
        assert result["metadata"]["original_word_count"] == 6
        assert result["metadata"]["enhanced_word_count"] > 0

        # lower temperature than style transform — enhancement should be consistent
        call_args = ai_service.client.chat.completions.create.call_args
        assert call_args[1]["temperature"] == 0.3

    @pytest.mark.asyncio
    async def test_empty_content_rejected_without_calling_openai(self, ai_service):
        result = await ai_service.enhance_text(content="   ", enhancement_type="clarity")
        assert result["success"] is False
        assert "required" in result["error"].lower()
        ai_service.client.chat.completions.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_type_rejected_without_calling_openai(self, ai_service):
        result = await ai_service.enhance_text(content="Hello.", enhancement_type="bogus")
        assert result["success"] is False
        assert "unsupported" in result["error"].lower()
        ai_service.client.chat.completions.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_openai_error_handled(self, ai_service):
        ai_service.client.chat.completions.create.side_effect = Exception("OpenAI down")
        result = await ai_service.enhance_text(content="Hello.", enhancement_type="tone")
        assert result["success"] is False
        assert "OpenAI down" in result["error"]
        assert result["enhanced"] == ""

    @pytest.mark.asyncio
    async def test_truncated_output_is_rejected_not_saved(self, ai_service):
        """A length-truncated enhancement must fail, not silently overwrite the chapter."""
        ai_service.client.chat.completions.create.return_value.choices[0].finish_reason = "length"
        result = await ai_service.enhance_text(
            content="A very long chapter...", enhancement_type="vocabulary"
        )
        assert result["success"] is False
        assert "too long" in result["error"].lower()
        assert result["enhanced"] == ""

    @pytest.mark.asyncio
    async def test_each_type_sends_distinct_prompt(self, ai_service):
        """Different enhancement types must send different prompts to the model."""
        sent_prompts = []
        for t in ["clarity", "grammar", "tone", "vocabulary"]:
            await ai_service.enhance_text(content="Same source.", enhancement_type=t)
            user_msg = ai_service.client.chat.completions.create.call_args[1]["messages"][-1]
            sent_prompts.append(user_msg["content"])
        assert len(set(sent_prompts)) == 4
