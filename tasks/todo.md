# Issue #53 [P2.7] — Fix incomplete progress tracking for chapter question workflows

Branch: `feature/53-question-progress-tracking`

## Findings (plan adapted to actual code)
Backend already supplies progress + per-question `response_status` (DRAFT/COMPLETED;
unanswered = undefined). The CodeRabbit/Traycer "replace stub Progress bar" task is
**already done** — `QuestionProgress.tsx` already imports the real shadcn `Progress`.
Remaining genuine gaps, frontend only:

## Tasks
- [ ] **A** `QuestionContainer.handleResponseSaved` refreshes only progress, not the
  questions array → dropdown/dots show stale status. Refresh both (call `fetchQuestions`
  which already re-fetches progress). Pass `questions` to `QuestionProgress`.
- [ ] **B** `QuestionProgress` dots use positional logic (`index < progress.completed`),
  wrong for out-of-order answers. Use per-question `response_status`.
- [ ] **C** `QuestionNavigation`: add `findNextUnanswered` + "Next Unanswered" button
  (disabled when all completed).
- [ ] **D** `QuestionNavigation` dropdown: mark unanswered questions distinctly (○ + muted).
- [ ] **E** Tests: QuestionProgress (per-question dots), QuestionNavigation (next-unanswered
  + dropdown marker), QuestionContainer (refresh-on-save), E2E progress spec.

## Acceptance criteria mapping
- "X of Y answered" / progress bar % — already present (QuestionProgress). Verify.
- Unanswered distinct — D.
- "Next Unanswered" navigates — C.
- Progress persists across sessions — backend persists; load on mount. Verify.
- Real-time updates — A.
- Integration + E2E tests — E.

## Out of scope
No backend changes. No new keyboard shortcut (YAGNI). Minimal diff.
