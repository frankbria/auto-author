"""
Professional export templates for PDF/DOCX (issue #59).

A template is just a dict of layout settings (page size, margins, font, spacing,
running header/footer). Three are shipped: classic fiction, modern non-fiction,
academic. Callers resolve a template by id and optionally merge user overrides,
then hand the resulting dict to ExportService.

ponytail: a dict literal *is* the registry — no JSON files, no loader, no Pydantic
models, no separate service class. Validation is a couple of range checks where
bad input would actually break layout.
"""
from copy import deepcopy
from typing import Dict, List, Optional

# Named page sizes in inches (width, height). Resolved to points downstream.
PAGE_SIZES_INCHES: Dict[str, tuple] = {
    "6x9": (6.0, 9.0),        # standard trade-paperback trim
    "letter": (8.5, 11.0),
    "A4": (8.27, 11.69),
}

# Margin floor. POD services (KDP/IngramSpark) want >= 0.25"; our defaults are
# >= 0.6" inside so the gutter is safe. ponytail: a single floor, not per-page
# gutter math by page count.
MIN_MARGIN_INCHES = 0.25
MIN_FONT_SIZE = 8
MAX_FONT_SIZE = 18


TEMPLATES: Dict[str, Dict] = {
    "classic_fiction": {
        "id": "classic_fiction",
        "name": "Classic Fiction",
        "description": "Timeless 6×9 trade-paperback layout for novels and narrative non-fiction.",
        "category": "fiction",
        "best_for": "Novels, short-story collections, memoir",
        "page_size": "6x9",
        "margins": {"top": 0.75, "bottom": 0.75, "inside": 0.65, "outside": 0.6},
        "font": {"family": "serif", "pdf_font": "Times-Roman", "docx_font": "Garamond", "size": 11},
        "line_height": 1.3,
        "first_line_indent": 0.2,
        "header": {"left": "{book_title}", "right": "{author}"},
        "footer": {"center": "{page}"},
    },
    "modern_nonfiction": {
        "id": "modern_nonfiction",
        "name": "Modern Non-Fiction",
        "description": "Clean letter-size layout with generous spacing for business and how-to books.",
        "category": "non-fiction",
        "best_for": "Business, self-help, how-to, reference",
        "page_size": "letter",
        "margins": {"top": 1.0, "bottom": 1.0, "inside": 1.0, "outside": 1.0},
        "font": {"family": "sans", "pdf_font": "Helvetica", "docx_font": "Calibri", "size": 11},
        "line_height": 1.5,
        "first_line_indent": 0.25,
        "header": {"left": "{author}", "right": "{book_title}"},
        "footer": {"center": "{page}"},
    },
    "academic": {
        "id": "academic",
        "name": "Academic",
        "description": "Double-spaced A4 layout with wide margins for theses and scholarly work.",
        "category": "academic",
        "best_for": "Theses, dissertations, research papers",
        "page_size": "A4",
        "margins": {"top": 1.0, "bottom": 1.0, "inside": 1.25, "outside": 1.25},
        "font": {"family": "serif", "pdf_font": "Times-Roman", "docx_font": "Times New Roman", "size": 12},
        "line_height": 2.0,
        "first_line_indent": 0.5,
        "header": {"left": "{book_title}", "right": "{author}"},
        "footer": {"center": "{page}"},
    },
}

DEFAULT_TEMPLATE_ID = "classic_fiction"


def list_templates() -> List[Dict]:
    """Return all templates (full spec — the frontend uses this for preview)."""
    return [deepcopy(t) for t in TEMPLATES.values()]


def get_template(template_id: str) -> Dict:
    """Return one template by id. Raises KeyError if unknown."""
    if template_id not in TEMPLATES:
        raise KeyError(f"Unknown export template: {template_id}")
    return deepcopy(TEMPLATES[template_id])


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def resolve_template(
    template_id: Optional[str], custom_options: Optional[Dict] = None
) -> Optional[Dict]:
    """
    Resolve a template id into a full spec dict, merging optional user overrides.

    Returns None when template_id is falsy (caller falls back to legacy styling).
    Raises KeyError for an unknown id, ValueError for malformed custom_options.

    Recognised override keys (all optional):
      font_size (int), line_height (float), first_line_indent (float),
      margins ({top,bottom,inside,outside} in inches),
      header ({left,right}), footer ({center}).
    """
    if not template_id:
        return None

    template = get_template(template_id)
    if not custom_options:
        return template

    if not isinstance(custom_options, dict):
        raise ValueError("custom_options must be an object")

    if "font_size" in custom_options:
        template["font"]["size"] = int(
            _clamp(float(custom_options["font_size"]), MIN_FONT_SIZE, MAX_FONT_SIZE)
        )
    if "line_height" in custom_options:
        template["line_height"] = _clamp(float(custom_options["line_height"]), 1.0, 3.0)
    if "first_line_indent" in custom_options:
        template["first_line_indent"] = _clamp(
            float(custom_options["first_line_indent"]), 0.0, 1.0
        )
    if "margins" in custom_options:
        if not isinstance(custom_options["margins"], dict):
            raise ValueError("custom_options.margins must be an object")
        for side in ("top", "bottom", "inside", "outside"):
            if side in custom_options["margins"]:
                template["margins"][side] = _clamp(
                    float(custom_options["margins"][side]), MIN_MARGIN_INCHES, 2.0
                )
    for hf, keys in (("header", ("left", "right")), ("footer", ("center",))):
        if hf in custom_options:
            if not isinstance(custom_options[hf], dict):
                raise ValueError(f"custom_options.{hf} must be an object")
            for key in keys:
                if key in custom_options[hf]:
                    template[hf][key] = str(custom_options[hf][key])

    return template
