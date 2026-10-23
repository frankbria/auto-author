"""Inline formatting as the PDF, DOCX and EPUB builders receive it (#1030, #1190).

The builders used to be handed Markdown's `**`, `_`, backticks and `[](...)`
and printed them. They now get private-use characters around a bold, italic,
code, strike-through, superscript or subscript span, and around a link, which
also carries its address: nothing the author types can be one (they are
removed from chapter text first), so `**`, `__init__` and `[not a link]` typed
in a chapter stay text. Each builder turns the marks into its own formatting.
"""

import html
import re
from urllib.parse import urlparse

from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import RGBColor

BOLD = ("\ue000", "\ue001")
ITALIC = ("\ue002", "\ue003")
CODE = ("\ue004", "\ue005")
STRIKE = ("\ue006", "\ue007")
SUP = ("\ue008", "\ue009")
SUB = ("\ue00a", "\ue00b")
PAIRS = {"bold": BOLD, "italic": ITALIC, "code": CODE, "strike": STRIKE, "sup": SUP, "sub": SUB}
_ALL = "".join(on + off for on, off in PAIRS.values())

# A link is LINK_ON address LINK_SEP text LINK_OFF, and never spans a line break.
LINK_ON, LINK_SEP, LINK_OFF = "\ue00c", "\ue00d", "\ue00e"
_LINK = re.compile(f"{LINK_ON}([^{LINK_SEP}]*){LINK_SEP}(.*?){LINK_OFF}")
_LINK_CHARS = re.compile(f"[{LINK_ON}{LINK_SEP}{LINK_OFF}]")
_ANY = re.compile(f"[{_ALL}{LINK_ON}{LINK_SEP}{LINK_OFF}]")
_LINK_SCHEMES = {"http", "https", "mailto"}


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


def code(self, el, text, parent_tags):
    """markdownify's converter for inline <code>. A code block (<pre><code>) is
    markdownify's own, and a mark nested inside code is as typed."""
    if "pre" in parent_tags:
        return text
    return inline(CODE)(self, el, text, parent_tags)


def link(self, el, text, parent_tags):
    """markdownify's converter for <a>. Only web and mail addresses become
    links; any other (a script, a path with no site) leaves its text."""
    if "_noformat" in parent_tags:
        return text
    from markdownify import chomp

    prefix, suffix, text = chomp(_LINK_CHARS.sub("", text))
    href = (el.get("href") or "").strip()
    if not text:
        return ""
    if urlparse(href).scheme.lower() not in _LINK_SCHEMES or re.search(r"[\s\x00-\x1f]", href):
        return f"{prefix}{text}{suffix}"
    return f"{prefix}{LINK_ON}{href}{LINK_SEP}{text}{LINK_OFF}{suffix}"


def _balanced(text: str) -> str:
    """Keep only the marks that pair up in order. A span cut by a paragraph
    break leaves half a pair in a block, and a close can come before an open:
    either would hand a builder a stray or unclosed tag (#1030)."""
    keep = set()
    for on, off in PAIRS.values():
        opened = []
        for i, ch in enumerate(text):
            if ch == on:
                opened.append(i)
            elif ch == off and opened:
                keep.update((opened.pop(), i))
    return "".join(ch for i, ch in enumerate(text) if ch not in _ALL or i in keep)


def as_tags(escaped: str, bold: tuple, italic: tuple, **others: tuple) -> str:
    """Escaped text with the marks as markup: ("<b>", "</b>") for ReportLab,
    ("<strong>", "</strong>") for XHTML. `others` names the tags for `code`,
    `strike`, `sup`, `sub` and `link`, whose start tag has `{}` where the
    address goes. A mark with no tag is dropped and its text kept."""
    link_start, link_end = others.pop("link", ("", ""))
    text = _LINK.sub(
        lambda m: link_start.format(html.escape(html.unescape(m.group(1)))) + m.group(2) + link_end if link_start else m.group(2),
        _balanced(escaped),
    )
    tags = {"bold": bold, "italic": italic, **others}
    for name, (on, off) in PAIRS.items():
        start, end = tags.get(name, ("", ""))
        text = text.replace(on, start).replace(off, end)
    return text


_TOKEN = re.compile(f"({LINK_ON}[^{LINK_SEP}]*{LINK_SEP}|{LINK_OFF}|[{_ALL}])")


def add_runs(paragraph, text: str) -> None:
    """The text as python-docx runs, formatted where the marks say."""
    depth = {mark: 0 for mark in _ALL}
    anchor = None
    for piece in _TOKEN.split(_balanced(text)):
        if not piece:
            continue
        if piece[0] == LINK_ON:
            anchor = _hyperlink(paragraph, piece[1:-1])
        elif piece == LINK_OFF:
            anchor = None
        elif piece in _ALL:
            depth[piece] += 1  # opens minus closes, so <b><strong>x</strong> y</b> stays bold
        else:
            run = paragraph.add_run(piece)

            def on(pair):
                return depth[pair[0]] > depth[pair[1]]

            run.bold = on(BOLD) or None
            run.italic = on(ITALIC) or None
            run.font.strike = on(STRIKE) or None
            if on(SUP):  # the two are one setting in python-docx: set only the one wanted
                run.font.superscript = True
            elif on(SUB):
                run.font.subscript = True
            if on(CODE):
                run.font.name = "Courier New"
            if anchor is not None:
                run.font.color.rgb = RGBColor(0x05, 0x63, 0xC1)
                run.font.underline = True
                anchor.append(run._r)


def _hyperlink(paragraph, address: str):
    """An empty w:hyperlink to `address` at the end of the paragraph. python-docx
    has no call for it; this is its oxml route."""
    anchor = OxmlElement("w:hyperlink")
    anchor.set(qn("r:id"), paragraph.part.relate_to(address, RELATIONSHIP_TYPE.HYPERLINK, is_external=True))
    paragraph._p.append(anchor)
    return anchor
