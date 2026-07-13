# Issue #197 [P2.5]: Fix auto-save-clears-error bug in QuestionDisplay

**Plan source**: CodeRabbit comment (2026-07-04). Design choice pre-resolved (option 2): gate auto-save on `saveStatus !== 'error'` AND clear error state on genuine user edit so auto-save resumes naturally. Manual Retry button untouched.

**Plan verification (2026-07-12)**: all targets confirmed — auto-save effect `QuestionDisplay.tsx:314-328` guards only `responseText.trim() && !isSaving`; bare `onChange={setResponseText}` at :508; three `it.skip`s at test lines 197/252/276 with TODOs + console.logs.

## Adaptations to the CodeRabbit plan
1. **Mock/timing corrections (authorized by plan Phase 2 Task 2)**: `ErrorHandler.execute` internally retries NETWORK/SERVER errors 3 attempts with backoff 1s+2s+**4s** (incl. a wasted sleep after the final attempt) ≈ 7s before throwing — the tests' 5s `waitFor` timeouts are too short (their "~3000ms" comment miscounted); bump to 10s waitFor / 15s jest. The completion test's `.mockRejectedValueOnce().mockResolvedValueOnce()` would be absorbed by the *internal* retry and succeed without ever showing the error — change to 3 rejections (exhaust internal retries) then resolve for the manual Retry click.
2. **Extra regression pins** (cheap, direct AC evidence): (a) after a failed save with a non-retryable error, wait >3s real time → error banner still visible and `saveQuestionResponse` called exactly once (pins "auto-save suppressed after failure"); (b) typing after an error clears the banner and resets status (pins the resume path).

## Todo
- [ ] Branch `fix/197-autosave-clears-error`
- [ ] RED: un-skip the 3 tests (with corrected mocks/timeouts) → fail on current code
- [ ] Fix: gate auto-save effect on `saveStatus !== 'error'` (+ dep), wrap onChange to clear error state on edit
- [ ] GREEN: 3 un-skipped + 2 new pins pass; remove TODOs + console.logs; full QuestionDisplay suites green
- [ ] Full frontend suite + lint + typecheck; coverage gates green
- [ ] Deslop scan, quality gate (opencode/codex review pre-PR)
- [ ] PR, post-PR review, demo (error persists >3s in real browser), CI gate, merge
