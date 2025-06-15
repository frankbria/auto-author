'use client';

import { useEffect, useState } from 'react';
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
import bookClient from '@/lib/api/bookClient';
import {
  Bold,
  Italic,
  Underline as UnderlineIcon,
  Strikethrough,
  Heading1,
  Heading2,
  Heading3,
  List,
  ListOrdered,
  Quote,
  Code,
  Undo,
  Redo,
  Minus
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { DraftGenerator } from './DraftGenerator';

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
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [autoSavePending, setAutoSavePending] = useState(false);
  const [lastAutoSavedContent, setLastAutoSavedContent] = useState(initialContent);
  
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

  // Auto-save functionality
  useEffect(() => {
    if (!autoSavePending || !editor || isSaving) return;
    
    const timer = setTimeout(async () => {
      const content = editor.getHTML();
      if (content === lastAutoSavedContent) return;
      
      setIsSaving(true);
      setError(null);
      try {
        await bookClient.saveChapterContent(bookId, chapterId, content);
        setLastSaved(new Date());
        setLastAutoSavedContent(content);
        setAutoSavePending(false);
      } catch (err) {
        console.error('Failed to auto-save chapter:', err);
        setError('Failed to auto-save chapter content');
      } finally {
        setIsSaving(false);
      }
    }, 3000);
    
    return () => clearTimeout(timer);
  }, [autoSavePending, bookId, chapterId, editor, isSaving, lastAutoSavedContent]);

  const handleSave = async (isAutoSave: boolean = false) => {
    if (isSaving || !editor) return;
    
    const content = editor.getHTML();
    setIsSaving(true);
    setError(null);
    
    try {
      await bookClient.saveChapterContent(bookId, chapterId, content);
      setLastSaved(new Date());
      setLastAutoSavedContent(content);
      if (onSave) {
        onSave(content);
      }
      if (!isAutoSave) {
        console.log('Chapter content saved successfully');
      }
    } catch (err) {
      console.error('Failed to save chapter:', err);
      setError('Failed to save chapter content');
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
      {error && (
        <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-2 text-sm">
          {error}
        </div>
      )}
      
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
          <Bold className="h-4 w-4" />
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
          <Italic className="h-4 w-4" />
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
          <UnderlineIcon className="h-4 w-4" />
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
          <Strikethrough className="h-4 w-4" />
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
          <Heading1 className="h-4 w-4" />
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
          <Heading2 className="h-4 w-4" />
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
          <Heading3 className="h-4 w-4" />
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
          <List className="h-4 w-4" />
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
          <ListOrdered className="h-4 w-4" />
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
          <Quote className="h-4 w-4" />
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
          <Code className="h-4 w-4" />
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
          <Undo className="h-4 w-4" />
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
          <Redo className="h-4 w-4" />
        </Button>
        
        <Button
          variant="ghost"
          size="sm"
          onClick={() => editor?.chain().focus().setHorizontalRule().run()}
          className="h-8 w-8 p-0 bg-transparent"
          title="Horizontal Rule"
          type="button"
        >
          <Minus className="h-4 w-4" />
        </Button>
        </div>
        
        {/* AI Draft Generator */}
        <DraftGenerator
          bookId={bookId}
          chapterId={chapterId}
          chapterTitle={chapterTitle}
          onDraftGenerated={handleDraftGenerated}
        />
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
          {lastSaved && (
            <span className="text-xs text-muted-foreground">
              Last saved: {lastSaved.toLocaleTimeString()}
            </span>
          )}
        </div>
        <Button
          onClick={() => handleSave(false)}
          disabled={isSaving}
        >
          {isSaving ? 'Saving...' : 'Save'}
        </Button>
      </div>
    </div>
  );
}
