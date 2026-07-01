# Issue #61 — [P3.3] Implement Markdown export format

**Branch**: `feature/issue-61-markdown-export`
Mirror the EPUB pattern (#147). Fourth export format alongside PDF/DOCX/EPUB.

## Scope decisions (adapted from Traycer/CodeRabbit plans)
- **Keep**: single-file `.md` + multi-file `.zip` (AC explicitly requires "single file vs. multiple files"); images preserved (`ignore_images=False`); `/markdown` endpoint; `/formats` entry.
- **Drop (YAGNI)**: GFM-vs-standard flavor toggle — not in AC; html2text output is already standard/GitHub-compatible Markdown.
- **Leave alone**: dedicated `export/page.tsx` (only does pdf/docx, already lacks EPUB — same as #147 left it). Primary path is `page.tsx` → `ExportOptionsModal`.

## Backend
- [ ] `export_service.generate_markdown(book_data, chapters, multi_file=False)` → async, `asyncio.to_thread(_build_markdown)`. Single: UTF-8 `# title` + metadata + `## Chapter N: title` + html2text(content, images on). Multi: zip of `NN-slug.md` per chapter. Guard `HTML2TEXT_AVAILABLE` → `ExportUnavailableError`.
- [ ] `export_book()`: add `multi_file` param + `'markdown'`/`'md'` dispatch.
- [ ] `/markdown` endpoint (mirror EPUB): `include_empty_chapters` + `multi_file` query; auth/ownership/rate-limit; `text/markdown` or `application/zip`; `access_type="export_markdown"`.
- [ ] `/formats`: add markdown entry (`available: HTML2TEXT_AVAILABLE`, options incl. `multi_file`).
- [ ] Tests: service + endpoint. Update `len(formats)==3`->`4` + availability dict.

## Frontend
- [ ] `ExportFormat` += `'markdown'`; `ExportOptions` += `markdownMultiFile?`.
- [ ] `ExportOptionsModal`: markdown radio option + "Separate file per chapter" switch (markdown-only).
- [ ] `bookClient.exportMarkdown(bookId, {includeEmptyChapters, multiFile})`.
- [ ] `page.tsx` handleExport: route markdown; filename `.md` (single) / `.zip` (multi).
- [ ] `generateFilename`: map `markdown`->`md`. Fix stale `validateExportOptions` allowlist.
- [ ] Tests: modal option + switch; bookClient URL; generateFilename md.

## Gates
- [ ] Backend pytest --cov >=85; frontend gates 85/85/75/85; lint/typecheck; E2E green; demo AC.
