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
  'data-testid'?: string;
}

export function TabContent({ 
  bookId, 
  activeChapterId,
  chapters,
  onContentChange,
  onChapterSave,
  'data-testid': testId
}: TabContentProps) {  
  if (!activeChapterId) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <h3 className="text-lg font-medium mb-2 text-foreground">No Chapter Selected</h3>
          <p className="text-muted-foreground">Select a chapter tab to begin editing</p>
        </div>
      </div>
    );
  }

  // Find the active chapter to get its title
  const activeChapter = chapters.find(ch => ch.id === activeChapterId);
  const chapterTitle = activeChapter?.title || 'Untitled Chapter';

  return (
    <div className="flex-1 overflow-hidden" data-testid={testId}>
      <ErrorBoundary fallback={<div>Something went wrong with this chapter</div>}>
        <ChapterEditor
          bookId={bookId}
          chapterId={activeChapterId}
          chapterTitle={chapterTitle}
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
