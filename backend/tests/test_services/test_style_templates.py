"""Unit tests for writing-style transformation templates (issue #58)."""
import pytest

from app.services.style_templates import (
    STYLE_LABELS,
    STYLE_GUIDANCE,
    available_styles,
    is_valid_style,
    get_style_transformation_prompt,
)

FIVE_STYLES = ["professional", "conversational", "academic", "creative", "technical"]


def test_exactly_the_five_documented_styles():
    assert sorted(available_styles()) == sorted(FIVE_STYLES)
    assert set(STYLE_LABELS) == set(FIVE_STYLES)
    assert set(STYLE_GUIDANCE) == set(FIVE_STYLES)


def test_is_valid_style():
    assert is_valid_style("academic") is True
    assert is_valid_style("inspirational") is False  # removed in #55
    assert is_valid_style("") is False


def test_prompt_includes_content_and_style_label():
    prompt = get_style_transformation_prompt("The cat sat.", "professional")
    assert "The cat sat." in prompt
    assert "Professional" in prompt
    assert "preserve" in prompt.lower()


def test_each_style_produces_a_distinct_prompt():
    """The whole point of #58: styles must differ. Guidance blocks are distinct."""
    prompts = {s: get_style_transformation_prompt("Same source text.", s) for s in FIVE_STYLES}
    # All five guidance blocks present and pairwise different.
    assert len(set(prompts.values())) == 5
    for style in FIVE_STYLES:
        assert STYLE_GUIDANCE[style] in prompts[style]


def test_invalid_style_raises():
    with pytest.raises(ValueError):
        get_style_transformation_prompt("text", "nonsense")
