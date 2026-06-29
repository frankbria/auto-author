# Issue #56 — [P2.6] Enhance voice input with AI analysis and formatting

Branch: `feature/56-voice-input-ai-enhancement`

## Approach (adapted from Traycer plan)
Mirror the #57 `enhance-text` / #58 `transform-style` house pattern: a dedicated
service module + `ai_service` method + chapter-scoped **preview-only** endpoint +
frontend dialog + client method + tests. Raw dictated text → AI cleanup → side-by-side
preview → apply/revert (reusing ChapterEditor's existing snapshot/revert infra).

### Autonomous design decisions (no architectural fork → no approval needed)
- **Single "cleanup" mode** (one AI pass: filler removal + paragraph breaks at natural
  pauses + grammar/punctuation), NOT the Traycer 3 boolean toggles. The AC lists all
  three as expected *outcomes*, not user options; "toggle raw vs enhanced" = the
  side-by-side preview + revert. Fewer moving parts. (Deviation from original plan.)
- Temperature **0.3** (conservative, like `enhance_text`) — voice cleanup must not invent content.
- **Reuse** ChapterEditor `getEnhanceContent` + `handleApplyEnhancement` + `preEnhanceContent`
  revert button — no new editor state needed.
- Ignore the unmounted `/transcribe` router and the deleted `chapter_error_handler` /
  `chapter_cache_service` that the Traycer plan referenced (gone in #120).
- E2E **route-mocks** the enhance endpoint — browser SpeechRecognition is native and
  non-deterministic/unavailable headless (same approach as content-enhancement.spec.ts).

## Steps (TDD: tests first)
- [ ] 1. Backend service `app/services/transcription_enhancement.py` + test
- [ ] 2. `ai_service.enhance_transcription(content)` + test
- [ ] 3. Endpoint `POST /books/{id}/chapters/{cid}/enhance-transcription` in books.py + test
- [ ] 4. `bookClient.enhanceVoiceTranscription(bookId, chapterId, {content})`
- [ ] 5. `VoiceEnhancer.tsx` dialog (intro→enhancing→preview, DOMPurify side-by-side) + test
- [ ] 6. Wire VoiceEnhancer into ChapterEditor toolbar (reuse revert)
- [ ] 7. E2E `frontend/src/e2e/voice-enhancement.spec.ts`
- [ ] 8. Docs (CLAUDE.md Recent Changes) + close #56

## Acceptance Criteria (from issue)
- [ ] Voice transcription works reliably (existing VoiceTextInput — unchanged)
- [ ] AI enhancement removes filler words
- [ ] Paragraphs break at natural pauses
- [ ] Grammar and punctuation improved
- [ ] Users can toggle raw vs. enhanced (preview + revert)
- [ ] Enhancement processing shows loading indicator
- [ ] Side-by-side preview before accepting
- [ ] E2E test verifies voice-to-enhanced workflow
