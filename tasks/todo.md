# Issue #193 — [P2.1] Live /chapters route serves hardcoded mock questions for every book

**Branch**: `fix/193-remove-mock-chapters-page`
**Plan source**: CodeRabbit comment (2026-07-04, design choice resolved: delete, not rewire). Verified against codebase 2026-07-12.

## Verified facts (plan adaptation)

- `frontend/src/app/dashboard/books/[bookId]/chapters/page.tsx` is the mock page (hardcoded ML questions, `setTimeout` fake regeneration, ignores `bookId`). No unit tests reference it; no `layout/loading/error` companions in the folder; sibling `[chapterId]/page.tsx` (legacy self-redirecting editor) stays.
- Only reference: `frontend/src/e2e/complete-authoring-journey.spec.ts:201` — inside a `test.skip`'d journey (CI has no OpenAI key), so the rewrite keeps the spec valid for future un-skip but nothing runs it today.
- **Plan correction**: chapter tab clicks don't update the URL (`?chapter=` is read-only initial state in `page.tsx:91`), so the rewritten step can't extract the chapter id from the URL. It opens the first sidebar tab (`[data-testid="chapter-tab"]:not([data-tab])`, mirroring `chapter-questions-tabs.spec.ts`), waits for the "Chapter editor view" tablist, and reads the id from the tab's `data-rfd-draggable-id` ancestor.
- Step 5's `[data-testid="chapter-tab"][data-tab="questions"]` selector already matches the live ChapterEditor (`ChapterEditor.tsx:498-499`) — untouched.
- `NavigationFix.test.tsx:55` asserts navigation does NOT push to '/chapters' — unaffected (stays green).

## Steps

- [x] 1. Delete `frontend/src/app/dashboard/books/[bookId]/chapters/page.tsx`
- [x] 2. Rewrite journey spec step 4 (navigate via real tabbed interface, id from draggable attr)
- [x] 3. Frontend suite + lint + typecheck green — 115 suites, 2096 passed / 8 skipped, coverage gates green
- [x] 4. Deslop scan clean; opencode (GLM) pre-PR review: "clean to merge"
- [x] 5. PR #278; post-PR fresh-session review "clean to merge", posted as comment
- [x] 6. Demo (`docs/demos/2026-07-12-issue-193-remove-mock-chapters.md`, showboat verify green): main 200 + fake ML questions for real gardening book vs branch 404, same session; real Interview Questions tab shown working on branch
- [x] 7. CI green + final triage; docs sync; merge

## Acceptance criteria

- [x] The abandoned page is deleted (AC "delete" branch); `/dashboard/books/<id>/chapters` no longer resolves (404 demoed)
- [x] Real Q&A flow (ChapterEditor "Interview Questions" tab) unaffected (demoed)
