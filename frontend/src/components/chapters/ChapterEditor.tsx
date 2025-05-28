'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

interface ChapterEditorProps {
  bookId: string;
  chapterId: string;
  initialContent?: string;
  onSave?: (content: string) => void;
}

export function ChapterEditor({ 
  bookId, 
  chapterId, 
  initialContent = '', 
  onSave 
}: ChapterEditorProps) {
  const [content, setContent] = useState(initialContent);
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    try {      // TODO: Implement actual save logic
      if (onSave) {
        onSave(content);
      }
      console.log('Saving content for chapter:', chapterId, 'in book:', bookId);
    } catch (error) {
      console.error('Failed to save chapter:', error);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 p-4">
        <Textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Start writing your chapter content..."
          className="h-full min-h-[500px] resize-none"
        />
      </div>
      <div className="border-t p-4 flex justify-between items-center">
        <span className="text-sm text-muted-foreground">
          {content.length} characters
        </span>
        <Button 
          onClick={handleSave} 
          disabled={isSaving}
        >
          {isSaving ? 'Saving...' : 'Save'}
        </Button>
      </div>
    </div>
  );
}
