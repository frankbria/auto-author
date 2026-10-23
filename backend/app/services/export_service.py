"""
Export Service: the export pool, validation and the time budget, over the
format builders composed from app.services.export (#988).
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, BinaryIO

from app.core.config import settings
from app.services.export.docx_builder import DocxMixin
from app.services.export.epub_builder import EpubMixin
from app.services.export.errors import (
    ExportTimeoutError,
    ExportUnavailableError,
    ExportValidationError,
)
from app.services.export.markdown_builder import MarkdownMixin
from app.services.export.outline import strip_non_xml
from app.services.export.outline import OutlineMixin
from app.services.export.pdf_builder import PdfMixin
from app.services.export_templates import resolve_template

__all__ = [
    "EXPORT_THREAD_NAME_PREFIX",
    "ExportService",
    "ExportTimeoutError",
    "ExportUnavailableError",
    "ExportValidationError",
    "export_executor",
    "export_service",
]

logger = logging.getLogger(__name__)

# Export builds are CPU-bound (reportlab / python-docx) and run in worker
# threads. `asyncio.to_thread` would put them on the event loop's DEFAULT
# executor — the very pool app/services/ai/transport.py uses to offload blocking OpenAI calls
# (#175) — so a burst of oversized exports could occupy every worker and queue
# AI generation behind builds whose clients already gave up at the 504. Giving
# exports their own bounded pool keeps that blast radius inside exports (#345).
#
# This bounds the damage; it does not reliably cancel. A build that is still
# QUEUED when the timeout fires is genuinely cancelled and never runs — the
# executor future had not started, so cancel() takes. A build already RUNNING
# cannot be stopped: Python cannot kill a running thread, so it continues to
# completion holding its slot. EXPORT_MAX_WORKERS is therefore the number of
# concurrently-stuck *running* exports it takes to block further exports — AI
# stays unaffected either way, which is the point.
EXPORT_THREAD_NAME_PREFIX = "export_worker"

export_executor = ThreadPoolExecutor(
    max_workers=settings.EXPORT_MAX_WORKERS,
    thread_name_prefix=EXPORT_THREAD_NAME_PREFIX,
)


async def _run_export_build(func, *args):
    """Run a blocking export build on the dedicated export pool.

    The drop-in replacement for ``asyncio.to_thread`` in this module — same
    shape, different (bounded, isolated) executor.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(export_executor, func, *args)


class ExportService(PdfMixin, DocxMixin, EpubMixin, MarkdownMixin, OutlineMixin):
    """Service for exporting books to PDF and DOCX formats."""

    async def generate_pdf(
        self,
        book_data: Dict,
        chapters: List[Dict],
        output_stream: Optional[BinaryIO] = None,
        page_size: str = "letter",
        template: Optional[Dict] = None,
    ) -> bytes:
        """
        Generate a PDF from book data and chapters.

        ReportLab is synchronous and CPU-bound, so the build runs on the
        dedicated export pool to keep the event loop responsive for large books.
        An outer asyncio timeout stops the *waiting*, not the build — the thread
        runs to completion regardless (#345).

        ``template`` (optional) is a resolved export-template dict; when omitted
        the legacy hardcoded styling is used unchanged.
        """
        return await _run_export_build(
            self._build_pdf, book_data, chapters, output_stream, page_size, template
        )

    async def generate_docx(
        self,
        book_data: Dict,
        chapters: List[Dict],
        output_stream: Optional[BinaryIO] = None,
        template: Optional[Dict] = None,
    ) -> bytes:
        """
        Generate a DOCX file from book data and chapters.

        python-docx is synchronous and CPU-bound; the build runs on the
        dedicated export pool so large books don't block the event loop. A
        timeout fires on the await, but cannot stop the build (#345).

        ``template`` (optional) is a resolved export-template dict; when omitted
        the legacy Word styling is used unchanged.
        """
        return await _run_export_build(
            self._build_docx, book_data, chapters, output_stream, template
        )

    async def generate_epub(
        self,
        book_data: Dict,
        chapters: List[Dict],
    ) -> bytes:
        """
        Generate an EPUB (3.0) file from book data and chapters.

        The build is synchronous, so it runs on the dedicated export pool to
        keep the event loop responsive — same pattern as PDF/DOCX. An outer
        timeout abandons the await; it does not stop the build (#345).
        """
        return await _run_export_build(self._build_epub, book_data, chapters)

    async def generate_markdown(
        self,
        book_data: Dict,
        chapters: List[Dict],
        multi_file: bool = False,
    ) -> bytes:
        """
        Generate Markdown from book data and chapters.

        ``multi_file=False`` returns a single ``.md`` file (UTF-8 bytes);
        ``multi_file=True`` returns a ZIP archive with one ``NN-slug.md`` per
        chapter. Runs on the dedicated export pool so large books don't block
        the loop — same pattern as PDF/DOCX/EPUB. An outer timeout abandons the
        await; it does not stop the build (#345).
        """
        return await _run_export_build(
            self._build_markdown, book_data, chapters, multi_file
        )

    def validate_book_for_export(
        self, book_data: Dict, include_empty_chapters: bool = False
    ) -> None:
        """
        Validate that a book has exportable content before starting generation.

        Raises ExportValidationError with a user-facing message when there is
        nothing to export, so the caller can return a clear 400 instead of
        producing a near-empty file or an opaque failure.
        """
        chapters = self._select_chapters(book_data, include_empty_chapters)
        if not chapters:
            toc = book_data.get('table_of_contents', {})
            has_chapters = bool(self._flatten_chapters(toc.get('chapters', [])))
            if has_chapters:
                raise ExportValidationError(
                    "This book has no chapter content yet. Add content to at "
                    "least one chapter, or enable 'Include empty chapters' to "
                    "export the outline."
                )
            raise ExportValidationError(
                "This book has no chapters to export. Generate a table of "
                "contents and add some content first."
            )

    def book_stats(self, book_data: Dict) -> Dict:
        """Compute export statistics (counts, word count, estimated pages)."""
        all_chapters = self._flatten_chapters(
            book_data.get('table_of_contents', {}).get('chapters', [])
        )
        with_content = [c for c in all_chapters if c.get('content', '').strip()]
        word_count = sum(
            len(self._clean_html_content(c.get('content', '')).split())
            for c in with_content
        )
        # ponytail: ~300 words/page is a fine rough estimate for a UI hint.
        estimated_pages = max(1, -(-word_count // 300)) if word_count else 0
        return {
            "total_chapters": len(all_chapters),
            "chapters_with_content": len(with_content),
            "total_word_count": word_count,
            "estimated_pages": estimated_pages,
        }

    async def export_book(
        self,
        book_data: Dict,
        format: str = "pdf",
        include_empty_chapters: bool = False,
        page_size: str = "letter",
        timeout_seconds: Optional[float] = None,
        template_id: Optional[str] = None,
        custom_options: Optional[Dict] = None,
        multi_file: bool = False,
    ) -> bytes:
        """
        Export a book in the specified format.

        Validates content first, then generates within a time budget. When a
        ``template_id`` is given, professional template styling is applied (with
        optional ``custom_options`` overrides). Raises ExportValidationError (no
        content), ExportTimeoutError (too slow), ValueError (bad format/options),
        or KeyError (unknown template).
        """
        self.validate_book_for_export(book_data, include_empty_chapters)
        book_data = strip_non_xml(book_data)

        flattened_chapters = self._select_chapters(book_data, include_empty_chapters)

        # Add author name from owner data if available
        if 'author_name' not in book_data and book_data.get('owner_name'):
            book_data['author_name'] = book_data['owner_name']

        template = resolve_template(template_id, custom_options)

        fmt = format.lower()
        if fmt == 'pdf':
            generator = self.generate_pdf(
                book_data, flattened_chapters, page_size=page_size, template=template
            )
        elif fmt == 'docx':
            generator = self.generate_docx(
                book_data, flattened_chapters, template=template
            )
        elif fmt == 'epub':
            # EPUB has its own reflowable layout — no page_size/template styling.
            generator = self.generate_epub(book_data, flattened_chapters)
        elif fmt in ('markdown', 'md'):
            # Markdown is plain text — no page_size/template styling.
            generator = self.generate_markdown(
                book_data, flattened_chapters, multi_file=multi_file
            )
        else:
            raise ValueError(f"Unsupported export format: {format}")

        if timeout_seconds is None:
            return await generator
        try:
            return await asyncio.wait_for(generator, timeout=timeout_seconds)
        except asyncio.TimeoutError as e:
            # wait_for abandons the await; it cannot stop the worker thread, so
            # the build runs to completion holding one of EXPORT_MAX_WORKERS
            # slots after the client has already received its 504. Previously
            # this happened silently — an operator saw the 504 and no reason for
            # the throughput drop that followed (#345).
            logger.warning(
                "Export timed out after %ss (format=%s, title=%r, chapters=%d). "
                "If the build had already started it is NOT cancelled and is "
                "still running, holding 1 of %d export slots until it finishes.",
                timeout_seconds,
                fmt,
                book_data.get("title", "<untitled>"),
                len(flattened_chapters),
                settings.EXPORT_MAX_WORKERS,
            )
            raise ExportTimeoutError(
                "Export took too long. This usually happens with very large "
                "books — try exporting fewer chapters, or try again in a moment."
            ) from e


# Create singleton instance
export_service = ExportService()
