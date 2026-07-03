# Claude Code Configuration - SPARC Development Environment

## 🚨 CRITICAL: CONCURRENT EXECUTION & FILE MANAGEMENT

**ABSOLUTE RULES**:
1. ALL operations MUST be concurrent/parallel in a single message
2. **NEVER save working files, text/mds and tests to the root folder**
3. ALWAYS organize files in appropriate subdirectories

### ⚡ GOLDEN RULE: "1 MESSAGE = ALL RELATED OPERATIONS"

**MANDATORY PATTERNS:**
- **TodoWrite**: ALWAYS batch ALL todos in ONE call (5-10+ todos minimum)
- **Task tool**: ALWAYS spawn ALL agents in ONE message with full instructions
- **File operations**: ALWAYS batch ALL reads/writes/edits in ONE message
- **Bash commands**: ALWAYS batch ALL terminal operations in ONE message
- **Memory operations**: ALWAYS batch ALL memory store/retrieve in ONE message

### 📁 File Organization Rules

**NEVER save to root folder. Use these directories:**
- `/src` - Source code files
- `/tests` - Test files
- `/docs` - Documentation and markdown files
- `/config` - Configuration files
- `/scripts` - Utility scripts
- `/examples` - Example code

---

## Recent Changes

### 2026-07-02
- **Complete account settings (#64, P3.6)**: full-stack. Adapted the CodeRabbit plan (2026-06-21), which had drifted on 5 counts — the settings page was **not** a stub (theme/email toggles already saved with a load-guard), the style list was the pre-#55 six, export lacked EPUB/Markdown, `userClient.ts` was superseded by `useProfileApi`, and its "Active Sessions via backend `/sessions/list`" targeted **dead infrastructure** (app-session middleware keys off `request.state.user`, which nothing sets post-better-auth → list always empty). Sessions use better-auth native `listSessions`/`revokeSession`/`revokeOtherSessions` instead.
  - **Backend**: `UserPreferences` (model + schema) gains validated fields — `default_writing_style` (Literal of the 5 shipped styles), `auto_save_interval` (3–30s, default 3 = shipped behavior), `default_export_format` (pdf/docx/epub/markdown), `default_page_size` (letter/A4), `include_empty_chapters`, `writing_reminders`, `progress_updates`, `backup_notifications`. No new endpoints — rides `PATCH /users/me`. NB: `UserUpdate.preferences` replaces the whole object (Pydantic fills omitted fields with defaults), so every client **merges loaded prefs before saving** — the page-level contract tested since #63. Notification toggles are stored contract only: the backend sends no email today (no SMTP/provider code); nothing was invented (YAGNI).
  - **Settings page** (`dashboard/settings`) → 4 Radix tabs (Writing/Export/Notifications/Security), keeping the load-before-save guard + merge-on-save. Theme select wired to next-themes `setTheme` → **applied immediately** (previously the stored theme never touched the UI). Decorative unwired controls (font size, 1–300s interval) removed. New `components/settings/*`: three controlled pref forms + `PasswordChangeForm` (better-auth `changePassword`, `revokeOtherSessions: true`), `TwoFactorSetup` (TOTP via better-auth `twoFactor` plugin: password → QR (`react-qr-code`) + copyable backup codes → verify), `ActiveSessionsList`.
  - **2FA plumbing**: `auth.ts` adds `appName` + `twoFactor()` plugin (Mongo adapter needs no migration); `auth-client.ts` adds `twoFactorClient` with redirect → new `/auth/verify-2fa` page (6-digit auto-submit, trust-device, backup-code path). **Sign-in fix**: the page unconditionally `router.push`ed after non-error sign-in — now returns early on `twoFactorRedirect` so it can't race the 2FA redirect to `/dashboard`. The auth-client cast was rebuilt (`typeof baseAuthClient & …`) so plugin method types survive.
  - **Prefs applied app-wide** via new cached `useUserPreferences` hook (one GET per page load; settings save calls `invalidateUserPreferencesCache`): `DraftGenerator`/`DraftGenerationButton` pre-select the default style (touched-guard so user picks win; shared `lib/constants/writing-styles` replaces duplicated arrays), `ExportOptionsModal` seeds format/page-size/include-empty, `ChapterEditor` auto-save delay = `auto_save_interval` (shared `lib/constants/auto-save`, invalid → 3s).
  - **Jest gotcha**: suites load the **real** `auth-client.ts` safely only because `better-auth/react` is moduleNameMapper'd to a mock — the new `better-auth/client/plugins` import (ESM-only) broke every such suite until mapped to `__mocks__/better-auth-client-plugins.ts`. Global mocks extended (authClient security methods, `useUserPreferences` → null so consumers keep shipped defaults; override per-suite for regression tests). Also: Radix `TabsTrigger` doesn't activate on `fireEvent.click` (mousedown-based) — use `userEvent.click`. A full-suite run alongside the dev server + Playwright produced 35 **contention flakes** (all pass isolated and in a quiet full run) — don't debug "failures" while a Next dev server is compiling.
  - **Reviews (pre-PR)**: CodeRabbit CLI (8 findings) — 5 fixed (verify-2fa missing catch on transport failure; cache-clobber race → generation counter; disable-2FA status stuck "Enabled" until session refetch → `localEnabledOverride` both directions; manual TOTP secret fallback beside the QR; missing `progress_updates` round-trip assert), 1 partially adopted (E2E failed-save + revoke-session cases added; full 2FA E2E skipped — unit-covered, plugin internals brittle to route-mock), 2 rebutted (native `<select>` is the #63 profile pattern — labeled, jsdom-testable; null-not-cached is intentional retry-on-error). Self-review also caught the **sign-in/2FA race** above. Report: `docs/code-review/2026-07-02-account-settings-review.md`.
  - **Tests**: backend preference validation/persistence (15, incl. 422 bounds + direct-Mongo round-trip — GET /users/me echoes the mocked session user in the harness, so persistence asserts against the collection); frontend settings page (10), security components (11), verify-2fa (4), `useUserPreferences` cache (4), applied-defaults regressions (7, incl. auto-save waits-for-10s test); route-mocked E2E `settings.spec.ts` (**5 passed**: merged-PATCH save, export-tab defaults, failed-save keeps edits, revoke-session, password change via `/api/auth/change-password`). Frontend **2003 passed / 8 skipped, 108/108 suites**, coverage 89.96/81.04/86.51/91.2; backend **1034 passed / 14 skipped, 91.87% cov**. **Local-env gotcha**: `backend/.env` had `BYPASS_AUTH=true` (leftover) — it makes exactly the auth-assertion tests fail (401-expected, role-forbidden, session-middleware); run backend suites with `BYPASS_AUTH=false` locally.
  - **Demo round (real better-auth, no bypass — signup→settings→2FA)** caught two real issues the unit/E2E nets missed, fixed post-PR: (1) **theme was invisible** — `tailwind.config.js` hardcoded dark RGBs for card/muted/accent/secondary/popover and pointed background/foreground at `var(--color-*)` names that only exist in the Tailwind-**v4** `@theme inline` block, which this **v3** project ignores (so `bg-background` never resolved). Config now reads the real `:root`/`.dark` variables — `.dark` values match the old RGBs, so the default dark look is pixel-equivalent, and Light genuinely flips the dashboard shell (root/dashboard layouts moved off `bg-gray-950` to tokens; brand indigo/destructive stay fixed). (2) **theme-change clobbered edits**: syncing the stored theme on load put next-themes' `setTheme` in `loadPreferences`' deps; its identity changes after a theme change → loader re-fired → wiped in-progress edits and reverted the theme. Fixed with a setTheme ref + once-per-visit sync guard; regression test makes the mock return a fresh `setTheme` identity per render. **Demo verified end-to-end**: prefs PATCH→reload persistence; light/dark immediate + on-load; full TOTP loop (enable → QR + manual secret + backup codes → verify with a Python-computed RFC-6238 code → sign-out → sign-in lands on `/auth/verify-2fa` → fresh code auto-submits → dashboard). NB `agent-browser click @ref` doesn't reliably fire React handlers on this page — use `eval` `.click()`; snapshot refs go stale after every `open`.
  - **Status**: ✅ Complete

### 2026-07-01
- **Complete user profile editing (#63, P3.5)**: PR #170 — full-stack. The backend user model + `GET/PATCH/DELETE /users/me` (better-auth) already existed; verified-before-building, this closed the real gaps: the missing frontend page, avatar upload, validation, and profile→export author info. **Plan drift corrected**: Traycer/CodeRabbit both mirrored `book_cover_upload.py` (**deleted in #93**) — mirrored the live cover path (`books.py` + `FileUploadService`) instead; `useOptimizedClerkImage` still exists (legacy name, the pre-existing `ProfilePage.test` requires it) so kept, not renamed; Clerk test mocks → better-auth.
  - **Frontend**: new `app/profile/page.tsx` (name/bio/preferences/avatar/delete-account) built to the **pre-existing `ProfilePage.test.tsx` contract** — which was in jest `testPathIgnorePatterns` ("missing module"); now un-ignored since the page exists. The test mocks `react-hook-form`/ui/`useProfileApi`/`useOptimizedClerkImage`, and its `useProfileApi` mock omits `getUserProfile` → the page **guards the profile fetch** and seeds initial state from `useSession()`, hydrating full data (bio/prefs) from GET /users/me when available. Only `Form`+`FormField` are mocked from `ui/form`, so the page uses a native `<form onSubmit={form.handleSubmit(onSubmit)}>` + plain `Label`/`Input`/`Switch` (no FormItem/Label/Control/Message). `useProfileApi` rewritten from Clerk-era "deprecated" throw-stubs to real cookie-auth `getUserProfile`/`updateUserProfile`/`deleteUserAccount`. New `ProfilePictureUpload` (client type/size validation, multipart POST). "Profile" nav → `/profile`.
  - **Backend**: `POST /users/me/avatar` + `FileUploadService.process_and_save_profile_picture` (fits 400×400 aspect-preserving — not cropped square, UI circles it via object-cover; single image no thumbnail). `UserUpdate` field-length limits (name ≤50, display ≤100, bio ≤1000) + `theme` Literal enum. Export author injection: the verified owner (`current_user`, no extra DB hit) supplies `author_name` (display_name → "first last") + `author_bio` merged into `book_data` for all 4 formats; PDF/DOCX render an "About the Author" section.
  - **codex (pre-PR, cross-family)** found 4, all fixed with tests: **decompression-bomb guard** in `validate_image_upload` (50MP cap, hardens cover too); **persist-before-delete-avatar** (update_user first, cleanup the new file on failure, then remove the old — no orphan / no dangling pointer); **bio XML-escaped** before ReportLab `Paragraph` (unescaped `<` would crash PDF); the relative-`/uploads` URL note is a **pre-existing app-wide pattern** (covers render `cover_image_url` the same way; prod uses cloud storage) → documented, not diverged. **Post-PR round (2026-07-02)**: a manually-triggered CodeRabbit review posted 8 findings — 5 fixed (display_name editable+persisted; `.min(1)` dropped so null-name users can save; hydration reset guarded by `isDirty`+unmount so a slow fetch can't clobber edits; errors read from public `form.formState` not private `control._formState`; PDF bio uses template-aware styles), 3 rebutted (default-export claim false — `useProfileApi.ts` has one; Vitest migration — repo is Jest; `verify()` stream concern — already re-seeks). A second `codex review` caught a real P2 the first round missed: hydration seeded `displayName` from `first_name` only when unset, so a later save persisted a **truncated author name** into exports — now seeds first+last (E2E regression test). Demo'd end-to-end with **real better-auth session** (signup→profile edit→avatar→DOCX/PDF containing "About the Author" + bio); NB the bypass-auth mock user can't demo export-author or PATCH persistence (mock isn't a DB record).
  - **Tests**: backend avatar endpoint (success/invalid-type/too-large/replaces-old/persists/401) + service (local/cloud/bomb/path-traversal) + export author (injection, real-DOCX "About the Author" bio, markup-doesn't-crash) + validation (422 over-length/bad-theme); frontend ProfilePage (7, un-ignored) + ProfilePictureUpload + useProfileApi units + route-mocked E2E `profile-editing.spec.ts` (edit→save asserts PATCH; avatar upload asserts POST + image). Backend **1024 passed / 14 skipped, 91.85% cov**; frontend **1972 passed / 8 skipped**; CI Backend/Frontend/**E2E (real backend)** all green.
  - **Status**: ✅ Complete

- **Question regeneration with improved quality (#62, P3.4)**: PR #169 — full-stack. Adapted the CodeRabbit/Traycer plan, whose **Phase 2 was stale** (it wired in `QuestionFeedbackService`/`question_quality_service`/`RefinementAction`, all deleted in #120) — dropped and replaced with a minimal rating→prompt wiring (YAGNI). Verified before building: per-question regenerate button, full-set `regenerate-questions` endpoint + `regenerateChapterQuestions`, thumbs rating UI, focus types, and rate limiting already existed.
  - **Confirmed bug fixed**: `QuestionContainer.handleRegenerateQuestion` called `bookClient.generateQuestions` (the TOC clarifying-questions method) instead of a chapter regenerate → per-question regenerate was broken. Now hits the new single-question endpoint.
  - **New endpoint** `POST /books/{id}/chapters/{cid}/questions/{qid}/regenerate` (books.py) — regenerate one question in place, ownership 403/404, rate-limited 2/180s, **429** at a per-question cap (`MAX_QUESTION_REGENERATION_COUNT=5`). Replacement is a single atomic **CAS `find_one_and_update`** on `regeneration_count` (`replace_question_in_place` in `db/questions.py`): same `_id` preserved, so there's **no delete/create data-loss window**, racing regenerations serialize (loser gets no doc → 409-style `QuestionNotFoundError`), the counter can't double-increment, and the prior **rating stays attached** (feedback isn't orphaned). The question's stale response is cleared (old answer no longer applies). AI candidate is generated **before** any mutation.
  - **Prompt quality**: both regen paths now thread **previous question texts** ("generate meaningfully different… don't repeat") + **feedback guidance** aggregated from prior low ratings (≤2★, via new `get_ratings_for_chapter`). Also fixed a **pre-existing** `audience`/`target_audience` key mismatch that silently dropped audience guidance from all generation.
  - **Frontend**: `regenerateSingleQuestion` client (parses structured error, attaches `statusCode` so the 429 cap is detected without string-matching); "Regenerate All" button → `RegenerateQuestionsDialog` (focus checkboxes + keep-answered toggle); per-question "Regenerated N/5" display, regenerate disabled at the cap **and** while a request is in flight; single-regen refreshes `cachedQuestions` + progress so stale-while-revalidate can't resurrect the replaced question.
  - **Reviews**: `codex` (pre-PR) caught the concurrency-duplicate + over-generation; CodeRabbit (post-PR) caught the delete/create loss window, the audience key bug, stale cache/progress, missing in-flight disable, and raw-error leakage — all fixed (the atomic in-place replace resolved three data-integrity findings at once). The "feedback orphaned on delete" finding is moot with in-place replace (same id keeps the rating).
  - **Tests**: backend unit (prompt context, `_build_feedback_guidance`, single-regen success/limit/not-found/wrong-chapter/lost-race, count=1) + integration (200/429/404/403, stale-response cleared); frontend unit (client statusCode, container rewire asserting the TOC method is NOT called, limit + in-flight UI, dialog) + route-mocked E2E `question-regeneration.spec.ts`. Backend **1001 passed / 15 skipped, ~92% cov**; frontend **1959+ passed**, gates green; CI (Backend/Frontend/E2E) green.
  - **Status**: ✅ Complete

- **chapters.py bulk-status concurrency guard + read-handler error handling (#159, P3.8)**: PR #165 — backend-only; two latent defects from the #94 verbatim move, flagged by CodeRabbit on #157.
  - **Adaptation**: the CodeRabbit plan targeted `books.py` claiming `chapters.py` didn't exist — **stale** (#94/#157 already extracted these handlers). Fixes applied in `chapters.py`. **Dropped plan Phase 3** (repo-wide ruff `B008`/`B904` config): ruff B rules aren't enabled here and the lint hook is non-blocking (`|| true`) — new lint scope for an optional nit, out of scope for a bug fix (YAGNI).
  - **Lost-update fix**: `update_chapter_status_bulk` overwrote the entire `table_of_contents` via `update_book()` with **no version check** — a concurrent TOC edit was silently clobbered. Now persists through a new `update_chapter_statuses_with_version_guard()` in `toc_transactions.py`: a **single compare-and-swap `update_one`** filtered on `table_of_contents.version`. A bulk change touches one document, so a single conditional update is atomic on its own — **no transaction** — so the guard holds on both replica-set and standalone (a transaction would surface a concurrent commit as a `WriteConflict`→500). Stale version → `modified_count==0` → `Version conflict` → **409**, mirroring create/update/delete_chapter. Handler keeps its ownership pre-check (wrong-owner **403**, missing book **404**) and up-front transition validation (invalid **400**). Helper re-emits the `book_update` audit log the old `update_book()` path produced. **codex + CodeRabbit** drove: CAS-not-transaction (reliable 409), audit-log preservation, version-**absent** legacy TOC matched on `$exists:false` (no false conflict), and wrapping the post-commit `log_access` loop so a logging failure can't fail an already-committed update (matches `update_chapter_content`).
  - **Structured errors**: `get_chapters_metadata`, `get_tab_state`, `list_chapters`, `save_tab_state` had no `try/except` → unlogged 500 on unexpected error. Each now `except HTTPException: raise / except Exception: logger.error(exc_info=True) → structured 500`, preserving 404/403.
  - **Tests**: helper unit tests (happy+audit, stale→conflict-no-write, version-less TOC, nested, no-match, timestamp, not-found, wrong-owner) + endpoint tests (409 mapping, structured 500 per handler, 404 preserved, logging-failure→200-and-persisted). Backend **986 passed / 15 skipped, 92.17% cov**. CI green (Backend/Frontend/E2E); CodeRabbit findings all addressed.
  - **Follow-up**: the same non-transactional full-TOC-overwrite pattern lives in other `books.py` handlers (`update_chapter_content`, summary/toc) — the issue's deferred "shared fix", not done here.
  - **Status**: ✅ Complete

### 2026-06-30
- **Markdown export format (#61, P3.3)**: PR #164 — fourth export format alongside PDF/DOCX/EPUB, built by mirroring the EPUB pattern (#147).
  - **Backend**: `ExportService.generate_markdown(book_data, chapters, multi_file=False)` — single `.md` (book title `#` + metadata + per-chapter `##` + html2text-converted content) or a ZIP of `NN-slug.md` files (`zipfile`). A **dedicated `html2text` instance with `ignore_images=False`** preserves image refs (`![alt](src)`) — the shared text-extraction converter strips them. Worker thread (asyncio.to_thread) like PDF/DOCX/EPUB; `HTML2TEXT_AVAILABLE` guard → `ExportUnavailableError`. `export_book()` gains a `multi_file` param + `'markdown'`/`'md'` dispatch. New `GET /books/{id}/export/markdown` (`include_empty_chapters`, `multi_file`) — auth/ownership/10-per-hr rate-limit, `text/markdown` (single) or `application/zip` (multi, `_chapters.zip`), `access_type="export_markdown"`; markdown added to `/export/formats`.
  - **Frontend**: `ExportFormat` += `'markdown'`; `ExportOptions` += `markdownMultiFile`. `ExportOptionsModal` Markdown radio + **markdown-only "Separate File Per Chapter" switch**; `bookClient.exportMarkdown`; `page.tsx` handleExport routing; `generateFilename` maps `markdown`→`.md` (`.zip` for multi-file via an extension-override arg). Fixed stale `validateExportOptions` allowlist (was pdf/docx only).
  - **Scope**: **dropped** the Traycer/CodeRabbit plan's GFM-vs-standard flavor toggle (YAGNI — html2text output is already standard/GitHub-compatible Markdown, not an AC). Subtitle renders as emphasis, not `##`, so it doesn't compete with chapter headings in a viewer outline. Legacy `export/page.tsx` left pdf/docx-only (already lacked EPUB — same as #147). Content sub-headings converted verbatim (max fidelity).
  - **Tests**: backend service (single hierarchy, image refs, multi-file zip, dispatch, availability guard) + endpoint (single/multi/404/403, `/formats` lists markdown, `len(formats)` 3→4); frontend modal option/switch, `bookClient` URL, `generateFilename`. Backend **970 passed, 92.08% cov** (export_service 94%); frontend **1943 passed**, gates green.
  - **Status**: ✅ Complete

- **Decompose books.py — map + first extraction (#94, P3.1)**: PR #157 — backend-only, **behavior-preserving move** (not a redesign). First slice of the 3,496-line `books.py` decomposition.
  - **Drift**: plan was written at 3,184 lines; `books.py` had grown to **3,496** — re-derived ranges per the plan's drift-check. Key structural fact: **no module-level helpers** — every `def` is a route handler, so a cluster's only cross-file deps are imports + shared services (`chapter_access_service` spans chapters/content/questions; `chapter_status_service` is chapters-only). That's why the chapters slice extracted with zero helper duplication.
  - **Extracted** the 9 chapter-management handlers (a **contiguous block**, orig. lines 1442–1994: create/get/update/delete/list/metadata/bulk-status/tab-state) verbatim into new `chapters.py`, mounted `include_router(chapters.router, prefix="/books")` **after** the books include. `books.py`: 3,496 → **2,928** lines (−568), 43 → 34 handlers; trimmed the 10 imports the move orphaned (pre-existing dead imports left alone — out of scope). Handler order preserved so the GET literals `/metadata`, `/tab-state` still precede `/{chapter_id}` (the #121 route-shadow bug); `bulk-status` is PATCH-only so its order is moot.
  - **Route table (method, path) verified byte-identical** before/after (69 routes, diff clean) — the invariant that matters for a move. Deliverable **`plans/010-books-decomposition-map.md`** catalogs all 43 handlers by cluster + line range with the suggested extraction order for the remaining slices (content/analytics → questions → drafts → summaries/toc).
  - **Tests**: new `test_chapters_characterization.py` asserts route-table identity (every chapter path still served, owned by `chapters.router`, no duplicate mount, GET-literal ordering). Existing `test_books_chapters_crud_coverage` + `test_books_chapter_content_coverage` are the behavioral net (pass **before + after**). Full backend **961 passed / 15 skipped, 92.38% cov** (`chapters.py` 87%). CI all green (Backend/Frontend/**E2E Playwright**).
  - **CodeRabbit triage (verify-before-fix)**: 3 Major findings, all on **verbatim-moved code** (byte-identical to backup) → deferred as out-of-scope for a move, tracked as follow-ups: dead `create_chapter` "Parent not found" branch (404 vs 400) → **#158**; missing structured try/except on read handlers + bulk-status non-transactional full-TOC overwrite (lost-update) → **#159**. CR's suggestion to assert `bulk-status` precedes `{chapter_id}` was **rejected** — it's PATCH-only, no collision; the assertion fails and encodes a false invariant (caught by running it).
  - **Status**: ✅ Complete

### 2026-06-30
- **Wire Interview Questions / Chapter Editor tabs (#110, P2.12)**: PR #156 — frontend-only. The issue premise was **stale**: `QuestionContainer` was already wired live into `ChapterEditor` (the #105/#54 hand-rolled "Write / Interview Questions" button toggle), so AC-1 (reachable) + AC-2 (answer + persist) were already met. The orphaned `ChapterQuestions.tsx` (Radix tabs) was never in a live route. Closed the real gap: proper tab semantics + un-skipping the E2E infra.
  - **`ChapterEditor.tsx`**: button toggle → Radix `<Tabs>` ("Interview Questions" / "Chapter Editor"), which supplies `role=tab/tablist/tabpanel`, `data-state`, `aria-selected`, `aria-labelledby`, and native arrow-key roving for free (less code than hand-adding them). `QuestionContainer` in the questions tab; TipTap editor in the editor tab. Chose to **adapt the shipped toggle**, not resurrect `ChapterQuestions` (which lacks an editor panel; its CodeRabbit-plan `editor→draft` rename would break the tabs-nav spec's `sessionStorage==='editor'` assertion).
  - **Editor stays the default view** — `saveStatus`/`localStorage`/`questionsToggle` unit tests (~10) assume the editor renders on mount; the E2E specs assumed questions-first. Adapting the specs I was un-skipping is a far smaller blast radius than breaking the unit suite. Tab `value="editor"` **plus** a separate `data-tab="draft"` attribute satisfies both the tabs-nav spec (`'editor'`) and the journey spec (`[data-tab="draft"]`) without a conflicting rename.
  - **Per-chapter persistence**: selected tab saved in `sessionStorage['chapterQuestionsTab_<book>_<chapter>']`, restored in an effect keyed on the storage key (not the `useState` initializer) — `TabContent` renders `ChapterEditor` **without a key**, so a once-only initializer left the tab on the previous chapter's view + risked an SSR hydration mismatch (codex P2, fixed pre-merge; +rerender regression test).
  - **Ctrl+digit intentionally NOT bound** to the view toggle — `ChapterTabs` owns `Ctrl+1..9` for chapter quick-switch (shipped + tested); binding it here hijacked chapter nav (caught in local E2E). Tabs stay keyboard-operable via Radix arrow roving + click.
  - **Gotcha**: a `display` utility (`flex`) on a Radix `TabsContent` **overrides the `hidden` attribute** (`.flex{display:flex}` beats `[hidden]{display:none}`), leaving the inactive panel visible and covering the active panel's buttons — moved the flex layout to an inner wrapper. jsdom didn't apply the stylesheet so unit tests missed it; the real-browser E2E (`chapter-questions-progress` "Next Unanswered" click) caught it.
  - **Tests**: un-skipped + rewrote `chapter-questions-tabs.spec.ts` (5 skipped → live; removed silent `if(isVisible)` guards; **7 passed / 1 AI-skip** in CI on real backend). The AI-dependent `complete-authoring-journey` full journey **stays skipped** (CI has no OpenAI key; uses fixed timeouts) — its `data-tab` selectors are now satisfied so it can be un-skipped once AI is keyed/mocked. Frontend **1932 passed**, coverage 90.7/82.9/87.2/91.8 (gates green); backend untouched. CI all green (Frontend/Backend/**E2E Playwright**); codex P2 fixed; CodeRabbit clean (1 Minor stale-docstring nit fixed).
  - **Status**: ✅ Complete

### 2026-06-29
- **Accessibility — WCAG 2.1 AA (#50, P2.10)**: PR #154 — frontend-only, evidence-driven from a 3-explorer + jest-axe audit (foundation already solid: Radix, jest-axe 0 violations on tested components, correctly-labeled forms — so this closed the real gaps, not a blind sweep).
  - **ARIA labels** on icon-only controls (a bare `title=` is an unreliable SR name): `EditorToolbar`'s 14 buttons → `aria-label` + `aria-pressed`, wrapped in `role="toolbar"`; `TabBar` scroll up/down, `TabOverflowMenu` trigger, `UserButton` avatar.
  - **Skip link + landmarks**: root layout adds a "Skip to main content" link and its wrapper `<main>`→`<div>`. Exactly **one `<main id="main-content" tabIndex={-1}>` per route in every render state** — dashboard content, `auth/layout` (covers all auth pages + Suspense fallbacks), landing (content/loading/error), `ProtectedRoute` loading/redirect, `error.tsx`, and the root ErrorBoundary fallback. `QuestionContainer`'s self-`<main>`→ labeled `<section>` (no nested main). Dashboard `<nav>`s labeled. **codex's 4-round adversarial review drove this robustness** — each round caught a real fallback-state gap (public/auth targets, ProtectedRoute loading, nested main, route-error states).
  - **Keyboard/forms**: `DeleteBookModal` wrapped in `<form>` (Enter submits when confirmation matches; async `handleConfirm` guarded against unhandled rejection); input `aria-invalid` + `aria-describedby`, error `role="alert"`.
  - **Focus/contrast**: global `:focus-visible` outline fallback for `a`/native controls (`button`/`input`/`select`/`textarea`/`summary`)/`[role=button]`/`[tabindex]`; `SummaryInput` help text `gray-600`-on-dark (failed AA) → `gray-400`.
  - **Deferred (documented)**: arrow-key roving tab nav — `TabBar` uses react-beautiful-dnd, which reserves Space/arrows for keyboard drag-reorder; roving nav would conflict. Tabs are already keyboard-operable (`tabIndex=0` + Enter/Space → WCAG 2.1.1 met) + Ctrl+1-9. Arrow roving is an ARIA-APG recommendation, not an AA criterion. **Manual-only ACs**: Lighthouse >95, NVDA/JAWS.
  - **Tests**: new `EditorToolbar` a11y test (14 accessible names + `role=toolbar` + `aria-pressed` + axe); `DeleteBookModal` Enter-submit + `aria-invalid`/`role=alert`; `QuestionContainer` a11y tests retargeted to the labeled region. Frontend **1930 passed**, coverage 90.7/82.9/87.2/91.8 (gates green). CI all green (Frontend/Backend/E2E). codex clean; CodeRabbit's actionable items addressed (Vitest-migration nitpick rejected — repo is Jest end-to-end, no Vitest config).
  - **Status**: ✅ Complete

### 2026-06-29
- **Mobile responsiveness (#51, P2.9)**: PR #153 — frontend-only. Driven by the orphaned `responsive.spec.ts` (the real acceptance spec), not the CodeRabbit plan's wording.
  - **Touch targets (WCAG 2.5.5, 44px on `<768px`)** applied via responsive base classes (`max-md:`) instead of the plan's **opt-in `mobile`/`icon-mobile` button variants** — the spec asserts *every rendered button* is ≥44px, which an unused variant can't satisfy. One edit per primitive, desktop sizes unchanged: `ui/button` (`max-md:min-h-11 max-md:min-w-11` on the CVA base → all buttons app-wide, no call-site churn), `ui/input`/`ui/select` (`max-md:min-h-11`). `ui/radio-group`/`ui/switch` keep the compact visual but expand the tap area to 44px via a transparent `::before` overlay. Raw `<button>`s that bypass the Button component (auth password toggles; dashboard nav/menu toggles) got explicit mobile sizing + `max-md:pr-14` on password inputs so the bigger toggle doesn't overlap text.
  - **Swipe navigation**: new `hooks/useSwipeGesture` (native touch events, threshold + horizontal/vertical discrimination so it won't hijack vertical scroll, SSR-safe). Uses a **callback ref** (not a ref object) so it binds when the swipeable element mounts *after* the first render — `useMediaQuery` starts `false`, so `ChapterTabs` renders the swipe wrapper only on a later render; a one-time `[]` effect would never attach (codex caught this as a P1). `ChapterTabs` wires swipe left/right → next/prev chapter on mobile only (`touch-action: pan-y`), walking the full `state.chapters` order (what the mobile selector shows), not `tab_order`.
  - **Viewport**: `app/layout` exports Next.js `viewport` (`device-width`, `initial-scale=1`, `viewport-fit=cover`). **No `maximum-scale`** — blocking zoom is a WCAG 1.4.4 violation (plan hedged; dropped it).
  - **E2E activation**: moved orphaned `frontend/e2e/responsive.spec.ts` → `frontend/src/e2e/` (into `testDir`); removed forbidden `waitForTimeout`; fixed a `button.first()` flaw that resolved the DOM-present-but-hidden mobile-menu toggle on desktop. The CI **E2E Tests (Playwright)** job runs `--project=chromium` with backend+Mongo, so the spec's in-test `setViewportSize` mobile checks run there; the 6 chapter-page-fixture-dependent tests stay `skip`ped.
  - **Dropped as already-satisfied** (verified, not re-done): `QuestionNavigation` already `min-h-[44px] min-w-[44px]`; `textarea` already `min-h-16` (64px).
  - **Tests**: `useSwipeGesture.test` (incl. a late-mount regression test that fails against the old one-time-effect version) + `ChapterTabs` mobile-swipe cases. Frontend **1909 passed**, coverage 91.0/83.1/88.8/92.1 (gates green); `responsive.spec.ts` **36 passed/6 skipped** under the CI prod-build config. Backend untouched. CI all green (Frontend/Backend/E2E). `codex` cross-family review clean (P1 callback-ref, P2 swipe-order, P3 password-padding all fixed pre-merge); CodeRabbit App auto-skipped on a title-keyword false-positive.
  - **Status**: ✅ Complete

### 2026-06-29
- **Comprehensive loading indicators & skeleton screens (#52, P2.8)**: PR #152 — frontend-only; adapted the CodeRabbit issue plan, reusing existing `Skeleton`/`LoadingStateManager`/inline-spinner (no new abstraction, no new deps)
  - **Page-level skeletons** (replace centered spinners → mirror real layout, prevent layout shift, `role="status"`/`aria-live`/`aria-busy` + sr-only text): `dashboard/page.tsx` + `dashboard/loading.tsx` (book-card grid), `dashboard/books/[bookId]/page.tsx` (breadcrumb/title/stepper/two-column/tabs), `ChapterTabs.tsx` (**orientation-aware** tab-list + content — vertical split or horizontal stack).
  - **Component loading-state gaps**: `TocReview` "Accept & Continue" spinner + "Saving…"; `ClarifyingQuestions` skeleton + disabled inputs during initial response load (new `isLoadingResponses`); `BookMetadataForm` spinner + `disabled` inputs while auto-saving; `ChapterQuestions` explicit "Loading progress…" indicator (was a blank gap).
  - **Already-satisfied tasks dropped** (verified in code, not re-done): DraftGenerator dead `LoadingStateManager` (fixed in #55 — `isGenerating` checked first; only the now-dead inline button spinner removed here) and DraftGenerationButton fetch-gap (`step='generating'` is set *before* the fetch, so `LoadingStateManager` already shows). Plan's `LoadingSpinner` doesn't exist → used inline spinner/`Loading03Icon`. The big-ticket ACs (>2s progress %, >5s est. time) were already met by `LoadingStateManager` on the AI ops.
  - **Tests**: new `TocReview.test.tsx`, `BookMetadataForm.test.tsx`, `pages/LoadingSkeletons.test.tsx`; extended `ClarifyingQuestions`/`ChapterTabs`/`ChapterQuestionsTabs` tests (skeleton role/aria, disabled state, skeleton→content transition, orientation). The new initial-load skeleton made 12 `ClarifyingQuestions` tests query before the mocked load resolved → switched those to `await findBy*`. Frontend **1898 passed**, coverage 91/83/89/92 (gates green); backend untouched.
  - **Process note**: an initial `git add -A` swept pre-existing untracked working files (`plans/`, `tasks/lessons.md`, a **staging-only** E2E spec, helper scripts) into the commit; the staging spec needs live auth and **failed the normal E2E job** (looked like the feature broke E2E — it hadn't). Fixed with `git rm --cached` (kept on disk), no force-push. Lesson logged. **Stage explicitly when untracked files are outside the change.**
  - **Status**: ✅ Complete

### 2026-06-29
- **Chapter-question progress tracking (#53, P2.7)**: PR #151 — frontend-only; backend already supplied progress + per-question `response_status`
  - The CodeRabbit/Traycer "replace stub progress bar with shadcn `Progress`" task was **already done** in the codebase, so it was omitted. Closed the real gaps:
    - `QuestionContainer.handleResponseSaved` now re-fetches the **questions array** (via `fetchQuestions(true)`, which also refreshes progress), not just the aggregate summary — so dropdown/dot statuses update in real time instead of going stale until reload.
    - `QuestionProgress` dots colour from each question's `response_status` (green/amber/blue-current/gray) instead of positional `index < completed` logic (wrong for out-of-order answers); falls back to positional when no `questions` prop.
    - `QuestionNavigation` gains a **"Next Unanswered"** button (`findNextUnanswered`, wraps, disabled when all completed) and marks unanswered dropdown items distinctly (`○` + `text-muted-foreground`; completed `✓`/draft `⚙️` unchanged).
  - **Tests**: `QuestionProgress.test.tsx` (per-question dots + positional fallback), `QuestionNavigation.test.tsx` (`findNextUnanswered`, Next-Unanswered button, `○` marker), `QuestionContainer.test.tsx` (refresh-on-save); route-mocked E2E `chapter-questions-progress.spec.ts` reaches `QuestionContainer` via the ChapterEditor "Interview Questions" tab (#105). Two pre-existing `getByRole('button',{name:/next/i})` queries tightened to `/^next$/i` to disambiguate the new button. Frontend **1890 passed**, coverage 90.98/82.99/88.62/91.97 (gates green); backend unchanged. `ResponseStatus` enum has only DRAFT/COMPLETED — unanswered = `undefined` (the plan's `'not_answered'` string isn't in the frontend type).
  - **Status**: ✅ Complete

### 2026-06-29
- **AI voice-input enhancement / dictation cleanup (#56, P2.6)**: built by **mirroring the #57 enhance-text pattern** end to end (no new deps, no transcription-router changes)
  - **Backend**: `app/services/transcription_enhancement.py` (single `TRANSCRIPTION_CLEANUP_GUIDANCE` + `get_transcription_enhancement_prompt(content)` — fact-preserving). `ai_service.enhance_transcription(content)` (temp **0.3**, conservative; rejects length-truncated output so a long dictation can't be silently shortened; structured `{success, enhanced, metadata}`). New `POST /books/{id}/chapters/{cid}/enhance-transcription` (session auth, ownership 403, **chapter-existence 404**, 10/h rate limit, 400 empty-content, 503 on AI failure). **Preview-only, no persistence.**
  - **Single "cleanup" mode** (one pass: filler removal + paragraph breaks at natural pauses + grammar/punctuation) rather than the Traycer plan's 3 boolean toggles — the AC lists all three as expected *outcomes*, not user options; "toggle raw vs enhanced" = the side-by-side preview + revert.
  - **Frontend**: `VoiceEnhancer.tsx` dialog (intro→enhancing→preview; DOMPurify-sanitized raw-vs-cleaned side-by-side; mirrors `ContentEnhancer`); `bookClient.enhanceVoiceTranscription()`. `ChapterEditor` toolbar **Clean up dictation** button — **reuses** the existing `getEnhanceContent` + `handleApplyEnhancement` + **"Revert enhancement"** snapshot/revert (no new editor state).
  - **Tests**: backend `test_transcription_enhancement` + `test_ai_service_transcription` + `test_transcription_enhancement_endpoint` (success/400/404-book/404-chapter/403/503); frontend `VoiceEnhancer.test.tsx`; route-mocked E2E `voice-enhancement.spec.ts` (raw dictation→clean up→preview→apply→revert). Backend **957 passed, 92.36% cov** (`transcription_enhancement.py` 100%); frontend **1878 passed**, gates green (85/85/75/85).
  - **NB**: the unmounted `/transcribe` router and the Traycer plan's references to the deleted `chapter_error_handler`/`chapter_cache_service` (gone in #120) are intentionally untouched. E2E route-mocks the endpoint — browser SpeechRecognition is native/non-deterministic and unavailable headless (webkit/Mobile-Safari editor-load fails pre-existingly in this env; same as the #57 spec).
  - **Status**: ✅ Complete

### 2026-06-28
- **EPUB export format (#60, P2.3)**: PR #147 — third export format alongside PDF/DOCX
  - **Backend**: `ExportService.generate_epub()` via `ebooklib==0.20` (async worker thread, same pattern as PDF/DOCX). Title page + per-chapter `EpubHtml`, `EpubNcx` (EPUB2 nav) **and** `EpubNav` (EPUB3 nav) for max ereader compat, ordered spine. Reuses the shared HTML→formatted-text pipeline (`_extract_text_formatting`) so chapter content renders as **well-formed XHTML** — raw TipTap HTML isn't always XML-valid and would break ereaders/lxml. **Gotcha fixed**: no `<?xml … encoding …?>` prolog on `EpubHtml.content` — ebooklib parses it as a `str` during nav generation and lxml rejects a unicode string carrying an encoding decl (silently empties the body → `ParserError: Document is empty`). ebooklib writes its own prolog.
  - `export_book()` gains `'epub'` dispatch (no page_size/template — EPUB is reflowable); guarded import → `EPUB_AVAILABLE`. New `GET /books/{id}/export/epub` endpoint (auth, ownership, `log_access("export_epub")`, 10/h rate limit, 503 when ebooklib missing). EPUB listed in `/export/formats`.
  - **Frontend**: `ExportFormat` union gains `'epub'`; EPUB radio option in `ExportOptionsModal` (page-size stays PDF-only); `bookClient.exportEPUB()`; `handleExport` routing. `generateFilename` already keys off `format` → `.epub` automatic. `TemplateSelector.format` prop widened to `ExportFormat`.
  - **Tests**: backend service (valid EPUB zip: `mimetype` first+STORED, nav+ncx+chapter XHTML, chapter text survives), `export_book('epub')`, availability guard; endpoint happy/404/403 + `/formats` lists epub; frontend modal option + `bookClient.exportEPUB` URL. Backend suite **923 passed, 92.32% cov** (export_service 95%); frontend gates green.
  - **Known limits**: flat TOC (each chapter top-level — navigable; nest by `level` later); no ISBN (book model has no field); device testing (Kindle/Kobo/Apple Books) is manual, covered here by spec-conformant structure assertions.
  - **Status**: ✅ Complete

- **AI content enhancement for existing chapter text (#57, P2.5)**: PR #149 — built by **mirroring the #58 style-transformation pattern** end to end (no new deps, no diff library, no floating-selection UI)
  - **Backend**: `app/services/content_enhancement.py` (4 fact-preserving dimensions — clarity/grammar/tone/vocabulary — `ENHANCEMENT_LABELS`/`ENHANCEMENT_GUIDANCE`/`is_valid_enhancement`/`get_enhancement_prompt`, mirrors `style_templates.py`). `ai_service.enhance_text(content, enhancement_type)` (temp **0.3** — conservative vs style's 0.7; rejects length-truncated output so a too-long chapter can't be silently shortened; structured `{success, enhanced, metadata}`). New `POST /books/{id}/chapters/{cid}/enhance-text` (session auth, ownership 403, **chapter-existence 404**, 10/h rate limit, 400 validation, 503 on AI failure). **Preview-only, no persistence.**
  - **Frontend**: `ContentEnhancer.tsx` dialog (options→enhancing→preview; DOMPurify-sanitized side-by-side before/after; mirrors `StyleTransformer`); `bookClient.enhanceChapterText()`. `ChapterEditor` toolbar **Enhance** button — enhances the **current selection if any, else the whole chapter** (captures the range so apply replaces exactly that), snapshot + **"Revert enhancement"** single-level undo.
  - **Tests**: backend `test_content_enhancement` + `test_ai_service_enhancement` + `test_enhancement_endpoint` (all 4 types, 400/404-book/404-chapter/403/503); frontend `ContentEnhancer.test.tsx`; route-mocked E2E `content-enhancement.spec.ts` (open→pick→preview→apply→revert). Backend **943 passed, 92.4% cov** (`content_enhancement.py` 100%); frontend gates green.
  - **NB**: `#41` ("robust AI error handling") listed as a blocker was already satisfied — the structured AI-failure→503 path exists. The mirrored `transform-style` endpoint still lacks the chapter-existence check (not retrofitted here). codex pre-PR review caught the missing chapter check; fixed before opening the PR.
  - **Status**: ✅ Complete

### 2026-06-27
- **Restore pre-commit/CI gate enforcement — stop merging with `--no-verify`/`--admin` (#118, capstone)**: process/enforcement, no app behavior change
  - **Gates verified green at baseline**: backend coverage **92.4%** (`pytest --cov=app --cov-fail-under=85`, 888 passed/15 skipped); frontend coverage clears **85/85/75/85** (1856 passed/8 skipped, 90 suites). `pre-commit run --all-files` passes with no bypass. All four blocking coverage issues (#68, #93, #116, #117) closed; no coverage gate remains red.
  - **CI now actually enforces coverage**: removed `continue-on-error: true` from both "Check coverage threshold" steps in `.github/workflows/tests.yml` (the old "don't fail CI until we reach 85%" escape) — a coverage regression now fails `Frontend Tests` / `Backend Tests`.
  - **Branch protection on `main`** (was unprotected): required status checks (strict/up-to-date) = `Frontend Tests` + `Backend Tests`; merges route through a PR. `--admin` override stays for true emergencies but is no longer the norm. (E2E intentionally out of scope per the issue.)
  - **Docs**: neutralized the stale `--no-verify`/"baseline gates red" boilerplate in this file; the Pre-Commit section now states gates are green and enforced. (No PR template file exists, so nothing to scrub there.)
  - **Demonstrated**: this issue's own PR merged through required checks **without** `--admin`.
  - **Status**: ✅ Complete

### 2026-06-26
- **Test coverage for books.py endpoints 41% → 89% + 6 real bug fixes (#121)**: PR #138 (reliability-labeled)
  - **244 new integration tests** across 7 files in `tests/test_api/test_routes/` (one per endpoint group: book CRUD/summary, pre-TOC AI, TOC, chapter CRUD, chapter content/tab-state, chapter questions, draft/style). Each endpoint covers happy-path + 404 + 403 (wrong owner) + validation/AI-error branches. Real local MongoDB + mocked session auth (`auth_client_factory`); AI endpoints patch `ai_service`. Full backend suite green: **714 passed, 17 skipped**.
  - **Real production bugs found while testing and fixed** (tests now assert correct behavior, not the bugs):
    1. `create_chapter` passed `add_chapter_with_transaction(parent_id=…)` but the param is `parent_chapter_id` → every chapter create 500'd.
    2. `update_chapter` passed `update_chapter_with_transaction(updates=…)` but the param is `chapter_updates` → every chapter update 500'd.
    3. `get_chapter_analytics` passed `user_id=`/`chapter_id=` kwargs the service rejects → always 500. Now `get_chapter_analytics(book_id, days)`.
    4. `batch-content` with `include_metadata` `await`ed the **sync** `calculate_reading_time` and passed content text instead of a word count → crash.
    5. `GET /chapters/metadata` and `GET /chapters/tab-state` were registered **after** `/chapters/{chapter_id}` → permanently route-shadowed (404). Moved both before the parameterized route.
    6. Offensive-summary filter regex used `"\\b"` (literal backslash-b) not `"\b"` → never matched real input.
  - **Test infra (`conftest.py`)**: test DB name now env-overridable via `TEST_MONGO_URI` (default unchanged, enables parallel/sharded runs); `motor_reinit_db` now rebinds `app.db.toc_transactions` to the per-test client (it captured `_client`/`books_collection` at import), so transactional chapter endpoints run for real instead of against a closed loop.
  - **NB (historical)**: this PR predated the coverage work and was committed with `--no-verify` while overall backend coverage was still <85%. As of #118 the backend gate is green (92%) and enforcement is restored — `--no-verify`/`--admin` are no longer used as the norm. Coordinates with #94 (covers the monolith as-is; tests grouped by area to move cleanly when split).
  - **Status**: ✅ Complete

### 2026-06-26
- **Remove dead service code + omit seed script from coverage (#120)**: backend cleanup, no behavior change
  - **Deleted 9 dead service modules (4,983 LOC)**: `content_analysis_service`, `historical_data_service`, `question_feedback_service`, `chapter_error_handler`, `chapter_cache_service`, `user_level_adaptation`, `question_quality_service`, `genre_question_templates`, `chapter_soft_delete_service`. Each verified unreferenced in `app/` (no importers, no `services/__init__.py` re-exports, no dynamic/class-name refs). `chapter_error_handler` ↔ `chapter_cache_service` were mutually-dead (only imported each other).
  - **Deleted 5 ghost validation scripts** that referenced the chapter cache/error modules and were run by nothing (pytest collected 0 tests; not in CI): `tests/test_chapter_tabs_api.py`, `archived_tests/test_chapter_tabs_api.py`, root `validate_chapter_tabs.py` / `quick_validate.py` / `simple_validate.py`.
  - **Coverage**: added `*/populate_db_test_data.py` (seed script) to `.coveragerc` omit. Backend coverage **~50% → 71%** with zero new tests (the dead modules were the drag). Suite green: **466 passed, 17 skipped**.
  - **Docs**: scrubbed deleted-module refs from `docs/ai-caching-and-error-handling.md` (tree + links); added a removal note to `docs/developer-guide-question-system.md` (4 of its documented modules were dead). Historical analysis snapshots (`docs/analysis/*`, `TEST_COVERAGE_REPORT.md`) left as-is — they identify this dead code.
  - **Status**: ✅ Complete

### 2026-06-26
- **Harden full staging E2E journey + wire chapter Q&A (#105)**: PRs #134 + #135
  - **Root finding**: the #54 interview-questions Q&A loop (`QuestionContainer`, with real `PUT .../questions/{id}/response` persistence) existed but was **never mounted** in any navigable route — only a hardcoded-mock `/chapters` page used it. So #54 was untestable. `ChapterEditor` now has a **Write / Interview Questions** tab toggle that mounts `QuestionContainer`, making generate→answer→persist real. +3 unit tests.
  - **Real backend bugs fixed (both blocked the live wizard)**:
    1. `generate-toc` only read the *persisted* `book.question_responses`, but the `ClarifyingQuestions` wizard sends responses in the request **body** and never persists them → every wizard TOC generation 400'd "Question responses are required". Now reads body first, falls back to persisted. +1 test.
    2. `analyze-summary` **persisted failed AI analyses**, which permanently poisoned readiness (`has_analysis=true`, `meets_minimum=false`) and blocked TOC forever after one transient error. Now returns a retryable 503 and doesn't persist, so readiness falls back to the deterministic word/char check. +1 test.
    3. OpenAI key: service only read `OPENAI_AUTOAUTHOR_API_KEY`; staging's was stale/invalid. Now reads canonical `OPENAI_API_KEY` (legacy fallback); deploy writes it. +2 tests. **NB: the running staging key only refreshes on redeploy.**
  - **Test hardening**: new shared `tests/e2e/staging/fixtures/journey.helpers.ts` (real selectors + network waits + a `READY_SUMMARY` the AI judges ready); `complete-user-journey.spec.ts` and the #54 regression **un-`fixme`'d**; removed **every** `page.waitForTimeout()` and silent `if(isVisible)` skip (CLAUDE.md forbidden). Fixes all four issue items: delayed book-create nav, summary fill-race (re-fill-until-submit-enables), the auto-running TOC wizard, and the forbidden patterns.
  - **Verify**: full staging suite **4/4 pass, 3 consecutive runs** (12/12) against live `dev.autoauthor.app` with real Better-auth + real AI — meets the issue's >95% bar.
  - **Status**: ✅ Complete

### 2026-06-26
- **Nova migration residual cleanup (#65)**: finished the lucide→hugeicons + zinc→gray drift left after PR #73
  - **Context**: PR #73 (Dec 24) already did the bulk nova migration (style/baseColor/iconLibrary in `components.json`, Nunito Sans). #65 stayed open because the literal AC ("no lucide-react imports", "no zinc colors") weren't fully met.
  - **Icons**: converted the remaining 14 source files off `lucide-react` to `<HugeiconsIcon icon={…}/>` from `@hugeicons/core-free-icons` — 6 feature files (auth sign-in/up, reset/forgot-password, `PasswordRequirements`, `SessionWarning`) + 8 stock shadcn `ui/*` primitives (dialog, select, checkbox, dropdown-menu, sheet, radio-group, breadcrumb, sonner). Removed `lucide-react` from `package.json`/lockfile and two dead `jest.mock('lucide-react')` blocks. **Zero lucide refs remain.**
  - **Colors**: `zinc-* → gray-*` across 20 files (mechanical className swap). **Zero zinc refs remain.**
  - **Cleanup**: removed the now-obsolete `frontend/backup-pre-nova/` migration-backup dir (git preserves history).
  - **Verify**: typecheck clean, lint 0 errors, prod build green (compiles every converted route), 89/89 suites + 1853 tests pass, coverage stmt 92 / lines 93 / func 90 / branch 83.
  - **Status**: ✅ Complete

### 2026-06-25
- **Flaky test fix + frontend coverage to 85% (#68)**: tests-mostly
  - **Flaky `TabStatePersistence`**: the "saves tab state…" case raced the 1s debounced auto-save under real timers. Now uses `jest.useFakeTimers()` + `advanceTimersByTime(1000)` and an `afterEach(jest.useRealTimers())` so it's deterministic and can't leak timer state into the full run.
  - **Coverage**: global was stmt 74 / lines 75 / func 67 / branch 62 → now **stmt 92 / lines 93 / func 90 / branch 83**, clearing the pre-commit gate (85/85/75) without `--no-verify`. ~700 unit tests added across `lib/errors/*`, `lib/api/bookClient.ts`, `lib/security.ts`, `lib/performance/*`, `lib/loading/timeEstimator.ts`, `lib/utils/toc-to-tabs-converter.ts`, `lib/toast.ts`, hooks (`useTocSync`, `usePerformanceTracking`), and components (`ErrorNotification`, `QuestionDisplay/Container/Navigation/Generator`, `ClarifyingQuestions`, `ChapterTabs`/`MobileChapterTabs`/`TabBar`/`TabContextMenu`/`TabOverflowMenu`, `ui/dropdown-menu`, `ui/sheet`).
  - **Real bugs fixed while testing**: `sanitizeFileName` regex `[^a-zA-Z0-9.-_]` was a char *range* (46–95) so `/ : \ @` slipped through while `-` was stripped — hyphen now escaped (path-traversal hardening); `showRecoveryNotification` printed "2 attempt" (singular) — fixed to plural; removed a dead empty `useEffect`/`getToken` + orphaned `useSession` in `ClarifyingQuestions.tsx`.
  - **Status**: ✅ Complete

- **Transcription test coverage + dead-code removal (#93)**: tests-only plan 009
  - **transcription.py**: 40% → 85% via new `backend/tests/test_api/test_transcription.py` (POST /transcribe auth/413/400/happy/service-error; GET /status; POST /validate). Router isn't mounted on the app, so tests mount it on a bare FastAPI app + override auth; transcription service patched (no AWS/audio)
  - **Drift**: `app/api/endpoints/book_cover_upload.py` was dead code (never imported) — an unmounted duplicate of the live cover endpoint in `books.py`. Removed it (same pattern as #92's `book_cascade_delete.py`); added a wrong-owner (404) case to the existing `test_book_cover_upload.py` which already exercises the live `books.py` path
  - **Status**: ✅ Complete (PR #131)

- **Writing style transformation (#58)**: New feature — rewrite existing chapter text into a chosen style (distinct from draft-from-Q&A)
  - **Backend**: `app/services/style_templates.py` (5 documented styles with distinct tone/vocab/structure guidance + `get_style_transformation_prompt`); `ai_service.transform_text_style(content, target_style)` (temp 0.7, preserves facts); new endpoint `POST /books/{id}/chapters/{cid}/transform-style` (auth + ownership + rate limit, **preview-only, no persistence**)
  - **Frontend**: `StyleTransformer.tsx` dialog (pick style → before/after preview → apply); wired into `ChapterEditor` toolbar with a **client-side snapshot revert** ("Revert style" button) — single-level undo, no backend version storage; `bookClient.transformChapterStyle`
  - **Tests**: backend `test_style_templates` + `test_ai_service_style_transformation` + `test_style_transformation` (15 tests: distinct prompts per style, validation, auth, AI-failure→503); frontend `StyleTransformer.test.tsx`; deterministic route-mocked E2E `frontend/src/e2e/style-transformation.spec.ts` (transform → preview → apply → revert)
  - **Note**: the stale deployment spec `tests/e2e/deployment/06-draft-writing-styles.spec.ts` still references the old 6 draft styles (real-auth suite) — not rewritten here
  - **Status**: ✅ Complete

- **AI Draft Generation alignment (#55)**: Feature was already ~95% built; closed the real gaps the stale issue/bot plans missed
  - **Writing styles**: both `DraftGenerator.tsx` and `DraftGenerationButton.tsx` now ship the 5 documented styles (Professional, Conversational, Academic, Creative, Technical) matching the user manual + AC, replacing the prior mismatched 6. Backend is style-agnostic (free-text into the prompt) → no backend change
  - **Bug fix**: `DraftGenerator.tsx` loading state was unreachable (ternary checked `!generatedDraft` before `isGenerating`, so the form always rendered during generation); reordered so the loading view shows. `DraftGenerationButton.tsx` already had a correct step machine
  - **A11y**: associated the style/length selects and the per-question input with labels in `DraftGenerator.tsx`
  - **Tests**: added a regression test asserting the loading state renders during generation; new deterministic route-mocked E2E `frontend/src/e2e/draft-generation.spec.ts` (open → pick style → generate → preview → insert into editor)
  - **Status**: ✅ Complete

### 2026-06-24
- **Error/Success Feedback Unification (#46)**: Closed user-facing feedback gaps and standardized the notification path
  - **Duplicate Toaster**: `layout.tsx` mounted two sonner Toasters → duplicate toasts; removed the redundant one, kept theme-aware `SonnerToaster`
  - **new-book silent failure**: create errors only `console.error`'d; now classified and shown via `showErrorNotification` with a retry action, plus a success toast on create
  - **ChapterTabs retry**: load-error "Retry" did a full `window.location.reload()`; now calls `refreshChapters()` (data refresh, no page reload)
  - **Standardization**: all toasts route through the single `@/lib/toast` wrapper (added a `variant` compat shim); migrated 5 direct-`sonner` + 6 `useToast` call sites by import swap
  - **Tests**: `NewBookPage.test.tsx` (success toast + redirect / error notification + no redirect), `ChapterTabs.test.tsx` (retry refreshes, no reload); migration mocks updated
  - **Status**: ✅ Complete (PR #115)

### 2026-06-22
- **TOC Generation Hardening (#48)**: Closed reliability gaps in the AI TOC flow
  - **analyze-summary endpoint**: now uses the same structured AI-error handling as generate-questions/generate-toc (timeouts → 503 with retry info, instead of an opaque 500)
  - **Frontend**: `bookClient` AI methods surface the backend's `detail.message`, and `TocGenerationWizard` shows it (meaningful error text + existing retry button) rather than a generic string
  - **Malformed AI responses**: `ai_service._parse_toc_response` now rejects unusable output (empty/title-less chapters, unparseable text) with a retryable `AI_INVALID_RESPONSE` error instead of silently fabricating a generic placeholder TOC; it also unwraps the common `table_of_contents` JSON wrapper so valid-but-wrapped responses parse correctly
  - **Tests**: backend integration tests for AI timeouts/invalid responses across all 3 TOC endpoints; `bookClient` error-surfacing unit tests; deterministic route-mocked E2E (`frontend/src/e2e/toc-generation-resilience.spec.ts`) for the error→retry recovery path
  - **Status**: ✅ Complete

### 2025-12-24
- **Cookie-Based Authentication Reconciliation**: Aligned backend auth with better-auth's cookie-based session management
  - **Problem**: Backend expected JWT tokens in Authorization headers, but better-auth uses httpOnly session cookies
  - **Solution**: Created new session validation module to read and validate better-auth session cookies
  - **Changes**:
    - New module: `backend/app/core/better_auth_session.py` for session cookie validation
    - New dependency: `get_current_user_from_session()` replaces JWT-based authentication
    - New role checker: `SessionRoleChecker` for cookie-based authorization
    - Updated all 25+ protected endpoints to use session-based auth
    - Frontend: Removed Bearer token logic, uses `credentials: 'include'` for cookies
  - **Files Modified**:
    - `backend/app/core/security.py` - Added session-based auth functions
    - `backend/app/core/better_auth_session.py` - New session validator
    - `backend/app/api/endpoints/*.py` - Updated all endpoints
    - `frontend/src/hooks/useAuthFetch.ts` - Cookie-based fetch
    - `frontend/src/lib/api/bookClient.ts` - Deprecated token methods
  - **Test Updates**: All test fixtures updated to mock session-based auth
  - **Documentation**: Updated migration guide with cookie-based auth section
  - **Status**: ✅ Complete - Backend now validates session cookies from better-auth

### 2025-12-17
- **Better-Auth Migration**: Complete migration from Clerk to better-auth authentication
  - **Scope**: 70+ files across frontend (Next.js) and backend (FastAPI)
  - **Changes**:
    - JWT algorithm: RS256 (Clerk) → HS256 (better-auth)
    - User ID field: `clerk_id` → `auth_id`
    - Frontend: Removed `@clerk/nextjs`, added `better-auth` with MongoDB adapter
    - Backend: Removed Clerk JWKS verification, added HS256 JWT validation
    - Environment: Simplified to `BETTER_AUTH_SECRET` and `BETTER_AUTH_URL`
  - **Security Fixes**:
    - **BLOCKER**: Removed hardcoded JWT secret, added strong validation (min 32 chars)
    - **HIGH**: Changed `NEXT_PUBLIC_BYPASS_AUTH` to server-only `BYPASS_AUTH` with production safety check
    - **HIGH**: Disabled auto-user creation from JWT - require explicit registration
  - **Test Results**: 231/251 backend tests passing (92%), all security tests updated for better-auth
  - **Cleanup**: Removed Clerk documentation, test files, and CSP headers
  - **Status**: ✅ Migration complete with all security vulnerabilities fixed

### 2025-11-22
- **Auto-Create Users from Clerk on First Login**: Enhanced authentication to automatically create user records
  - **Problem**: Users authenticating via Clerk weren't being created in backend database
  - **Solution**: Modified `security.py` to auto-create users from Clerk JWT on first login
  - **Changes**: Enhanced `get_current_user()` to create missing users, added comprehensive logging
  - **Impact**: Seamless user onboarding without manual database setup
  - **Status**: ✅ Deployed to staging - authentication now fully automated

- **Staging Deployment Workflow**: GitHub Actions workflow for automated staging deployments
  - **Achievement**: Complete CI/CD pipeline for staging environment
  - **Infrastructure**: SSH deployment, PM2 process management, health checks with retries
  - **Configuration**: Backend on port 8000, frontend on port 3003, CORS validation
  - **Process**: Uses `pm2 delete` + `pm2 start` instead of restart for clean release pickup
  - **Status**: ✅ Operational at https://dev.autoauthor.app (frontend) and https://api.dev.autoauthor.app (backend)

- **Public Access to Landing Page**: Fixed middleware to allow unauthenticated access to root
  - **Problem**: Root landing page was requiring authentication
  - **Solution**: Updated middleware.ts to explicitly allow public access to `/`
  - **Impact**: Marketing/landing page now accessible without login
  - **Status**: ✅ Deployed to staging

### 2025-11-07
- **E2E Test Suite Complete**: Comprehensive automated testing with 85%+ coverage
  - **Achievement**: Created comprehensive deployment test suite (01-05) with 54+ tests
  - **Infrastructure**: Fixtures (auth, test-data, performance), Helpers (console/network/CSP monitors), Page Objects (7 pages)
  - **Coverage**: Pre-flight (7 tests), User Journey (8 tests), Advanced Features (8 tests), Security/Performance (12 tests), Regression (19+ tests)
  - **Performance Budgets**: All operations validated (TOC <3000ms, Export <5000ms, Auto-save <1000ms, Page Nav <500ms)
  - **Status**: ✅ auto-author-59 completed - 85%+ automation coverage achieved, ready for CI/CD

- **MongoDB Atlas SSL Connection Fix**: Resolved test database connection issues
  - **Problem**: 13 tests failing with SSL handshake errors connecting to MongoDB Atlas
  - **Solution**: Updated test infrastructure to use local MongoDB for all tests
  - **Changes**: Added sessions_collection to conftest fixture, updated session.py to use base.sessions_collection
  - **Impact**: 9/15 session service tests now passing (was 3/15), all SSL errors eliminated
  - **Status**: ✅ auto-author-70 completed - tests now use local MongoDB correctly

- **Frontend Test Suite Status**: All environmental test issues resolved
  - **Test Results**: 732/735 tests passing (99.6% pass rate, 3 skipped)
  - **Test Suites**: 51/51 passing (100%)
  - **Resolution**: Mocks already in place (Next.js router, ResizeObserver, TipTap, Clerk)
  - **Excluded Tests**: ProfilePage.test.tsx, SystemIntegration.test.tsx (awaiting feature implementation)
  - **errorHandler.test.ts**: All 43 tests passing with Jest
  - **Status**: ✅ auto-author-60 completed - no fixes needed, infrastructure working correctly

### 2025-11-06
- **TOC JWT Bug Fix**: Fixed JWT token expiration during long TOC workflows (11+ seconds) by implementing token provider pattern in BookClient
- **E2E Tests Enabled**: Complete authoring journey E2E test now active in `frontend/src/e2e/complete-authoring-journey.spec.ts`
- **TDD Enforcement**: Pre-commit hooks now enforce unit tests, E2E tests, and ≥85% coverage for all commits
- **GitHub Actions**: Implemented automated test workflow for frontend, backend, and E2E tests
- **Documentation Automation**: Pre-commit hooks auto-sync CURRENT_SPRINT.md and IMPLEMENTATION_PLAN.md from bd tracker (local only - .beads/ is gitignored)

### 2025-11-01
- **Session Management (NEW)**
- **Session Tracking**: Automatic session creation and activity monitoring
- **Security Features**: Session fingerprinting, suspicious activity detection, concurrent session limits
- **Session Timeouts**: 30-minute idle timeout, 12-hour absolute timeout
- **Frontend Integration**: `useSession` hook with auto-refresh and warning notifications
- **API Endpoints**: Complete session management API (`/api/v1/sessions/*`)
- **Comprehensive Tests**: 85%+ test coverage for session management

### Security & Authentication (2025-10-29)
- **JWT Verification Fix**: Switched from hardcoded public key to Clerk JWKS endpoint (`https://clerk.{domain}/.well-known/jwks.json`)
- **Auth Bypass Mode**: Added `BYPASS_AUTH=true` environment variable for E2E testing
- **Security Audit**: Comprehensive authentication middleware review completed

### Testing Infrastructure
- **E2E Test Suite**: Complete Playwright tests with auth bypass support
- **Test Data Helpers**: Comprehensive fixtures for books, chapters, and TOC data
- **Condition-based Waiting**: Replaced arbitrary timeouts with state polling
- **Page Objects**: Full coverage (auth, dashboard, books, summary, TOC wizard, chapter editor, export)

### Test Analysis Reports
- `docs/POST_DEPLOYMENT_TEST_REPORT.md`: Comprehensive test status after staging deployment
  - Frontend: 99.6% pass rate (732/735 tests passing, 3 skipped)
  - Backend: 98.9% pass rate (2 asyncio failures), 41% coverage vs 85% target
- `backend/TEST_COVERAGE_REPORT.md`: Module-by-module coverage analysis with 4-week improvement plan
- `frontend/docs/TEST_FAILURE_ANALYSIS.md`: Categorized frontend failures with fix priorities

### Known Issues
- **Backend Coverage**: ✅ resolved — now **~92%** (≥85% gate enforced as of #118; was 41%). Historical gaps (`security.py`, `transcription.py`, `book_cover_upload.py` duplicate) closed via #93/#116/#117.
- **Backend Asyncio**: 2 test failures related to event loop lifecycle
- **Backend Module Structure**: Missing `__init__.py` in `app/api/middleware/` causing import errors

### Package Updates
- Upgraded `lucide-react` to 0.468.0
- Resolved 5 npm audit vulnerabilities
- Updated `.gitignore` to exclude test artifacts

---

## Project Structure
- `frontend/` - Next.js application
- `backend/` - FastAPI Python application
- `docs/` - Project documentation
  - `POST_DEPLOYMENT_TEST_REPORT.md` - Comprehensive test analysis
  - `references/` - On-demand reference documentation (read when needed)
- `backend/TEST_COVERAGE_REPORT.md` - Backend coverage details
- `frontend/docs/TEST_FAILURE_ANALYSIS.md` - Frontend test categorization
- `claudedocs/` - Claude-specific analysis reports and detailed plans
- `archive/` - Historical planning documents (read-only)

---

## 📚 On-Demand Reference Documentation

For detailed information on specific topics, **read these files when needed** using the Read tool:

### Task Management
**File**: `docs/references/beads-workflow.md`
**When to read**: Before creating tasks, checking task status, or planning work
**Summary**: bd (Beads) is the single source of truth for all task tracking. Contains workflow patterns, commands, and integration guidelines.

### Documentation Standards
**File**: `docs/references/documentation-management.md`
**When to read**: Before creating new documentation, updating docs, or organizing files
**Summary**: Document hierarchy, decision trees, lifecycle management, and quality standards for all project documentation.

### Component Usage Patterns
**File**: `docs/references/component-documentation.md`
**When to read**: When using LoadingStateManager, ProgressIndicator, DeleteBookModal, or similar components
**Summary**: Comprehensive usage examples, props, integration patterns, and test coverage for reusable components.

### Quality Requirements
**File**: `docs/references/quality-standards.md`
**When to read**: Before marking features complete, submitting PRs, or implementing new features
**Summary**: Testing requirements (85% coverage), git workflow, documentation synchronization, and feature completion checklist.

### Performance Guidelines
**File**: `docs/references/performance-monitoring.md`
**When to read**: When implementing performance-sensitive features, tracking operations, or optimizing code
**Summary**: Performance tracking system, budgets (TOC: 3000ms, Export: 5000ms), Core Web Vitals, and integration patterns.

### Testing Practices
**File**: `docs/references/testing-infrastructure.md`
**When to read**: When writing tests, fixing test issues, or implementing TDD workflows
**Summary**: Test helpers (condition-based waiting, test data setup, error handling), E2E test suites, running tests, and known issues.

---

## Project Overview

This project uses SPARC (Specification, Pseudocode, Architecture, Refinement, Completion) methodology with Claude-Flow orchestration for systematic Test-Driven Development.

## Quick Start Commands

### SPARC Commands
- `npx claude-flow sparc modes` - List available modes
- `npx claude-flow sparc run <mode> "<task>"` - Execute specific mode
- `npx claude-flow sparc tdd "<feature>"` - Run complete TDD workflow

### Task Management (bd/Beads)
- `bd ready` - View unblocked tasks ready to start
- `bd list --status open` - View all open tasks
- `bd create "Task" -p 0 -t feature -d "Description"` - Create task
- `bd close <task-id> --reason "Completed"` - Close completed task

### Build & Test
- `npm run build` - Build project
- `npm test` - Run tests
- `npm run test:coverage` - Run tests with coverage
- `npm run lint` - Linting
- `npm run typecheck` - Type checking

### Backend Testing
Test/load tooling is in optional extras (`[project.optional-dependencies]`), so
production installs stay lean. Install the `test` extra once before running:
```bash
cd backend
uv sync --extra test    # one-time: installs pytest, faker, httpx, coverage…
uv run pytest --cov=app tests/ --cov-report=term-missing
```

### E2E Testing
```bash
cd frontend
npx playwright test --ui    # Run with UI mode (recommended)

# With auth bypass (for testing without real auth)
BYPASS_AUTH=true npx playwright test
```

#### Staging E2E (real auth against https://dev.autoauthor.app)
```bash
cd frontend
cp tests/e2e/staging/.env.test.example tests/e2e/staging/.env.test  # set STAGING_TEST_EMAIL / STAGING_TEST_PASSWORD
npm run test:e2e:staging
```
- Specs: `tests/e2e/staging/complete-user-journey.spec.ts` (full journey) and `regressions.spec.ts` (Issue #83 regressions: session/401, ObjectId, #54 answer persistence).
- CI: `.github/workflows/e2e-staging-tests.yml` runs on a 6h schedule, manual dispatch, and PRs labeled `e2e-staging`. Requires GitHub Secrets `TEST_USER_EMAIL` / `TEST_USER_PASSWORD` (the fixture also accepts `STAGING_TEST_EMAIL` / `STAGING_TEST_PASSWORD` locally).
- See `tests/e2e/staging/README.md` for details.

---

## Key Features

### ✅ Production Ready
- User authentication (better-auth with HS256 JWT verification)
- **Session Management** (Activity tracking, security features, timeout handling)
- Book CRUD operations with metadata
- **Book Deletion UI** (Type-to-confirm with data loss warnings)
- TOC generation with AI wizard
- Chapter tabs interface (vertical layout with keyboard shortcuts)
- **Rich Text Editor** (TipTap with full formatting)
- **AI Draft Generation** (Q&A to narrative with multiple styles)
- **Auto-save System** (3s debounce + localStorage backup on network failure)
- **Keyboard Accessibility** (WCAG 2.1 compliant)
- **Voice Input Integration** (Browser Speech API)
- **Export functionality** (PDF/DOCX with customizable options)
- **Performance Monitoring** (Core Web Vitals + operation budgets)
- **Unified Error Handling** (automatic retry with exponential backoff)

### 🚧 In Progress
See `CURRENT_SPRINT.md` for active tasks or run `bd ready` for unblocked work.

### 🔧 Test Infrastructure Status
- **Frontend**: 88.7% pass rate (613/691 tests passing)
  - 75 failures are environmental (missing mocks, not code bugs)
  - Fix plan: 3.5-5.5 hours across 4 phases
- **Backend**: 888 passed / 15 skipped; **~92% coverage** (≥85% gate enforced as of #118)
- **E2E**: Comprehensive Playwright suite with auth bypass support

---

## Code Style & Best Practices

- **Modular Design**: Files under 500 lines
- **Environment Safety**: Never hardcode secrets
- **Test-First**: Write tests before implementation (TDD)
- **Clean Architecture**: Separate concerns
- **Documentation**: Keep synchronized with code

---

## 🔒 MANDATORY: TDD & E2E Test Enforcement

**CRITICAL**: This project REQUIRES Test-Driven Development and E2E test coverage for ALL features. No feature is complete without proper test coverage.

### Pre-Commit Hook Requirements

**ALL commits MUST pass these gates:**

1. **Unit Tests**: All unit tests must pass
   ```bash
   # Frontend
   cd frontend && npm test

   # Backend
   cd backend && uv run pytest tests/
   ```

2. **E2E Tests**: All E2E tests must pass
   ```bash
   # Basic E2E tests
   cd frontend && npx playwright test

   # Deployment test suite (comprehensive)
   cd frontend && npx playwright test --config=tests/e2e/deployment/playwright.config.ts
   ```

3. **Test Coverage**: Minimum 85% coverage required
   ```bash
   # Frontend
   cd frontend && npm test -- --coverage --coverageThreshold='{"global":{"lines":85}}'

   # Backend
   cd backend && uv run pytest --cov=app tests/ --cov-fail-under=85
   ```

4. **Linting & Type Checking**: No errors allowed
   ```bash
   cd frontend && npm run lint && npm run typecheck
   cd backend && uv run mypy app/
   ```

### Feature Branch Workflow (MANDATORY)

**NEVER commit directly to `main` or `develop`. Always use feature branches:**

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit (pre-commit hooks will run automatically)
git add .
git commit -m "feat: implement your feature"

# Push to remote
git push -u origin feature/your-feature-name

# Create Pull Request for review
# PR must have:
# - All tests passing
# - ≥85% test coverage
# - E2E test for user-facing features
# - Updated documentation
```

### Feature Completion Checklist (ENFORCED)

**A feature is NOT complete until ALL of these are done:**

- [ ] **Unit tests written** (≥85% coverage for new code)
- [ ] **E2E test created** (for user-facing features)
- [ ] **All tests passing** (unit + E2E)
- [ ] **Documentation updated** (CLAUDE.md, API docs, user guides)
- [ ] **Performance validated** (meets operation budgets)
- [ ] **Accessibility verified** (WCAG 2.1 Level AA minimum)
- [ ] **Code reviewed** (PR approved by team)
- [ ] **bd task closed** (`bd close <task-id> --reason "Completed in PR #123"`)

### E2E Test Coverage Requirements

**EVERY user-facing feature MUST have an E2E test that validates:**

1. **Happy Path**: Complete user journey from start to finish
2. **Error Handling**: How the system handles failures
3. **Performance**: Operation completes within budget
4. **Accessibility**: Keyboard navigation works
5. **Data Integrity**: Data persists correctly

**Example - TOC Generation Feature:**
```typescript
// frontend/tests/e2e/toc-generation.spec.ts
test('user can generate TOC from book summary', async ({ page }) => {
  // 1. Create book with summary
  // 2. Navigate to TOC wizard
  // 3. Answer clarifying questions
  // 4. Verify TOC generates within 3000ms budget
  // 5. Verify TOC data saves to database
  // 6. Verify TOC appears in book view
});
```

### Pre-Commit Hook Setup

**✅ PRE-COMMIT HOOKS ARE CONFIGURED AND ENFORCED**

**Gates are green at baseline and enforced (#118).** Backend coverage is ~92% and frontend coverage clears 85/85/75/85, so `pre-commit run --all-files` passes cleanly. Commit and merge **without** `--no-verify` / `gh pr merge --admin` — `main` branch protection requires the `Frontend Tests` and `Backend Tests` checks (coverage included) to pass before merge. The `--no-verify` escape hatch below is for genuine emergencies only, not routine use.

This project uses automated pre-commit hooks that run before every commit. These hooks enforce TDD and quality standards.

**Install pre-commit hooks (one-time setup):**

```bash
# Install pre-commit (if not already installed)
pip install pre-commit

# Install the git hook scripts
cd /home/frankbria/projects/auto-author
pre-commit install

# Test the hooks
pre-commit run --all-files
```

**What runs on every commit:**

1. **Documentation Auto-Sync** (always runs)
   - Exports current sprint from bd tracker
   - Exports implementation plan from bd tracker
   - Auto-adds updated docs to commit

2. **Frontend Quality Gates** (runs when frontend/ files change)
   - Linting (`npm run lint`)
   - Type checking (`npm run typecheck`)
   - Unit tests (`npm test`)
   - Coverage check (≥85% required)
   - E2E tests (Playwright)

3. **Backend Quality Gates** (runs when backend/ files change)
   - Linting (`ruff check`)
   - Unit tests (`pytest tests/`)
   - Coverage check (≥85% required)

4. **General Code Quality** (always runs)
   - Trailing whitespace removal
   - End-of-file fixing
   - YAML/JSON validation
   - Merge conflict detection
   - Large file detection (>1MB blocked)
   - Private key detection

**Configuration:** See `.pre-commit-config.yaml` in project root for full details.

**Bypassing hooks (emergency only):**
```bash
git commit --no-verify -m "hotfix: emergency fix"
# Then immediately create follow-up task:
bd create "Add tests for emergency hotfix" -p 0 -t bug
```

### Test Quality Standards

**Tests MUST be:**
- **Isolated**: No dependencies on external services (use mocks)
- **Repeatable**: Same result every time
- **Fast**: Unit tests <1s each, E2E tests <30s each
- **Meaningful**: Test behavior, not implementation
- **Maintainable**: Clear, well-documented test code

**Tests MUST NOT:**
- Use arbitrary timeouts (`await page.waitForTimeout(5000)` ❌)
- Depend on test execution order
- Leave side effects (data, files, processes)
- Test internal implementation details

---

## Deployment Information
- The staging server is located at: https://dev.autoauthor.app (frontend) and https://api.dev.autoauthor.app (backend)
- You can access the staging server with SSH with username root. The keys are local; no password is required.
- There are deployment scripts in the git workflow directories
- **IMPORTANT** there are other aplications on the server. Be aware of port considerations. Right now, the backend uses 8000 and the frontend uses 3002, but be aware that this could change. Check nginx settings for the latest information.
- The applications are managed via PM2 on the server. Since the deployment has a symlinked current release directory, sometimes that needs to be checked if things are out of sync.

---

## 🚀 Available Agents


---

## 🎯 Claude Code vs MCP Tools

### Claude Code Handles ALL:
- File operations (Read, Write, Edit, MultiEdit, Glob, Grep) unless the edits are complex or long
- Code generation and programming
- Bash commands and system operations
- Implementation work
- Project navigation and analysis
- TodoWrite and task management
- Git operations
- Package management
- Testing and debugging

---

## Important Workflow Notes

### Before Starting Work
1. Run `bd ready` to see unblocked tasks
2. Check `CURRENT_SPRINT.md` for sprint context
3. Read relevant reference docs from `docs/references/` as needed

### Before Completing Features
1. Read `docs/references/quality-standards.md` for completion checklist
2. Verify 85% test coverage minimum
3. Run linting and type checking
4. Commit with conventional commit messages
5. Close task in bd: `bd close <task-id> --reason "Completed in PR #123"`

### When Creating Documentation
1. Read `docs/references/documentation-management.md` first
2. Check existing documents before creating new ones
3. Default to updating IMPLEMENTATION_PLAN.md
4. Use bd for tasks: `bd create "Task" -p 1 -t feature`

### When Using Components
1. Read `docs/references/component-documentation.md` for usage patterns
2. Check LoadingStateManager, ProgressIndicator, DeleteBookModal examples
3. Follow accessibility standards (WCAG 2.1 compliant)

---

## Quick Reference: When to Read Reference Docs

| Scenario | Read This File |
|----------|---------------|
| Creating/checking tasks | `docs/references/beads-workflow.md` |
| Creating documentation | `docs/references/documentation-management.md` |
| Using reusable components | `docs/references/component-documentation.md` |
| Completing features | `docs/references/quality-standards.md` |
| Performance optimization | `docs/references/performance-monitoring.md` |
| Writing/fixing tests | `docs/references/testing-infrastructure.md` |
| Understanding test status | `docs/POST_DEPLOYMENT_TEST_REPORT.md` |
| Backend coverage details | `backend/TEST_COVERAGE_REPORT.md` |
| Frontend test failures | `frontend/docs/TEST_FAILURE_ANALYSIS.md` |

---

## Environment Information

**Package Management**:
- Python: uv for environment and package management
- Node.js: npm for frontend dependencies

**Task Tracking**:
- Use bd (Beads) for all task management
- Run `bd quickstart` to learn the system
- Markdown files (CURRENT_SPRINT.md, IMPLEMENTATION_PLAN.md) are auto-generated snapshots

**Documentation Structure**:
- `CLAUDE.md` (this file) - Quick reference and core guidelines
- `docs/references/*.md` - Detailed reference documentation (read on-demand)
- `claudedocs/*.md` - Technical analysis and detailed plans
- `archive/*.md` - Historical planning documents (read-only)

**Environment Variables**:
- `BYPASS_AUTH=true` - Disable authentication for E2E testing (development only)
- Standard Next.js and FastAPI environment variables (see `.env.example`)

---

## API Overview

### Authentication
- **Production**: Better-auth JWT verification using HS256 shared secret
- **Testing**: `BYPASS_AUTH=true` creates mock authenticated context
- **Security**: Never use auth bypass in production environments

### Core Endpoints
- `/api/v1/books` - Book CRUD operations
- `/api/v1/chapters` - Chapter management
- `/api/v1/toc` - Table of Contents generation
- `/api/v1/export` - PDF/DOCX export

See backend API documentation for full endpoint reference.
