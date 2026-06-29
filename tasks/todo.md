# Issue #59 — [P2.2] Professional export templates for PDF and DOCX

Blocked-by #49 is **closed** → unblocked. Branch: `feature/59-export-templates`.

## Acceptance Criteria (the real target)
- [ ] ≥3 professional templates available
- [ ] Template preview shows before export
- [ ] PDF output meets professional standards (margins, font, headers/footers)
- [ ] DOCX output uses proper styles
- [ ] Templates support customization
- [ ] Fonts, margins, headers configurable
- [ ] Output suitable for print-on-demand (POD margins)
- [ ] E2E test verifies template export

## Adapted plan (lean — diverges from the traycer plan on purpose)

### Backend
1. `backend/app/services/export_templates.py` — a `TEMPLATES` dict registry (3 templates:
   `classic_fiction`, `modern_nonfiction`, `academic`) + `list_templates()`, `get_template(id)`,
   `resolve_template(id, custom_options)` (merge user overrides). Each template = page_size,
   margins (top/bottom/inside/outside, POD-safe >=0.5"), font family, font_size, line_height (leading),
   first_line_indent, header (left/right), footer.
   - *Skipped vs traycer:* separate `template_service.py` + Pydantic `export_template.py` models +
     JSON files + a validator. A dict literal + dict-merge is the registry. `ponytail:`
2. `export_service.py` — `_build_pdf`/`generate_pdf` and `_build_docx`/`generate_docx` accept
   `template: Optional[Dict]`. Apply margins, base font, size, leading, indent; add a running
   header + page-number footer via reportlab `onPage` callbacks; DOCX sets Normal/Heading fonts +
   section header/footer. `template=None` -> **current behavior unchanged** (backward compat).
   - Font reality: reportlab ships only base-14 (Helvetica/Times/Courier). Map serif->Times-Roman,
     sans->Helvetica. DOCX uses font-name strings Word resolves locally (Garamond/Calibri/TNR fine).
     `ponytail:` name the ceiling, no TTF embedding.
   - *Skipped:* PDF/A-1b verification, font-embedding checks, drop caps, footnotes,
     gutter-by-page-count, recto/verso alternating headers.
3. `export.py` endpoints — add `template_id` + `custom_options` (JSON str) query params to `/pdf`
   and `/docx`; thread through `export_book`. Add `GET /books/{id}/export/templates` returning the
   spec list (this *is* the preview data — no preview images).

### Frontend
4. `types/export.ts` — `ExportTemplate`, `TemplateCustomization`; extend `ExportOptions` with
   `templateId?` + `customization?`.
5. `components/export/TemplateSelector.tsx` — radio cards (name/description/best-for) + an inline
   **spec preview** (page size, margins, font, spacing) = "preview before export". Includes a small
   collapsible customization (font size + margin override) = "supports customization".
   - *Skipped:* separate `TemplatePreview` modal, comparison view, react-hook-form/zod panel.
6. Integrate `TemplateSelector` into the dedicated export page
   (`app/dashboard/books/[bookId]/export/page.tsx`, the navigable/demoable flow) **and**
   `ExportOptionsModal.tsx`. Pass `templateId`/`customization` to bookClient.
7. `lib/api/bookClient.ts` — `getExportTemplates(bookId)`; add `templateId`/`customization` to
   `exportPDF`/`exportDOCX` URL params.

### Tests
8. Backend: `tests/test_services/test_export_templates.py` (registry, get/list, merge);
   extend `test_export_service.py` (export with each template applies margins/font, header present);
   extend `test_api/test_export_endpoints.py` (template_id param, /templates list, custom_options,
   bad template_id).
9. Frontend: `TemplateSelector.test.tsx`; extend `ExportOptionsModal.test.tsx`.
10. E2E: route-mocked `src/e2e/export-templates.spec.ts` (select template -> preview -> export).

### Docs
11. `backend/app/templates/export/README.md` (template structure) + user-manual section. *Skipped:*
    preview-image assets.

## Quality gates
- Backend `pytest --cov=app --cov-fail-under=85`; frontend jest 85/85/75/85; lint+typecheck; E2E.
- TDD: tests first per chunk.
