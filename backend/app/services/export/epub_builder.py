"""The EPUB builder (#988)."""
import html
from typing import Dict, List

from app.services import inline_marks
from app.services.epub_writer import write_epub


class EpubMixin:
    def _xhtml_heading(self, chapter: Dict, index: int) -> str:
        """The chapter's heading as XHTML, one heading level down for each level of nesting."""
        level = min(chapter.get('level', 1), 6)
        return f"<h{level}>{html.escape(self._chapter_heading(chapter, index))}</h{level}>"

    def _chapter_to_xhtml(self, chapter: Dict, index: int, lead: str = "") -> str:
        """Render a chapter to a complete, well-formed XHTML document.

        Reuses the shared HTML→formatted-text pipeline (same as PDF/DOCX) so the
        output is guaranteed valid XHTML — raw TipTap HTML isn't always XML-valid
        and would break ereaders. ``lead`` is the headings of the chapters this
        one is the first document under.
        """
        heading = html.escape(self._chapter_heading(chapter, index))
        parts = [lead, self._xhtml_heading(chapter, index)]

        if chapter.get("description"):
            parts.append(f"<p><em>{html.escape(chapter['description'])}</em></p>")

        content = chapter.get("content", "")
        if content:
            heading_tag = {"heading1": "h2", "heading2": "h3", "heading3": "h4"}
            for para in self._extract_text_formatting(content):
                text = inline_marks.as_tags(
                    html.escape(para["text"]), ("<strong>", "</strong>"), ("<em>", "</em>")
                )
                tag = heading_tag.get(para["style"], "p")
                parts.append(f"<{tag}>{text}</{tag}>")
        elif not chapter.get("heading_only"):
            parts.append("<p><em>(No content yet)</em></p>")

        return self._xhtml_document(heading, "".join(parts))

    @staticmethod
    def _xhtml_document(escaped_title: str, body: str) -> str:
        """One of the book's documents, complete, as the EPUB file stores it."""
        return (
            "<?xml version='1.0' encoding='utf-8'?>\n<!DOCTYPE html>\n"
            '<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en"><head>'
            f"<title>{escaped_title}</title></head><body>{body}</body></html>"
        )

    def _build_epub(self, book_data: Dict, chapters: List[Dict]) -> bytes:
        title = book_data.get("title", "Untitled")
        author = book_data.get("author_name") or book_data.get("owner_name")

        # Title page
        meta_lines = []
        if book_data.get("subtitle"):
            meta_lines.append(f"<h2>{html.escape(book_data['subtitle'])}</h2>")
        if author:
            meta_lines.append(f"<p>by {html.escape(author)}</p>")
        for label, key in (("Genre", "genre"), ("Target Audience", "target_audience")):
            if book_data.get(key):
                meta_lines.append(f"<p>{label}: {html.escape(book_data[key])}</p>")
        if book_data.get("description"):
            meta_lines.append(f"<p>{html.escape(book_data['description'])}</p>")
        documents = [(
            "title.xhtml",
            self._xhtml_document(html.escape(title), f"<h1>{html.escape(title)}</h1>" + "".join(meta_lines)),
        )]

        # Chapters. A reader starts a new page for each document, so a chapter
        # that only heads its subchapters gets none of its own: its heading
        # opens the first document under it, and its navigation entry points
        # there (#805).
        entries, lead = [], ""
        for i, chapter in enumerate(chapters, 1):
            level = chapter.get("level", 1)
            if chapter.get("heading_only"):
                first_under = next(
                    j for j in range(i, len(chapters)) if not chapters[j].get("heading_only")
                )
                lead += self._xhtml_heading(chapter, i)
                entries.append((level, self._chapter_heading(chapter, i), f"chap_{first_under + 1}.xhtml"))
                continue
            documents.append((f"chap_{i}.xhtml", self._chapter_to_xhtml(chapter, i, lead)))
            lead = ""
            entries.append((level, self._chapter_heading(chapter, i), f"chap_{i}.xhtml"))

        return write_epub(
            identifier=str(book_data.get("id") or book_data.get("_id") or "auto-author-book"),
            title=title,
            author=author,
            description=book_data.get("description"),
            subject=book_data.get("genre"),
            documents=documents,
            # Subchapters sit under their chapter in the reader's navigation.
            toc=[("Title Page", "title.xhtml", []), *self._nested(entries)],
        )
