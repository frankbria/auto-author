# Issue #201 — [P2.9] Core authoring journey has no CI-runnable E2E (all skipped)

**Plan source**: self-authored (issue had no plan comment, only CodeRabbit boilerplate).
**Branch**: feature/issue-201-ci-runnable-e2e

## Facts established (verified in code)

- CI `e2e-tests` job runs a **real backend + Mongo** (`BYPASS_AUTH=true`, DB `auto_author_e2e_test`), chromium only, **no OpenAI key** (`.github/workflows/tests.yml:116-215`). So deterministic endpoints are live in CI; only AI endpoints need `page.route` mocks.
- `TocGenerationWizard.handleAcceptToc` persists via deterministic `PUT /books/{id}/toc` (`TocGenerationWizard.tsx:183`) — browser-mocking `generate-toc` still yields **real persisted TOC** after Accept.
- `editing-autosave-flow.spec.ts` route globs are broken: `**/api/books/...` never matches `/api/v1/books/...`, and it checks `PUT||POST` while the real save is **PATCH** `/books/{id}/chapters/{id}/content` (`bookClient.ts:988`). Its `text=/saved.*✓/i` assertion can never match (icon is SVG, no ✓ glyph, `ChapterEditor.tsx:807-808`).
- `error-recovery-flow.spec.ts` pins **nonexistent behavior**: `bookClient.createBook` is a plain fetch with zero retry (`bookClient.ts:340-350`). Real create-book error UX = classified error notification + no redirect (#46). Real retry-with-backoff = QuestionDisplay save path (internal ErrorHandler, exactly 3 attempts, then persistent error + Retry — #197).
- `interview-prompts.spec.ts` "NOT IMPLEMENTED" premise is stale — the feature shipped (`QuestionContainer` in `ChapterEditor.tsx:515`); its ~15 aspirational testids don't exist; real coverage lives in `chapter-questions-tabs.spec.ts` + the new journey spec.
- Save-status footer (`ChapterEditor.tsx:793-816`) is text-only: "Saving...", "Saved {time}", "Not saved yet"; backup banner/buttons/error text all exist with stable text.

## Steps

- [x] 1. **ChapterEditor testids** (only app-code change): add `data-testid="save-status-indicator"` + `data-save-status={saveStatus}` to the save-status footer. Everything else already has stable text/roles — YAGNI on further testids.
- [x] 2. **Rewrite + un-skip `complete-authoring-journey.spec.ts`** (AC1): real backend for book create → summary → TOC accept (real PUT /toc) → chapter content autosave; `page.route` mocks ONLY for AI + question-store endpoints (`analyze-summary`, book-level `generate-questions`, `generate-toc`, chapter `generate-questions` + `GET questions` + `PUT response` + `question-progress`, `generate-draft`) using the proven `**/books/...` globs (draft-generation.spec.ts pattern). Assert outcome evidence: TOC persisted (chapter tabs render from backend), content persisted (re-GET via API), draft in `.tiptap`. Remove `waitForTimeout`s, silent `if(isVisible)` guards, and the two self-skipping stub tests. Cleanup book in afterEach.
- [x] 3. **Rewrite + un-skip `editing-autosave-flow.spec.ts`** (AC2a): seed via `createTestBookWithTOC`, drive the real tabbed book page (openFirstChapter idiom). Tests: typing → Saving… → Saved (via `waitForResponse` on PATCH); debounce collapses N keystrokes → 1 PATCH; PATCH failure (route abort) → error text + localStorage backup written; reload → recovery banner → Restore restores content / Dismiss clears; recovery after failure → Saved again. Fix globs/method; drop the ✓ assertion for the new testid.
- [x] 4. **Rewrite + un-skip `error-recovery-flow.spec.ts`** (AC2b): pin behavior that actually ships — (a) create-book 5xx → error notification, no redirect, form input retained; route restored + resubmit succeeds; (b) question-response save failure → exactly 3 automatic attempts (retry-with-backoff evidence via request count) then persistent error + Retry button; (c) non-retryable 4xx → no auto-retry storm on create. Deviation: the old suite's exponential-backoff-on-createBook premise is false (no retry code on that path).
- [x] 5. **Delete `interview-prompts.spec.ts`** (AC3 "update/remove" → remove): stale premise, aspirational selectors, cross-browser rationale moot (CI is chromium-only); questions coverage = chapter-questions-tabs.spec.ts + journey step. Precedent: #200.
- [x] 6. **Verify**: run the three specs locally against real backend+Mongo (chromium); mutation-check at least one behavior pin per spec (e.g. break debounce/save-status → spec fails); full frontend unit suite + lint + typecheck; confirm CI e2e job now executes the un-skipped suites.

## Acceptance criteria

- [x] AC1: route/service-mocked full-journey spec runs in CI without a live key (journey spec un-skipped, chromium, no OPENAI env).
- [x] AC2: missing data-testids added; autosave + error-recovery suites un-skipped and executing.
- [x] AC3: stale "NOT IMPLEMENTED" suite removed.

## Key decisions (autonomous, safe defaults)

- Hybrid mocking (real deterministic backend + AI-only route mocks) over full route-mock: matches CI reality, proves real persistence; precedent chapter-questions-tabs + draft-generation.
- Error-recovery retargeted to shipped behavior instead of un-skipping a spec that pins fiction.
- Remove (not rewrite) interview-prompts: duplicate coverage, dead selectors.
- Drive autosave tests through the real tabbed book page, not the legacy `/chapters/[chapterId]` redirect shim (#193 calls it legacy; pinning tests to it invites churn).
