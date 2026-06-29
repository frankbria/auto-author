# Issue #60 — [P2.3] Implement EPUB export format

Adapted from CodeRabbit/Traycer plan, verified against the codebase. Mirrors the
existing PDF/DOCX pattern exactly — no architectural fork. Branch: `feature/60-epub-export`.

## Backend
- [ ] Add `ebooklib==0.20` to `backend/pyproject.toml` deps + `requirements.in`; regen `uv.lock` + `requirements.txt`.
- [ ] `export_service.py`: guarded `import ebooklib` → `EPUB_AVAILABLE`.
- [ ] `generate_epub(book_data, chapters) -> bytes` (async + `_build_epub` worker thread). Title page + per-chapter `EpubHtml`, `EpubNcx`/`EpubNav`, spine. Reuse `_clean_html_content`. Raise `ExportUnavailableError` when lib missing.
- [ ] `export_book()`: add `elif fmt == 'epub'` dispatch (no page_size).
- [ ] `export.py`: `GET /export/epub` endpoint (auth, ownership, log_access `export_epub`, rate limit 10/h, StreamingResponse `application/epub+zip`, 503 guard). Import `EPUB_AVAILABLE`.
- [ ] `/formats`: add EPUB descriptor with `available: EPUB_AVAILABLE`.

## Frontend
- [ ] `types/export.ts`: `ExportFormat = 'pdf' | 'docx' | 'epub'`.
- [ ] `ExportOptionsModal.tsx`: EPUB RadioGroupItem (green icon). Page-size block already gated on pdf.
- [ ] `bookClient.ts`: `exportEPUB(bookId, {includeEmptyChapters})`.
- [ ] book `page.tsx` `handleExport`: `else if (options.format === 'epub')` branch.

## Tests (TDD)
- [ ] backend: `generate_epub` valid EPUB zip (mimetype, chapters present), `export_book('epub')`, availability guard, endpoint happy/404/403, formats lists epub.
- [ ] frontend: ExportOptionsModal renders+selects EPUB; bookClient.exportEPUB URL.

## Notes
- "Tested in Kindle/Kobo/Apple Books" = manual; covered by EPUB-structure assertions in tests.
