"""The PDF builder (ReportLab) (#988)."""
import io
import html
from typing import Dict, List, Optional, BinaryIO

from app.services import inline_marks
from app.services.export.errors import ExportUnavailableError
from app.services.export_templates import PAGE_SIZES_INCHES

# Optional export dependencies are guarded so the service (and the rest of the
# API) still imports if a library is missing — only the affected format fails,
# and it fails loudly with a clear message rather than at import time.
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak,
        Table, TableStyle
    )
    from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
    from reportlab import rl_config
    # Paragraph() resolves <img src=...>. reportlab 5.0.1 already refuses URL
    # sources (http, file://, data:) with its defaults; this pins that so an
    # upgrade that loosens them cannot turn <img> into SSRF. It does NOT stop a
    # plain filesystem path, which reportlab opens before any scheme check:
    # _pdf_text is the only guard against embedding a server-local file (#752).
    rl_config.trustedSchemes = ['data']
    rl_config.trustedHosts = []
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


def _pdf_text(value) -> str:
    """Escape user text for ReportLab Paragraph(), which parses XML-like markup (#752)."""
    return html.escape(str(value), quote=False)


def _pdf_inline(value) -> str:
    """Chapter text for Paragraph(): escaped, with its bold and italic (#1030)."""
    return inline_marks.as_tags(_pdf_text(value), ("<b>", "</b>"), ("<i>", "</i>"))


class PdfMixin:
    def _make_header_footer(self, template: Dict, book_data: Dict, page):
        """Return an onPage(canvas, doc) callback drawing the running header/footer."""
        page_w, page_h = page
        margins = template["margins"]
        left = self._resolve_tokens(template.get("header", {}).get("left", ""), book_data)
        right = self._resolve_tokens(template.get("header", {}).get("right", ""), book_data)
        center = template.get("footer", {}).get("center", "")

        def _draw(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 9)
            canvas.setFillGray(0.4)
            y_header = page_h - margins["top"] * inch + 0.25 * inch
            y_footer = margins["bottom"] * inch - 0.35 * inch
            if left:
                canvas.drawString(margins["inside"] * inch, y_header, left)
            if right:
                canvas.drawRightString(page_w - margins["outside"] * inch, y_header, right)
            if center:
                text = center.replace("{page}", str(canvas.getPageNumber()))
                canvas.drawCentredString(page_w / 2.0, y_footer, text)
            canvas.restoreState()

        return _draw

    def _build_pdf(
        self,
        book_data: Dict,
        chapters: List[Dict],
        output_stream: Optional[BinaryIO] = None,
        page_size: str = "letter",
        template: Optional[Dict] = None,
    ) -> bytes:
        if not PDF_AVAILABLE:
            raise ExportUnavailableError(
                "PDF export unavailable: reportlab is not installed"
            )

        # Create output buffer if not provided
        if output_stream is None:
            output_stream = io.BytesIO()

        # Page size + margins: template wins, else legacy 1" margins on letter/A4.
        if template:
            w_in, h_in = PAGE_SIZES_INCHES[template["page_size"]]
            page = (w_in * inch, h_in * inch)
            m = template["margins"]
            margin_left, margin_right = m["inside"] * inch, m["outside"] * inch
            margin_top, margin_bottom = m["top"] * inch, m["bottom"] * inch
        else:
            page = letter if page_size == "letter" else A4
            margin_left = margin_right = margin_top = margin_bottom = 72

        # Create document
        doc = SimpleDocTemplate(
            output_stream,
            pagesize=page,
            rightMargin=margin_right,
            leftMargin=margin_left,
            topMargin=margin_top,
            bottomMargin=margin_bottom,
        )

        # Create styles
        styles = getSampleStyleSheet()

        # Body font/size/leading/indent from the template, else legacy defaults.
        if template:
            body_font = template["font"]["pdf_font"]
            body_size = template["font"]["size"]
            body_leading = body_size * template["line_height"]
            body_indent = template["first_line_indent"] * inch
            heading_font = (
                "Helvetica-Bold" if template["font"]["family"] == "sans" else "Times-Bold"
            )
        else:
            body_font, body_size, body_leading, body_indent = "Helvetica", 11, 16, 0
            heading_font = "Helvetica-Bold"

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontName=heading_font,
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        )

        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=16,
            textColor=colors.HexColor('#666666'),
            spaceAfter=12,
            alignment=TA_CENTER
        )

        chapter_title_style = ParagraphStyle(
            'ChapterTitle',
            parent=styles['Heading1'],
            fontName=heading_font,
            fontSize=20,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=20,
            spaceBefore=30
        )

        heading2_style = ParagraphStyle(
            'Heading2',
            parent=styles['Heading2'],
            fontName=heading_font,
            fontSize=16,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=12,
            spaceBefore=20
        )

        heading3_style = ParagraphStyle(
            'Heading3',
            parent=styles['Heading3'],
            fontName=heading_font,
            fontSize=14,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=10,
            spaceBefore=15
        )

        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontName=body_font,
            fontSize=body_size,
            alignment=TA_JUSTIFY,
            spaceAfter=12,
            leading=body_leading,
            firstLineIndent=body_indent,
        )

        # Build story
        story = []

        # Title page
        story.append(Paragraph(_pdf_text(book_data.get('title', 'Untitled')), title_style))

        if book_data.get('subtitle'):
            story.append(Paragraph(_pdf_text(book_data['subtitle']), subtitle_style))

        story.append(Spacer(1, 0.5*inch))

        # Author info
        if book_data.get('author_name'):
            story.append(Paragraph(f"by {_pdf_text(book_data['author_name'])}", subtitle_style))

        # About the Author (from the owner's profile bio). Escape the free-text
        # bio — ReportLab's Paragraph parses XML-like markup, so unescaped
        # characters like '<' would break PDF generation.
        if book_data.get('author_bio'):
            story.append(Spacer(1, 0.25*inch))
            story.append(Paragraph("About the Author", heading2_style))
            story.append(Paragraph(_pdf_text(book_data['author_bio']), body_style))

        # Genre and audience
        metadata_parts = []
        if book_data.get('genre'):
            metadata_parts.append(f"Genre: {_pdf_text(book_data['genre'])}")
        if book_data.get('target_audience'):
            metadata_parts.append(f"Target Audience: {_pdf_text(book_data['target_audience'])}")

        if metadata_parts:
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph(' • '.join(metadata_parts), styles['Normal']))

        # Description
        if book_data.get('description'):
            story.append(Spacer(1, 0.5*inch))
            story.append(Paragraph(_pdf_text(book_data['description']), body_style))

        # Page break after title page
        story.append(PageBreak())

        # Table of Contents
        story.append(Paragraph("Table of Contents", chapter_title_style))
        story.append(Spacer(1, 0.2*inch))

        toc_data = []
        for i, chapter in enumerate(chapters, 1):
            # Simple TOC without page numbers for now
            toc_data.append(list(self._contents_entry(chapter, i)))

        if toc_data:
            toc_table = Table(toc_data, colWidths=[0.5*inch, 5*inch])
            toc_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(toc_table)

        story.append(PageBreak())

        # Chapters
        for i, chapter in enumerate(chapters, 1):
            # Chapter title, in a smaller style for anything under a chapter
            level = chapter.get('level', 1)
            title_style = {1: chapter_title_style, 2: heading2_style}.get(level, heading3_style)
            story.append(Paragraph(_pdf_text(self._chapter_heading(chapter, i)), title_style))

            # Chapter description
            if chapter.get('description'):
                story.append(Paragraph(_pdf_text(chapter['description']), styles['Italic']))
                story.append(Spacer(1, 0.2*inch))

            # Chapter content
            content = chapter.get('content', '')
            if content:
                # Extract and format content
                formatted_content = self._extract_text_formatting(content)

                for para in formatted_content:
                    if para['style'] == 'heading1':
                        story.append(Paragraph(_pdf_inline(para['text']), chapter_title_style))
                    elif para['style'] == 'heading2':
                        story.append(Paragraph(_pdf_inline(para['text']), heading2_style))
                    elif para['style'] == 'heading3':
                        story.append(Paragraph(_pdf_inline(para['text']), heading3_style))
                    else:
                        story.append(Paragraph(_pdf_inline(para['text']), body_style))
            elif not chapter.get('heading_only'):
                story.append(Paragraph("(No content yet)", styles['Italic']))

            # Add page break after each chapter except the last
            if i < len(chapters) and not chapter.get('heading_only'):
                story.append(PageBreak())

        # Build PDF. With a template, draw a running header/footer on every page
        # except the title page (clean first page is the professional convention).
        if template:
            draw = self._make_header_footer(template, book_data, page)
            doc.build(story, onLaterPages=draw)
        else:
            doc.build(story)

        # Get bytes if using BytesIO
        if isinstance(output_stream, io.BytesIO):
            output_stream.seek(0)
            return output_stream.getvalue()

        return b''
