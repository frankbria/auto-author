import bookClient, { type ChapterSaveConflict } from '@/lib/api/bookClient';
import {
  ChapterBackup,
  setValidatedItem,
  validateChapterBackup,
} from '@/lib/storage/dataValidator';

export const chapterBackupKey = (bookId: string, chapterId: string) =>
  `chapter-backup-${bookId}-${chapterId}`;

/** An edit not yet confirmed saved, tagged with the chapter it was typed into. */
export interface PendingChapterEdit {
  bookId: string;
  chapterId: string;
  content: string;
}

/**
 * The server copy of each chapter this editor last saw (#760): its save token,
 * echoed verbatim as expected_last_modified, and its text. Keyed by
 * chapterBackupKey. A chapter with no entry saves unconditionally.
 */
export type SeenChapters = Map<string, { lastModified?: string | null; content: string }>;

export const isChapterConflict = (err: unknown): err is ChapterSaveConflict =>
  (err as { statusCode?: unknown } | null)?.statusCode === 409;

/**
 * Saves an edit on the token last seen for its chapter, and records the token
 * the save returns before resolving, so a save queued behind this one sends it.
 */
export async function saveChapterEdit(
  edit: PendingChapterEdit,
  seen: SeenChapters,
  options: { keepalive?: boolean } = {}
) {
  const key = chapterBackupKey(edit.bookId, edit.chapterId);
  const known = seen.get(key);
  const send = (expectedLastModified: string | null | undefined) =>
    bookClient.saveChapterContent(edit.bookId, edit.chapterId, edit.content, true, {
      ...options,
      expectedLastModified,
    });
  let result;
  try {
    result = await send(known?.lastModified);
  } catch (err) {
    // A status change moves the token without touching the text. If the text is
    // still the copy this editor last saw, no one's words are at stake: resend
    // once on the new token. Any other conflict is the writer's call.
    if (!known || !isChapterConflict(err) || err.currentContent !== known.content) throw err;
    result = await send(err.currentLastModified);
  }
  seen.set(key, { lastModified: result.last_modified, content: edit.content });
  return result;
}

/** Keeps content that failed to save in localStorage. Returns whether it was stored. */
export function backupChapterContent(
  { bookId, chapterId, content }: PendingChapterEdit,
  err: unknown
): boolean {
  const backup: ChapterBackup = {
    content,
    timestamp: Date.now(),
    error: err instanceof Error ? err.message : 'Unknown error',
  };
  return setValidatedItem(chapterBackupKey(bookId, chapterId), backup, validateChapterBackup);
}

/**
 * Saves an edit the editor is leaving behind (unmount or chapter change, #757).
 * Nothing is left on screen to report a failure to, so a failed save becomes the
 * backup the editor offers to restore next time that chapter opens.
 *
 * A save still in flight goes first. Otherwise its older content could land
 * after this edit, and its success handler could clear this edit's backup. It
 * also moves the chapter's token, which this save then sends.
 */
export async function flushChapterContent(
  edit: PendingChapterEdit,
  seen: SeenChapters,
  inFlightSave: Promise<unknown> | null = null
): Promise<void> {
  await inFlightSave?.catch(() => {});
  try {
    // A conflict lands in the backup too: leaving never overwrites the other copy.
    await saveChapterEdit(edit, seen, { keepalive: true });
    localStorage.removeItem(chapterBackupKey(edit.bookId, edit.chapterId));
  } catch (err) {
    console.error('Failed to save chapter content on leaving it:', err);
    backupChapterContent(edit, err);
  }
}
