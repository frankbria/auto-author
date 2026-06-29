"""Unit tests for content-enhancement templates (issue #57)."""
import pytest

from app.services.content_enhancement import (
    ENHANCEMENT_LABELS,
    ENHANCEMENT_GUIDANCE,
    available_enhancements,
    is_valid_enhancement,
    get_enhancement_prompt,
)

FOUR_TYPES = ["clarity", "grammar", "tone", "vocabulary"]


def test_exactly_the_four_documented_types():
    assert sorted(available_enhancements()) == sorted(FOUR_TYPES)
    assert set(ENHANCEMENT_LABELS) == set(FOUR_TYPES)
    assert set(ENHANCEMENT_GUIDANCE) == set(FOUR_TYPES)


def test_is_valid_enhancement():
    assert is_valid_enhancement("grammar") is True
    assert is_valid_enhancement("seo") is False
    assert is_valid_enhancement("") is False


def test_prompt_includes_content_and_label():
    prompt = get_enhancement_prompt("The cat sat.", "clarity")
    assert "The cat sat." in prompt
    assert "Clarity" in prompt
    assert "preserve" in prompt.lower()


def test_each_type_produces_a_distinct_prompt():
    """The four enhancement types must differ — distinct guidance blocks."""
    prompts = {t: get_enhancement_prompt("Same source text.", t) for t in FOUR_TYPES}
    assert len(set(prompts.values())) == 4
    for t in FOUR_TYPES:
        assert ENHANCEMENT_GUIDANCE[t] in prompts[t]


def test_invalid_type_raises():
    with pytest.raises(ValueError):
        get_enhancement_prompt("text", "nonsense")
