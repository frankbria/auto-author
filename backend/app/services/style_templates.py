"""
Writing-style transformation templates (issue #58).

Five styles documented in AUTO_AUTHOR_USER_MANUAL.md. Each carries distinct
tone / vocabulary / structure guidance so the same source text transforms into
clearly different output. Every prompt explicitly preserves facts and meaning.
"""
from typing import Dict, List

# value -> human label (mirrors the frontend WRITING_STYLES from #55)
STYLE_LABELS: Dict[str, str] = {
    "professional": "Professional",
    "conversational": "Conversational",
    "academic": "Academic",
    "creative": "Creative",
    "technical": "Technical",
}

# value -> distinct guidance block injected into the transformation prompt
STYLE_GUIDANCE: Dict[str, str] = {
    "professional": (
        "Formal business tone. Clear, direct statements and active voice. "
        "Polished, industry-appropriate vocabulary; no slang or contractions. "
        "Confident and concise; structured paragraphs."
    ),
    "conversational": (
        "Friendly, approachable, and warm — like talking to a friend. "
        "Use contractions, second person ('you'), and everyday vocabulary. "
        "Short, easy sentences and the occasional rhetorical question."
    ),
    "academic": (
        "Scholarly and precise. Measured, objective tone with careful "
        "qualifications. Formal vocabulary, complex sentence structure, and "
        "an analytical, evidence-oriented framing. Avoid casual phrasing."
    ),
    "creative": (
        "Vivid and expressive. Use imagery, metaphor, varied rhythm, and "
        "sensory detail to engage the reader. Evocative word choice while "
        "keeping the underlying information intact."
    ),
    "technical": (
        "Precise and instructional. Unambiguous terminology, step-oriented "
        "structure, and concrete specifics. Neutral tone; avoid subjective "
        "or emotive language. Favor clarity over flourish."
    ),
}


def available_styles() -> List[str]:
    """Return the supported style values."""
    return list(STYLE_LABELS.keys())


def is_valid_style(style: str) -> bool:
    """True if `style` is a supported writing style."""
    return style in STYLE_LABELS


def get_style_transformation_prompt(content: str, target_style: str) -> str:
    """
    Build the prompt that rewrites `content` into `target_style`.

    Raises ValueError if the style is unsupported.
    """
    if not is_valid_style(target_style):
        raise ValueError(f"Unsupported writing style: {target_style!r}")

    label = STYLE_LABELS[target_style]
    guidance = STYLE_GUIDANCE[target_style]

    return f"""Rewrite the following text in a {label} writing style.

{label} style guidance:
{guidance}

Critical requirements:
- Preserve ALL facts, names, numbers, and the original meaning exactly.
- Do not add new information or remove any substantive point.
- Only change tone, vocabulary, phrasing, and sentence structure.
- Keep a similar overall length and any existing structure (headings, lists).
- Return only the rewritten text, with no preamble or commentary.

Text to rewrite:
{content}
"""
