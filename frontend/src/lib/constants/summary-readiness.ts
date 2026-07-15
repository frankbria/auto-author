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
 * Word count matching Python's `str.split()` — splits on runs of any whitespace and
 * ignores leading/trailing whitespace. The backend counts with `len(summary.split())`;
 * counting differently here would reintroduce client/server disagreement at the boundary.
 */
export function countSummaryWords(text: string): number {
  const trimmed = text.trim();
  if (!trimmed) return 0;
  return trimmed.split(/\s+/).length;
}

/**
 * Returns a user-facing error for a summary, or '' when it is ready for TOC generation.
 * Character count is untrimmed to match the backend's `len(summary)`.
 */
export function getSummaryReadinessError(text: string): string {
  if (!text.trim()) return 'Please provide a summary of your book.';

  const words = countSummaryWords(text);
  if (words < SUMMARY_MIN_WORDS) {
    return `Summary must be at least ${SUMMARY_MIN_WORDS} words (currently ${words}).`;
  }
  if (text.length < SUMMARY_MIN_CHARACTERS) {
    return `Summary must be at least ${SUMMARY_MIN_CHARACTERS} characters (currently ${text.length}).`;
  }
  if (text.length > SUMMARY_MAX_CHARACTERS) {
    return `Summary must be at most ${SUMMARY_MAX_CHARACTERS} characters.`;
  }
  if (OFFENSIVE_REGEX.test(text)) return 'Summary contains inappropriate language.';
  if (NON_ENGLISH_REGEX.test(text)) return 'Please write your summary in English.';
  return '';
}
