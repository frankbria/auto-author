"""Tests for the voice-transcription cleanup template (issue #56)."""
from app.services.transcription_enhancement import (
    TRANSCRIPTION_ENHANCEMENT_LABEL,
    get_transcription_enhancement_prompt,
)


def test_label_defined():
    assert TRANSCRIPTION_ENHANCEMENT_LABEL == "Dictation Cleanup"


def test_prompt_includes_content_and_cleanup_guidance():
    content = "um so the cat you know sat on the mat"
    prompt = get_transcription_enhancement_prompt(content)
    assert content in prompt
    # Covers the three AC outcomes: fillers, paragraphs, grammar/punctuation.
    lowered = prompt.lower()
    assert "filler" in lowered
    assert "paragraph" in lowered
    assert "punctuation" in lowered


def test_prompt_preserves_facts_instruction():
    prompt = get_transcription_enhancement_prompt("some text")
    assert "Preserve ALL facts" in prompt
    # Must not invent or paraphrase content.
    assert "do not paraphrase" in prompt.lower()
