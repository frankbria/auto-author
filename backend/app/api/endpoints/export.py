"""
Export endpoints for generating PDF and DOCX files
"""
import json
import logging
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from app.api.dependencies import get_rate_limiter
from app.core.security import get_current_user_from_session
from app.db.book import get_book_by_id
from app.services.export_service import (
    export_service,
    ExportUnavailableError,
    ExportValidationError,
    ExportTimeoutError,
    PDF_AVAILABLE,
    DOCX_AVAILABLE,
    EPUB_AVAILABLE,
    HTML2TEXT_AVAILABLE,
)
from app.services.export_templates import list_templates
from app.services.chapter_access_service import chapter_access_service
from app.core.config import settings
from datetime import datetime, timezone
import io

router = APIRouter(
    prefix="/books/{book_id}/export",
    tags=["export"],
)

logger = logging.getLogger(__name__)


def _parse_custom_options(raw: Optional[str]) -> Optional[Dict]:
    """Parse the optional custom_options JSON string, 400 on malformed input."""
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        raise HTTPException(
            status_code=400, detail="custom_options must be valid JSON"
        ) from e
    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=400, detail="custom_options must be a JSON object"
        )
    return parsed


@router.get("/pdf")
async def export_book_pdf(
    book_id: str,
    current_user: Dict = Depends(get_current_user_from_session),
    include_empty_chapters: bool = Query(
        False,
        description="Include chapters without content"
    ),
    page_size: str = Query(
        "letter",
        description="Page size (letter or A4)",
        pattern="^(letter|A4)$"
    ),
    template_id: Optional[str] = Query(
        None, description="Professional export template id (see /export/templates)"
    ),
    custom_options: Optional[str] = Query(
        None, description="JSON object of template overrides (font_size, margins, ...)"
    ),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=10, window=3600)),  # 10 exports per hour
):
    """
    Export a book as a PDF file.

    Returns a PDF file with all book content formatted for reading.
    """
    # Get book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to export this book"
        )

    parsed_custom_options = _parse_custom_options(custom_options)

    # Log the export request
    try:
        await chapter_access_service.log_access(
            user_id=current_user.get("auth_id"),
            book_id=book_id,
            chapter_id=None,  # Book-level access
            access_type="export_pdf",
            metadata={
                "include_empty_chapters": include_empty_chapters,
                "page_size": page_size,
                "template_id": template_id,
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception:
        logger.error("Failed to log export access", exc_info=True)

    try:
        # Generate PDF
        pdf_content = await export_service.export_book(
            book_data=book,
            format="pdf",
            include_empty_chapters=include_empty_chapters,
            page_size=page_size,
            timeout_seconds=settings.EXPORT_TIMEOUT_SECONDS,
            template_id=template_id,
            custom_options=parsed_custom_options,
        )

        # Create filename
        safe_title = "".join(
            c for c in book.get("title", "untitled")
            if c.isalnum() or c in (' ', '-', '_')
        ).rstrip()
        filename = f"{safe_title}.pdf"

        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(pdf_content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_content)),
            }
        )

    except ExportValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except KeyError as e:
        raise HTTPException(
            status_code=400, detail=f"Unknown export template: {template_id}"
        ) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ExportTimeoutError as e:
        logger.warning("PDF export timed out for book %s", book_id)
        raise HTTPException(status_code=504, detail=str(e)) from e
    except ExportUnavailableError as e:
        logger.warning("PDF export unavailable: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception:
        logger.error("Failed to generate PDF", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate PDF"
        )


@router.get("/docx")
async def export_book_docx(
    book_id: str,
    current_user: Dict = Depends(get_current_user_from_session),
    include_empty_chapters: bool = Query(
        False,
        description="Include chapters without content"
    ),
    template_id: Optional[str] = Query(
        None, description="Professional export template id (see /export/templates)"
    ),
    custom_options: Optional[str] = Query(
        None, description="JSON object of template overrides (font_size, margins, ...)"
    ),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=10, window=3600)),  # 10 exports per hour
):
    """
    Export a book as a DOCX (Microsoft Word) file.

    Returns a DOCX file with all book content formatted for editing.
    """
    # Get book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to export this book"
        )

    parsed_custom_options = _parse_custom_options(custom_options)

    # Log the export request
    try:
        await chapter_access_service.log_access(
            user_id=current_user.get("auth_id"),
            book_id=book_id,
            chapter_id=None,  # Book-level access
            access_type="export_docx",
            metadata={
                "include_empty_chapters": include_empty_chapters,
                "template_id": template_id,
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception:
        logger.error("Failed to log export access", exc_info=True)

    try:
        # Generate DOCX
        docx_content = await export_service.export_book(
            book_data=book,
            format="docx",
            include_empty_chapters=include_empty_chapters,
            timeout_seconds=settings.EXPORT_TIMEOUT_SECONDS,
            template_id=template_id,
            custom_options=parsed_custom_options,
        )

        # Create filename
        safe_title = "".join(
            c for c in book.get("title", "untitled")
            if c.isalnum() or c in (' ', '-', '_')
        ).rstrip()
        filename = f"{safe_title}.docx"

        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(docx_content),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(docx_content)),
            }
        )

    except ExportValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except KeyError as e:
        raise HTTPException(
            status_code=400, detail=f"Unknown export template: {template_id}"
        ) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ExportTimeoutError as e:
        logger.warning("DOCX export timed out for book %s", book_id)
        raise HTTPException(status_code=504, detail=str(e)) from e
    except ExportUnavailableError as e:
        logger.warning("DOCX export unavailable: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception:
        logger.error("Failed to generate DOCX", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate DOCX"
        )


@router.get("/epub")
async def export_book_epub(
    book_id: str,
    current_user: Dict = Depends(get_current_user_from_session),
    include_empty_chapters: bool = Query(
        False,
        description="Include chapters without content"
    ),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=10, window=3600)),  # 10 exports per hour
):
    """
    Export a book as an EPUB file.

    Returns an EPUB 3.0 file optimized for ereaders (Kindle, Kobo, Apple Books).
    """
    # Get book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to export this book"
        )

    # Log the export request
    try:
        await chapter_access_service.log_access(
            user_id=current_user.get("auth_id"),
            book_id=book_id,
            chapter_id=None,  # Book-level access
            access_type="export_epub",
            metadata={
                "include_empty_chapters": include_empty_chapters,
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception:
        logger.error("Failed to log export access", exc_info=True)

    try:
        # Generate EPUB
        epub_content = await export_service.export_book(
            book_data=book,
            format="epub",
            include_empty_chapters=include_empty_chapters,
            timeout_seconds=settings.EXPORT_TIMEOUT_SECONDS,
        )

        # Create filename
        safe_title = "".join(
            c for c in book.get("title", "untitled")
            if c.isalnum() or c in (' ', '-', '_')
        ).rstrip()
        filename = f"{safe_title}.epub"

        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(epub_content),
            media_type="application/epub+zip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(epub_content)),
            }
        )

    except ExportValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ExportTimeoutError as e:
        logger.warning("EPUB export timed out for book %s", book_id)
        raise HTTPException(status_code=504, detail=str(e)) from e
    except ExportUnavailableError as e:
        logger.warning("EPUB export unavailable: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception:
        logger.error("Failed to generate EPUB", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate EPUB"
        )


@router.get("/markdown")
async def export_book_markdown(
    book_id: str,
    current_user: Dict = Depends(get_current_user_from_session),
    include_empty_chapters: bool = Query(
        False,
        description="Include chapters without content"
    ),
    multi_file: bool = Query(
        False,
        description="Export one Markdown file per chapter as a ZIP archive"
    ),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=10, window=3600)),  # 10 exports per hour
):
    """
    Export a book as Markdown.

    Returns a single ``.md`` file, or (with ``multi_file=true``) a ZIP archive
    containing one Markdown file per chapter — ideal for version control and
    platform compatibility.
    """
    # Get book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to export this book"
        )

    # Log the export request
    try:
        await chapter_access_service.log_access(
            user_id=current_user.get("auth_id"),
            book_id=book_id,
            chapter_id=None,  # Book-level access
            access_type="export_markdown",
            metadata={
                "include_empty_chapters": include_empty_chapters,
                "multi_file": multi_file,
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception:
        logger.error("Failed to log export access", exc_info=True)

    try:
        # Generate Markdown
        md_content = await export_service.export_book(
            book_data=book,
            format="markdown",
            include_empty_chapters=include_empty_chapters,
            timeout_seconds=settings.EXPORT_TIMEOUT_SECONDS,
            multi_file=multi_file,
        )

        # Create filename
        safe_title = "".join(
            c for c in book.get("title", "untitled")
            if c.isalnum() or c in (' ', '-', '_')
        ).rstrip()
        if multi_file:
            filename = f"{safe_title}_chapters.zip"
            media_type = "application/zip"
        else:
            filename = f"{safe_title}.md"
            media_type = "text/markdown"

        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(md_content),
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(md_content)),
            }
        )

    except ExportValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ExportTimeoutError as e:
        logger.warning("Markdown export timed out for book %s", book_id)
        raise HTTPException(status_code=504, detail=str(e)) from e
    except ExportUnavailableError as e:
        logger.warning("Markdown export unavailable: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.error("Failed to generate Markdown", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate Markdown"
        ) from e


@router.get("/formats")
async def get_export_formats(
    book_id: str,
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Get available export formats and their options.
    """
    # Verify book exists and user has access
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this book"
        )

    # Return available formats, flagging which are actually functional based on
    # whether their backing libraries are installed.
    return {
        "formats": [
            {
                "format": "pdf",
                "name": "PDF Document",
                "description": "Portable Document Format - ideal for reading and printing",
                "mime_type": "application/pdf",
                "extension": ".pdf",
                "available": PDF_AVAILABLE,
                "options": {
                    "page_size": ["letter", "A4"],
                    "include_empty_chapters": "boolean"
                }
            },
            {
                "format": "docx",
                "name": "Word Document",
                "description": "Microsoft Word format - ideal for further editing",
                "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "extension": ".docx",
                "available": DOCX_AVAILABLE,
                "options": {
                    "include_empty_chapters": "boolean"
                }
            },
            {
                "format": "epub",
                "name": "EPUB Ebook",
                "description": "EPUB format - optimized for ereaders and ebook platforms",
                "mime_type": "application/epub+zip",
                "extension": ".epub",
                "available": EPUB_AVAILABLE,
                "options": {
                    "include_empty_chapters": "boolean"
                }
            },
            {
                "format": "markdown",
                "name": "Markdown Document",
                "description": "Markdown format - ideal for version control and platform compatibility",
                "mime_type": "text/markdown",
                "extension": ".md",
                "available": HTML2TEXT_AVAILABLE,
                "options": {
                    "include_empty_chapters": "boolean",
                    "multi_file": "boolean"
                }
            }
        ],
        "book_stats": export_service.book_stats(book),
        "templates": list_templates(),
    }


@router.get("/templates")
async def get_export_templates(
    book_id: str,
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    List the available professional export templates (full spec).

    The frontend renders these directly as the template preview before export.
    """
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this book"
        )

    return {"templates": list_templates()}
