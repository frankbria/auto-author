'use client';

import { useEffect, useCallback } from 'react';
import { useChapterTabs } from '@/hooks/useChapterTabs';
import { useTocSync } from '@/hooks/useTocSync';
import { TabBar } from './TabBar';
import { TabContent } from './TabContent';
import TabContextMenu from './TabContextMenu';

interface ChapterTabsProps {
  bookId: string;
  initialActiveChapter?: string;
  className?: string;
  orientation?: 'horizontal' | 'vertical';
}

export function ChapterTabs({ bookId, initialActiveChapter, className, orientation = 'vertical' }: ChapterTabsProps) {
  const {
    state,
    actions: {
      setActiveChapter,
      reorderTabs,
      closeTab,
      updateChapterStatus,
      saveTabState,
      refreshChapters
    },
    loading,
    error
  } = useChapterTabs(bookId, initialActiveChapter);

  // Set up TOC synchronization
  useTocSync({ 
    bookId, 
    onTocChanged: refreshChapters,
    pollInterval: 3000 // Poll every 3 seconds as fallback
  });

  const handleTabSelect = useCallback((chapterId: string) => {
    setActiveChapter(chapterId);
    saveTabState(); // Persist state
  }, [setActiveChapter, saveTabState]);

  const handleTabReorder = useCallback((sourceIndex: number, destinationIndex: number) => {
    reorderTabs(sourceIndex, destinationIndex);
  }, [reorderTabs]);

  // Keyboard navigation (Ctrl+1, Ctrl+2, etc.)
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.ctrlKey && event.key >= '1' && event.key <= '9') {
        event.preventDefault();
        const tabIndex = parseInt(event.key) - 1;
        const chapterId = state.tab_order[tabIndex];
        if (chapterId) {
          handleTabSelect(chapterId);
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [state.tab_order, handleTabSelect]);
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center">
          <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500 mb-2"></div>
          <p className="text-zinc-400">Loading chapters...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-900/20 border border-red-700 rounded-lg text-red-400">
        <h3 className="font-bold mb-1">Error loading chapters</h3>
        <p>{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-3 px-3 py-1 bg-red-800/40 hover:bg-red-800/70 text-red-200 text-sm rounded"
        >
          Retry
        </button>
      </div>
    );
  }  return (
    <div className={orientation === 'vertical' ? `flex h-full ${className}` : className}>
      <TabBar
        chapters={state.chapters}
        activeChapterId={state.active_chapter_id}
        tabOrder={state.tab_order}
        onTabSelect={handleTabSelect}
        onTabReorder={handleTabReorder}
        onTabClose={closeTab}
        orientation={orientation}
      />
      <TabContent
        bookId={bookId}
        activeChapterId={state.active_chapter_id}
        chapters={state.chapters}
        onContentChange={(chapterId, content) => {
          // Handle real-time content changes for auto-save
          console.log(`Content changed for chapter ${chapterId}: ${content.length} characters`);
        }}        onChapterSave={(chapterId) => {
          // Handle chapter save completion
          console.log(`Chapter ${chapterId} saved successfully`);
          saveTabState(); // Update tab state when content is saved
        }}
      />
      <TabContextMenu
        onStatusUpdate={updateChapterStatus}
        onDelete={(chapterId: string) => {
          console.log(`Delete chapter with ID: ${chapterId}`);
        }}
      />
    </div>
  );
}
