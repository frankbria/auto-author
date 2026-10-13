"""EPUB export without ebooklib (#824).

ebooklib is AGPL-3.0-or-later and wrote every EPUB this MIT-licensed repository
exports. The file format is a zip with a fixed first entry and four small XML
files around the book's own documents, so the standard library writes it now.

These check the container the way a reading system reads it: from the first
entry, to the package document, to everything that names. epubcheck, the
format's own validator, is run on the result in the demo.
"""

import re
import zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree

import pytest

import app.services.export_service as export_service_module
from app.services.epub_writer import write_epub

OPF = "{http://www.idpf.org/2007/opf}"
DC = "{http://purl.org/dc/elements/1.1/}"
XHTML = "{http://www.w3.org/1999/xhtml}"
NCX = "{http://www.daisy.org/z3986/2005/ncx/}"
CONTAINER = "{urn:oasis:names:tc:opendocument:xmlns:container}"

# A title that is not safe to paste into XML or an attribute.
AWKWARD = 'Tom & Jerry: A <Study> of "cats"'


def _page(title: str, body: str) -> str:
    return (
        "<?xml version='1.0' encoding='utf-8'?>\n<!DOCTYPE html>\n"
        f'<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en"><head><title>{title}</title></head>'
        f"<body>{body}</body></html>"
    )


def _book(**changes) -> zipfile.ZipFile:
    given = dict(
        identifier="book-824",
        title=AWKWARD,
        author="A. Writer",
        description="About cats & mice.",
        subject="Non-fiction",
        documents=[
            ("title.xhtml", _page("Title", "<h1>Title</h1>")),
            ("chap_1.xhtml", _page("One", "<h1>One</h1><p>Text.</p>")),
            ("chap_3.xhtml", _page("Two", "<h1>Two</h1><h2>2.1</h2>")),
            ("chap_4.xhtml", _page("2.2", "<h2>2.2</h2>")),
        ],
        toc=[
            ("Title Page", "title.xhtml", []),
            ("Chapter 1: One", "chap_1.xhtml", []),
            ("Chapter 2: Part <Two>", "chap_3.xhtml", [
                ("2.1 First & foremost", "chap_3.xhtml", [("2.1.1 A detail", "chap_3.xhtml", [])]),
                ("2.2 Second", "chap_4.xhtml", []),
            ]),
        ],
    )
    given.update(changes)
    return zipfile.ZipFile(BytesIO(write_epub(**given)))


def _package(book: zipfile.ZipFile):
    """The package document, found the way a reading system finds it, and the folder it is in."""
    container = ElementTree.fromstring(book.read("META-INF/container.xml"))
    path = container.find(f"{CONTAINER}rootfiles/{CONTAINER}rootfile").get("full-path")
    return ElementTree.fromstring(book.read(path)), path.rsplit("/", 1)[0] + "/"


def _nested_labels(element, item, label, below):
    """[(label, [those under it])] for a navigation list in either of its two formats."""
    return [(label(i), _nested_labels(below(i), item, label, below) if below(i) is not None else []) for i in element.findall(item)]


def test_the_first_entry_is_the_media_type_and_is_not_compressed():
    """A reading system identifies the file by these bytes at a fixed offset."""
    first = _book().infolist()[0]

    assert first.filename == "mimetype"
    assert first.compress_type == zipfile.ZIP_STORED
    assert first.extra == b""
    assert _book().read("mimetype") == b"application/epub+zip"


def test_everything_the_package_names_is_in_the_file_and_everything_in_the_file_is_named():
    book = _book()
    package, folder = _package(book)
    named = {folder + item.get("href") for item in package.findall(f"{OPF}manifest/{OPF}item")}
    present = {name for name in book.namelist() if name.startswith(folder) and not name.endswith(".opf")}

    assert named == present
    assert {"EPUB/title.xhtml", "EPUB/chap_1.xhtml", "EPUB/chap_3.xhtml", "EPUB/chap_4.xhtml", "EPUB/nav.xhtml", "EPUB/toc.ncx"} == named


def test_the_reading_order_is_the_documents_in_the_order_given_with_the_contents_page_after_the_first():
    package, _ = _package(_book())
    href = {item.get("id"): item.get("href") for item in package.findall(f"{OPF}manifest/{OPF}item")}
    spine = package.find(f"{OPF}spine")

    assert [href[ref.get("idref")] for ref in spine.findall(f"{OPF}itemref")] == [
        "title.xhtml", "nav.xhtml", "chap_1.xhtml", "chap_3.xhtml", "chap_4.xhtml",
    ]
    assert href[spine.get("toc")] == "toc.ncx"


def test_the_manifest_says_which_document_is_the_contents_page():
    package, _ = _package(_book())
    items = package.findall(f"{OPF}manifest/{OPF}item")

    assert [item.get("href") for item in items if item.get("properties") == "nav"] == ["nav.xhtml"]
    assert len({item.get("id") for item in items}) == len(items), "two items share an id"


def test_the_metadata_is_what_was_given():
    package, _ = _package(_book())
    metadata = package.find(f"{OPF}metadata")

    assert metadata.find(f"{DC}title").text == AWKWARD
    assert metadata.find(f"{DC}creator").text == "A. Writer"
    assert metadata.find(f"{DC}description").text == "About cats & mice."
    assert metadata.find(f"{DC}subject").text == "Non-fiction"
    assert metadata.find(f"{DC}language").text == "en"
    identifier = metadata.find(f"{DC}identifier")
    assert identifier.text == "book-824"
    assert package.get("unique-identifier") == identifier.get("id")
    modified = [m.text for m in metadata.findall(f"{OPF}meta") if m.get("property") == "dcterms:modified"]
    assert len(modified) == 1 and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", modified[0])


def test_what_was_not_given_is_left_out_not_written_empty():
    package, _ = _package(_book(author=None, description=None, subject=None))
    metadata = package.find(f"{OPF}metadata")

    assert metadata.find(f"{DC}creator") is None
    assert metadata.find(f"{DC}description") is None
    assert metadata.find(f"{DC}subject") is None


def test_the_contents_page_nests_as_the_book_does():
    nav = ElementTree.fromstring(_book().read("EPUB/nav.xhtml"))
    toc = next(n for n in nav.iter(f"{XHTML}nav") if n.get("{http://www.idpf.org/2007/ops}type") == "toc")

    assert _nested_labels(
        toc.find(f"{XHTML}ol"), f"{XHTML}li", lambda li: li.find(f"{XHTML}a").text, lambda li: li.find(f"{XHTML}ol")
    ) == [
        ("Title Page", []),
        ("Chapter 1: One", []),
        ("Chapter 2: Part <Two>", [("2.1 First & foremost", [("2.1.1 A detail", [])]), ("2.2 Second", [])]),
    ]
    assert [a.get("href") for a in toc.iter(f"{XHTML}a")] == [
        "title.xhtml", "chap_1.xhtml", "chap_3.xhtml", "chap_3.xhtml", "chap_3.xhtml", "chap_4.xhtml",
    ]


def test_the_older_contents_file_nests_the_same_way():
    """toc.ncx is what readers from before EPUB 3 use."""
    ncx = ElementTree.fromstring(_book().read("EPUB/toc.ncx"))
    points = list(ncx.iter(f"{NCX}navPoint"))

    assert _nested_labels(
        ncx.find(f"{NCX}navMap"), f"{NCX}navPoint", lambda p: p.find(f"{NCX}navLabel/{NCX}text").text, lambda p: p
    ) == [
        ("Title Page", []),
        ("Chapter 1: One", []),
        ("Chapter 2: Part <Two>", [("2.1 First & foremost", [("2.1.1 A detail", [])]), ("2.2 Second", [])]),
    ]
    assert [p.find(f"{NCX}content").get("src") for p in points] == [
        "title.xhtml", "chap_1.xhtml", "chap_3.xhtml", "chap_3.xhtml", "chap_3.xhtml", "chap_4.xhtml",
    ]
    assert len({p.get("id") for p in points}) == len(points), "two entries share an id"
    uid = next(m.get("content") for m in ncx.iter(f"{NCX}meta") if m.get("name") == "dtb:uid")
    assert uid == "book-824", "it has to be the package's identifier"


def test_every_file_in_it_is_well_formed_whatever_the_title():
    book = _book()

    for name in book.namelist():
        if name != "mimetype":
            ElementTree.fromstring(book.read(name))  # raises on a stray & or <


def test_the_documents_are_stored_as_they_were_given():
    assert _book().read("EPUB/chap_1.xhtml").decode() == _page("One", "<h1>One</h1><p>Text.</p>")


def test_ebooklib_is_gone_from_the_code_the_manifest_and_the_lock():
    backend = Path(export_service_module.__file__).resolve().parents[2]

    assert not hasattr(export_service_module, "epub")
    assert "ebooklib" not in Path(export_service_module.__file__).read_text().lower()
    assert "ebooklib" not in (backend / "pyproject.toml").read_text().lower()
    assert "ebooklib" not in (backend / "uv.lock").read_text().lower()


@pytest.mark.asyncio
async def test_the_export_service_writes_a_book_through_it():
    """End to end: a book with a chapter that only heads its subchapters (#805)."""
    book = {
        "id": "b1", "title": AWKWARD, "author_name": "A. Writer",
        "table_of_contents": {"chapters": [
            {"id": "c1", "title": "Planning", "content": "", "order": 1, "subchapters": [
                {"id": "c1a", "title": "Outlines", "content": "<p>Text & more.</p>", "order": 1},
            ]},
            {"id": "c2", "title": "Writing", "content": "<p>Words.</p>", "order": 2},
        ]},
    }

    exported = zipfile.ZipFile(BytesIO(await export_service_module.export_service.export_book(book, format="epub")))

    package, folder = _package(exported)
    assert package.find(f"{OPF}metadata/{DC}title").text == AWKWARD
    for name in exported.namelist():
        if name != "mimetype":
            ElementTree.fromstring(exported.read(name))
    nav = ElementTree.fromstring(exported.read(folder + "nav.xhtml"))
    assert [(a.text, a.get("href")) for a in nav.iter(f"{XHTML}a")] == [
        ("Title Page", "title.xhtml"),
        ("Chapter 1: Planning", "chap_2.xhtml"),
        ("1.1 Outlines", "chap_2.xhtml"),
        ("Chapter 2: Writing", "chap_3.xhtml"),
    ]
