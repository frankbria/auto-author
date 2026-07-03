'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import Placeholder from '@tiptap/extension-placeholder';
import CharacterCount from '@tiptap/extension-character-count';
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
import bookClient from '@/lib/api/bookClient';
import { HugeiconsIcon } from '@hugeicons/react';
import {
  TextBoldIcon,
  TextItalicIcon,
  TextUnderlineIcon,
  Strikethrough,
  Heading01Icon,
  Heading02Icon,
  Heading03Icon,
  ListViewIcon,
  MenuSquareIcon,
  QuoteUpIcon,
  CodeIcon,
  Undo02Icon,
  Redo02Icon,
  MinusSignIcon,
  CheckmarkCircle01Icon,
  Loading03Icon
} from '@hugeicons/core-free-icons';
import { cn } from '@/lib/utils';
import { usePerformanceTracking } from '@/hooks/usePerformanceTracking';
import { useUserPreferences } from '@/hooks/useUserPreferences';
import { AUTO_SAVE_DEFAULT_SECONDS, isValidAutoSaveInterval } from '@/lib/constants/auto-save';
import { DraftGenerator } from './DraftGenerator';
import { StyleTransformer } from './StyleTransformer';
import { ContentEnhancer } from './ContentEnhancer';
import { VoiceEnhancer } from './VoiceEnhancer';
import QuestionContainer from './questions/QuestionContainer';
import { useRouter } from 'next/navigation';
import {
  validateChapterBackup,
  getValidatedItem,
  setValidatedItem,
  ChapterBackup,
} from '@/lib/storage/dataValidator';

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
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [autoSavePending, setAutoSavePending] = useState(false);
  const [lastAutoSavedContent, setLastAutoSavedContent] = useState(initialContent);
  const [hasBackup, setHasBackup] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
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
  // Default to the writing view. The saved per-chapter choice is restored in the
  // effect below (not the initializer) so it (a) re-runs when this editor is
  // reused for a different chapter — TabContent renders it without a key — and
  // (b) can't cause an SSR hydration mismatch.
  const [view, setView] = useState<'questions' | 'editor'>('editor');

  const handleViewChange = useCallback(
    (next: string) => {
      if (next !== 'questions' && next !== 'editor') return;
      setView(next);
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

  // Restore (or reset) the tab whenever the chapter changes.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const saved = sessionStorage.getItem(viewStorageKey);
      setView(saved === 'questions' || saved === 'editor' ? saved : 'editor');
    } catch {
      setView('editor');
    }
  }, [viewStorageKey]);

  // Keyboard access to the tabs is Radix's native arrow-key roving (WCAG tab
  // pattern) plus clicking. Ctrl+digit is intentionally NOT bound here — it is
  // owned by the ChapterTabs chapter quick-switch (Ctrl+1..9), so binding it to
  // the view toggle would hijack chapter navigation.

  const router = useRouter();

  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
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
      if (html !== lastAutoSavedContent) {
        setAutoSavePending(true);
        setHasUnsavedChanges(true);
      }
    },
    editorProps: {
      attributes: {
        class: 'focus:outline-none text-black',
      },
    },
    // Set this to false to avoid SSR hydration issues
    immediatelyRender: false,
  });

  // Check for localStorage backup on mount (with validation)
  useEffect(() => {
    const backupKey = `chapter-backup-${bookId}-${chapterId}`;
    const backup = getValidatedItem<ChapterBackup>(backupKey, validateChapterBackup);
    if (backup) {
      setHasBackup(true);
    }
  }, [bookId, chapterId]);

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

  // Load chapter content if no initial content provided
  useEffect(() => {
    const loadChapterContent = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const contentData = await bookClient.getChapterContent(bookId, chapterId);
        if (editor) {
          editor.commands.setContent(contentData.content || '');
          setLastAutoSavedContent(contentData.content || '');
        }
      } catch (err) {
        // Ignore tab state errors as they shouldn't affect the editor functionality
        if (err instanceof Error && !err.message.includes('Failed to get tab state')) {
          console.error('Failed to load chapter content:', err);
          setError('Failed to load chapter content');
        } else {
          console.warn('Tab state error occurred but content may still load:', err);
          // Continue loading with empty content in case of tab state errors
          if (editor) {
            editor.commands.setContent('');
            setLastAutoSavedContent('');
          }
        }
      } finally {
        setIsLoading(false);
      }
    };
    if (!initialContent && bookId && chapterId) {
      loadChapterContent();
    }
  }, [bookId, chapterId, initialContent, editor]);

  // Update content if initialContent changes
  useEffect(() => {
    if (editor && initialContent && editor.getHTML() !== initialContent) {
      editor.commands.setContent(initialContent);
      setLastAutoSavedContent(initialContent);
    }
  }, [initialContent, editor]);

  // Auto-save functionality with localStorage backup
  useEffect(() => {
    if (!autoSavePending || !editor || isSaving) return;

    const timer = setTimeout(async () => {
      const content = editor.getHTML();
      if (content === lastAutoSavedContent) return;

      setIsSaving(true);
      setError(null);
      try {
        await trackOperation('auto-save', async () => {
          return await bookClient.saveChapterContent(bookId, chapterId, content);
        }, { bookId, chapterId, contentLength: content.length });
        setLastSaved(new Date());
        setLastAutoSavedContent(content);
        setAutoSavePending(false);
        setHasUnsavedChanges(false);

        // Clear backup after successful save
        const backupKey = `chapter-backup-${bookId}-${chapterId}`;
        localStorage.removeItem(backupKey);
        setHasBackup(false);
      } catch (err) {
        console.error('Failed to auto-save chapter:', err);

        // Backup to localStorage on failure (with validation)
        try {
          const backupKey = `chapter-backup-${bookId}-${chapterId}`;
          const backup: ChapterBackup = {
            content,
            timestamp: Date.now(),
            error: err instanceof Error ? err.message : 'Unknown error'
          };
          const saved = setValidatedItem(backupKey, backup, validateChapterBackup);
          if (saved) {
            setHasBackup(true);
            setError('Failed to auto-save. Content backed up locally.');
          } else {
            setError('Failed to auto-save and backup chapter content');
          }
        } catch (storageErr) {
          console.error('Failed to backup to localStorage:', storageErr);
          setError('Failed to auto-save chapter content');
        }
      } finally {
        setIsSaving(false);
      }
    }, autoSaveDelayMs);

    return () => clearTimeout(timer);
  }, [autoSavePending, autoSaveDelayMs, bookId, chapterId, editor, isSaving, lastAutoSavedContent]);

  const handleSave = async (isAutoSave: boolean = false) => {
    if (isSaving || !editor) return;

    const content = editor.getHTML();
    setIsSaving(true);
    setError(null);

    try {
      await trackOperation('manual-save', async () => {
        return await bookClient.saveChapterContent(bookId, chapterId, content);
      }, { bookId, chapterId, contentLength: content.length });
      setLastSaved(new Date());
      setLastAutoSavedContent(content);
      setHasUnsavedChanges(false);

      // Clear backup after successful save
      const backupKey = `chapter-backup-${bookId}-${chapterId}`;
      localStorage.removeItem(backupKey);
      setHasBackup(false);

      if (onSave) {
        onSave(content);
      }
      if (!isAutoSave) {
        console.log('Chapter content saved successfully');
      }
    } catch (err) {
      console.error('Failed to save chapter:', err);
      setError('Failed to save chapter content');

      // Backup to localStorage on manual save failure too
      try {
        const backupKey = `chapter-backup-${bookId}-${chapterId}`;
        const backup: ChapterBackup = {
          content,
          timestamp: Date.now(),
          error: err instanceof Error ? err.message : 'Unknown error'
        };
        setValidatedItem(backupKey, backup, validateChapterBackup);
        setHasBackup(true);
      } catch (storageErr) {
        console.error('Failed to backup after manual save failure:', storageErr);
      }
    } finally {
      setIsSaving(false);
    }
  };

  const handleDraftGenerated = (draft: string) => {
    if (editor) {
      // Insert the draft at the current cursor position
      editor.chain().focus().insertContent(draft).run();
      // Trigger auto-save
      setAutoSavePending(true);
    }
  };

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

  const handleRecoverBackup = () => {
    const backupKey = `chapter-backup-${bookId}-${chapterId}`;
    const backup = getValidatedItem<ChapterBackup>(backupKey, validateChapterBackup);
    if (backup && editor) {
      try {
        editor.commands.setContent(backup.content);
        setAutoSavePending(true); // Trigger auto-save of recovered content
        setHasUnsavedChanges(true);
        setHasBackup(false);
        localStorage.removeItem(backupKey);
      } catch (err) {
        console.error('Failed to recover backup:', err);
        setError('Failed to recover backed up content');
      }
    }
  };

  const handleDismissBackup = () => {
    const backupKey = `chapter-backup-${bookId}-${chapterId}`;
    localStorage.removeItem(backupKey);
    setHasBackup(false);
  };

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="mt-2 text-sm text-muted-foreground">Loading chapter content...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {hasBackup && (
        <div className="bg-yellow-500/10 border border-yellow-500/20 text-yellow-700 dark:text-yellow-400 px-4 py-2 text-sm flex items-center justify-between">
          <span>A local backup of your content is available. Would you like to restore it?</span>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={handleRecoverBackup}
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
        </div>
      )}
      {error && (
        <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-2 text-sm">
          {error}
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
      <div className="border-b border-border p-1 bg-muted/30 flex flex-wrap gap-1 items-center justify-between">
        <div className="flex flex-wrap gap-1 items-center">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => editor?.chain().focus().toggleBold().run()}
          className={cn(
            'h-8 w-8 p-0',
            editor?.isActive('bold') ? 'bg-muted' : 'bg-transparent'
          )}
          title="Bold"
          type="button"
        >
          <HugeiconsIcon icon={TextBoldIcon} size={16} />
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => editor?.chain().focus().toggleItalic().run()}
          className={cn(
            'h-8 w-8 p-0',
            editor?.isActive('italic') ? 'bg-muted' : 'bg-transparent'
          )}
          title="Italic"
          type="button"
        >
          <HugeiconsIcon icon={TextItalicIcon} size={16} />
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => editor?.chain().focus().toggleUnderline().run()}
          className={cn(
            'h-8 w-8 p-0',
            editor?.isActive('underline') ? 'bg-muted' : 'bg-transparent'
          )}
          title="Underline"
          type="button"
        >
          <HugeiconsIcon icon={TextUnderlineIcon} size={16} />
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => editor?.chain().focus().toggleStrike().run()}
          className={cn(
            'h-8 w-8 p-0',
            editor?.isActive('strike') ? 'bg-muted' : 'bg-transparent'
          )}
          title="Strikethrough"
          type="button"
        >
          <HugeiconsIcon icon={Strikethrough} size={16} />
        </Button>

        <div className="w-px h-6 bg-border mx-1" />

        <Button
          variant="ghost"
          size="sm"
          onClick={() => editor?.chain().focus().toggleHeading({ level: 1 }).run()}
          className={cn(
            'h-8 w-8 p-0',
            editor?.isActive('heading', { level: 1 }) ? 'bg-muted' : 'bg-transparent'
          )}
          title="Heading 1"
          type="button"
        >
          <HugeiconsIcon icon={Heading01Icon} size={16} />
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()}
          className={cn(
            'h-8 w-8 p-0',
            editor?.isActive('heading', { level: 2 }) ? 'bg-muted' : 'bg-transparent'
          )}
          title="Heading 2"
          type="button"
        >
          <HugeiconsIcon icon={Heading02Icon} size={16} />
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => editor?.chain().focus().toggleHeading({ level: 3 }).run()}
          className={cn(
            'h-8 w-8 p-0',
            editor?.isActive('heading', { level: 3 }) ? 'bg-muted' : 'bg-transparent'
          )}
          title="Heading 3"
          type="button"
        >
          <HugeiconsIcon icon={Heading03Icon} size={16} />
        </Button>

        <div className="w-px h-6 bg-border mx-1" />

        <Button
          variant="ghost"
          size="sm"
          onClick={() => editor?.chain().focus().toggleBulletList().run()}
          className={cn(
            'h-8 w-8 p-0',
            editor?.isActive('bulletList') ? 'bg-muted' : 'bg-transparent'
          )}
          title="Bullet List"
          type="button"
        >
          <HugeiconsIcon icon={ListViewIcon} size={16} />
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => editor?.chain().focus().toggleOrderedList().run()}
          className={cn(
            'h-8 w-8 p-0',
            editor?.isActive('orderedList') ? 'bg-muted' : 'bg-transparent'
          )}
          title="Ordered List"
          type="button"
        >
          <HugeiconsIcon icon={MenuSquareIcon} size={16} />
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => editor?.chain().focus().toggleBlockquote().run()}
          className={cn(
            'h-8 w-8 p-0',
            editor?.isActive('blockquote') ? 'bg-muted' : 'bg-transparent'
          )}
          title="Blockquote"
          type="button"
        >
          <HugeiconsIcon icon={QuoteUpIcon} size={16} />
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => editor?.chain().focus().toggleCodeBlock().run()}
          className={cn(
            'h-8 w-8 p-0',
            editor?.isActive('codeBlock') ? 'bg-muted' : 'bg-transparent'
          )}
          title="Code Block"
          type="button"
        >
          <HugeiconsIcon icon={CodeIcon} size={16} />
        </Button>

        <div className="w-px h-6 bg-border mx-1" />

        <Button
          variant="ghost"
          size="sm"
          onClick={() => editor?.chain().focus().undo().run()}
          disabled={!editor?.can().chain().focus().undo().run()}
          className="h-8 w-8 p-0 bg-transparent"
          title="Undo"
          type="button"
        >
          <HugeiconsIcon icon={Undo02Icon} size={16} />
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => editor?.chain().focus().redo().run()}
          disabled={!editor?.can().chain().focus().redo().run()}
          className="h-8 w-8 p-0 bg-transparent"
          title="Redo"
          type="button"
        >
          <HugeiconsIcon icon={Redo02Icon} size={16} />
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => editor?.chain().focus().setHorizontalRule().run()}
          className="h-8 w-8 p-0 bg-transparent"
          title="Horizontal Rule"
          type="button"
        >
          <HugeiconsIcon icon={MinusSignIcon} size={16} />
        </Button>
        </div>

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
            {editor?.storage.characterCount.characters() ?? 0} characters
          </span>
          <div className="flex items-center gap-2">
            {isSaving && (
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <HugeiconsIcon icon={Loading03Icon} size={12} className="animate-spin" />
                Saving...
              </span>
            )}
            {!isSaving && lastSaved && (
              <span className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
                <HugeiconsIcon icon={CheckmarkCircle01Icon} size={12} />
                Saved {lastSaved.toLocaleTimeString()}
              </span>
            )}
            {!isSaving && !lastSaved && (
              <span className="text-xs text-muted-foreground">
                Not saved yet
              </span>
            )}
          </div>
        </div>
        <Button
          onClick={() => handleSave(false)}
          disabled={isSaving}
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
