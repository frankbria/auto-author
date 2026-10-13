"""An EPUB 3 file from XHTML documents, with the standard library (#824).

It replaced ebooklib, which is AGPL-3.0-or-later. The format is a zip: a first
entry that names the media type, a pointer to the package document, the package
document (what the book is, which files it has, in what order), two tables of
contents (EPUB 3's and the older NCX that EPUB 2 readers use), and the book's
own documents, which the caller supplies as complete XHTML.
"""

import io
import re
import zipfile
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from xml.sax.saxutils import escape, quoteattr

# (label, the document it opens, the entries under it)
Entry = Tuple[str, str, list]

_XML = "<?xml version='1.0' encoding='utf-8'?>\n"
# What XML 1.0 allows nowhere, such as a form feed pasted from a PDF: one of these and no reader opens the file.
_NOT_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")
_CONTAINER = (
    _XML
    + '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">'
    '<rootfiles><rootfile media-type="application/oebps-package+xml" full-path="EPUB/content.opf"/></rootfiles>'
    "</container>"
)


def _package(identifier, title, language, author, description, subject, names: List[str]) -> str:
    optional = "".join(
        f"<dc:{tag}>{escape(value)}</dc:{tag}>"
        for tag, value in (("creator", author), ("description", description), ("subject", subject))
        if value
    )
    modified = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    items = "".join(
        f'<item id="doc_{i}" href={quoteattr(name)} media-type="application/xhtml+xml"/>' for i, name in enumerate(names)
    )
    # The contents page comes after the first document (the title page), as it always has.
    order = ["doc_0", "nav", *(f"doc_{i}" for i in range(1, len(names)))]
    return (
        _XML
        + '<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="id" version="3.0">'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f'<dc:identifier id="id">{escape(identifier)}</dc:identifier>'
        f"<dc:title>{escape(title)}</dc:title>"
        f"<dc:language>{escape(language)}</dc:language>"
        f"{optional}"
        f'<meta property="dcterms:modified">{modified}</meta>'
        "</metadata>"
        f"<manifest>{items}"
        '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
        "</manifest>"
        '<spine toc="ncx">' + "".join(f'<itemref idref="{ref}"/>' for ref in order) + "</spine>"
        "</package>"
    )


def _nav_list(entries: List[Entry]) -> str:
    if not entries:
        return ""
    return "<ol>" + "".join(
        f"<li><a href={quoteattr(href)}>{escape(label)}</a>{_nav_list(below)}</li>" for label, href, below in entries
    ) + "</ol>"


def _nav(title: str, language: str, toc: List[Entry]) -> str:
    return (
        _XML
        + "<!DOCTYPE html>\n"
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
        f"lang={quoteattr(language)} xml:lang={quoteattr(language)}>"
        f"<head><title>{escape(title)}</title></head>"
        f'<body><nav epub:type="toc" id="toc" role="doc-toc"><h2>{escape(title)}</h2>{_nav_list(toc)}</nav></body>'
        "</html>"
    )


def _ncx(identifier: str, title: str, toc: List[Entry]) -> str:
    count = 0

    def points(entries: List[Entry]) -> str:
        nonlocal count
        written = []
        for label, href, below in entries:
            count += 1
            written.append(
                f'<navPoint id="nav_{count}" playOrder="{count}"><navLabel><text>{escape(label)}</text></navLabel>'
                f"<content src={quoteattr(href)}/>{points(below)}</navPoint>"
            )
        return "".join(written)

    return (
        _XML
        + '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
        f"<head><meta name=\"dtb:uid\" content={quoteattr(identifier)}/></head>"
        f"<docTitle><text>{escape(title)}</text></docTitle>"
        f"<navMap>{points(toc)}</navMap>"
        "</ncx>"
    )


def write_epub(
    *,
    identifier: str,
    title: str,
    documents: List[Tuple[str, str]],
    toc: List[Entry],
    author: Optional[str] = None,
    description: Optional[str] = None,
    subject: Optional[str] = None,
    language: str = "en",
) -> bytes:
    """The bytes of an EPUB 3 file.

    ``documents`` are (file name, complete XHTML) in reading order; ``toc`` is
    the table of contents as nested (label, file name, entries under it).
    """
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as book:
        # First, and not compressed: a reader identifies the file by these
        # bytes at a fixed offset, before it can read the zip's directory.
        book.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        files = [
            ("META-INF/container.xml", _CONTAINER),
            ("EPUB/content.opf", _package(identifier, title, language, author, description, subject, [name for name, _ in documents])),
            ("EPUB/nav.xhtml", _nav(title, language, toc)),
            ("EPUB/toc.ncx", _ncx(identifier, title, toc)),
            *((f"EPUB/{name}", xhtml) for name, xhtml in documents),
        ]
        for name, xml in files:
            book.writestr(name, _NOT_XML.sub("", xml))
    return output.getvalue()
