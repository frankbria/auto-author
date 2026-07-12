# Issue #203 — [P2.11] TOC clarifying-questions shows 'Auto-saved' but never persists

**Branch**: `feature/issue-203-toc-autosave-persist`
**Plan source**: CodeRabbit comment (2026-07-04), verified against codebase 2026-07-11.

## Verified facts (plan adaptation)

- Issue body says "bookClient exposes only a GET" — **stale**: `saveQuestionResponses` (PUT) exists at `bookClient.ts:929` and hits `PUT /books/{id}/question-responses`, which the backend serves (`books.py:994`) accepting exactly `{question, answer}` items (rejects empty answers → the component's non-empty filter is required and already there).
- The only blocker was the type annotation: `bookClient.ts` imports `QuestionResponse` from `@/types/chapter-questions` (has `response_text`), while the wire shape and the component use `@/types/toc.QuestionResponse` (`{question, answer}`).
- **Hydration is also silently broken**: mount effect reads `response.response_text`, backend returns `answer` — saved answers never pre-fill. Two existing tests characterize this bug (`response_text` fixtures).
- Wizard sends responses in the generate-toc request body (#105), so submit-path persistence is defense-in-depth only.
- Design choice (autonomous): wire real persistence (AC branch 2) — endpoint + client already exist; removing the indicator would be weaker UX for no less work.

## Steps

- [x] 1. `bookClient.ts`: alias `QuestionResponse as TocQuestionResponse` from `@/types/toc`; retype plural `saveQuestionResponses` / `getQuestionResponses` only; fix the stale top-of-file comment. Per-chapter singular methods untouched.
- [x] 2. `ClarifyingQuestions.tsx`:
  - Debounced effect calls `bookClient.saveQuestionResponses(bookId, nonEmptyResponses)`; `lastSaved` set from returned `answered_at` only on success; failure → keep indicator un-saved + lightweight error state (no silent success).
  - Stale-response guard (generation counter ref) so an out-of-order save can't clobber newer UI state.
  - Hydration maps `answer` (not `response_text`).
  - `handleSubmit` best-effort saves before `onSubmit` (failure doesn't block TOC generation — responses ride the generate-toc body).
- [x] 3. Tests (`ClarifyingQuestions.test.tsx`) — TDD, updated first:
  - Auto-saved appears only after mocked `saveQuestionResponses` resolves, called with `{question, answer}` payload.
  - Failure path: reject → no "Auto-saved", error affordance shown.
  - Hydration fixtures corrected to `{question, answer}`.
  - Submit-path save assertion.
- [x] 4. Full frontend suite + lint + typecheck; deslop scan.
- [x] 5. opencode (GLM) pre-PR review (codex fallback per hang memory).
- [x] 6. PR; post-PR review posted as comment.
- [x] 7. Demo (showboat + agent-browser): real servers, type answer → refresh → answer survives (main loses it).
- [x] 8. CI green + final triage; docs sync; merge.

## Acceptance criteria

- [x] Debounced effect wired to real save endpoint (AC option 2)
- [x] A test asserts the indicator only shows after a real successful persist
