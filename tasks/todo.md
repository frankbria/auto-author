# [P2.17] #218 — Summary readiness gate: contradictory word/char copy + threshold mismatch

**Plan source**: self-authored (no plan comment on the issue).
**Approval**: autonomous — no architectural fork.

## The real gate (verified, not assumed)

Both backend paths enforce the **identical** minimum — there is no AI-decided threshold:

| Location | Rule |
|---|---|
| `backend/app/api/endpoints/books.py:1150` (deterministic fallback, no analysis) | `word_count >= 30 and char_count >= 150` |
| `backend/app/services/ai_service.py:483` (AI-analysis path) | `word_count >= 30 and char_count >= 150` |

The frontend wizard gates on `meets_minimum_requirements` (`TocGenerationWizard.tsx:97`) and ignores
`is_ready_for_toc` entirely. So **30 words AND 150 characters** is the one true gate.

Four numbers currently describe "long enough"; only one is enforced:

| Location | Claim | Enforced? |
|---|---|---|
| backend (both paths) | 30 words + 150 chars | **YES** |
| `summary/page.tsx:9` `MIN_SUMMARY_LENGTH = 30` | 30 **characters** | client-side only, far too weak |
| `summary/page.tsx:225` guideline copy | "Minimum 30 **words** recommended" | no (and contradicts the counter 2 lines above) |
| `NotReadyMessage.tsx:128` | "at least 500-1000 words" | no — fiction |
| `bookClient.ts:512` doc comment | "Need: 100+ words." | no — fiction |

The `30` on the summary page and the `30` in the backend are the same digits in **different units**
(chars vs words) — a coincidence that invites a wrong "fix".

## Design decisions (autonomous — no architectural fork)

1. **Hard client gate == the exact backend gate** (30 words AND 150 chars), not a soft warning. The AC
   allows either; a hard gate at the real threshold is what "consistent with the real AI readiness
   threshold before the user invests time" literally asks for. A soft warning would still let the user
   walk into the dead-end.
2. **Word counting must match Python's `str.split()` exactly**, or client and server disagree at the
   boundary — which is the very bug class being fixed. `text.trim().split(/\s+/).filter(Boolean).length`.
3. **Char count stays untrimmed** (`text.length`) to match backend `len(summary)`.
4. Constants live in `frontend/src/lib/constants/summary-readiness.ts`, following the established
   pattern (`auto-save.ts`, `writing-styles.ts`, `book-metadata.ts`): documented SSOT + issue ref.
5. **No data loss from raising the gate**: the debounced auto-save (`page.tsx:55-73`) persists
   independently of validation, so a user under the threshold keeps their work — they just can't proceed.
6. `NotReadyMessage`'s "500-1000 words" is replaced by the real requirement stated as a requirement,
   keeping any aspiration separate from the threshold. No invented numbers.

## Steps

1. **Create `frontend/src/lib/constants/summary-readiness.ts`** — `SUMMARY_MIN_WORDS = 30`,
   `SUMMARY_MIN_CHARACTERS = 150`, `SUMMARY_MAX_CHARACTERS = 2000`, `countSummaryWords()`,
   `getSummaryReadinessError()`. Docstring cites the backend file:line it mirrors.
   Tests: `frontend/src/lib/constants/__tests__/summary-readiness.test.ts`.
2. **`summary/page.tsx`** — drop `MIN_SUMMARY_LENGTH`, delegate to `getSummaryReadinessError()`;
   counter shows words **and** characters against both minimums; fix the contradictory guideline copy.
   Tests: new `frontend/src/app/dashboard/books/[bookId]/summary/__tests__/page.test.tsx` (none exist today).
3. **`NotReadyMessage.tsx:128`** — replace the "500-1000 words" fiction with the real threshold.
   Tests: extend/create a copy pin.
4. **`bookClient.ts:512`** — correct the "100+ words" doc comment.

## Acceptance criteria

- [ ] AC1: words/characters copy mismatch fixed (counter, guideline text, NotReadyMessage tips all agree)
- [ ] AC2: client gate raised to be consistent with the real AI readiness threshold (30 words AND 150 chars)
- [ ] AC3: the dead-end is gone — a summary that passes the client gate is accepted by the wizard

## Test strategy

- Constants unit tests: boundary cases (29/30 words, 149/150 chars), Python-`split()` parity
  (multiple spaces, newlines, tabs, leading/trailing whitespace, empty).
- Summary page tests: submit blocked under each threshold, enabled at exactly the threshold,
  counter copy, guideline copy, no contradictory strings.
- NotReadyMessage: pin that the fictional "500-1000" copy is gone and the real threshold is shown.
- **RED-verify every behavior pin at birth** + mutation-check per repo convention.
- Demo (Phase 11, hard gate): real backend + Mongo, main-vs-branch differential proving the dead-end
  on main and its absence on the branch.
