import { logger } from '@/lib/logger';
import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { useEditor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import CharacterCount from '@tiptap/extension-character-count';
import bookClient, { type ChapterSaveConflict } from '@/lib/api/bookClient';
import { usePerformanceTracking } from '@/hooks/usePerformanceTracking';
import { useUserPreferences } from '@/hooks/useUserPreferences';
import { AUTO_SAVE_DEFAULT_SECONDS, isValidAutoSaveInterval } from '@/lib/constants/auto-save';
import {
  validateChapterBackup,
  getValidatedItem,
  cleanupStorage,
  ChapterBackup,
} from '@/lib/storage/dataValidator';
import {
  backupChapterContent,
  chapterBackupKey,
  chapterDroppedKey,
  flushChapterContent,
  isChapterConflict,
  keepDroppedChapterText,
  reportSaveFailure,
  saveSucceeded,
  PendingChapterEdit,
  saveChapterEdit,
  SeenChapters,
  readHasBackup,
} from './chapterContentSave';

// Storage raises no event for writes in the same tab: the writers here re-render.
export const subscribeToNothing = () => () => {};

interface ChapterContentOptions {
  bookId: string;
  chapterId: string;
  initialContent: string;
  onSave?: (content: string) => void;
  onContentChange?: (content: string) => void;
}

/**
 * The chapter text's lifecycle for ChapterEditor: the TipTap editor, load and
 * Retry, autosave with backoff, manual save, flush on leaving, backup restore
 * and the save-conflict choice.
 */
export function useChapterContent({
  bookId,
  chapterId,
  initialContent,
  onSave,
  onContentChange,
}: ChapterContentOptions) {
  const { trackOperation } = usePerformanceTracking();
  // Auto-save frequency honors the user's stored preference (#64); anything
  // missing/out-of-range falls back to the shipped 3s default.
  const userPreferences = useUserPreferences();
  const preferredAutoSaveInterval = userPreferences?.auto_save_interval;
  const autoSaveDelayMs =
    (isValidAutoSaveInterval(preferredAutoSaveInterval)
      ? preferredAutoSaveInterval
      : AUTO_SAVE_DEFAULT_SECONDS) * 1000;
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // A chapter that failed to load is read-only and never saved: the editor does
  // not hold its text, so any save would overwrite it (#757). Retry bumps the attempt.
  const [loadFailed, setLoadFailed] = useState(false);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [loaded, setLoaded] = useState<{ key: string; content: string; lastModified?: string | null } | null>(null);
  // A Questions-tab draft used while the load had failed waits for Retry's text (#875).
  const draftWhileFailedRef = useRef<{ key: string; html: string } | null>(null);
  // The latest edit the server does not have yet, flushed if the editor goes away.
  const unsavedRef = useRef<PendingChapterEdit | null>(null);
  // The save request in flight, which a flush waits for so it cannot land last.
  const inFlightSaveRef = useRef<Promise<unknown> | null>(null);
  // Save tokens (#760), from GET content and each save, never chapter metadata.
  const seenRef = useRef<SeenChapters>(new Map());
  // A save the server rejected because the chapter changed elsewhere. Saving
  // stops until the writer reloads the server copy or overwrites it.
  const [conflict, setConflict] = useState<ChapterSaveConflict | null>(null);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [autoSavePending, setAutoSavePending] = useState(false);
  // Consecutive failed autosaves: each one doubles the wait before the next try,
  // up to 30s, so an outage is not a request every few seconds (#855). Any save
  // that works resets it, and so does a change of chapter.
  const autoSaveFailuresRef = useRef(0);
  const [lastAutoSavedContent, setLastAutoSavedContent] = useState(initialContent);
  const backupKey = chapterBackupKey(bookId, chapterId);
  const droppedKey = chapterDroppedKey(bookId, chapterId);
  // The backup Restore offers: a failed save's first, then text dropped on Reload (#760).
  const restoreKey = useSyncExternalStore(
    subscribeToNothing,
    () => (readHasBackup(backupKey) ? backupKey : readHasBackup(droppedKey) ? droppedKey : null),
    () => null
  );
  const hasBackup = restoreKey !== null;
  // The chapter on screen, for saves that come back after the editor moved on.
  const shownChapterRef = useRef(backupKey);
  useEffect(() => {
    shownChapterRef.current = backupKey;
  }, [backupKey]);
  // Storage raises no event in the tab that wrote it; bumping this re-reads it.
  // The initialiser runs once, as the editor mounts and before a backup is looked
  // for: backups past their week are removed, here and for every other chapter (#831).
  const [, setBackupWrites] = useState(() => {
    cleanupStorage();
    return 0;
  });
  const noteBackupWrite = () => setBackupWrites((n) => n + 1);
  // A backup older than the saved chapter, which the writer has asked to restore.
  // It is a question about one backup: shown only while that backup is the one
  // on offer, so it cannot be answered for another chapter's (#831).
  const [askedAbout, setOlderBackup] = useState<{ key: string; backedUp: number; saved: number } | null>(null);
  const olderBackup = askedAbout?.key === restoreKey ? askedAbout : null;
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const editor = useEditor({
    extensions: [
      // trailingNode is new in StarterKit v3 and ON by default: it keeps an
      // empty paragraph at the end of the document so there is always somewhere
      // to click below the last block. Disabled deliberately — the editor's HTML
      // is what gets persisted and exported, so leaving it on would append a
      // <p></p> to every chapter a user saves. That is a content change, and a
      // dependency upgrade is the wrong place to make one; enabling it is a
      // product decision with a migration behind it (#385).
      StarterKit.configure({ trailingNode: false }),
      Placeholder.configure({
        placeholder: 'Start writing your chapter content...',
      }),
      CharacterCount,
    ],
    content: initialContent,
    onUpdate: ({ editor }) => {
      const html = editor.getHTML();
      if (onContentChange) {
        onContentChange(html);
      }
      if (loadFailed) return;
      // Tagged with its chapter now, so a flush can never send it to the next one.
      unsavedRef.current = html !== lastAutoSavedContent ? { bookId, chapterId, content: html } : null;
      // While saves are failing, each edit refreshes the backup: the next try may be
      // up to 30s away, and a crash before it would lose what was typed since (#855).
      if (autoSaveFailuresRef.current > 0 && unsavedRef.current) {
        backupChapterContent(unsavedRef.current, new Error('Not saved yet: autosave is retrying'));
      }
      if (html !== lastAutoSavedContent) {
        setAutoSavePending(true);
        setHasUnsavedChanges(true);
      }
    },
    editorProps: {
      attributes: {
        class: 'focus:outline-hidden text-black',
      },
    },
    // Set this to false to avoid SSR hydration issues
    immediatelyRender: false,
  });

  // Warn user before leaving page with unsaved changes
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges && autoSavePending) {
        e.preventDefault();
        e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
        return e.returnValue;
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasUnsavedChanges, autoSavePending]);

  // Load chapter content if no initial content provided. The load waits on the
  // chapter, not the editor: the editor is null on the first render, and waiting
  // on it fetched every chapter twice and dropped the first answer (#758).
  useEffect(() => {
    // A response for a chapter that is no longer this effect's chapter must not
    // land: it would become the content the next save writes under the new id (#756).
    let ignore = false;
    const loadChapterContent = async () => {
      setIsLoading(true);
      setError(null);
      setLoaded(null);
      // A conflict belongs to the chapter it was raised on.
      setConflict(null);
      try {
        const contentData = await bookClient.getChapterContent(bookId, chapterId);
        if (ignore) return;
        setLoaded({
          key: chapterBackupKey(bookId, chapterId),
          content: contentData.content || '',
          lastModified: contentData.last_modified,
        });
        setLoadFailed(false);
      } catch (err) {
        // The superseding load owns the spinner.
        if (ignore) return;
        console.error('Failed to load chapter content:', err);
        setError('Failed to load chapter content');
        setLoadFailed(true);
        setIsLoading(false);
      }
    };
    if (!initialContent && bookId && chapterId) {
      loadChapterContent();
    }
    return () => {
      ignore = true;
    };
  }, [bookId, chapterId, initialContent, loadAttempt]);

  // The loaded text goes into the editor once both exist, and only then does the
  // spinner give way to it.
  useEffect(() => {
    if (!editor || loaded?.key !== backupKey) return;
    // Loading is not an edit: no update event, so nothing is marked unsaved (#831).
    editor.commands.setContent(loaded.content, { emitUpdate: false });
    seenRef.current.set(loaded.key, { lastModified: loaded.lastModified, content: loaded.content });
    unsavedRef.current = null;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- syncing the imperative editor, as below
    setLastAutoSavedContent(loaded.content);
    setIsLoading(false);
    const draft = draftWhileFailedRef.current;
    draftWhileFailedRef.current = null;
    if (draft?.key !== loaded.key) return;
    // Appended, not inserted at the cursor: setContent left none the writer chose.
    editor.commands.insertContentAt(editor.state.doc.content.size, draft.html);
    unsavedRef.current = { bookId, chapterId, content: editor.getHTML() };
    setAutoSavePending(true);
    setHasUnsavedChanges(true);
  }, [backupKey, bookId, chapterId, editor, loaded]);

  // A chapter that failed to load is read-only (#757).
  useEffect(() => {
    editor?.setEditable(!loadFailed, false);
  }, [editor, loadFailed]);

  // React does not unmount on unload; pagehide is the last event a closing page
  // reliably gets, so an edit inside the debounce goes out with keepalive (#875).
  useEffect(() => {
    const flushOnPageHide = () => {
      const edit = unsavedRef.current;
      unsavedRef.current = null;
      if (edit) void flushChapterContent(edit, seenRef.current, inFlightSaveRef.current);
    };
    window.addEventListener('pagehide', flushOnPageHide);
    return () => window.removeEventListener('pagehide', flushOnPageHide);
  }, []);

  // Leaving a chapter, by unmount (TabContent keys the editor per chapter) or a
  // caller swapping chapterId, must not drop an edit still inside the autosave
  // debounce or typed during an in-flight save (#757).
  useEffect(
    () => () => {
      const edit = unsavedRef.current;
      unsavedRef.current = null;
      autoSaveFailuresRef.current = 0;
      if (edit) void flushChapterContent(edit, seenRef.current, inFlightSaveRef.current);
    },
    [bookId, chapterId]
  );

  // Update content if initialContent changes
  useEffect(() => {
    if (editor && initialContent && editor.getHTML() !== initialContent) {
      editor.commands.setContent(initialContent, { emitUpdate: false });
      unsavedRef.current = null;
      // Synchronising an external system (#584): the TipTap editor is imperative,
      // and whether it needs new content is only knowable by reading it. The saved
      // marker must move with the content pushed into it, or the next update reads
      // as an unsaved change; deriving it during render would change which content
      // counts as saved.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLastAutoSavedContent(initialContent);
    }
  }, [initialContent, editor]);

  // A save clears the pending state only if the editor still holds what was
  // sent. An edit typed while the request was in flight stays pending, and the
  // autosave effect re-arms for it because lastAutoSavedContent changed (#757).
  const markSaved = (content: string) => {
    saveSucceeded();
    autoSaveFailuresRef.current = 0;
    setLastAutoSavedContent(content);
    if (editor?.getHTML() !== content) return;
    unsavedRef.current = null;
    setAutoSavePending(false);
    setHasUnsavedChanges(false);
  };

  // The local text stays in the editor and in a backup; nothing else saves
  // until the writer picks a version, and neither choice is ever made for them.
  const handleConflict = (content: string, err: ChapterSaveConflict) => {
    const backedUp = backupChapterContent({ bookId, chapterId, content }, err);
    noteBackupWrite();
    // A save that comes back after the editor moved to another chapter is
    // backed up under its own chapter; the choice belongs to that chapter.
    if (shownChapterRef.current !== chapterBackupKey(bookId, chapterId)) return;
    setConflict(err);
    setError(
      backedUp
        ? 'This chapter was changed somewhere else since you opened it. Your text is still here and backed up on this device. Which version do you want to keep?'
        : 'This chapter was changed somewhere else since you opened it. Your text is still here, but it could not be backed up on this device. Copy anything you want to keep before choosing.'
    );
  };

  const resolveConflict = (keep: 'mine' | 'theirs') => {
    if (!conflict || !editor) return;
    // The dropped text, including edits made since the conflict, stays
    // restorable. If it cannot be stored, it stays in the editor instead.
    if (keep === 'theirs' && !keepDroppedChapterText({ bookId, chapterId, content: editor.getHTML() })) {
      setError(
        'Could not back up your text on this device, so it was not replaced. Copy anything you want to keep, then choose again.'
      );
      return;
    }
    seenRef.current.set(backupKey, {
      lastModified: conflict.currentLastModified,
      content: conflict.currentContent,
    });
    setConflict(null);
    setError(null);
    if (keep === 'mine') {
      void handleSave(false);
      return;
    }
    // The conflict-time backup is older text the dropped copy already holds.
    localStorage.removeItem(backupKey);
    noteBackupWrite();
    editor.commands.setContent(conflict.currentContent);
    unsavedRef.current = null;
    setLastAutoSavedContent(conflict.currentContent);
    setAutoSavePending(false);
    setHasUnsavedChanges(false);
  };

  // Auto-save functionality with localStorage backup
  useEffect(() => {
    if (!autoSavePending || !editor || isSaving || loadFailed || conflict) return;

    const delay = Math.max(autoSaveDelayMs, Math.min(autoSaveDelayMs * 2 ** autoSaveFailuresRef.current, 30_000));
    const timer = setTimeout(async () => {
      const content = editor.getHTML();
      if (content === lastAutoSavedContent) {
        // Nothing to save, but the pending flag must drop: typing only re-arms
        // this timer by flipping it false -> true. Loading a chapter raises an
        // update that sets it with no edit made, so leaving it set here killed
        // autosave for anyone who read for a few seconds before typing (#756).
        setAutoSavePending(false);
        setHasUnsavedChanges(false);
        return;
      }

      setIsSaving(true);
      setError(null);
      try {
        await (inFlightSaveRef.current = trackOperation('auto-save', async () => {
          return await saveChapterEdit({ bookId, chapterId, content }, seenRef.current);
        }, { bookId, chapterId, contentLength: content.length }));
        setLastSaved(new Date());
        markSaved(content);

        // Clear backup after successful save
        localStorage.removeItem(chapterBackupKey(bookId, chapterId));
        noteBackupWrite();
      } catch (err) {
        console.error('Failed to auto-save chapter:', err);

        if (isChapterConflict(err)) {
          handleConflict(content, err);
          return;
        }
        reportSaveFailure('auto-save', err);
        autoSaveFailuresRef.current += 1;
        if (backupChapterContent({ bookId, chapterId, content }, err)) {
          noteBackupWrite();
          setError('Failed to auto-save. Content backed up locally.');
        } else {
          setError('Failed to auto-save and backup chapter content');
        }
      } finally {
        setIsSaving(false);
      }
    }, delay);

    return () => clearTimeout(timer);
  }, [autoSavePending, autoSaveDelayMs, bookId, chapterId, conflict, editor, isSaving, lastAutoSavedContent, loadFailed]);

  const handleSave = async (isAutoSave: boolean = false) => {
    if (isSaving || !editor || loadFailed) return;

    const content = editor.getHTML();
    setIsSaving(true);
    setError(null);

    try {
      await (inFlightSaveRef.current = trackOperation('manual-save', async () => {
        return await saveChapterEdit({ bookId, chapterId, content }, seenRef.current);
      }, { bookId, chapterId, contentLength: content.length }));
      setLastSaved(new Date());
      markSaved(content);

      // Clear backup after successful save
      localStorage.removeItem(chapterBackupKey(bookId, chapterId));
      noteBackupWrite();

      if (onSave) {
        onSave(content);
      }
      if (!isAutoSave) {
        logger.debug('Chapter content saved successfully');
      }
    } catch (err) {
      console.error('Failed to save chapter:', err);
      if (isChapterConflict(err)) {
        handleConflict(content, err);
        return;
      }
      setError('Failed to save chapter content');
      reportSaveFailure('manual-save', err);

      // Backup to localStorage on manual save failure too
      backupChapterContent({ bookId, chapterId, content }, err);
      noteBackupWrite();
    } finally {
      setIsSaving(false);
    }
  };

  // A backup is restored without a question when it is the newer text, which is
  // what a failed save leaves. One older than the saved chapter would replace
  // newer writing, so the writer is told which is which and asked (#831).
  const handleRecoverBackup = (confirmed = false) => {
    if (!restoreKey) return;
    const backup = getValidatedItem<ChapterBackup>(restoreKey, validateChapterBackup);
    if (backup && editor) {
      const savedAt = Date.parse(seenRef.current.get(backupKey)?.lastModified ?? '');
      if (!confirmed && backup.timestamp < savedAt) {
        setOlderBackup({ key: restoreKey, backedUp: backup.timestamp, saved: savedAt });
        return;
      }
      setOlderBackup(null);
      try {
        editor.commands.setContent(backup.content);
        setAutoSavePending(true); // Trigger auto-save of recovered content
        setHasUnsavedChanges(true);
        noteBackupWrite();
        localStorage.removeItem(restoreKey);
      } catch (err) {
        console.error('Failed to recover backup:', err);
        reportSaveFailure('restore', err);
        setError('Failed to recover backed up content');
      }
    }
  };

  const handleDismissBackup = () => {
    if (restoreKey) localStorage.removeItem(restoreKey);
    setOlderBackup(null);
    noteBackupWrite();
  };

  const handleDraftGenerated = (draft: string) => {
    if (!editor) return;
    if (loadFailed) {
      const earlier = draftWhileFailedRef.current?.key === backupKey ? draftWhileFailedRef.current.html : '';
      draftWhileFailedRef.current = { key: backupKey, html: earlier + draft };
      return;
    }
    // Insert the draft at the current cursor position
    editor.chain().focus().insertContent(draft).run();
    // Trigger auto-save
    setAutoSavePending(true);
  };

  return {
    editor,
    isLoading,
    error,
    loadFailed,
    retryLoad: () => setLoadAttempt((n) => n + 1),
    conflict,
    resolveConflict,
    lastSaved,
    isSaving,
    handleSave,
    hasBackup,
    olderBackup,
    keepSavedText: () => setOlderBackup(null),
    handleRecoverBackup,
    handleDismissBackup,
    handleDraftGenerated,
    lastAutoSavedContent,
    setAutoSavePending,
    setHasUnsavedChanges,
  };
}
