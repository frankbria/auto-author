'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import bookClient from '@/lib/api/bookClient';

interface ChapterEditorProps {
  bookId: string;
  chapterId: string;
  initialContent?: string;
  onSave?: (content: string) => void;
  onContentChange?: (content: string) => void;
}

export function ChapterEditor({ 
  bookId, 
  chapterId, 
  initialContent = '', 
  onSave,
  onContentChange
}: ChapterEditorProps) {
  const [content, setContent] = useState(initialContent);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  // Load chapter content if no initial content provided
  useEffect(() => {
    const loadChapterContent = async () => {
      setIsLoading(true);
      setError(null);
        try {
        const contentData = await bookClient.getChapterContent(bookId, chapterId);
        setContent(contentData.content || '');
      } catch (err) {
        console.error('Failed to load chapter content:', err);
        setError('Failed to load chapter content');
      } finally {
        setIsLoading(false);
      }
    };

    if (!initialContent && bookId && chapterId) {
      loadChapterContent();
    }
  }, [bookId, chapterId, initialContent]);

  // Auto-save functionality
  useEffect(() => {
    if (!content || content === initialContent) return;    const handleAutoSave = async () => {
      if (isSaving) return;
      
      setIsSaving(true);
      setError(null);
      
      try {
        await bookClient.saveChapterContent(bookId, chapterId, content);
        setLastSaved(new Date());
      } catch (err) {
        console.error('Failed to auto-save chapter:', err);
        setError('Failed to auto-save chapter content');
      } finally {
        setIsSaving(false);
      }
    };

    const autoSaveTimer = setTimeout(() => {
      handleAutoSave();
    }, 3000); // Auto-save after 3 seconds of inactivity

    return () => clearTimeout(autoSaveTimer);
  }, [content, initialContent, bookId, chapterId, isSaving]);
  // Notify parent of content changes
  useEffect(() => {
    if (onContentChange) {
      onContentChange(content);
    }
  }, [content, onContentChange]);
  const handleSave = async (isAutoSave: boolean = false) => {
    if (isSaving) return;
    
    setIsSaving(true);
    setError(null);
    
    try {
      await bookClient.saveChapterContent(bookId, chapterId, content);
      setLastSaved(new Date());
      
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

  const handleContentChange = (newContent: string) => {
    setContent(newContent);
    if (error) setError(null); // Clear error when user types
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
      )}      <div className="flex-1 p-4">
        <Textarea
          value={content}
          onChange={(e) => handleContentChange(e.target.value)}
          placeholder="Start writing your chapter content..."
          className="h-full min-h-[500px] resize-none bg-background text-foreground border-border focus:border-ring"
        />
      </div>      <div className="border-t border-border p-4 flex justify-between items-center bg-muted/20">
        <div className="flex items-center gap-4">
          <span className="text-sm text-foreground">
            {content.length} characters
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
