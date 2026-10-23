"""Everything markdownify does: chapter HTML as the text the PDF, DOCX and EPUB
builders take, and the Markdown export itself (#988)."""
import io
import html
import re
import textwrap
from typing import Dict, List

from app.services import inline_marks
from app.services.export.errors import ExportUnavailableError

# Optional export dependencies are guarded so the service (and the rest of the
# API) still imports if a library is missing — only the affected format fails,
# and it fails loudly with a clear message rather than at import time.
try:
    from markdownify import ATX, MarkdownConverter, abstract_inline_conversion
    MARKDOWNIFY_AVAILABLE = True
except ImportError:
    MARKDOWNIFY_AVAILABLE = False


# Where text can stand on its own line: the chapter itself and a <div>; and what
# ends the line before it.
_BARE_BLOCKS = {"[document]", "div", "article", "section"}
_BLOCKS = {"p", "div", "article", "section", "ul", "ol", "pre", "blockquote", "table", "hr", "h1", "h2", "h3", "h4", "h5", "h6"}


def _html_to_markdown(content: str, *, for_a_markdown_reader: bool) -> str:
    """Chapter HTML as Markdown, with markdownify (MIT). It replaced a
    GPL-3.0-or-later converter on every export path (#823).

    `for_a_markdown_reader` is the Markdown export: images are kept, and text
    that only looks like markup is escaped, so that `__init__` is not the word
    init in bold. Without it the result is for the PDF, DOCX and EPUB builders,
    which print what they are given: no images, and no backslashes.

    The converter is built here, on each call, so nothing is shared between two
    exports running at once (#751).
    """

    # In the Markdown export a chapter's own headings sit below its `##` chapter
    # heading, so that an <h1> in the text cannot outrank the book's title (#61).
    # Done here, where a heading is known to be one. It used to be done by
    # rewriting every line of the result that began with `#`, which also
    # rewrote the comments in a fenced code block.
    below_the_chapter_heading = 2 if for_a_markdown_reader else 0

    class _Chapter(MarkdownConverter):
        if for_a_markdown_reader:
            # `_italic_` beside `**bold**`, as every export has had it until now.
            convert_em = convert_i = abstract_inline_conversion(lambda self: "_")
        else:
            # Marks the builders turn into formatting, not `**` printed (#1030).
            convert_b = convert_strong = inline_marks.inline(inline_marks.BOLD)
            convert_em = convert_i = inline_marks.inline(inline_marks.ITALIC)
            convert_s = convert_del = convert_strike = inline_marks.inline(inline_marks.STRIKE)
            convert_sup = inline_marks.inline(inline_marks.SUP)
            convert_sub = inline_marks.inline(inline_marks.SUB)
            convert_code = inline_marks.code
            convert_a = inline_marks.link

        def process_text(self, el, parent_tags=None):
            # Marks go from the text as parsed: &#xe00c; in the source is a mark
            # only once decoded. Text that opens a bare block or the chapter is
            # a paragraph the author typed: `# ` must not read as a heading (#1190).
            text = inline_marks.without_marks(super().process_text(el, parent_tags))
            prev = el.previous_sibling
            if (not for_a_markdown_reader and el.parent is not None
                    and el.parent.name in _BARE_BLOCKS and (prev is None or prev.name in _BLOCKS)):
                text = re.sub(r"^(\s*)(#{1,6} )", r"\1\\\2", text)
            return text

        def convert_p(self, el, text, parent_tags):
            # A paragraph that begins `# ` is escaped for the builders too, so
            # that `_extract_text_formatting` can tell it from a heading (#1026).
            if not for_a_markdown_reader:
                text = re.sub(r"^(\s*)(#{1,6} )", r"\1\\\2", text)
            return super().convert_p(el, text, parent_tags)

        def convert_hN(self, n, el, text, parent_tags):
            # markdownify stops at the sixth level itself.
            return super().convert_hN(n + below_the_chapter_heading, el, text, parent_tags)

    converter = _Chapter(
        heading_style=ATX,  # the default writes an h1 as text over a row of `=`
        bullets="*",  # the default changes the bullet at each level of nesting
        # Only ever `img` here. `strip` drops a tag and keeps the text inside
        # it; a <script> or <style> named here would put its code in the book.
        # Left alone, markdownify drops both, text and all.
        strip=None if for_a_markdown_reader else ["img"],
        escape_asterisks=for_a_markdown_reader,
        escape_underscores=for_a_markdown_reader,
        escape_misc=for_a_markdown_reader,
    )
    # The editor writes &nbsp; for a second space in a row. Marks typed into
    # the text itself are removed, so only the converter can make one (#1030).
    return converter.convert(inline_marks.without_marks(content)).replace("\xa0", " ")


def _blocks_for_the_builders(markdown: str) -> str:
    """Markdown as the PDF, DOCX and EPUB builders take it: one paragraph per
    block separated by a blank line, printed as it comes, and called a heading
    when it begins with `# `.

    So a code block loses its fence and is indented, as it always reached them:
    at the margin, a line of code beginning `# ` would be set as a heading. And
    a list, which Markdown writes as one block, gets a blank line before each
    item, or its lines would run together in a paragraph.
    """
    parts = re.split(r'(?ms)^```[^\n]*\n(.*?)^```[ \t]*$', markdown)
    for i, part in enumerate(parts):
        if i % 2:  # the inside of a code block
            parts[i] = textwrap.indent(part, '    ')
        else:
            parts[i] = re.sub(r'\n(?=[ \t]*(?:\*|\d+\.) )', '\n\n', part)
    return ''.join(parts)


class MarkdownMixin:
    def _clean_html_content(self, content: str) -> str:
        """Convert HTML content to clean text, preserving basic formatting."""
        if not content:
            return ""

        if MARKDOWNIFY_AVAILABLE:
            markdown_text = _blocks_for_the_builders(
                _html_to_markdown(content, for_a_markdown_reader=False)
            )
        else:
            # ponytail: markdownify not installed — fall back to a tag strip that
            # preserves block boundaries so words/paragraphs don't merge.
            text = re.sub(r'(?is)<(script|style).*?>.*?</\1>', '', content)
            text = re.sub(r'(?i)</(p|div|h[1-6]|li|br|tr)>', '\n', text)
            text = re.sub(r'(?is)<[^>]+>', '', text)
            markdown_text = html.unescape(text)

        # Clean up excessive newlines
        markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)

        # Newlines only: a code block that opens the chapter keeps its indent.
        return markdown_text.strip('\n')

    def _extract_text_formatting(self, content: str) -> List[Dict]:
        """Extract text and basic formatting from HTML content."""
        # This is a simple implementation - could be enhanced with proper HTML parsing
        clean_text = self._clean_html_content(content)

        # Split into paragraphs
        paragraphs = clean_text.split('\n\n')

        formatted_content = []
        for para in paragraphs:
            if not para.strip():
                continue

            # A paragraph that began `# ` arrives as `\# `: not a heading (#1026).
            if re.match(r'\\#{1,6} ', para):
                formatted_content.append({
                    'text': para[1:].strip(),
                    'style': 'normal'
                })
            elif para.startswith('# '):
                formatted_content.append({
                    'text': para[2:].strip(),
                    'style': 'heading1'
                })
            elif para.startswith('## '):
                formatted_content.append({
                    'text': para[3:].strip(),
                    'style': 'heading2'
                })
            elif para.startswith('### '):
                formatted_content.append({
                    'text': para[4:].strip(),
                    'style': 'heading3'
                })
            else:
                # Regular paragraph
                formatted_content.append({
                    'text': para.strip(),
                    'style': 'normal'
                })

        return formatted_content

    @staticmethod
    def _slugify(text: str) -> str:
        """Lowercase, hyphenate, strip non-word chars for safe filenames."""
        slug = re.sub(r'[^\w\s-]', '', (text or '').lower()).strip()
        slug = re.sub(r'[\s_-]+', '-', slug).strip('-')
        return slug or 'chapter'

    def _content_to_markdown(self, content: str) -> str:
        """Convert chapter HTML to Markdown, preserving images and links.

        Images are kept, so ``<img>`` becomes ``![alt](src)`` (issue #61 AC:
        images referenced with correct paths), unlike the text the PDF, DOCX and
        EPUB builders are given.
        """
        if not content:
            return "*(No content yet)*"
        if MARKDOWNIFY_AVAILABLE:
            md = _html_to_markdown(content, for_a_markdown_reader=True)
        else:
            # ponytail: no markdownify — reuse the block-preserving tag strip.
            md = self._clean_html_content(content)
        return re.sub(r'\n{3,}', '\n\n', md).strip()

    def _chapter_markdown(self, chapter: Dict, index: int) -> str:
        """Render one chapter to Markdown (heading level tracks nesting depth)."""
        # level 1 chapter -> '##' (book title owns '#'); deeper nests indent.
        heading = '#' * min(6, chapter.get('level', 1) + 1)
        parts = [f"{heading} {self._chapter_heading(chapter, index)}"]
        if chapter.get('description'):
            parts.append(f"*{chapter['description']}*")
        if not chapter.get('heading_only'):
            parts.append(self._content_to_markdown(chapter.get('content', '')))
        return "\n\n".join(parts)

    def _build_markdown(
        self, book_data: Dict, chapters: List[Dict], multi_file: bool = False
    ) -> bytes:
        if not MARKDOWNIFY_AVAILABLE:
            raise ExportUnavailableError(
                "Markdown export unavailable: markdownify is not installed"
            )

        if multi_file:
            output = io.BytesIO()
            import zipfile
            with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zf:
                for i, chapter in enumerate(chapters, 1):
                    name = f"{i:02d}-{self._slugify(chapter.get('title', ''))}.md"
                    zf.writestr(name, self._chapter_markdown(chapter, i) + "\n")
            output.seek(0)
            return output.getvalue()

        lines = [f"# {book_data.get('title', 'Untitled')}"]
        if book_data.get('subtitle'):
            # Emphasis, not a heading: the subtitle shouldn't compete with
            # chapter headings in a Markdown viewer's outline.
            lines.append(f"*{book_data['subtitle']}*")
        author = book_data.get('author_name') or book_data.get('owner_name')
        if author:
            lines.append(f"by {author}")
        metadata_parts = []
        if book_data.get('genre'):
            metadata_parts.append(f"Genre: {book_data['genre']}")
        if book_data.get('target_audience'):
            metadata_parts.append(f"Target Audience: {book_data['target_audience']}")
        if metadata_parts:
            lines.append(' • '.join(metadata_parts))
        if book_data.get('description'):
            lines.append(book_data['description'])

        for i, chapter in enumerate(chapters, 1):
            lines.append(self._chapter_markdown(chapter, i))

        return ("\n\n".join(lines).strip() + "\n").encode('utf-8')
