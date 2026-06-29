"""Tests for AIService.enhance_transcription (issue #56)."""
import pytest
from unittest.mock import Mock, patch
from app.services.ai_service import AIService
from openai import OpenAI


class TestAIServiceTranscriptionEnhancement:
    @pytest.fixture
    def mock_openai_client(self):
        mock_client = Mock(spec=OpenAI)
        mock_completion = Mock()
        mock_completion.choices = [
            Mock(
                message=Mock(content="The cat sat on the mat."),
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
    async def test_cleanup_success(self, ai_service):
        result = await ai_service.enhance_transcription(
            content="um so the cat you know sat on the mat"
        )
        assert result["success"] is True
        assert result["enhanced"] == "The cat sat on the mat."
        assert result["metadata"]["enhancement_type"] == "transcription"
        assert result["metadata"]["enhancement_label"] == "Dictation Cleanup"
        assert result["metadata"]["original_word_count"] == 10
        assert result["metadata"]["enhanced_word_count"] > 0

        # Conservative temperature — cleanup must not invent content.
        call_args = ai_service.client.chat.completions.create.call_args
        assert call_args[1]["temperature"] == 0.3

    @pytest.mark.asyncio
    async def test_empty_content_rejected_without_calling_openai(self, ai_service):
        result = await ai_service.enhance_transcription(content="   ")
        assert result["success"] is False
        assert "required" in result["error"].lower()
        ai_service.client.chat.completions.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_openai_error_handled(self, ai_service):
        ai_service.client.chat.completions.create.side_effect = Exception("OpenAI down")
        result = await ai_service.enhance_transcription(content="um hello")
        assert result["success"] is False
        assert "OpenAI down" in result["error"]
        assert result["enhanced"] == ""

    @pytest.mark.asyncio
    async def test_truncated_output_is_rejected_not_saved(self, ai_service):
        """A length-truncated cleanup must fail, not silently overwrite the chapter."""
        ai_service.client.chat.completions.create.return_value.choices[0].finish_reason = "length"
        result = await ai_service.enhance_transcription(content="a very long dictation ...")
        assert result["success"] is False
        assert "too long" in result["error"].lower()
        assert result["enhanced"] == ""
