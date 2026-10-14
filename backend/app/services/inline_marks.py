"""Bold and italic as the PDF, DOCX and EPUB builders receive them (#1030).

The builders used to be handed Markdown's `**` and `_` and printed them. They
now get private-use characters around a bold or italic span: nothing the
author types can be one (they are removed from chapter text first), so `**`
and `__init__` typed in a chapter stay text. Each builder turns the marks
into its own formatting.
"""

import re

BOLD = ("", "")
ITALIC = ("", "")
_ALL = BOLD + ITALIC
_ANY = re.compile("[" + "".join(_ALL) + "]")


def without_marks(text: str) -> str:
    return _ANY.sub("", text)


def inline(marks):
    """A markdownify converter for <b>/<strong> or <em>/<i> that writes `marks`,
    keeping markdownify's own handling of the spaces at either end."""
    from markdownify import chomp

    on, off = marks

    def convert(self, el, text, parent_tags):
        if "_noformat" in parent_tags:  # inside code: as typed
            return text
        prefix, suffix, text = chomp(text)
        return f"{prefix}{on}{text}{off}{suffix}" if text else ""

    return convert


def _balanced(text: str) -> str:
    # A span cut by a paragraph break leaves half a pair in each block: drop
    # that kind of mark from the block rather than hand a builder open tags.
    for on, off in (BOLD, ITALIC):
        if text.count(on) != text.count(off):
            text = text.replace(on, "").replace(off, "")
    return text


def as_tags(escaped: str, bold: tuple, italic: tuple) -> str:
    """Escaped text with the marks as markup: ("<b>", "</b>") for ReportLab,
    ("<strong>", "</strong>") for XHTML."""
    text = _balanced(escaped)
    for (on, off), (start, end) in ((BOLD, bold), (ITALIC, italic)):
        text = text.replace(on, start).replace(off, end)
    return text


def add_runs(paragraph, text: str) -> None:
    """The text as python-docx runs, bold and italic where the marks say."""
    bold = italic = False
    for piece in re.split(f"({_ANY.pattern})", _balanced(text)):
        if piece in BOLD:
            bold = piece == BOLD[0]
        elif piece in ITALIC:
            italic = piece == ITALIC[0]
        elif piece:
            run = paragraph.add_run(piece)
            run.bold, run.italic = bold or None, italic or None
