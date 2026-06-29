"""
Content-enhancement templates (issue #57).

Improve existing chapter text along one of four dimensions. Each carries
distinct guidance so the same source text is enhanced in a clearly different
way. Every prompt explicitly preserves facts and meaning — enhancement
improves quality without changing what the text says.

Mirrors the writing-style transformation module (style_templates.py, #58).
"""
from typing import Dict, List

# value -> human label (mirrors the frontend ENHANCEMENT_TYPES)
ENHANCEMENT_LABELS: Dict[str, str] = {
    "clarity": "Clarity",
    "grammar": "Grammar",
    "tone": "Tone",
    "vocabulary": "Vocabulary",
}

# value -> distinct guidance block injected into the enhancement prompt
ENHANCEMENT_GUIDANCE: Dict[str, str] = {
    "clarity": (
        "Simplify complex sentences and remove redundancy. Improve logical "
        "flow so each idea leads naturally to the next. Prefer plain, direct "
        "phrasing over convoluted constructions. Keep the original meaning."
    ),
    "grammar": (
        "Fix grammatical errors, punctuation, and awkward sentence structure. "
        "Correct subject-verb agreement, tense, and articles. Preserve the "
        "author's voice and the original meaning; change only what is wrong."
    ),
    "tone": (
        "Improve engagement and readability by smoothing the tone and rhythm. "
        "Make the writing flow naturally and hold the reader's attention while "
        "preserving the core message and the author's intent."
    ),
    "vocabulary": (
        "Replace weak or repetitive words with stronger, more precise "
        "alternatives and add variety to word choice. Keep an appropriate "
        "reading level; avoid over-complication or obscure jargon."
    ),
}


def available_enhancements() -> List[str]:
    """Return the supported enhancement-type values."""
    return list(ENHANCEMENT_LABELS.keys())


def is_valid_enhancement(enhancement_type: str) -> bool:
    """True if `enhancement_type` is a supported enhancement."""
    return enhancement_type in ENHANCEMENT_LABELS


def get_enhancement_prompt(content: str, enhancement_type: str) -> str:
    """
    Build the prompt that enhances `content` along `enhancement_type`.

    Raises ValueError if the enhancement type is unsupported.
    """
    if not is_valid_enhancement(enhancement_type):
        raise ValueError(f"Unsupported enhancement type: {enhancement_type!r}")

    label = ENHANCEMENT_LABELS[enhancement_type]
    guidance = ENHANCEMENT_GUIDANCE[enhancement_type]

    return f"""Improve the following text for {label}.

{label} guidance:
{guidance}

Critical requirements:
- Preserve ALL facts, names, numbers, and the original meaning exactly.
- Do not add new information or remove any substantive point.
- Improve quality only; do not rewrite into a different topic or voice.
- Keep a similar overall length and any existing structure (headings, lists).
- Return only the improved text, with no preamble or commentary.

Text to improve:
{content}
"""
