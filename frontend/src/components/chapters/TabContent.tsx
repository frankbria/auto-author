'use client';

import { useState, useEffect } from 'react';
import { ChapterTabMetadata } from '@/types/chapter-tabs';
import { chapterTabsApi } from '@/lib/api/chapter-tabs';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { ErrorBoundary } from '@/components/ui/error-boundary';
import { ChapterEditor } from './ChapterEditor';

interface TabContentProps {
  bookId: string;
  activeChapterId: string | null;
  chapters: ChapterTabMetadata[];
}

export function TabContent({ bookId, activeChapterId }: TabContentProps) {
  const [chapterContent, setChapterContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!activeChapterId) return;

    const loadChapterContent = async () => {
      setLoading(true);
      setError(null);      try {
        const content = await chapterTabsApi.getChapterContent(bookId, activeChapterId);
        setChapterContent(content);
      } catch (error) {
        console.error('Failed to load chapter content:', error);
        setError('Failed to load chapter content');
      } finally {
        setLoading(false);
      }
    };

    loadChapterContent();
  }, [bookId, activeChapterId]);

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

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center text-destructive">
          <h3 className="text-lg font-medium mb-2">Error Loading Chapter</h3>
          <p>{error}</p>
          <button 
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-md"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-hidden">
      <ErrorBoundary fallback={<div>Something went wrong with this chapter</div>}>        <ChapterEditor
          bookId={bookId}
          chapterId={activeChapterId}
          initialContent={chapterContent || ''}
          onSave={(content: string) => {
            // Handle content save
            console.log('Chapter content saved:', content);
          }}
        />
      </ErrorBoundary>
    </div>
  );
}