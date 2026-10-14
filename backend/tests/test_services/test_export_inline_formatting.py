"""Bold and italic are bold and italic in the PDF, DOCX and EPUB (#1030).

The builders were handed chapter text with Markdown's `**` and `_` around the
words the author had made bold or italic, and printed the markers. Text that
only looks like a marker (`__init__`, `2 * 3 * 4`) must still print as typed,
and the Markdown export keeps its markers: there they are the format.
"""

import re
import zipfile
from io import BytesIO

import pytest
from docx import Document

from app.services.export_service import export_service
from tests.test_services.test_export_service import _PDF_STREAM, _pdf_page_text

pytestmark = pytest.mark.asyncio

FORMATTED = "<p>Some <strong>bold</strong> and <em>italic</em> text.</p>"
LOOKALIKES = "<p>__init__ and 2 * 3 * 4 and snake_case_name</p>"
NESTED = "<h2>A <strong>bold</strong> heading</h2><ul><li><em>slanted</em> item</li></ul>"


def _book(content: str) -> dict:
    return {"title": "Inline", "table_of_contents": {"chapters": [
        {"id": "c1", "title": "Only", "content": content, "subchapters": []}
    ]}}


async def _export(content: str, fmt: str) -> bytes:
    return await export_service.export_book(_book(content), format=fmt)


async def _docx_paragraph(content: str, text: str):
    doc = Document(BytesIO(await _export(content, "docx")))
    return next(p for p in doc.paragraphs if p.text == text)


def _styled_runs(paragraph) -> list:
    return [(r.text, bool(r.bold), bool(r.italic)) for r in paragraph.runs if r.text]


async def _epub_chapter(content: str) -> str:
    with zipfile.ZipFile(BytesIO(await _export(content, "epub"))) as zf:
        return "".join(zf.read(n).decode() for n in zf.namelist() if n.endswith("html"))


async def _pdf_runs(content: str) -> list:
    """(base font, text) of every piece of text the PDF draws."""
    pdf = await _export(content, "pdf")
    assert _PDF_STREAM.search(pdf)
    fonts = dict((n.decode(), f.decode()) for f, n in re.findall(rb"/BaseFont /([\w-]+) /Encoding /\w+ /Name /(F\d+)", pdf))
    runs, font = [], None
    for token in re.finditer(rb"/(F\d+) [\d.]+ Tf|\(((?:\\.|[^\\)])*)\) Tj", _pdf_page_text(pdf)):
        if token.group(1):
            font = fonts[token.group(1).decode()]
        else:
            runs.append((font, token.group(2).decode("latin-1")))
    return runs


class TestBoldAndItalicAreSet:
    async def test_docx(self):
        paragraph = await _docx_paragraph(FORMATTED, "Some bold and italic text.")
        assert ("bold", True, False) in _styled_runs(paragraph)
        assert ("italic", False, True) in _styled_runs(paragraph)

    async def test_epub(self):
        assert "<p>Some <strong>bold</strong> and <em>italic</em> text.</p>" in await _epub_chapter(FORMATTED)

    async def test_pdf(self):
        runs = await _pdf_runs(FORMATTED)
        assert any(text == "bold" and "Bold" in font for font, text in runs), runs
        assert any(text == "italic" and ("Italic" in font or "Oblique" in font) for font, text in runs), runs
        assert not any("**" in text or "_italic_" in text for _, text in runs)


class TestTextThatOnlyLooksLikeAMarkerIsAsTyped:
    async def test_docx(self):
        paragraph = await _docx_paragraph(LOOKALIKES, "__init__ and 2 * 3 * 4 and snake_case_name")
        assert not any(bold or italic for _, bold, italic in _styled_runs(paragraph))

    async def test_epub(self):
        assert "<p>__init__ and 2 * 3 * 4 and snake_case_name</p>" in await _epub_chapter(LOOKALIKES)

    async def test_pdf(self):
        drawn = "".join(text for _, text in await _pdf_runs(LOOKALIKES))
        assert "__init__ and 2 * 3 * 4 and snake_case_name" in drawn


class TestInsideAHeadingAndAListItem:
    async def test_docx(self):
        heading = await _docx_paragraph(NESTED, "A bold heading")
        item = await _docx_paragraph(NESTED, "* slanted item")
        assert ("bold", True, False) in _styled_runs(heading)
        assert ("slanted", False, True) in _styled_runs(item)

    async def test_epub(self):
        chapter = await _epub_chapter(NESTED)
        assert "A <strong>bold</strong> heading" in chapter
        assert "<p>* <em>slanted</em> item</p>" in chapter


async def test_the_markdown_export_keeps_its_markers():
    markdown = (await _export(FORMATTED, "markdown")).decode()
    assert "Some **bold** and _italic_ text." in markdown


async def test_half_a_pair_is_dropped_rather_than_left_open():
    """A bold span cut by a paragraph break leaves half a pair in each block;
    an unclosed <b> would stop ReportLab and break the EPUB's XHTML."""
    from app.services import inline_marks

    on, off = inline_marks.BOLD
    assert inline_marks.as_tags(f"one {on}half", ("<b>", "</b>"), ("<i>", "</i>")) == "one half"
    assert inline_marks.as_tags(f"{on}whole{off}", ("<b>", "</b>"), ("<i>", "</i>")) == "<b>whole</b>"
