# Issue #247 — Entitlement 402s never reach the Upgrade CTA (wizard + draft dialog; draft dialog leaks raw JSON)

Frontend-only. PR target: main. Plan source: CodeRabbit comment on #247, adapted. **No architectural fork** — the plan's two design choices are already resolved (inline affordance; deep-link target), and my changes are drift corrections → approved autonomously.

## Plan drift corrections (vs the CodeRabbit plan)

1. **Phase 4 DROPPED — already shipped in #246 (#222)**: `ErrorNotification.tsx:97` already navigates to `/dashboard/settings?tab=billing`, and `dashboard/settings/page.tsx` already validates `?tab=` against `SETTINGS_TABS` and strips it via `replaceState`. The plan was generated pre-#246.
2. **NotReadyMessage optional task SKIPPED (YAGNI)**: its swallowed analyze-summary failure calls `onRetry()` → fresh `checkTocReadiness` → analyze 402 → now routes to the entitlement ERROR panel anyway. No extra plumbing needed.
3. The "skipped `TocGenerationWizard.test.tsx`" the plan references is a placeholder test that never mounts the wizard (router-context excuse). New wizard entitlement tests go in `frontend/src/components/toc/__tests__/` with a `next/navigation` mock (established repo pattern).

## Steps

- [ ] 1. `bookClient.generateChapterDraft` non-OK branch → `throw await this.aiError(response, 'Failed to generate draft')` (kills the raw-JSON leak, attaches `statusCode` for the 402 classifier).
- [ ] 2. `DraftGenerator.handleGenerateDraft` → call `generateChapterDraftWithErrorHandling` (inside `trackOperation`); branch on `result.data`; delete the local `Generation Failed` toast (the wrapper fires the classified notification — Upgrade toast for 402).
- [ ] 3. `DraftGenerationButton.handleGenerateDraft` → keep the local try/catch for `getChapterQAResponses` + minimum-responses check (non-AI errors keep the inline error state); the draft call goes through the wrapper; on failure set inline `error` from `result.error` (clean message), `step='options'`, no raw toast.
- [ ] 4. `WizardState` gains `errorStatusCode?: number` (`frontend/src/types/toc.ts`).
- [ ] 5. `TocGenerationWizard`: nested analyze-summary catch routes `statusCode === 402` to the ERROR step (no longer swallowed); all outer catches (`checkTocReadiness`, `generateQuestions`, `handleQuestionSubmit`, `handleRegenerateToc`, `handleAcceptToc`) capture `statusCode` into `errorStatusCode`; ERROR render passes it to `ErrorDisplay`.
- [ ] 6. `ErrorDisplay`: optional `statusCode` prop; when 402 → "Upgrade Required" panel with an Upgrade link to `/dashboard/settings?tab=billing`, entitlement copy, no "Try Again", no generic troubleshooting tips.
- [ ] 7. Tests (TDD):
  - `bookClient.test.ts`: update `generateChapterDraft` non-OK expectation (parsed message + `statusCode`, no raw body); add 402 `detail.error` case.
  - `DraftGenerator.test.tsx` / `DraftGenerationButton.test.tsx`: mock the wrapper; assert no raw payload rendered/toasted; entitlement path returns without local toast; non-entitlement failure shows friendly `result.error`.
  - New wizard test: analyze-summary 402 → ERROR step renders Upgrade link (`?tab=billing`), no "Try Again"; non-402 analyze failure still proceeds to readiness check (regression).
- [ ] 8. Quality gate: full frontend suite + lint + typecheck; opencode pre-PR review; PR; post-PR review; demo (hard gate); CI; merge.

## Acceptance criteria (from issue)

- Entitlement denials in the TOC wizard surface an upgrade affordance deep-linking to `/dashboard/settings?tab=billing` (not "Try Again").
- Draft dialog 402 shows the Upgrade CTA path; **no raw JSON payload renders in the UI** anywhere in these flows.
