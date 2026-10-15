/**
 * The browser storage that holds a user's writing, or their place in it (#855).
 *
 * Chapter backups, edits the server refused, summary drafts, open tabs and TOC
 * change markers sit in localStorage per book; the questions/editor toggle sits
 * in sessionStorage. The theme is the device's, and stays.
 */
export const LOCAL_PREFIXES = [
  'chapter-backup-',
  'chapter-dropped-',
  'book-summary-', // also book-summary-unsaved-
  'tabState_',
  'toc-updated-',
];
export const SESSION_PREFIXES = ['chapterQuestionsTab_'];

function clear(storage: Storage, prefixes: string[]): void {
  // Collected first: removing while indexing shifts the keys under the loop.
  const doomed = Object.keys(storage).filter((key) => prefixes.some((prefix) => key.startsWith(prefix)));
  doomed.forEach((key) => storage.removeItem(key));
}

/** Remove every copy of the user's writing this browser holds. */
export function clearLocalWriting(): void {
  try {
    clear(localStorage, LOCAL_PREFIXES);
    clear(sessionStorage, SESSION_PREFIXES);
  } catch {
    // Storage that cannot be read (blocked, private mode) holds nothing of ours.
  }
}
