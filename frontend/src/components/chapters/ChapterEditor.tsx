'use client';

import { useCallback, useRef, useState, useSyncExternalStore } from 'react';
import { useEditorState, EditorContent } from '@tiptap/react';
import './editor.css';

// Required types declaration to avoid TypeScript errors
declare module '@tiptap/react' {
  interface Commands<ReturnType> {
    toggleBold: () => ReturnType;
    toggleItalic: () => ReturnType;
    toggleUnderline: () => ReturnType;
    toggleStrike: () => ReturnType;
    toggleHeading: (attributes: { level: 1 | 2 | 3 | 4 | 5 | 6 }) => ReturnType;
    toggleBulletList: () => ReturnType;
    toggleOrderedList: () => ReturnType;
    toggleBlockquote: () => ReturnType;
    toggleCodeBlock: () => ReturnType;
    undo: () => ReturnType;
    redo: () => ReturnType;
    setHorizontalRule: () => ReturnType;
  }
}
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { HugeiconsIcon } from '@hugeicons/react';
import {
  CheckmarkCircle01Icon,
  AlertCircleIcon,
  Loading03Icon
} from '@hugeicons/core-free-icons';
import { EditorToolbar } from './EditorToolbar';
import { DraftGenerator } from './DraftGenerator';
import { StyleTransformer } from './StyleTransformer';
import { ContentEnhancer } from './ContentEnhancer';
import { VoiceEnhancer } from './VoiceEnhancer';
import QuestionContainer from './questions/QuestionContainer';
import { useRouter } from 'next/navigation';
import { subscribeToNothing, useChapterContent } from './useChapterContent';

type ChapterView = 'questions' | 'editor';

function readSavedView(key: string): ChapterView {
  try {
    return sessionStorage.getItem(key) === 'questions' ? 'questions' : 'editor';
  } catch {
    // Storage can be unavailable (privacy modes); the writing view is the default.
    return 'editor';
  }
}

interface ChapterEditorProps {
  bookId: string;
  chapterId: string;
  chapterTitle?: string;
  initialContent?: string;
  onSave?: (content: string) => void;
  onContentChange?: (content: string) => void;
}

export function ChapterEditor({
  bookId,
  chapterId,
  chapterTitle = 'Untitled Chapter',
  initialContent = '',
  onSave,
  onContentChange
}: ChapterEditorProps) {
  const {
    editor,
    isLoading,
    error,
    loadFailed,
    retryLoad,
    conflict,
    resolveConflict,
    lastSaved,
    isSaving,
    handleSave,
    hasBackup,
    olderBackup,
    keepSavedText,
    handleRecoverBackup,
    handleDismissBackup,
    handleDraftGenerated,
    lastAutoSavedContent,
    setAutoSavePending,
    setHasUnsavedChanges,
  } = useChapterContent({ bookId, chapterId, initialContent, onSave, onContentChange });
  // Snapshot of content before a style transform, for single-level revert (#58).
  const [preTransformContent, setPreTransformContent] = useState<string | null>(null);
  // Snapshot + target range before a content enhancement, for single-level revert (#57).
  const [preEnhanceContent, setPreEnhanceContent] = useState<string | null>(null);
  const enhanceRangeRef = useRef<{ from: number; to: number } | null>(null);
  // Toggle between writing the chapter and answering its interview questions (#105/#54/#110).
  // Radix Tabs values: 'editor' = writing view, 'questions' = interview questions.
  // Default is the writing view (matches shipped UX + editor-focused unit tests); the
  // last choice is remembered per chapter in sessionStorage.
  const viewStorageKey = `chapterQuestionsTab_${bookId}_${chapterId}`;
  // The saved per-chapter choice is read, not copied into state by an effect
  // (#584). The server snapshot is the writing view, so hydration still matches,
  // and a new key re-reads storage if a caller reuses this editor for another
  // chapter without remounting it (TabContent keys it by chapter since #756). A
  // choice made here is tagged with its chapter for the same reason, and wins
  // even if persisting it failed.
  const savedView = useSyncExternalStore(
    subscribeToNothing,
    () => readSavedView(viewStorageKey),
    () => 'editor' as const
  );
  const [chosenView, setChosenView] = useState<{ key: string; view: ChapterView } | null>(null);
  const view = chosenView?.key === viewStorageKey ? chosenView.view : savedView;

  const handleViewChange = useCallback(
    (next: string) => {
      if (next !== 'questions' && next !== 'editor') return;
      setChosenView({ key: viewStorageKey, view: next });
      if (typeof window !== 'undefined') {
        try {
          sessionStorage.setItem(viewStorageKey, next);
        } catch {
          // Persisting the tab choice is best-effort.
        }
      }
    },
    [viewStorageKey]
  );

  // Keyboard access to the tabs is Radix's native arrow-key roving (WCAG tab
  // pattern) plus clicking. Ctrl+digit is intentionally NOT bound here — it is
  // owned by the ChapterTabs chapter quick-switch (Ctrl+1..9), so binding it to
  // the view toggle would hijack chapter navigation.

  const router = useRouter();

  // useEditor does not re-render on transactions, so a count read straight off
  // the editor in render froze at the first keystroke (#855).
  const characters = useEditorState({
    editor,
    selector: ({ editor: current }) => current?.storage.characterCount.characters() ?? 0,
  });

  // Apply a style transform: snapshot the current content, then replace it (#58).
  const handleApplyStyleTransform = (transformed: string) => {
    if (editor) {
      setPreTransformContent(editor.getHTML());
      editor.commands.setContent(transformed);
      setAutoSavePending(true);
    }
  };

  // Revert the last style transform (single-level undo).
  const handleRevertStyleTransform = () => {
    if (editor && preTransformContent !== null) {
      editor.commands.setContent(preTransformContent);
      // Only mark a pending save if the restored content differs from what's
      // saved. If the transform was reverted before its autosave fired, the
      // chapter already matches storage — clear the dirty flags so the user
      // isn't warned about unsaved changes for content that was never saved.
      if (preTransformContent !== lastAutoSavedContent) {
        setAutoSavePending(true);
        setHasUnsavedChanges(true);
      } else {
        setAutoSavePending(false);
        setHasUnsavedChanges(false);
      }
      setPreTransformContent(null);
    }
  };

  // Content enhancement (#57): enhance the selection if there is one, else the
  // whole chapter. Capture the target range so apply can replace exactly that.
  const getEnhanceContent = () => {
    if (!editor) return '';
    const { from, to, empty } = editor.state.selection;
    if (!empty) {
      enhanceRangeRef.current = { from, to };
      return editor.state.doc.textBetween(from, to, '\n');
    }
    enhanceRangeRef.current = null;
    return editor.getHTML();
  };

  const handleApplyEnhancement = (enhanced: string) => {
    if (!editor) return;
    setPreEnhanceContent(editor.getHTML());
    const range = enhanceRangeRef.current;
    if (range) {
      editor.chain().focus().insertContentAt(range, enhanced).run();
    } else {
      editor.commands.setContent(enhanced);
    }
    setAutoSavePending(true);
  };

  // Revert the last enhancement (single-level undo), mirroring style revert.
  const handleRevertEnhancement = () => {
    if (editor && preEnhanceContent !== null) {
      editor.commands.setContent(preEnhanceContent);
      if (preEnhanceContent !== lastAutoSavedContent) {
        setAutoSavePending(true);
        setHasUnsavedChanges(true);
      } else {
        setAutoSavePending(false);
        setHasUnsavedChanges(false);
      }
      setPreEnhanceContent(null);
    }
  };


  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <HugeiconsIcon icon={Loading03Icon} size={32} className="mx-auto animate-spin text-blue-600 dark:text-blue-400" />
          <p className="mt-2 text-sm text-muted-foreground">Loading chapter content...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Restoring or AI-editing a chapter that failed to load would put text in
          an editor that can never save it (#757), so those controls wait for Retry. */}
      {hasBackup && !loadFailed && !conflict && (
        <div className="bg-yellow-500/10 border border-yellow-500/20 text-yellow-700 dark:text-yellow-400 px-4 py-2 text-sm flex items-center justify-between">
          {olderBackup ? (
            <>
              <span role="alert">
                This backup is from {new Date(olderBackup.backedUp).toLocaleString()}, older than the saved chapter (
                {new Date(olderBackup.saved).toLocaleString()}). Restoring it replaces the newer text.
              </span>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => handleRecoverBackup(true)} className="text-xs">
                  Restore the older backup
                </Button>
                <Button size="sm" variant="ghost" onClick={keepSavedText} className="text-xs">
                  Keep the saved text
                </Button>
              </div>
            </>
          ) : (
            <>
              <span>A local backup of your content is available. Would you like to restore it?</span>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleRecoverBackup()}
                  className="text-xs"
                >
                  Restore Backup
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={handleDismissBackup}
                  className="text-xs"
                >
                  Dismiss
                </Button>
              </div>
            </>
          )}
        </div>
      )}
      {/* role="alert": a failed autosave means the user's writing may exist only
          in the localStorage backup. That is worth interrupting for, and it was
          previously announced not at all (#349). */}
      {error && (
        <div
          role="alert"
          className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-2 text-sm flex items-center justify-between gap-2"
        >
          <span>{error}</span>
          {loadFailed && (
            <Button size="sm" variant="outline" onClick={retryLoad}>
              Retry
            </Button>
          )}
          {conflict && (
            <div className="flex gap-2 shrink-0">
              <Button size="sm" variant="outline" onClick={() => resolveConflict('theirs')}>
                Reload their version
              </Button>
              <Button size="sm" variant="outline" onClick={() => resolveConflict('mine')}>
                Overwrite with mine
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Interview Questions / Chapter Editor tabs (#105/#54/#110) */}
      <Tabs
        value={view}
        onValueChange={handleViewChange}
        className="flex-1 flex flex-col min-h-0"
      >
        <TabsList
          className="w-full justify-start rounded-none border-b border-border bg-muted/20 h-auto px-2 py-1"
          aria-label="Chapter editor view"
        >
          <TabsTrigger
            value="questions"
            data-testid="chapter-tab"
            data-tab="questions"
            className="text-xs"
          >
            Interview Questions
          </TabsTrigger>
          <TabsTrigger
            value="editor"
            data-testid="chapter-tab"
            data-tab="draft"
            className="text-xs"
          >
            Chapter Editor
          </TabsTrigger>
        </TabsList>

        <TabsContent value="questions" className="flex-1 overflow-auto mt-0">
          <QuestionContainer
            bookId={bookId}
            chapterId={chapterId}
            chapterTitle={chapterTitle}
            onDraftGenerated={handleDraftGenerated}
            onSwitchToEditor={() => handleViewChange('editor')}
          />
        </TabsContent>

        {/* No display utility (flex/grid) on TabsContent — it would override
            Radix's `hidden` attribute and leave the inactive panel visible. */}
        <TabsContent value="editor" className="flex-1 min-h-0 mt-0">
        <div className="h-full flex flex-col min-h-0">
      {/* Editor Toolbar */}
      {!loadFailed && (
      <div className="border-b border-border p-1 bg-muted/30 flex flex-wrap gap-1 items-center justify-between">
        {/* Formatting controls live in a memoized child so a keystroke does
            not reconcile fourteen buttons and their icons (#347). It also
            carries the role="toolbar" / aria-label / aria-pressed semantics
            from #50, which had been sitting in an unreferenced component. */}
        <EditorToolbar editor={editor} />

        {/* AI Draft Generator */}
        <DraftGenerator
          bookId={bookId}
          chapterId={chapterId}
          chapterTitle={chapterTitle}
          onDraftGenerated={handleDraftGenerated}
        />

        {/* AI Style Transformer (#58) */}
        <StyleTransformer
          bookId={bookId}
          chapterId={chapterId}
          getCurrentContent={() => editor?.getHTML() ?? ''}
          onApply={handleApplyStyleTransform}
        />

        {preTransformContent !== null && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRevertStyleTransform}
            title="Revert the last style transformation"
            type="button"
          >
            Revert style
          </Button>
        )}

        {/* AI Content Enhancer (#57) */}
        <ContentEnhancer
          bookId={bookId}
          chapterId={chapterId}
          getCurrentContent={getEnhanceContent}
          onApply={handleApplyEnhancement}
        />

        {/* AI Voice/Dictation cleanup (#56) — shares the enhancement snapshot/revert. */}
        <VoiceEnhancer
          bookId={bookId}
          chapterId={chapterId}
          getCurrentContent={getEnhanceContent}
          onApply={handleApplyEnhancement}
        />

        {preEnhanceContent !== null && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRevertEnhancement}
            title="Revert the last enhancement"
            type="button"
          >
            Revert enhancement
          </Button>
        )}
      </div>
      )}

      {/* Editor Content */}
      <div className="flex-1 p-4 bg-white overflow-auto">
        <EditorContent
          editor={editor}
          className="w-full h-full min-h-[500px] tiptap-editor text-black"
        />
      </div>

      {/* Editor Footer */}
      <div className="border-t border-border p-4 flex justify-between items-center bg-muted/20">
        <div className="flex items-center gap-4">
          <span className="text-sm text-foreground">
            {characters ?? 0} characters
          </span>
          {/* Autosave result is otherwise a purely visual cue. Polite so it
              never interrupts typing — which is precisely what the user is
              doing when the 3s autosave fires (#349). */}
          <div
            role="status"
            aria-live="polite"
            className="flex items-center gap-2"
            data-testid="save-status-indicator"
            data-save-status={
              isSaving ? 'saving' : error ? 'error' : lastSaved ? 'saved' : 'idle'
            }
          >
            {isSaving && (
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <HugeiconsIcon icon={Loading03Icon} size={12} className="animate-spin" />
                Saving...
              </span>
            )}
            {/* `error` is checked before `lastSaved` because lastSaved survives
                from the previous successful save: without this the region
                announced "Saved 14:32" during a failure, which is both a stale
                success and the opposite of what happened. */}
            {!isSaving && error && (
              <span className="text-xs text-destructive flex items-center gap-1">
                <HugeiconsIcon icon={AlertCircleIcon} size={12} />
                Not saved
              </span>
            )}
            {!isSaving && !error && lastSaved && (
              <span className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
                <HugeiconsIcon icon={CheckmarkCircle01Icon} size={12} />
                Saved {lastSaved.toLocaleTimeString()}
              </span>
            )}
            {!isSaving && !error && !lastSaved && (
              <span className="text-xs text-muted-foreground">
                Not saved yet
              </span>
            )}
          </div>
        </div>
        <Button
          onClick={() => handleSave(false)}
          disabled={isSaving || loadFailed || !!conflict}
          busy={isSaving}
        >
          {isSaving ? 'Saving...' : 'Save'}
        </Button>
      </div>
        </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
