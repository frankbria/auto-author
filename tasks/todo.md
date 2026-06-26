# Issue #105 — Harden full staging E2E journey ✅ COMPLETE

**Done (PRs #134 + #135, merged + deployed):** staging suite 4/4 pass, 3 consecutive
runs against live dev.autoauthor.app. Wired Q&A into editor; fixed generate-toc
body-responses, analyze-summary readiness poisoning, and the OpenAI key name.


## Root-cause finding (drives scope)
The interview-questions Q&A loop (#54: generate → answer → persist) is **not mounted** in
any navigable route. `QuestionContainer`/`ChapterQuestions` exist with real persistence
(`PUT /books/{id}/chapters/{cid}/questions/{qid}/response`) but the live `ChapterEditor`
only surfaces draft + style-transform; the only `/chapters` page is hardcoded mock data.
**User chose: wire the Q&A UI into the editor (make #54 real), then harden + un-fixme.**

## Plan

### 1. Feature: mount Q&A panel in ChapterEditor
- [ ] Add `view: 'write' | 'questions'` state + a Write / Interview Questions toggle
- [ ] Render `<QuestionContainer bookId chapterId chapterTitle onDraftGenerated onSwitchToEditor>` in questions view
- [ ] Keep existing toolbar/editor/footer in write view
- [ ] Unit test: toggling renders QuestionContainer / back to editor (mock QuestionContainer)

### 2. Shared, correct E2E helpers (single source of selectors)
- [ ] `tests/e2e/staging/fixtures/journey.helpers.ts`: createBook (modal, 1500ms delayed nav),
      addSummary (wait GET settle → fill+verify → wait save), completeTocWizard (auto readiness →
      ClarifyingQuestions → "Generate Table of Contents" → TocReview "Accept & Continue" → /edit-toc),
      openChapterEditor, openQuestionsPanel, generate+answer questions (wait PUT .../response)

### 3. Harden specs (real selectors, web-first, network waits; no waitForTimeout / silent isVisible)
- [ ] `regressions.spec.ts` #54: un-fixme, rewrite via helpers
- [ ] `complete-user-journey.spec.ts`: un-fixme, rewrite full happy path incl. draft

### 4. Verify
- [x] Jest unit (272 chapters tests pass) + typecheck + lint (0 errors)
- [x] Live staging: session/401 ✓, ObjectId create ✓ (new dialog selectors), summary fill-race fix ✓
- [ ] BLOCKED — TOC/questions/draft legs: staging OpenAI key is INVALID (401 invalid_api_key
      on every AI call). Confirmed via authenticated analyze-summary response. **User must
      rotate `OPENAI_AUTOAUTHOR_API_KEY` on staging.** Then deploy this branch + re-run.

### 5. Backend robustness bug fixed (found while iterating)
- [x] `analyze_book_summary` persisted FAILED analyses → permanently poisoned the readiness
      check (has_analysis=true, meets_minimum=false). Now returns retryable 503 and does NOT
      persist, so readiness falls back to the deterministic word/char check. +1 test.

## Forbidden-pattern checklist (CLAUDE.md)
- [x] No `page.waitForTimeout()` (only mentioned in comments)
- [x] No silent `if (await x.isVisible())` skips

## Blocker for the user
Staging `OPENAI_AUTOAUTHOR_API_KEY` returns 401 invalid_api_key. Rotate it, then I deploy
this branch (frontend Q&A wiring + backend fix) and re-run the full journey for the >95% gate.
