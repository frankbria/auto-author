import bookClient from '@/lib/api/bookClient';
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
 * after this edit, and its success handler could clear this edit's backup.
 */
export async function flushChapterContent(
  edit: PendingChapterEdit,
  inFlightSave: Promise<unknown> | null = null
): Promise<void> {
  await inFlightSave?.catch(() => {});
  try {
    await bookClient.saveChapterContent(edit.bookId, edit.chapterId, edit.content, true, {
      keepalive: true,
    });
    localStorage.removeItem(chapterBackupKey(edit.bookId, edit.chapterId));
  } catch (err) {
    console.error('Failed to save chapter content on leaving it:', err);
    backupChapterContent(edit, err);
  }
}
