"""Importing the upload module must not build the upload service.

#941 made every book response import ``is_own_cover_url`` from this module. A
module-level ``FileUploadService()`` then ran on the first book list, and on a
box with no cloud storage and no writable ``uploads/`` it raised, so every
``GET /books`` answered 500 on staging.
"""

import importlib
from pathlib import Path

import pytest

import app.services.file_upload_service as fus
from app.schemas.book import BookResponse

BOOK_ID = "64b0c0ffee0000000000aaaa"
OWN_COVER = f"/uploads/cover_images/{BOOK_ID}_{'a' * 32}.jpg"


@pytest.fixture
def uploads_unavailable(monkeypatch):
    """Staging's container: no cloud storage, and uploads/ cannot be created."""
    def refuse(self, *args, **kwargs):
        raise PermissionError(13, "Permission denied", str(self))

    monkeypatch.setattr(Path, "mkdir", refuse)
    yield
    monkeypatch.undo()
    importlib.reload(fus)


def test_importing_the_module_does_not_build_the_service(uploads_unavailable):
    importlib.reload(fus)


def test_a_book_with_a_cover_serializes_when_uploads_are_unavailable(uploads_unavailable):
    importlib.reload(fus)
    book = BookResponse(
        id=BOOK_ID,
        title="t",
        owner_id="o",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        cover_image_url=OWN_COVER,
    )
    assert book.cover_image_url == OWN_COVER
