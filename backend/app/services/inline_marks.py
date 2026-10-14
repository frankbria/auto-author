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
    """Keep only the marks that pair up in order. A span cut by a paragraph
    break leaves half a pair in a block, and a close can come before an open:
    either would hand a builder a stray or unclosed tag (#1030)."""
    keep = set()
    for on, off in (BOLD, ITALIC):
        opened = []
        for i, ch in enumerate(text):
            if ch == on:
                opened.append(i)
            elif ch == off and opened:
                keep.update((opened.pop(), i))
    return "".join(ch for i, ch in enumerate(text) if ch not in _ALL or i in keep)


def as_tags(escaped: str, bold: tuple, italic: tuple) -> str:
    """Escaped text with the marks as markup: ("<b>", "</b>") for ReportLab,
    ("<strong>", "</strong>") for XHTML."""
    text = _balanced(escaped)
    for (on, off), (start, end) in ((BOLD, bold), (ITALIC, italic)):
        text = text.replace(on, start).replace(off, end)
    return text


def add_runs(paragraph, text: str) -> None:
    """The text as python-docx runs, bold and italic where the marks say."""
    depth = {mark: 0 for mark in _ALL}
    for piece in re.split(f"({_ANY.pattern})", _balanced(text)):
        if piece in _ALL:
            depth[piece] += 1  # opens minus closes, so <b><strong>x</strong> y</b> stays bold
        elif piece:
            run = paragraph.add_run(piece)
            run.bold = (depth[BOLD[0]] > depth[BOLD[1]]) or None
            run.italic = (depth[ITALIC[0]] > depth[ITALIC[1]]) or None
