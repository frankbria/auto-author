# Issue #62 [P3.4] — Question regeneration with improved quality

**Branch**: `feature/question-regeneration-62`
**Plan source**: CodeRabbit + Traycer comments, heavily adapted (Phase 2 was stale — see deviations).

## Reality check vs. the plan (verified in codebase)
Already exist → NOT rebuilt: per-question regenerate button, full-set `POST .../regenerate-questions`
endpoint + `bookClient.regenerateChapterQuestions`, rating UI (thumbs → `rate_question` →
`question_ratings`), focus types (CHARACTER/PLOT/SETTING/THEME/RESEARCH), rate limiting
(gen 3/120s, regen 2/180s).

**Bug confirmed**: `QuestionContainer.handleRegenerateQuestion` calls `bookClient.generateQuestions(bookId)`
(the TOC clarifying-questions method) instead of a chapter regenerate → per-question regenerate is broken.

**Stale plan section**: CodeRabbit Phase 2 wires in `QuestionFeedbackService` / `question_quality_service` /
`RefinementAction` / `analyze_question_feedback_trends` — ALL deleted in #120. Not resurrected (YAGNI).
Replaced with a minimal rating→prompt-guidance wiring so the already-collected ratings finally influence output.

## Acceptance criteria → coverage
- [ ] Regenerate button per question — EXISTS; fix its wiring (Step 6)
- [ ] Regenerate entire set — endpoint EXISTS; add UI (Step 7)
- [ ] Regenerated questions meaningfully different — Step 3 (previous-questions in prompt)
- [ ] Mark helpful/not helpful — EXISTS (thumbs rating)
- [ ] Feedback influences future questions — Step 4 (minimal rating aggregation → prompt)
- [ ] Specify question focus — regen endpoint already accepts `focus`; expose in UI (Step 7/6)
- [ ] Limit on regeneration attempts — rate limit EXISTS; add per-question `regeneration_count` cap (Step 1,5)
- [ ] E2E test — Step 10

## Steps

### Backend
1. **`regeneration_count` field** — add `regeneration_count: int = 0` to `QuestionBase` (schemas/book.py)
   so it flows through `model_dump()` on create + reads back on `Question` (default 0 for legacy docs).
   Add `MAX_QUESTION_REGENERATION_COUNT: int = 5` to `core/config.py`.
2. **DB helper** — `get_ratings_for_chapter(book_id, chapter_id, user_id)` in `db/questions.py`:
   join `question_ratings` to the chapter's questions, return `[{question_text, rating, feedback}]`.
   Export via `db/database.py` re-export (match existing pattern).
3. **Prompt builder** — add `previous_questions: Optional[List[str]] = None` +
   `feedback_guidance: Optional[str] = None` to `_build_question_generation_prompt`; append an
   "avoid duplicating these" block and (if present) a "users found these unhelpful" block. Thread the
   params through `generate_chapter_questions` and `generate_questions_for_chapter`.
4. **Feedback wiring (minimal)** — small service helper `_build_feedback_guidance(ratings)` → short string
   from low ratings (<=2) + their feedback text (None if no signal). Used by both regen paths.
5. **Single-question regen service + endpoint**:
   - service `regenerate_single_question(book_id, chapter_id, question_id, user_id, focus=None)`:
     fetch question (404 if missing/not-owned/wrong chapter); if `regeneration_count >=
     MAX_QUESTION_REGENERATION_COUNT` raise `RegenerationLimitError` → 429; gather sibling question texts
     (previous_questions) + feedback guidance; generate ONE question (reuse `generate_chapter_questions`,
     count=1, focus = passed focus or original type); delete old question (+its response) and create the
     new one with `order` preserved and `regeneration_count = old+1`; return the new `Question`.
   - endpoint `POST /{book_id}/chapters/{chapter_id}/questions/{question_id}/regenerate` in books.py
     (ownership 403/404, rate limit 2/180s, 429 on limit). No route-shadow (distinct `/regenerate` suffix).
   - full-set `regenerate_chapter_questions`: fetch existing question texts BEFORE delete → pass as
     previous_questions; also pass feedback guidance.

### Frontend
6. **Fix bug + single regen** — add `bookClient.regenerateSingleQuestion(bookId, chapterId, questionId, {focus?})`
   (POST new endpoint); rewire `QuestionContainer.handleRegenerateQuestion` to it; replace the one question
   in state from the response. Add `regeneration_count` to `Question` type.
7. **Regenerate-all UI** — "Regenerate All" button in QuestionContainer (visible when questions exist) →
   small dialog (mirror existing Radix Dialog pattern) with focus checkboxes + preserve-responses toggle →
   `bookClient.regenerateChapterQuestions(..., options, preserve)`; loading state.
8. **Limit display** — show `Regenerated N/5` per question in QuestionDisplay; disable regenerate + tooltip
   when at max.

### Tests
9. **Backend** — unit (prompt includes previous-questions + feedback guidance; `_build_feedback_guidance`);
   integration (`test_question_regeneration.py`): single-regen success + count increments + 429 at limit +
   404 wrong owner; full-regen passes previous questions.
10. **Frontend + E2E** — unit (bookClient method, handler rewire, limit-disable render); route-mocked E2E
    `question-regeneration.spec.ts` (regenerate one → replaced; regenerate-all dialog; limit disables button).

## Deviations from original plan
- Phase 2 (feedback service resurrection) dropped — service deleted in #120; replaced with minimal
  rating→prompt wiring (no new service/enum). YAGNI.
- Single-question regen kept (needed: the only existing regen endpoint nukes the whole set).
- "Limit" satisfied by BOTH existing rate limiting AND a per-question `regeneration_count` cap.
- Real-AI E2E (asserting semantic difference) stays out of CI (no OpenAI key) — route-mocked E2E instead,
  matching #56/#57/#58 precedent.

No substantive architectural fork → proceeding autonomously per Phase 4.
