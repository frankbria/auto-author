# Issue #194 — [P2.2] Legacy export page offers EPUB/Markdown but errors 'not yet implemented'

**Branch**: `fix/194-legacy-export-epub-markdown`
**Plan source**: CodeRabbit comment (design choice resolved: **wire**, not filter/delete). Verified against codebase 2026-07-12.

## Fork resolution (autonomous)

Issue AC offers wire OR filter OR remove. CodeRabbit chose **wire**; exploration confirms:
- The page is real and functional for PDF/DOCX (unlike #193's fabricated page) — URL-reachable, no trust defect.
- Nothing in production links to it, but delete has wider blast radius: `tests/e2e/page-objects/export.page.ts` + deployment specs + `ChapterBreadcrumb` pathname check.
- `bookClient.exportEPUB(bookId, {includeEmptyChapters})` and `exportMarkdown(bookId, {includeEmptyChapters, multiFile})` exist and match the plan's claimed signatures (verified `bookClient.ts:1733,1762`).

## Plan corrections found in exploration

1. **Plan defect**: "Leave `handleDownload` unchanged" is WRONG for markdown+multiFile — backend returns a ZIP but `format.extension` is `.md` (backend `export.py:528`). Fix: extension override to `.zip` when `selectedFormat==='markdown' && multiFile` (mirrors #61's `generateFilename` extensionOverride).
2. **Dead code**: `getStatusColor`/`getStatusText` in page.tsx defined but never used in JSX — delete (also helps the first-tests coverage-denominator gotcha from #247).

## Tasks

- [x] 1. Tests first (RED): new `src/app/dashboard/books/[bookId]/export/__tests__/page.test.tsx`
  - dispatch pins: pdf→exportPDF(pageSize+includeEmpty), docx→exportDOCX(includeEmpty), epub→exportEPUB(includeEmpty), markdown→exportMarkdown(includeEmpty+multiFile)
  - NO "not yet implemented" toast for epub/markdown (the regression pin)
  - markdown+multiFile download → filename ends `.zip`; markdown single-file → `.md`; pdf → `.pdf`
  - options UI: epub shows include-empty toggle; markdown shows include-empty + multi-file toggles
  - export summary reflects epub/markdown selections
  - extend `timeEstimator.test.ts`: `export.epub`/`export.markdown` budgets exist and estimate ≠ default fallback
- [x] 2. `timeEstimator.ts`: add `export.epub` + `export.markdown` budgets (modeled on docx; markdown lighter); widen `OperationMetadata.exportFormat` to include `'epub' | 'markdown'`
- [x] 3. `page.tsx`:
  - `multiFile` state (default false)
  - handleExport branches for epub/markdown (keep trailing else as unknown-format guard)
  - handleDownload `.zip` override for markdown+multiFile
  - icon map: epub 📖, markdown 📋 explicit
  - options blocks for epub/markdown; summary lines
  - getProgress: map selectedFormat → `export.{format}` key
  - delete dead getStatusColor/getStatusText
- [x] 4. GREEN: full frontend suite + lint + typecheck; coverage gates (page now in denominator)
- [x] 5. Deslop scan
- [x] 6. Pre-PR third-party review (opencode GLM primary, codex fallback)
- [x] 7. PR, post-PR review posted as comment
- [x] 8. Demo (hard gate): real servers, branch vs main — main shows "not yet implemented" toast for EPUB/Markdown; branch downloads real .epub/.md/.zip files (verify file magic bytes)
- [x] 9. CI green + final triage → docs sync → merge

## Acceptance criteria (from issue)

- [x] Selecting EPUB on the legacy export page produces a working export (no "not yet implemented")
- [x] Selecting Markdown likewise, including multi-file (ZIP) option
- [x] PDF/DOCX behavior unchanged

## Rider (user request, same PR)

- [x] Diagnosed Deploy-to-Staging failures on main: first-contact SSH timeout when two deploys race (not fail2ban — zero bans logged); staging was one commit stale (#278 never deployed)
- [x] Fix in deploy-staging.yml: concurrency group (serialize, no mid-flight cancel) + upload retried 3x/60s + ConnectTimeout=30; actionlint clean
- [x] Post-merge deploy run 29214388329 SUCCESS; release 20260713-000155 live; #194 marker present in deployed bundle; api+frontend health green
