"""The chapter outline every builder shares: selection, numbering, headings,
contents entries and the running-head tokens (#988)."""
from typing import Dict, List


class OutlineMixin:
    @staticmethod
    def _resolve_tokens(text: str, book_data: Dict) -> str:
        """Fill running-header/footer tokens from book-level data.

        ponytail: running heads are book-level (title/author), not per-chapter —
        {page} is handled at draw time since only the canvas knows the number.
        """
        if not text:
            return ""
        title = book_data.get("title", "Untitled")
        author = book_data.get("author_name") or book_data.get("owner_name") or ""
        return (
            text.replace("{book_title}", title)
            .replace("{running_head}", title)
            .replace("{author}", author)
            .replace("{chapter_title}", title)
        )

    def _flatten_chapters(
        self,
        chapters: List[Dict],
        level: int = 1,
        include_empty: bool = True,
        parent_number: str = "",
    ) -> List[Dict]:
        """Flatten nested chapters for export, each with its ``level`` and outline ``number``.

        A chapter with no text is left out when ``include_empty`` is false,
        unless one under it is kept: a chapter that only groups subchapters is
        the usual shape of a book, and they need its heading. Numbers count what
        is kept ("1", "1.1", "1.2", "2"), so they have no gaps (#805).
        """
        flattened = []
        kept = 0

        for chapter in chapters:
            number = f"{parent_number}{kept + 1}"
            below = self._flatten_chapters(
                chapter.get('subchapters') or [], level + 1, include_empty, f"{number}."
            )
            has_text = bool((chapter.get('content') or '').strip())
            if not (include_empty or below or has_text):
                continue
            kept += 1
            chapter_copy = chapter.copy()
            chapter_copy['level'] = level
            chapter_copy['number'] = number
            # No text of its own: it is there to head the chapters under it, so
            # it gets no "(No content yet)" line and no page to itself.
            chapter_copy['heading_only'] = bool(below) and not has_text
            flattened.append(chapter_copy)
            flattened.extend(below)

        return flattened

    @staticmethod
    def _number(chapter: Dict, index: int) -> str:
        """The chapter's outline number; its position in a list that was not numbered."""
        return chapter.get('number') or str(index)

    @classmethod
    def _chapter_heading(cls, chapter: Dict, index: int) -> str:
        """ "Chapter 2: Title" for a chapter, "2.1 Title" for anything under one."""
        number = cls._number(chapter, index)
        title = chapter.get('title', f'Chapter {number}')
        return f"{number} {title}" if '.' in number else f"Chapter {number}: {title}"

    @classmethod
    def _contents_entry(cls, chapter: Dict, index: int) -> tuple:
        """A table-of-contents row: ("2.", title) for a chapter, ("2.1", title) under one."""
        number = cls._number(chapter, index)
        label = number if '.' in number else f"{number}."
        return label, chapter.get('title', f'Chapter {number}')

    @staticmethod
    def _nested(entries: List[tuple]) -> List:
        """(level, label, document) in reading order as a table of contents:
        ``(label, document, [the entries under it])``."""
        root: List = []
        path = [root]  # path[d] holds the entries at depth d + 1
        for level, label, document in entries:
            del path[level:]
            node = (label, document, [])
            path[-1].append(node)
            path.append(node[2])
        return root

    def _select_chapters(
        self, book_data: Dict, include_empty_chapters: bool
    ) -> List[Dict]:
        """Flatten and number the TOC, dropping empty chapters unless explicitly included."""
        toc = book_data.get('table_of_contents', {})
        return self._flatten_chapters(
            toc.get('chapters', []), include_empty=include_empty_chapters
        )
