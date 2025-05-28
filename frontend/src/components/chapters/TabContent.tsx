'use client';

import { ChapterTabMetadata } from '@/types/chapter-tabs';
import { ErrorBoundary } from '@/components/ui/error-boundary';
import { ChapterEditor } from './ChapterEditor';

interface TabContentProps {
  bookId: string;
  activeChapterId: string | null;
  chapters: ChapterTabMetadata[];
  onContentChange?: (chapterId: string, content: string) => void;
  onChapterSave?: (chapterId: string, content: string) => void;
}

export function TabContent({ 
  bookId, 
  activeChapterId, 
  onContentChange,
  onChapterSave 
}: TabContentProps) {
  if (!activeChapterId) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <div className="text-center">
          <h3 className="text-lg font-medium mb-2">No Chapter Selected</h3>
          <p>Select a chapter tab to begin editing</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-hidden">
      <ErrorBoundary fallback={<div>Something went wrong with this chapter</div>}>
        <ChapterEditor
          bookId={bookId}
          chapterId={activeChapterId}
          onSave={(content: string) => {
            if (onChapterSave) {
              onChapterSave(activeChapterId, content);
            }
          }}
          onContentChange={(content: string) => {
            if (onContentChange) {
              onContentChange(activeChapterId, content);
            }
          }}
        />
      </ErrorBoundary>
    </div>
  );
}