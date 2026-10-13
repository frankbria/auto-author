"""
Test Export Service functionality
"""
import asyncio
import re
import logging
import threading
import pytest
from io import BytesIO
from unittest.mock import patch
from app.core.config import settings
from app.services.export_service import (
    export_service,
    export_executor,
    EXPORT_THREAD_NAME_PREFIX,
    ExportValidationError,
    ExportTimeoutError,
)
from docx import Document


class TestExportService:
    """Test the export service functionality."""

    @pytest.fixture
    def sample_book_data(self):
        """Sample book data for testing."""
        return {
            "title": "Test Book",
            "subtitle": "A Book for Testing",
            "description": "This is a test book used for testing the export functionality.",
            "genre": "Fiction",
            "target_audience": "General",
            "author_name": "Test Author",
            "table_of_contents": {
                "chapters": [
                    {
                        "id": "ch1",
                        "title": "Introduction",
                        "description": "The beginning of our story",
                        "content": "<h1>Welcome</h1><p>This is the <strong>first chapter</strong> of our book.</p><p>It contains some basic HTML formatting.</p>",
                        "order": 1,
                        "status": "completed",
                        "word_count": 100
                    },
                    {
                        "id": "ch2",
                        "title": "Chapter Two",
                        "description": "The plot thickens",
                        "content": "<h2>Chapter 2</h2><p>This chapter has a <em>different</em> heading level.</p><ul><li>Item 1</li><li>Item 2</li></ul>",
                        "order": 2,
                        "status": "completed",
                        "word_count": 150,
                        "subchapters": [
                            {
                                "id": "ch2.1",
                                "title": "Subsection 2.1",
                                "content": "<p>This is a subsection with its own content.</p>",
                                "order": 1,
                                "status": "draft",
                                "word_count": 50
                            }
                        ]
                    },
                    {
                        "id": "ch3",
                        "title": "Empty Chapter",
                        "description": "This chapter has no content",
                        "content": "",
                        "order": 3,
                        "status": "draft",
                        "word_count": 0
                    }
                ]
            }
        }

    def test_clean_html_content(self):
        """Test HTML to text conversion."""
        html = "<h1>Title</h1><p>This is a <strong>bold</strong> paragraph.</p>"
        result = export_service._clean_html_content(html)

        assert "# Title" in result
        assert "This is a **bold** paragraph." in result

    def test_extract_text_formatting(self):
        """Test text formatting extraction."""
        content = "<h1>Main Title</h1><p>Normal paragraph.</p><h2>Subtitle</h2>"
        formatted = export_service._extract_text_formatting(content)

        assert len(formatted) == 3
        assert formatted[0]['text'] == "Main Title"
        assert formatted[0]['style'] == 'heading1'
        assert formatted[1]['text'] == "Normal paragraph."
        assert formatted[1]['style'] == 'normal'
        assert formatted[2]['text'] == "Subtitle"
        assert formatted[2]['style'] == 'heading2'

    def test_flatten_chapters(self):
        """Test chapter flattening for nested structures."""
        chapters = [
            {
                "id": "1",
                "title": "Chapter 1",
                "subchapters": [
                    {"id": "1.1", "title": "Section 1.1"},
                    {"id": "1.2", "title": "Section 1.2"}
                ]
            },
            {"id": "2", "title": "Chapter 2"}
        ]

        flattened = export_service._flatten_chapters(chapters)

        assert len(flattened) == 4
        assert flattened[0]['level'] == 1
        assert flattened[1]['level'] == 2
        assert flattened[2]['level'] == 2
        assert flattened[3]['level'] == 1

    @pytest.mark.asyncio
    async def test_generate_pdf(self, sample_book_data):
        """Test PDF generation."""
        chapters = sample_book_data['table_of_contents']['chapters'][:2]  # Use first 2 chapters

        pdf_bytes = await export_service.generate_pdf(
            sample_book_data,
            chapters,
            page_size="letter"
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000  # Should have substantial content
        assert pdf_bytes.startswith(b'%PDF')  # PDF magic number

    @pytest.mark.asyncio
    async def test_generate_docx(self, sample_book_data):
        """Test DOCX generation."""
        chapters = sample_book_data['table_of_contents']['chapters'][:2]  # Use first 2 chapters

        docx_bytes = await export_service.generate_docx(
            sample_book_data,
            chapters
        )

        assert isinstance(docx_bytes, bytes)
        assert len(docx_bytes) > 1000  # Should have substantial content
        # DOCX files start with PK (ZIP format)
        assert docx_bytes.startswith(b'PK')

    @pytest.mark.asyncio
    async def test_export_book_pdf(self, sample_book_data):
        """Test complete book export to PDF."""
        pdf_bytes = await export_service.export_book(
            sample_book_data,
            format="pdf",
            include_empty_chapters=False
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000
        assert pdf_bytes.startswith(b'%PDF')

    @pytest.mark.asyncio
    async def test_export_book_docx(self, sample_book_data):
        """Test complete book export to DOCX."""
        docx_bytes = await export_service.export_book(
            sample_book_data,
            format="docx",
            include_empty_chapters=True
        )

        assert isinstance(docx_bytes, bytes)
        assert len(docx_bytes) > 1000
        assert docx_bytes.startswith(b'PK')

    @pytest.mark.asyncio
    async def test_generate_epub(self, sample_book_data):
        """EPUB generation produces a valid EPUB zip with chapter content."""
        import zipfile
        from io import BytesIO

        chapters = sample_book_data['table_of_contents']['chapters'][:2]

        epub_bytes = await export_service.generate_epub(sample_book_data, chapters)

        assert isinstance(epub_bytes, bytes)
        assert len(epub_bytes) > 1000
        # EPUB is a ZIP whose first entry is an uncompressed "mimetype" file.
        assert epub_bytes.startswith(b'PK')
        with zipfile.ZipFile(BytesIO(epub_bytes)) as zf:
            assert zf.read("mimetype") == b"application/epub+zip"
            names = zf.namelist()
            # Title page + both chapters are present as XHTML documents.
            assert any(n.endswith("title.xhtml") for n in names)
            assert any(n.endswith("chap_1.xhtml") for n in names)
            assert any(n.endswith("chap_2.xhtml") for n in names)
            # Navigation documents exist (TOC works in ereaders).
            assert any("nav" in n.lower() for n in names)
            assert any(n.endswith(".ncx") for n in names)
            # Chapter title text survives into the rendered XHTML.
            all_text = b"".join(zf.read(n) for n in names if n.endswith(".xhtml"))
            assert b"Introduction" in all_text

    @pytest.mark.asyncio
    async def test_export_book_epub(self, sample_book_data):
        """Complete book export to EPUB via the dispatcher."""
        epub_bytes = await export_service.export_book(
            sample_book_data,
            format="epub",
            include_empty_chapters=False,
        )

        assert isinstance(epub_bytes, bytes)
        assert len(epub_bytes) > 1000
        assert epub_bytes.startswith(b'PK')
        # Empty chapters excluded by default — the empty chapter has no content.
        assert b"Empty Chapter" not in epub_bytes

    @pytest.mark.asyncio
    async def test_generate_markdown_single_file(self, sample_book_data):
        """Single-file Markdown has a title H1, chapter headings, and content."""
        chapters = export_service._select_chapters(sample_book_data, False)
        md_bytes = await export_service.generate_markdown(sample_book_data, chapters)

        assert isinstance(md_bytes, bytes)
        text = md_bytes.decode('utf-8')
        # Book title is the top-level heading.
        assert text.startswith("# Test Book")
        # Chapters render with their own heading level below the book title.
        assert "## Chapter 1: Introduction" in text
        # HTML content is converted to Markdown (bold, list survive).
        assert "**first chapter**" in text
        assert "Item 1" in text
        # A chapter's own <h1>Welcome</h1> must not become a top-level '#'
        # heading that outranks the book title (proper hierarchy, issue #61).
        assert "\n# Welcome" not in text
        assert "### Welcome" in text

    @pytest.mark.asyncio
    async def test_generate_markdown_preserves_images(self):
        """<img> tags convert to Markdown image syntax with correct paths."""
        book = {
            "title": "Img Book",
            "table_of_contents": {"chapters": [{
                "id": "c1", "title": "Pics",
                "content": '<p><img src="https://ex.com/a.png" alt="Alt"></p>',
            }]},
        }
        chapters = export_service._select_chapters(book, False)
        text = (await export_service.generate_markdown(book, chapters)).decode('utf-8')
        assert "![Alt](https://ex.com/a.png)" in text

    @pytest.mark.asyncio
    async def test_generate_markdown_multi_file(self, sample_book_data):
        """Multi-file mode returns a ZIP with one .md per chapter."""
        import zipfile
        from io import BytesIO

        chapters = export_service._select_chapters(sample_book_data, False)
        zip_bytes = await export_service.generate_markdown(
            sample_book_data, chapters, multi_file=True
        )

        assert zip_bytes.startswith(b'PK')
        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
            assert all(n.endswith('.md') for n in names)
            assert len(names) == len(chapters)
            assert any('introduction' in n for n in names)
            assert b"**first chapter**" in zf.read(names[0])

    @pytest.mark.asyncio
    async def test_export_book_markdown(self, sample_book_data):
        """Complete book export to Markdown via the dispatcher."""
        md_bytes = await export_service.export_book(
            sample_book_data, format="markdown", include_empty_chapters=False
        )
        text = md_bytes.decode('utf-8')
        assert "# Test Book" in text
        # Empty chapter excluded by default.
        assert "Empty Chapter" not in text

    @pytest.mark.asyncio
    async def test_export_exclude_empty_chapters(self, sample_book_data):
        """Test that empty chapters are excluded when requested."""
        # Export without empty chapters
        pdf_bytes = await export_service.export_book(
            sample_book_data,
            format="pdf",
            include_empty_chapters=False
        )

        # The PDF should not contain "Empty Chapter" text
        # This is a basic check - in reality you'd parse the PDF
        assert b"Empty Chapter" not in pdf_bytes

    @pytest.mark.asyncio
    async def test_export_invalid_format(self, sample_book_data):
        """Test that invalid format raises error."""
        with pytest.raises(ValueError, match="Unsupported export format"):
            await export_service.export_book(
                sample_book_data,
                format="invalid"
            )

    @pytest.mark.asyncio
    async def test_export_with_no_content(self):
        """A book with no chapters is rejected with a clear validation error."""
        minimal_book = {
            "title": "Empty Book",
            "table_of_contents": {
                "chapters": []
            }
        }

        with pytest.raises(ExportValidationError) as exc:
            await export_service.export_book(minimal_book, format="pdf")
        assert "no chapters" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_export_empty_chapters_rejected_unless_included(self):
        """Chapters that exist but have no content are rejected by default,
        but exportable when include_empty_chapters is set."""
        book = {
            "title": "Outline Only",
            "table_of_contents": {
                "chapters": [
                    {"id": "1", "title": "Ch One", "content": "", "order": 1}
                ]
            },
        }

        with pytest.raises(ExportValidationError) as exc:
            await export_service.export_book(book, format="pdf")
        assert "no chapter content" in str(exc.value).lower()

        pdf_bytes = await export_service.export_book(
            book, format="pdf", include_empty_chapters=True
        )
        assert pdf_bytes.startswith(b"%PDF")

    @pytest.mark.asyncio
    async def test_book_stats_counts_words_and_pages(self):
        """book_stats reports chapter counts, word count, and estimated pages."""
        book = {
            "title": "Stats Book",
            "table_of_contents": {
                "chapters": [
                    {"id": "1", "title": "A",
                     "content": "<p>one two three four five</p>", "order": 1},
                    {"id": "2", "title": "B", "content": "", "order": 2},
                ]
            },
        }
        stats = export_service.book_stats(book)
        assert stats["total_chapters"] == 2
        assert stats["chapters_with_content"] == 1
        assert stats["total_word_count"] == 5
        assert stats["estimated_pages"] >= 1

    @pytest.mark.asyncio
    async def test_export_times_out_for_slow_generation(self):
        """A generation that exceeds the timeout raises ExportTimeoutError."""
        book = {
            "title": "Slow Book",
            "table_of_contents": {
                "chapters": [
                    {"id": "1", "title": "A", "content": "<p>hi</p>", "order": 1}
                ]
            },
        }

        async def slow_pdf(*args, **kwargs):
            await asyncio.sleep(0.2)
            return b"%PDF-never"

        with patch.object(export_service, "generate_pdf", side_effect=slow_pdf):
            with pytest.raises(ExportTimeoutError):
                await export_service.export_book(
                    book, format="pdf", timeout_seconds=0.01
                )

    @pytest.mark.asyncio
    async def test_export_large_book_succeeds(self):
        """A large book (100+ chapters) exports successfully within budget."""
        chapters = [
            {
                "id": str(i),
                "title": f"Chapter {i}",
                "content": f"<p>Content for chapter {i} with several words.</p>",
                "order": i,
            }
            for i in range(1, 121)
        ]
        book = {"title": "Big Book", "table_of_contents": {"chapters": chapters}}

        pdf_bytes = await export_service.export_book(
            book, format="pdf", timeout_seconds=60
        )
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 1000

    @pytest.mark.asyncio
    async def test_export_special_characters(self):
        """Test export with special characters in content."""
        book_data = {
            "title": "Special Characters & Symbols",
            "author_name": "Author <Name>",
            "table_of_contents": {
                "chapters": [{
                    "id": "1",
                    "title": "Symbols & More",
                    "content": "<p>Special chars: &amp; &lt; &gt; &quot;</p>",
                    "order": 1
                }]
            }
        }

        # Should not raise any errors
        pdf_bytes = await export_service.export_book(book_data, format="pdf")
        assert isinstance(pdf_bytes, bytes)

        docx_bytes = await export_service.export_book(book_data, format="docx")
        assert isinstance(docx_bytes, bytes)

class TestExportAvailabilityGuards:
    """Issue #45: export degrades gracefully when an optional library is missing."""

    @pytest.mark.asyncio
    async def test_generate_pdf_raises_when_reportlab_unavailable(self, monkeypatch):
        import app.services.export_service as es
        monkeypatch.setattr(es, "PDF_AVAILABLE", False)
        with pytest.raises(es.ExportUnavailableError, match="reportlab"):
            await es.export_service.generate_pdf({"title": "x"}, [])

    @pytest.mark.asyncio
    async def test_generate_docx_raises_when_docx_unavailable(self, monkeypatch):
        import app.services.export_service as es
        monkeypatch.setattr(es, "DOCX_AVAILABLE", False)
        with pytest.raises(es.ExportUnavailableError, match="python-docx"):
            await es.export_service.generate_docx({"title": "x"}, [])

    @pytest.mark.asyncio
    async def test_generate_epub_raises_when_ebooklib_unavailable(self, monkeypatch):
        import app.services.export_service as es
        monkeypatch.setattr(es, "EPUB_AVAILABLE", False)
        with pytest.raises(es.ExportUnavailableError, match="ebooklib"):
            await es.export_service.generate_epub({"title": "x"}, [])

    @pytest.mark.asyncio
    async def test_generate_markdown_raises_when_markdownify_unavailable(self, monkeypatch):
        import app.services.export_service as es
        monkeypatch.setattr(es, "MARKDOWNIFY_AVAILABLE", False)
        with pytest.raises(es.ExportUnavailableError, match="markdownify"):
            await es.export_service.generate_markdown({"title": "x"}, [])

    def test_clean_html_falls_back_without_markdownify(self, monkeypatch):
        import app.services.export_service as es
        monkeypatch.setattr(es, "MARKDOWNIFY_AVAILABLE", False)
        svc = es.ExportService()
        out = svc._clean_html_content("<p>Hello <strong>world</strong></p>")
        assert "Hello" in out and "world" in out
        assert "<" not in out


class TestTemplatedExport:
    """Export with professional templates (issue #59)."""

    @pytest.fixture
    def book_data(self):
        return {
            "title": "Templated Book",
            "subtitle": "A Test",
            "author_name": "Jane Doe",
            "description": "Desc.",
            "table_of_contents": {
                "chapters": [
                    {
                        "id": "c1",
                        "title": "One",
                        "content": "<p>Some real content for the first chapter.</p>",
                        "order": 1,
                        "status": "completed",
                        "word_count": 8,
                    }
                ]
            },
        }

    @pytest.mark.parametrize(
        "template_id", ["classic_fiction", "modern_nonfiction", "academic"]
    )
    @pytest.mark.asyncio
    async def test_pdf_export_with_each_template(self, book_data, template_id):
        out = await export_service.export_book(
            book_data, format="pdf", template_id=template_id
        )
        assert out[:4] == b"%PDF"
        assert len(out) > 500

    @pytest.mark.asyncio
    async def test_pdf_templates_differ_from_default(self, book_data):
        default = await export_service.export_book(book_data, format="pdf")
        templated = await export_service.export_book(
            book_data, format="pdf", template_id="academic"
        )
        assert default != templated  # different page size/margins/font

    @pytest.mark.asyncio
    async def test_docx_template_applies_section_and_font(self, book_data):
        out = await export_service.export_book(
            book_data, format="docx", template_id="academic"
        )
        doc = Document(BytesIO(out))
        section = doc.sections[0]
        # Academic = A4, 1.25" inside/outside, 1.0" top/bottom.
        assert round(section.left_margin.inches, 2) == 1.25
        assert round(section.right_margin.inches, 2) == 1.25
        assert round(section.top_margin.inches, 2) == 1.0
        normal = doc.styles["Normal"]
        assert normal.font.name == "Times New Roman"
        assert normal.font.size.pt == 12
        # Running header carries book/author text.
        assert "Templated Book" in section.header.paragraphs[0].text

    @pytest.mark.asyncio
    async def test_custom_options_override_font_size(self, book_data):
        out = await export_service.export_book(
            book_data,
            format="docx",
            template_id="classic_fiction",
            custom_options={"font_size": 14},
        )
        doc = Document(BytesIO(out))
        assert doc.styles["Normal"].font.size.pt == 14

    @pytest.mark.asyncio
    async def test_unknown_template_raises(self, book_data):
        with pytest.raises(KeyError):
            await export_service.export_book(
                book_data, format="pdf", template_id="not_a_template"
            )

    @pytest.mark.asyncio
    async def test_no_template_id_is_backward_compatible(self, book_data):
        out = await export_service.export_book(book_data, format="docx")
        doc = Document(BytesIO(out))
        # Default python-docx letter section, untouched header.
        assert doc.sections[0].header.paragraphs[0].text == ""


class TestExportExecutorIsolation:
    """#345: exports must not be able to starve the AI path.

    ``asyncio.to_thread`` dispatches to the event loop's *default*
    ThreadPoolExecutor — the same pool ``ai_service`` uses for blocking OpenAI
    calls. A burst of oversized exports could therefore occupy every worker and
    queue AI generation behind builds that a 504 has already given up on.
    Exports now run on their own bounded pool.
    """

    @pytest.mark.asyncio
    async def test_pdf_build_runs_on_the_dedicated_export_pool(self):
        """The build thread must belong to the export pool, not the default one.

        Asserting on the returned bytes would pass either way; the thread the
        work actually ran on is the thing that keeps AI unblocked, so that is
        what gets pinned. Default-executor threads are named
        ``asyncio_%d``/``ThreadPoolExecutor-*``, never ``export_*``.
        """
        seen = {}

        def fake_build(*args, **kwargs):
            seen["thread"] = threading.current_thread().name
            return b"%PDF-1.4 fake"

        with patch.object(export_service, "_build_pdf", side_effect=fake_build):
            await export_service.generate_pdf(
                {"title": "T"}, [{"id": "1", "title": "A", "content": "<p>x</p>"}]
            )

        assert seen["thread"].startswith(EXPORT_THREAD_NAME_PREFIX), (
            f"export ran on {seen['thread']!r}; it must run on the dedicated "
            "export pool or it can starve ai_service's OpenAI calls (#345)"
        )

    @pytest.mark.asyncio
    async def test_export_pool_is_bounded(self):
        """An unbounded pool would defeat the purpose — saturation is the point."""
        assert export_executor._max_workers == settings.EXPORT_MAX_WORKERS
        assert settings.EXPORT_MAX_WORKERS >= 1

    @pytest.mark.asyncio
    async def test_timeout_warns_that_the_thread_keeps_running(self, caplog):
        """A 504 with no log left an invisible stuck worker (#345).

        The warning is the only signal an operator gets that a slot is still
        occupied after the client got its error.
        """
        book = {
            "title": "Slow Book",
            "table_of_contents": {
                "chapters": [
                    {"id": "1", "title": "A", "content": "<p>hi</p>", "order": 1}
                ]
            },
        }

        async def slow_pdf(*args, **kwargs):
            await asyncio.sleep(0.2)
            return b"%PDF-never"

        with patch.object(export_service, "generate_pdf", side_effect=slow_pdf):
            with caplog.at_level(logging.WARNING, logger="app.services.export_service"):
                with pytest.raises(ExportTimeoutError):
                    await export_service.export_book(
                        book, format="pdf", timeout_seconds=0.01
                    )

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warnings, "a timed-out export must leave a warning behind"
        message = warnings[0].getMessage()
        assert "pdf" in message
        # The message must not repeat the old claim that the export was stopped.
        assert "not cancelled" in message.lower() or "still running" in message.lower()


class TestCleanHtmlConcurrency:
    """#751: one shared html2text parser leaked text between tenants."""

    def test_no_cross_document_leak_under_threads(self):
        from concurrent.futures import ThreadPoolExecutor
        import app.services.export_service as es

        svc = es.ExportService()
        tags = [f"TAG{i}X" for i in range(8)]
        docs = [
            "".join(f"<p>{t} para {j} <strong>{t}</strong> <a href='http://x/{t}'>l</a></p>" for j in range(30))
            for t in tags
        ]

        def work(i):
            for _ in range(200):
                out = svc._clean_html_content(docs[i])
                for other in tags:
                    if other != tags[i] and other in out:
                        return f"{tags[i]} output contains {other}"
                assert tags[i] in out
            return None

        with ThreadPoolExecutor(max_workers=8) as ex:
            results = list(ex.map(work, range(8)))
        assert results == [None] * 8
        assert svc._clean_html_content("<p>hello</p>") == "hello"


class TestPdfMarkupEscaping:
    """Issue #752: user text is data, never ReportLab markup."""

    @pytest.fixture
    def hostile_book(self, tmp_path):
        from PIL import Image
        img = tmp_path / "server_only.png"
        Image.new("RGB", (4, 4), "red").save(img)
        tag = f'<img src="{img}"/>'
        return {
            "title": "A </i> B <b>x",
            "subtitle": "Sub & <u>unbalanced",
            "author_name": "Au <thor>",
            "description": "Desc </b> & <para>",
            "genre": "G <i>",
            "target_audience": "T </i>",
            "table_of_contents": {"chapters": [{
                "id": "1",
                "title": "Ch </i> & <b>",
                "description": "CD </i> <b>",
                "content": f"<p>body &lt;b&gt;bold&lt;/b&gt; &amp; &lt;/i&gt; &lt;</p><p>&lt;img src=\"{img}\"/&gt;</p>",
                "order": 1,
            }]},
        }, tag

    @pytest.mark.asyncio
    async def test_hostile_text_exports_literally_without_images(
        self, hostile_book, monkeypatch
    ):
        from reportlab import rl_config
        monkeypatch.setattr(rl_config, "pageCompression", 0)
        monkeypatch.setattr(rl_config, "useA85", 0)
        book, tag = hostile_book
        pdf = await export_service.export_book(book, format="pdf")
        assert pdf.startswith(b"%PDF")
        # ReportLab splits text into (..) Tj fragments and wraps lines: compare
        # the concatenated text with whitespace removed.
        text = b"".join(re.findall(rb"\(([^)]*)\) Tj", pdf))
        text = re.sub(rb"\s+", b"", text)
        for literal in ("A </i> B <b>x", "Ch </i> & <b>", "CD </i> <b>",
                        "Desc </b> & <para>", "body <b>bold</b> & </i> <", tag):
            assert re.sub(r"\s+", "", literal).encode() in text, literal
        assert b"/Subtype /Image" not in pdf

    def test_only_data_scheme_trusted(self):
        from reportlab import rl_config
        assert list(rl_config.trustedSchemes) == ["data"]
        assert list(rl_config.trustedHosts) == []


class TestNonPdfFormatsKeepTextRaw:
    """#752 review: _pdf_text is ReportLab-only. python-docx escapes for itself
    and Markdown has nothing to escape, so escaping there shows up as a literal
    "&amp;" in the exported file."""

    BOOK = {
        "title": "Raw",
        "genre": "Sci-Fi & Fantasy",
        "target_audience": "Parents & <teens>",
        "table_of_contents": {"chapters": [
            {"id": "1", "title": "One", "content": "<p>Body</p>", "order": 1},
        ]},
    }

    @pytest.mark.asyncio
    async def test_docx_metadata_is_not_html_escaped(self):
        from io import BytesIO
        from docx import Document

        chapters = self.BOOK["table_of_contents"]["chapters"]
        docx_bytes = await export_service.generate_docx(self.BOOK, chapters)

        text = "\n".join(p.text for p in Document(BytesIO(docx_bytes)).paragraphs)
        assert "Genre: Sci-Fi & Fantasy" in text
        assert "Target Audience: Parents & <teens>" in text
        assert "&amp;" not in text and "&lt;" not in text

    @pytest.mark.asyncio
    async def test_markdown_metadata_is_not_html_escaped(self):
        chapters = self.BOOK["table_of_contents"]["chapters"]
        text = (await export_service.generate_markdown(self.BOOK, chapters)).decode("utf-8")

        assert "Genre: Sci-Fi & Fantasy" in text
        assert "Target Audience: Parents & <teens>" in text
        assert "&amp;" not in text and "&lt;" not in text


class TestHtmlBecomesMarkdownWithoutHtml2text:
    """#823: html2text is GPL-3.0-or-later and sat on every export path of an MIT-licensed
    repository. markdownify (MIT) replaces it. These pin what the exports depend on, most of
    it found by running both converters over the same chapter HTML and comparing."""

    @staticmethod
    def _builders_get(html):
        """The paragraphs the PDF, DOCX and EPUB builders are given."""
        import app.services.export_service as es

        return [(p["style"], p["text"]) for p in es.ExportService()._extract_text_formatting(html)]

    @staticmethod
    def _exported(html):
        import app.services.export_service as es

        return es.ExportService()._content_to_markdown(html)

    def test_html2text_is_gone_from_the_code_the_manifest_and_the_lock(self):
        from pathlib import Path

        import app.services.export_service as es

        backend = Path(es.__file__).resolve().parents[2]
        assert not hasattr(es, "html2text")
        assert "html2text" not in Path(es.__file__).read_text()
        assert "html2text" not in (backend / "pyproject.toml").read_text()
        assert "html2text" not in (backend / "uv.lock").read_text()

    def test_headings_keep_their_level(self):
        """markdownify's own default writes an h1 as a line of text over a line of `=`,
        which the builders would take for a paragraph."""
        assert self._builders_get("<h1>Top</h1><p>Text.</p><h2>Middle</h2><h3>Small</h3>") == [
            ("heading1", "Top"), ("normal", "Text."), ("heading2", "Middle"), ("heading3", "Small"),
        ]

    def test_each_list_item_is_its_own_paragraph_for_the_builders(self):
        """A tight Markdown list is one block. In a PDF paragraph its lines run together."""
        html = "<ul><li><p>One</p></li><li><p>Two</p></li></ul><ol><li><p>First</p></li><li><p>Second</p></li></ol>"

        assert [text for _, text in self._builders_get(html)] == ["* One", "* Two", "1. First", "2. Second"]

    def test_a_nested_list_keeps_every_item(self):
        html = "<ul><li><p>Outer</p><ul><li><p>Inner a</p></li><li><p>Inner b</p></li></ul></li><li><p>Last</p></li></ul>"

        assert [text for _, text in self._builders_get(html)] == ["* Outer", "* Inner a", "* Inner b", "* Last"]

    def test_a_script_or_a_style_block_contributes_nothing(self):
        """markdownify's `strip` option drops the tag and keeps the text inside it."""
        html = "<p>Kept.</p><script>alert(1)</script><style>p{color:red}</style><p>Also kept.</p>"

        assert [text for _, text in self._builders_get(html)] == ["Kept.", "Also kept."]
        assert self._exported(html) == "Kept.\n\nAlso kept."

    def test_the_builders_get_the_text_as_it_was_typed(self):
        """No backslash escapes: a PDF is not a Markdown reader and would print them."""
        html = "<p>snake_case_name and 2 * 3 and __init__</p><p>1. not a list</p><p>- not a bullet</p>"

        assert [text for _, text in self._builders_get(html)] == [
            "snake_case_name and 2 * 3 and __init__", "1. not a list", "- not a bullet",
        ]

    def test_the_markdown_export_escapes_text_that_only_looks_like_markup(self):
        """In a Markdown file `__init__` unescaped is the word init in bold, and a paragraph
        that starts with `# ` is a heading."""
        exported = self._exported("<p># not a heading</p><p>__init__ and 2 * 3</p><p>1. not a list</p>")

        assert exported == "\\# not a heading\n\n\\_\\_init\\_\\_ and 2 \\* 3\n\n1\\. not a list"

    def test_a_code_block_is_fenced_in_the_export_and_plain_for_the_builders(self):
        html = "<p>Before.</p><pre><code>def f(x):\n    return x * 2\n</code></pre>"

        assert self._exported(html) == "Before.\n\n```\ndef f(x):\n    return x * 2\n```"
        assert self._builders_get(html) == [("normal", "Before."), ("normal", "def f(x):\n    return x * 2")]

    def test_an_image_is_in_the_export_and_not_in_the_builders_text(self):
        html = '<p>Before.</p><img src="/uploads/owner_abc.png" alt="A chart"><p>After.</p>'

        assert self._exported(html) == "Before.\n\n![A chart](/uploads/owner_abc.png)\n\nAfter."
        assert [text for _, text in self._builders_get(html)] == ["Before.", "After."]

    def test_a_non_breaking_space_is_an_ordinary_space(self):
        """The editor writes &nbsp; for a second space in a row."""
        assert self._builders_get("<p>one&nbsp; two</p>") == [("normal", "one  two")]
        assert self._exported("<p>one&nbsp; two</p>") == "one  two"

    def test_emphasis_is_marked_as_it_always_was(self):
        """`_italic_` beside `**bold**`. markdownify's default is `*italic*`; every export
        until now has had the other, and the builders print the markers as they come."""
        html = "<p>Some <strong>bold</strong>, some <em>italic</em>, <i>too</i>.</p>"

        assert self._builders_get(html) == [("normal", "Some **bold**, some _italic_, _too_.")]
        assert self._exported(html) == "Some **bold**, some _italic_, _too_."

    def test_a_link_keeps_its_address(self):
        html = '<p>See <a href="https://example.com/a_b?x=1&amp;y=2">the page</a>.</p>'

        assert self._builders_get(html) == [("normal", "See [the page](https://example.com/a_b?x=1&y=2).")]
        assert self._exported(html) == "See [the page](https://example.com/a_b?x=1&y=2)."
