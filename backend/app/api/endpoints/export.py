"""
Export endpoints for generating PDF and DOCX files
"""
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from app.api.dependencies import get_rate_limiter
from app.core.security import get_current_user
from app.db.book import get_book_by_id
from app.services.export_service import export_service
from app.services.chapter_access_service import chapter_access_service
from datetime import datetime, timezone
import io

router = APIRouter(
    prefix="/books/{book_id}/export",
    tags=["export"],
)


@router.get("/pdf")
async def export_book_pdf(
    book_id: str,
    current_user: Dict = Depends(get_current_user),
    include_empty_chapters: bool = Query(
        False, 
        description="Include chapters without content"
    ),
    page_size: str = Query(
        "letter",
        description="Page size (letter or A4)",
        pattern="^(letter|A4)$"
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
    
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to export this book"
        )
    
    # Log the export request
    try:
        await chapter_access_service.log_access(
            user_id=current_user.get("clerk_id"),
            book_id=book_id,
            chapter_id=None,  # Book-level access
            access_type="export_pdf",
            metadata={
                "include_empty_chapters": include_empty_chapters,
                "page_size": page_size,
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as e:
        print(f"Failed to log export access: {e}")
    
    try:
        # Generate PDF
        pdf_content = await export_service.export_book(
            book_data=book,
            format="pdf",
            include_empty_chapters=include_empty_chapters,
            page_size=page_size
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
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PDF: {str(e)}"
        )


@router.get("/docx")
async def export_book_docx(
    book_id: str,
    current_user: Dict = Depends(get_current_user),
    include_empty_chapters: bool = Query(
        False,
        description="Include chapters without content"
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
    
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to export this book"
        )
    
    # Log the export request
    try:
        await chapter_access_service.log_access(
            user_id=current_user.get("clerk_id"),
            book_id=book_id,
            chapter_id=None,  # Book-level access
            access_type="export_docx",
            metadata={
                "include_empty_chapters": include_empty_chapters,
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as e:
        print(f"Failed to log export access: {e}")
    
    try:
        # Generate DOCX
        docx_content = await export_service.export_book(
            book_data=book,
            format="docx",
            include_empty_chapters=include_empty_chapters
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
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate DOCX: {str(e)}"
        )


@router.get("/formats")
async def get_export_formats(
    book_id: str,
    current_user: Dict = Depends(get_current_user),
):
    """
    Get available export formats and their options.
    """
    # Verify book exists and user has access
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this book"
        )
    
    # Return available formats
    return {
        "formats": [
            {
                "format": "pdf",
                "name": "PDF Document",
                "description": "Portable Document Format - ideal for reading and printing",
                "mime_type": "application/pdf",
                "extension": ".pdf",
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
                "options": {
                    "include_empty_chapters": "boolean"
                }
            }
        ],
        "book_stats": {
            "total_chapters": len(book.get("table_of_contents", {}).get("chapters", [])),
            "chapters_with_content": sum(
                1 for ch in book.get("table_of_contents", {}).get("chapters", [])
                if ch.get("content", "").strip()
            )
        }
    }