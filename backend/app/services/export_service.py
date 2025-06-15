"""
Export Service for generating PDF and DOCX files from book content
"""
import io
import asyncio
from typing import Dict, List, Optional, BinaryIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, KeepTogether
)
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
import html2text
import re


class ExportService:
    """Service for exporting books to PDF and DOCX formats."""
    
    def __init__(self):
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = False
        self.h2t.ignore_images = True
        self.h2t.body_width = 0  # Don't wrap lines
        
    def _clean_html_content(self, content: str) -> str:
        """Convert HTML content to clean text, preserving basic formatting."""
        if not content:
            return ""
        
        # Convert HTML to markdown
        markdown_text = self.h2t.handle(content)
        
        # Clean up excessive newlines
        markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)
        
        return markdown_text.strip()
    
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
                
            # Detect headings
            if para.startswith('# '):
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
    
    async def generate_pdf(
        self,
        book_data: Dict,
        chapters: List[Dict],
        output_stream: Optional[BinaryIO] = None,
        page_size: str = "letter"
    ) -> bytes:
        """
        Generate a PDF from book data and chapters.
        
        Args:
            book_data: Book metadata including title, author, etc.
            chapters: List of chapter data with content
            output_stream: Optional stream to write to
            page_size: Page size (letter or A4)
            
        Returns:
            PDF content as bytes
        """
        # Create output buffer if not provided
        if output_stream is None:
            output_stream = io.BytesIO()
        
        # Set page size
        page = letter if page_size == "letter" else A4
        
        # Create document
        doc = SimpleDocTemplate(
            output_stream,
            pagesize=page,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Create styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
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
            fontSize=20,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=20,
            spaceBefore=30
        )
        
        heading2_style = ParagraphStyle(
            'Heading2',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=12,
            spaceBefore=20
        )
        
        heading3_style = ParagraphStyle(
            'Heading3',
            parent=styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=10,
            spaceBefore=15
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            alignment=TA_JUSTIFY,
            spaceAfter=12,
            leading=16
        )
        
        # Build story
        story = []
        
        # Title page
        story.append(Paragraph(book_data.get('title', 'Untitled'), title_style))
        
        if book_data.get('subtitle'):
            story.append(Paragraph(book_data['subtitle'], subtitle_style))
        
        story.append(Spacer(1, 0.5*inch))
        
        # Author info
        if book_data.get('author_name'):
            story.append(Paragraph(f"by {book_data['author_name']}", subtitle_style))
        
        # Genre and audience
        metadata_parts = []
        if book_data.get('genre'):
            metadata_parts.append(f"Genre: {book_data['genre']}")
        if book_data.get('target_audience'):
            metadata_parts.append(f"Target Audience: {book_data['target_audience']}")
        
        if metadata_parts:
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph(' • '.join(metadata_parts), styles['Normal']))
        
        # Description
        if book_data.get('description'):
            story.append(Spacer(1, 0.5*inch))
            story.append(Paragraph(book_data['description'], body_style))
        
        # Page break after title page
        story.append(PageBreak())
        
        # Table of Contents
        story.append(Paragraph("Table of Contents", chapter_title_style))
        story.append(Spacer(1, 0.2*inch))
        
        toc_data = []
        for i, chapter in enumerate(chapters, 1):
            chapter_title = chapter.get('title', f'Chapter {i}')
            # Simple TOC without page numbers for now
            toc_data.append([f"{i}.", chapter_title])
        
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
            # Chapter title
            chapter_title = chapter.get('title', f'Chapter {i}')
            story.append(Paragraph(f"Chapter {i}: {chapter_title}", chapter_title_style))
            
            # Chapter description
            if chapter.get('description'):
                story.append(Paragraph(chapter['description'], styles['Italic']))
                story.append(Spacer(1, 0.2*inch))
            
            # Chapter content
            content = chapter.get('content', '')
            if content:
                # Extract and format content
                formatted_content = self._extract_text_formatting(content)
                
                for para in formatted_content:
                    if para['style'] == 'heading1':
                        story.append(Paragraph(para['text'], chapter_title_style))
                    elif para['style'] == 'heading2':
                        story.append(Paragraph(para['text'], heading2_style))
                    elif para['style'] == 'heading3':
                        story.append(Paragraph(para['text'], heading3_style))
                    else:
                        story.append(Paragraph(para['text'], body_style))
            else:
                story.append(Paragraph("(No content yet)", styles['Italic']))
            
            # Add page break after each chapter except the last
            if i < len(chapters):
                story.append(PageBreak())
        
        # Build PDF
        doc.build(story)
        
        # Get bytes if using BytesIO
        if isinstance(output_stream, io.BytesIO):
            output_stream.seek(0)
            return output_stream.getvalue()
        
        return b''
    
    async def generate_docx(
        self,
        book_data: Dict,
        chapters: List[Dict],
        output_stream: Optional[BinaryIO] = None
    ) -> bytes:
        """
        Generate a DOCX file from book data and chapters.
        
        Args:
            book_data: Book metadata including title, author, etc.
            chapters: List of chapter data with content
            output_stream: Optional stream to write to
            
        Returns:
            DOCX content as bytes
        """
        # Create document
        doc = Document()
        
        # Set up styles
        styles = doc.styles
        
        # Title page
        title = doc.add_heading(book_data.get('title', 'Untitled'), 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        if book_data.get('subtitle'):
            subtitle = doc.add_paragraph(book_data['subtitle'])
            subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
            subtitle.runs[0].font.size = Pt(18)
            subtitle.runs[0].font.color.rgb = RGBColor(102, 102, 102)
        
        doc.add_paragraph()  # Empty line
        
        # Author
        if book_data.get('author_name'):
            author = doc.add_paragraph(f"by {book_data['author_name']}")
            author.alignment = WD_ALIGN_PARAGRAPH.CENTER
            author.runs[0].font.size = Pt(14)
        
        # Metadata
        metadata_parts = []
        if book_data.get('genre'):
            metadata_parts.append(f"Genre: {book_data['genre']}")
        if book_data.get('target_audience'):
            metadata_parts.append(f"Target Audience: {book_data['target_audience']}")
        
        if metadata_parts:
            doc.add_paragraph()
            metadata = doc.add_paragraph(' • '.join(metadata_parts))
            metadata.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Description
        if book_data.get('description'):
            doc.add_paragraph()
            doc.add_paragraph(book_data['description'])
        
        # Page break
        doc.add_page_break()
        
        # Table of Contents
        doc.add_heading('Table of Contents', 1)
        
        for i, chapter in enumerate(chapters, 1):
            chapter_title = chapter.get('title', f'Chapter {i}')
            toc_entry = doc.add_paragraph(f"{i}. {chapter_title}")
            toc_entry.paragraph_format.left_indent = Inches(0.25)
        
        doc.add_page_break()
        
        # Chapters
        for i, chapter in enumerate(chapters, 1):
            # Chapter heading
            chapter_title = chapter.get('title', f'Chapter {i}')
            doc.add_heading(f"Chapter {i}: {chapter_title}", 1)
            
            # Chapter description
            if chapter.get('description'):
                desc = doc.add_paragraph(chapter['description'])
                desc.runs[0].italic = True
            
            # Chapter content
            content = chapter.get('content', '')
            if content:
                # Extract and format content
                formatted_content = self._extract_text_formatting(content)
                
                for para in formatted_content:
                    if para['style'] == 'heading1':
                        doc.add_heading(para['text'], 1)
                    elif para['style'] == 'heading2':
                        doc.add_heading(para['text'], 2)
                    elif para['style'] == 'heading3':
                        doc.add_heading(para['text'], 3)
                    else:
                        p = doc.add_paragraph(para['text'])
                        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            else:
                doc.add_paragraph("(No content yet)")
                doc.paragraphs[-1].runs[0].italic = True
            
            # Add page break after each chapter except the last
            if i < len(chapters):
                doc.add_page_break()
        
        # Save to stream
        if output_stream is None:
            output_stream = io.BytesIO()
        
        doc.save(output_stream)
        
        # Get bytes if using BytesIO
        if isinstance(output_stream, io.BytesIO):
            output_stream.seek(0)
            return output_stream.getvalue()
        
        return b''
    
    def _flatten_chapters(self, chapters: List[Dict], level: int = 1) -> List[Dict]:
        """Flatten nested chapter structure for export."""
        flattened = []
        
        for chapter in chapters:
            # Add the chapter itself
            chapter_copy = chapter.copy()
            chapter_copy['level'] = level
            flattened.append(chapter_copy)
            
            # Recursively add subchapters
            if chapter.get('subchapters'):
                flattened.extend(
                    self._flatten_chapters(chapter['subchapters'], level + 1)
                )
        
        return flattened
    
    async def export_book(
        self,
        book_data: Dict,
        format: str = "pdf",
        include_empty_chapters: bool = False,
        page_size: str = "letter"
    ) -> bytes:
        """
        Export a book in the specified format.
        
        Args:
            book_data: Complete book data including TOC and content
            format: Export format (pdf or docx)
            include_empty_chapters: Whether to include chapters without content
            page_size: Page size for PDF (letter or A4)
            
        Returns:
            Exported file content as bytes
        """
        # Extract and flatten chapters from TOC
        toc = book_data.get('table_of_contents', {})
        chapters = toc.get('chapters', [])
        
        # Flatten nested structure
        flattened_chapters = self._flatten_chapters(chapters)
        
        # Filter out empty chapters if requested
        if not include_empty_chapters:
            flattened_chapters = [
                ch for ch in flattened_chapters 
                if ch.get('content', '').strip()
            ]
        
        # Add author name from owner data if available
        if 'author_name' not in book_data and book_data.get('owner_name'):
            book_data['author_name'] = book_data['owner_name']
        
        # Generate export based on format
        if format.lower() == 'pdf':
            return await self.generate_pdf(
                book_data,
                flattened_chapters,
                page_size=page_size
            )
        elif format.lower() == 'docx':
            return await self.generate_docx(
                book_data,
                flattened_chapters
            )
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Create singleton instance
export_service = ExportService()