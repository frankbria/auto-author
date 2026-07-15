/**
 * Book-summary readiness thresholds — the single source of truth for the client.
 *
 * These MIRROR the backend TOC-readiness gate and must not drift from it:
 *   - backend/app/api/endpoints/books.py    (deterministic fallback, no AI analysis)
 *   - backend/app/services/ai_service.py    (AI-analysis path)
 * both of which compute `meets_minimum_requirements` as
 *   `word_count >= 30 and char_count >= 150`
 *
 * The TOC wizard gates on `meets_minimum_requirements` alone, so any client gate
 * weaker than this lets the user submit a summary that the wizard then bounces to
 * the NOT_READY screen — the dead-end fixed in issue #218.
 */
export const SUMMARY_MIN_WORDS = 30;
export const SUMMARY_MIN_CHARACTERS = 150;
export const SUMMARY_MAX_CHARACTERS = 2000;

const OFFENSIVE_REGEX = /\b(fuck|shit|bitch|asshole|bastard|dick|cunt|nigger|faggot|slut|whore)\b/i;
// Cyrillic, Arabic, CJK, Japanese, Korean
const NON_ENGLISH_REGEX = /[Ѐ-ӿ؀-ۿ一-鿿぀-ヿ가-힯]/;

/**
 * Python's `str.split()` whitespace set (every char where `str.isspace()` is true).
 *
 * Spelled out because JS `/\s/` is NOT the same set, and both divergences move the
 * word count away from the backend's `len(summary.split())`:
 *   - Python-only: \x1c-\x1f, \x85 — JS would not split, under-counting words and
 *     falsely rejecting a summary the backend accepts.
 *   - JS-only: ﻿ (BOM/ZWNBSP, common in pasted text) — JS would split, over-counting
 *     words and accepting a summary the backend rejects, recreating the #218 dead-end.
 */
const PY_WHITESPACE =
  '\\t\\n\\v\\f\\r\\x1c-\\x1f \\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000';
const PY_SPLIT_RE = new RegExp(`[${PY_WHITESPACE}]+`);
const PY_TRIM_RE = new RegExp(`^[${PY_WHITESPACE}]+|[${PY_WHITESPACE}]+$`, 'g');

/**
 * Word count matching Python's `str.split()` — splits on runs of whitespace and ignores
 * leading/trailing whitespace. The backend counts with `len(summary.split())`; counting
 * differently here would reintroduce the client/server disagreement at the boundary.
 */
export function countSummaryWords(text: string): number {
  const trimmed = text.replace(PY_TRIM_RE, '');
  if (!trimmed) return 0;
  return trimmed.split(PY_SPLIT_RE).length;
}

/**
 * Character count matching Python's `len(summary)` — i.e. Unicode code points.
 *
 * JS `String.length` counts UTF-16 code units, so every non-BMP character (emoji,
 * rarer CJK) counts twice: a mostly-emoji summary reads as 200 chars here but 100
 * to the backend, passing the client gate and then failing the real one — the #218
 * dead-end again. Untrimmed, matching `len(summary)`.
 */
export function countSummaryCharacters(text: string): number {
  return Array.from(text).length;
}

/**
 * Returns a user-facing error for a summary, or '' when it is ready for TOC generation.
 */
export function getSummaryReadinessError(text: string): string {
  if (!text.trim()) return 'Please provide a summary of your book.';

  const words = countSummaryWords(text);
  if (words < SUMMARY_MIN_WORDS) {
    return `Summary must be at least ${SUMMARY_MIN_WORDS} words (currently ${words}).`;
  }
  const characters = countSummaryCharacters(text);
  if (characters < SUMMARY_MIN_CHARACTERS) {
    return `Summary must be at least ${SUMMARY_MIN_CHARACTERS} characters (currently ${characters}).`;
  }
  if (characters > SUMMARY_MAX_CHARACTERS) {
    return `Summary must be at most ${SUMMARY_MAX_CHARACTERS} characters.`;
  }
  if (OFFENSIVE_REGEX.test(text)) return 'Summary contains inappropriate language.';
  if (NON_ENGLISH_REGEX.test(text)) return 'Please write your summary in English.';
  return '';
}
