"""
Voice-transcription cleanup template (issue #56).

Raw speech-to-text from voice input is verbatim: filler words, run-on
sentences, no paragraph breaks, missing punctuation. This single "cleanup"
pass turns that into readable prose — removing fillers, breaking paragraphs at
natural pauses, and fixing grammar/punctuation — WITHOUT changing what was said.

Single mode (unlike the multi-dimension content_enhancement.py, #57): the issue
treats filler removal, paragraphing, and grammar as one expected outcome, not a
menu of user choices.
"""

TRANSCRIPTION_ENHANCEMENT_LABEL = "Dictation Cleanup"

TRANSCRIPTION_CLEANUP_GUIDANCE = (
    "Clean up this raw voice transcription into readable written prose:\n"
    "- Remove filler words and verbal tics (\"um\", \"uh\", \"er\", \"like\", "
    "\"you know\", \"sort of\", \"kind of\", \"I mean\", \"basically\", "
    "\"actually\", repeated false starts).\n"
    "- Break the text into paragraphs at natural topic shifts and pauses.\n"
    "- Add correct punctuation and capitalization; fix grammar, tense, and "
    "subject-verb agreement.\n"
    "- Keep the speaker's wording, voice, and intent — do not paraphrase, "
    "summarize, or add ideas that were not spoken."
)


def get_transcription_enhancement_prompt(content: str) -> str:
    """Build the prompt that cleans up a raw voice transcription."""
    return f"""Clean up the following voice transcription.

{TRANSCRIPTION_CLEANUP_GUIDANCE}

Critical requirements:
- Preserve ALL facts, names, numbers, and the original meaning exactly.
- Do not add new information or remove any substantive point — only remove
  fillers and disfluencies.
- Return only the cleaned-up text, with no preamble or commentary.

Voice transcription to clean up:
{content}
"""
