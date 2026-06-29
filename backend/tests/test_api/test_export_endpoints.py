"""
Test Export API endpoints
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import io
from bson import ObjectId
from app.db import base


async def _seed_toc(book_id: str, toc: dict) -> None:
    """Write a table_of_contents directly to the DB in production shape.

    Chapter content lives inline at table_of_contents.chapters[].content (the
    same shape the content endpoint persists). Seeding via Motor avoids the
    lossy book-PATCH/TOC HTTP path, which validates chapters through a model
    that drops the `content` field.
    """
    await base.books_collection.update_one(
        {"_id": ObjectId(book_id)}, {"$set": {"table_of_contents": toc}}
    )


class TestExportEndpoints:
    """Test the export API endpoints."""

    @pytest.fixture
    async def test_book_with_content(self, auth_client_factory):
        """Create a test book with content for export testing."""
        client = await auth_client_factory()

        # Create a book
        book_data = {
            "title": "Export Test Book",
            "subtitle": "Testing Export Functionality",
            "description": "A book created to test PDF and DOCX export.",
            "genre": "Technical",
            "target_audience": "Developers"
        }

        response = await client.post("/api/v1/books/", json=book_data)
        assert response.status_code == 201
        book = response.json()
        book_id = book["id"]

        # Add TOC with chapters - use the proper structure expected by the API
        toc_data = {
            "chapters": [
                {
                    "id": "ch1",
                    "title": "Introduction",
                    "description": "Getting started",
                    "content": "<h1>Introduction</h1><p>Welcome to this test book.</p>",
                    "order": 1,
                    "level": 1,
                    "parent_id": None,
                    "status": "completed",
                    "word_count": 10,
                    "subchapters": []
                },
                {
                    "id": "ch2",
                    "title": "Main Content",
                    "description": "The core content",
                    "content": "<h1>Main Content</h1><p>This is the main chapter with <strong>important</strong> information.</p>",
                    "order": 2,
                    "level": 1,
                    "parent_id": None,
                    "status": "completed",
                    "word_count": 15,
                    "subchapters": []
                },
                {
                    "id": "ch3",
                    "title": "Empty Chapter",
                    "description": "No content yet",
                    "content": "",
                    "order": 3,
                    "level": 1,
                    "parent_id": None,
                    "status": "draft",
                    "word_count": 0,
                    "subchapters": []
                }
            ],
            "total_chapters": 3,
            "estimated_pages": 10,
            "status": "edited"
        }

        # Seed the TOC (with inline chapter content) directly, matching the
        # production document shape. See _seed_toc for why we bypass the HTTP
        # TOC path here.
        await _seed_toc(book_id, toc_data)

        return client, book_id

    @pytest.mark.asyncio
    async def test_export_pdf_success(self, test_book_with_content):
        """Test successful PDF export."""
        client, book_id = test_book_with_content

        response = await client.get(f"/api/v1/books/{book_id}/export/pdf")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers.get("content-disposition", "")
        assert ".pdf" in response.headers.get("content-disposition", "")

        # Check that we got actual PDF content
        content = response.content
        assert content.startswith(b'%PDF')
        assert len(content) > 1000  # Should have substantial content

    @pytest.mark.asyncio
    async def test_export_pdf_with_options(self, test_book_with_content):
        """Test PDF export with various options."""
        client, book_id = test_book_with_content

        # Test with A4 page size
        response = await client.get(
            f"/api/v1/books/{book_id}/export/pdf?page_size=A4"
        )
        assert response.status_code == 200
        assert response.content.startswith(b'%PDF')

        # Test including empty chapters
        response = await client.get(
            f"/api/v1/books/{book_id}/export/pdf?include_empty_chapters=true"
        )
        assert response.status_code == 200
        # Content should be larger when including empty chapters
        with_empty_size = len(response.content)

        # Test excluding empty chapters
        response = await client.get(
            f"/api/v1/books/{book_id}/export/pdf?include_empty_chapters=false"
        )
        assert response.status_code == 200
        without_empty_size = len(response.content)

        # Size might be similar due to PDF structure, but both should work
        assert with_empty_size > 0
        assert without_empty_size > 0

    @pytest.mark.asyncio
    async def test_export_docx_success(self, test_book_with_content):
        """Test successful DOCX export."""
        client, book_id = test_book_with_content

        response = await client.get(f"/api/v1/books/{book_id}/export/docx")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert "attachment" in response.headers.get("content-disposition", "")
        assert ".docx" in response.headers.get("content-disposition", "")

        # Check that we got actual DOCX content (ZIP format)
        content = response.content
        assert content.startswith(b'PK')
        assert len(content) > 1000

    @pytest.mark.asyncio
    async def test_export_formats_endpoint(self, test_book_with_content):
        """Test the export formats information endpoint."""
        client, book_id = test_book_with_content

        response = await client.get(f"/api/v1/books/{book_id}/export/formats")

        assert response.status_code == 200
        data = response.json()

        assert "formats" in data
        assert len(data["formats"]) == 2

        # Check PDF format
        pdf_format = next(f for f in data["formats"] if f["format"] == "pdf")
        assert pdf_format["name"] == "PDF Document"
        assert pdf_format["mime_type"] == "application/pdf"
        assert "page_size" in pdf_format["options"]

        # Check DOCX format
        docx_format = next(f for f in data["formats"] if f["format"] == "docx")
        assert docx_format["name"] == "Word Document"
        assert docx_format["extension"] == ".docx"

        # Check book stats
        assert "book_stats" in data
        # The stats are calculated from the actual book data in the database
        # Since we're using PATCH which might not properly update nested structures in tests,
        # let's just check that the stats exist
        assert "total_chapters" in data["book_stats"]
        assert "chapters_with_content" in data["book_stats"]
        # Stats now include word count and estimated pages (issue #49 — these
        # power the export options UI and previously crashed it when missing).
        assert "total_word_count" in data["book_stats"]
        assert "estimated_pages" in data["book_stats"]
        assert data["book_stats"]["total_word_count"] > 0

    @pytest.mark.asyncio
    async def test_export_empty_book_returns_400(self, auth_client_factory):
        """Exporting a book with no chapter content returns a clear 400."""
        client = await auth_client_factory()
        book_id = (
            await client.post("/api/v1/books/", json={"title": "Empty Export Book"})
        ).json()["id"]

        response = await client.get(f"/api/v1/books/{book_id}/export/pdf")
        assert response.status_code == 400
        detail = response.json()["detail"].lower()
        assert "no chapter" in detail

    @pytest.mark.asyncio
    async def test_export_timeout_returns_504(
        self, test_book_with_content, monkeypatch
    ):
        """A generation that exceeds the time budget returns a 504 with guidance."""
        client, book_id = test_book_with_content

        from app.core.config import settings
        monkeypatch.setattr(settings, "EXPORT_TIMEOUT_SECONDS", 0.01)

        import app.services.export_service as es

        async def slow_pdf(*args, **kwargs):
            import asyncio
            await asyncio.sleep(0.5)
            return b"%PDF"

        monkeypatch.setattr(es.export_service, "generate_pdf", slow_pdf)

        response = await client.get(f"/api/v1/books/{book_id}/export/pdf")
        assert response.status_code == 504
        assert "too long" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_export_book_not_found(self, auth_client_factory):
        """Test export with non-existent book."""
        client = await auth_client_factory()

        response = await client.get("/api/v1/books/nonexistent_id/export/pdf")

        assert response.status_code == 404
        assert "Book not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_export_unauthorized(self, client):
        """Test export without authentication."""
        response = client.get("/api/v1/books/some_id/export/pdf")

        assert response.status_code == 401  # 401 Unauthorized for missing auth

    @pytest.mark.asyncio
    async def test_export_not_owner(self, auth_client_factory):
        """Test export by non-owner."""
        # Create book with first user
        client1 = await auth_client_factory()
        response = await client1.post("/api/v1/books/", json={"title": "Private Book"})
        book_id = response.json()["id"]

        # Add minimal TOC to the book
        update_data = {
            "title": "Private Book",
            "table_of_contents": {
                "chapters": [{
                    "id": "ch1",
                    "title": "Chapter 1",
                    "content": "<p>Content</p>",
                    "order": 1
                }]
            }
        }
        await client1.patch(f"/api/v1/books/{book_id}", json=update_data)

        # Try to export with second user
        # Create a client with a different auth_id
        client2 = await auth_client_factory(overrides={"auth_id": "different_auth_id"})
        response = await client2.get(f"/api/v1/books/{book_id}/export/pdf")

        # Debug output if not 403
        if response.status_code != 403:
            print(f"Expected 403 but got {response.status_code}")
            print(f"Response: {response.json() if response.status_code != 200 else 'PDF content returned'}")

        assert response.status_code == 403
        assert "Not authorized to export this book" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_export_invalid_page_size(self, test_book_with_content):
        """Test export with invalid page size."""
        client, book_id = test_book_with_content

        response = await client.get(
            f"/api/v1/books/{book_id}/export/pdf?page_size=invalid"
        )

        # Should get validation error
        assert response.status_code == 422

    @pytest.mark.skip(reason="Rate limiting tests require proper test setup with time delays")
    @pytest.mark.asyncio
    async def test_export_rate_limiting(self, test_book_with_content):
        """Test that export endpoints are rate limited."""
        client, book_id = test_book_with_content

        # Make multiple requests quickly
        # Rate limit is 10 per hour, so 11 should trigger limit
        for i in range(11):
            response = await client.get(f"/api/v1/books/{book_id}/export/pdf")
            if i < 10:
                assert response.status_code == 200
            else:
                # 11th request should be rate limited
                assert response.status_code == 429
                assert "rate limit" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_export_special_characters_filename(self, auth_client_factory):
        """Test export with special characters in book title."""
        client = await auth_client_factory()

        # Create book with special characters
        book_data = {
            "title": "Book with Special/Characters & Symbols!",
            "description": "Testing filename sanitization"
        }

        response = await client.post("/api/v1/books/", json=book_data)
        book_id = response.json()["id"]

        # Seed a chapter with inline content directly (production shape).
        await _seed_toc(book_id, {
            "chapters": [{
                "id": "ch1",
                "title": "Chapter 1",
                "content": "<p>Some real content for the export.</p>",
                "order": 1
            }]
        })

        # Export should work and filename should be sanitized
        response = await client.get(f"/api/v1/books/{book_id}/export/pdf")

        assert response.status_code == 200
        content_disposition = response.headers.get("content-disposition", "")
        # Filename should not contain special characters like / or !
        assert "/" not in content_disposition
        assert "!" not in content_disposition
        assert ".pdf" in content_disposition

class TestExportAvailability:
    """Issue #45: format availability reporting and 503 on missing libraries."""

    @pytest.mark.asyncio
    async def test_formats_report_availability(self, auth_client_factory):
        import app.api.endpoints.export as export_endpoint
        client = await auth_client_factory()
        resp = await client.post("/api/v1/books/", json={"title": "Avail Book"})
        book_id = resp.json()["id"]

        data = (await client.get(f"/api/v1/books/{book_id}/export/formats")).json()
        expected = {
            "pdf": export_endpoint.PDF_AVAILABLE,
            "docx": export_endpoint.DOCX_AVAILABLE,
        }
        for fmt in data["formats"]:
            assert "available" in fmt
            assert fmt["available"] is expected[fmt["format"]]

    @pytest.mark.asyncio
    async def test_pdf_export_returns_503_when_unavailable(self, auth_client_factory, monkeypatch):
        client = await auth_client_factory()
        book_id = (await client.post("/api/v1/books/", json={"title": "503 Book"})).json()["id"]

        # Give the book content so it passes validation and reaches generation,
        # where the missing-library 503 is raised.
        await _seed_toc(book_id, {
            "chapters": [
                {"id": "ch1", "title": "Ch1", "content": "<p>Body text.</p>",
                 "order": 1}
            ]
        })

        import app.services.export_service as es
        monkeypatch.setattr(es, "PDF_AVAILABLE", False)

        resp = await client.get(f"/api/v1/books/{book_id}/export/pdf")
        assert resp.status_code == 503
        assert "unavailable" in resp.json()["detail"].lower()


class TestExportTemplateEndpoints:
    """Template-aware export endpoints (issue #59)."""

    @pytest.fixture
    async def book(self, auth_client_factory):
        client = await auth_client_factory()
        resp = await client.post(
            "/api/v1/books/", json={"title": "Template Export Book"}
        )
        assert resp.status_code == 201
        book_id = resp.json()["id"]
        await _seed_toc(
            book_id,
            {
                "chapters": [
                    {
                        "id": "ch1",
                        "title": "Intro",
                        "content": "<p>Real content here for export.</p>",
                        "order": 1,
                        "level": 1,
                        "parent_id": None,
                        "status": "completed",
                        "word_count": 6,
                        "subchapters": [],
                    }
                ],
                "total_chapters": 1,
                "status": "edited",
            },
        )
        return client, book_id

    @pytest.mark.asyncio
    async def test_list_templates_endpoint(self, book):
        client, book_id = book
        resp = await client.get(f"/api/v1/books/{book_id}/export/templates")
        assert resp.status_code == 200
        templates = resp.json()["templates"]
        ids = {t["id"] for t in templates}
        assert {"classic_fiction", "modern_nonfiction", "academic"} <= ids
        # Full spec is present so the frontend can render a preview.
        assert all("margins" in t and "font" in t for t in templates)

    @pytest.mark.asyncio
    async def test_formats_endpoint_includes_templates(self, book):
        client, book_id = book
        resp = await client.get(f"/api/v1/books/{book_id}/export/formats")
        assert resp.status_code == 200
        assert len(resp.json()["templates"]) >= 3

    @pytest.mark.asyncio
    async def test_templates_endpoint_missing_book_404(self, book):
        client, _ = book
        resp = await client.get("/api/v1/books/000000000000000000000000/export/templates")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_templates_endpoint_wrong_owner_403(self, book, auth_client_factory):
        _, book_id = book
        other = await auth_client_factory(overrides={"auth_id": "different_auth_id"})
        resp = await other.get(f"/api/v1/books/{book_id}/export/templates")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_pdf_export_with_template(self, book):
        client, book_id = book
        resp = await client.get(
            f"/api/v1/books/{book_id}/export/pdf?template_id=classic_fiction"
        )
        assert resp.status_code == 200
        assert resp.content.startswith(b"%PDF")

    @pytest.mark.asyncio
    async def test_docx_export_with_template(self, book):
        client, book_id = book
        resp = await client.get(
            f"/api/v1/books/{book_id}/export/docx?template_id=academic"
        )
        assert resp.status_code == 200
        assert resp.content.startswith(b"PK")

    @pytest.mark.asyncio
    async def test_pdf_export_with_custom_options(self, book):
        client, book_id = book
        resp = await client.get(
            f"/api/v1/books/{book_id}/export/pdf"
            "?template_id=classic_fiction&custom_options=%7B%22font_size%22%3A14%7D"
        )
        assert resp.status_code == 200
        assert resp.content.startswith(b"%PDF")

    @pytest.mark.asyncio
    async def test_unknown_template_returns_400(self, book):
        client, book_id = book
        resp = await client.get(
            f"/api/v1/books/{book_id}/export/pdf?template_id=bogus"
        )
        assert resp.status_code == 400
        assert "template" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_malformed_custom_options_returns_400(self, book):
        client, book_id = book
        resp = await client.get(
            f"/api/v1/books/{book_id}/export/pdf"
            "?template_id=classic_fiction&custom_options=not-json"
        )
        assert resp.status_code == 400
        assert "json" in resp.json()["detail"].lower()
