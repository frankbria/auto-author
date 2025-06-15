"""
Test Export Service functionality
"""
import pytest
from io import BytesIO
from app.services.export_service import export_service
from reportlab.pdfgen import canvas
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
        """Test export with minimal book data."""
        minimal_book = {
            "title": "Empty Book",
            "table_of_contents": {
                "chapters": []
            }
        }
        
        pdf_bytes = await export_service.export_book(
            minimal_book,
            format="pdf"
        )
        
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b'%PDF')
    
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